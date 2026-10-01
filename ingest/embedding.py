"""Validate every vector and adapt failing batches without dropping any text."""
from __future__ import annotations

import logging

import httpx
import numpy as np

from recovery import TemporaryFailure, delay, progress, setting

log = logging.getLogger("ingest.embedding")


def validated(payload: object, count: int) -> np.ndarray:
    try:
        vectors = np.asarray(payload, dtype=np.float32)
    except (ValueError, TypeError):
        raise TemporaryFailure("Embedding response contains malformed vectors") from None
    if vectors.ndim != 2 or len(vectors) != count or not vectors.shape[1]:
        raise TemporaryFailure("Embedding response has an incomplete batch")
    if not np.isfinite(vectors).all() or not np.all(np.any(vectors, axis=1)):
        raise TemporaryFailure("Embedding response contains invalid vectors")
    return vectors


def request_batch(client: httpx.Client, url: str, model: str, texts: list[str], budget: list[int] | None = None) -> np.ndarray:
    attempts = setting("embed_attempts")
    budget = budget if budget is not None else [setting("embed_request_budget")]
    for attempt in range(attempts):
        if budget[0] <= 0:
            raise TemporaryFailure("Adaptive embedding request budget exhausted")
        budget[0] -= 1
        try:
            response = client.post(f"{url}/api/embed", json={"model": model, "input": texts},
                                   timeout=setting("embed_timeout_seconds"))
            response.raise_for_status()
            payload = response.json()
            return validated(payload.get("embeddings") if isinstance(payload, dict) else None, len(texts))
        except (httpx.HTTPError, TemporaryFailure, ValueError, TypeError) as exc:
            permanent = isinstance(exc, httpx.HTTPStatusError) and exc.response.status_code not in (408, 429) and exc.response.status_code < 500
            if permanent:
                raise
            if attempt + 1 == attempts:
                if len(texts) > 1 and not isinstance(exc, httpx.TransportError):
                    middle = len(texts) // 2
                    log.warning("Embedding batch split count=%s; preserving every input", len(texts))
                    left = request_batch(client, url, model, texts[:middle], budget)
                    right = request_batch(client, url, model, texts[middle:], budget)
                    if left.shape[1] != right.shape[1]:
                        raise TemporaryFailure("Embedding dimensions changed between split batches")
                    return np.concatenate((left, right))
                raise TemporaryFailure("Embedding service retry budget exhausted") from None
            log.warning("Embedding request deferred kind=%s attempt=%s", type(exc).__name__, attempt + 1)
            delay(attempt)
    raise TemporaryFailure("Embedding retry budget exhausted")


def embed_all(client: httpx.Client, url: str, model: str, texts: list[str]) -> list[list[float]]:
    result, dimension = [], None
    batch_size = setting("embed_batch_size")
    for start in range(0, len(texts), batch_size):
        vectors = request_batch(client, url, model, texts[start:start + batch_size])
        if dimension is not None and vectors.shape[1] != dimension:
            raise TemporaryFailure("Embedding dimensions changed between batches")
        dimension = vectors.shape[1]
        result.extend(vectors.tolist())
        progress("embedding", .2 + .6 * len(result) / len(texts), chunks=len(texts), embedded=len(result))
    return result
