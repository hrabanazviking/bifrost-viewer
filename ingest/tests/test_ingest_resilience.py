"""Fault-oriented parser checks never modify the user's knowledge store."""
import os
import importlib.util
from pathlib import Path
import tempfile
import subprocess
import sys
import unittest
from unittest.mock import MagicMock, patch

import httpx
import psycopg

spec = importlib.util.spec_from_file_location("bifrost_ingest_test", Path(__file__).resolve().parents[1] / "ingest.py")
ingest = importlib.util.module_from_spec(spec)
with patch.dict(os.environ, {"INGEST_DB_URL": "postgresql:///unused", "OLLAMA_URL": "http://127.0.0.1:9", "INGEST_EMBED_MODEL": "test-model"}):
    spec.loader.exec_module(ingest)
import recovery  # noqa: E402


class IngestResilienceTests(unittest.TestCase):
    def setUp(self):
        self.settings = patch.dict(os.environ, {"INGEST_EMBED_ATTEMPTS": "1"})
        self.settings.start()
        self.addCleanup(self.settings.stop)

    def client(self, vectors):
        client = MagicMock()
        client.__enter__.return_value = client
        client.post.return_value.json.return_value = {"embeddings": vectors}
        return client

    def test_incomplete_singleton_embedding_is_rejected(self):
        with patch.object(ingest.httpx, "Client", return_value=self.client([])):
            with self.assertRaises(recovery.TemporaryFailure):
                ingest.embed(["one", "two"])

    def test_nonfinite_embedding_is_rejected(self):
        with patch.object(ingest.httpx, "Client", return_value=self.client([[float("nan"), 1]])):
            with self.assertRaises(recovery.TemporaryFailure):
                ingest.embed(["one"])

    def test_batches_preserve_count_and_order(self):
        client = self.client([])
        client.post.return_value.json.side_effect = [
            {"embeddings": [[1, 2], [3, 4]]}, {"embeddings": [[5, 6]]},
        ]
        with patch.dict(os.environ, {"INGEST_EMBED_BATCH_SIZE": "2"}), patch.object(ingest.httpx, "Client", return_value=client):
            self.assertEqual(ingest.embed(["one", "two", "three"]), [[1, 2], [3, 4], [5, 6]])
        self.assertEqual(client.post.call_count, 2)

    def test_failed_large_batch_splits_and_preserves_order(self):
        client = self.client([])
        client.post.return_value.json.side_effect = [
            {"embeddings": []}, {"embeddings": [[1, 2]]}, {"embeddings": [[3, 4]]},
        ]
        with patch.object(ingest.httpx, "Client", return_value=client):
            self.assertEqual(ingest.embed(["one", "two"]), [[1, 2], [3, 4]])
        self.assertEqual([call.kwargs["json"]["input"] for call in client.post.call_args_list], [["one", "two"], ["one"], ["two"]])

    def test_adaptive_request_budget_is_bounded(self):
        client = self.client([])
        with patch.dict(os.environ, {"INGEST_EMBED_REQUEST_BUDGET": "2"}), patch.object(ingest.httpx, "Client", return_value=client):
            with self.assertRaises(recovery.TemporaryFailure, msg="No endless split tree"):
                ingest.embed(["one", "two", "three", "four"])
        self.assertEqual(client.post.call_count, 2)

    def test_permanent_http_error_is_not_retried(self):
        client = self.client([])
        response = httpx.Response(404, request=httpx.Request("POST", "http://model/api/embed"))
        client.post.side_effect = httpx.HTTPStatusError("missing", request=response.request, response=response)
        with patch.object(ingest.httpx, "Client", return_value=client):
            with self.assertRaises(httpx.HTTPStatusError):
                ingest.embed(["one", "two"])
        self.assertEqual(client.post.call_count, 1)

    def test_wrong_response_shape_is_a_temporary_failure(self):
        client = self.client([])
        client.post.return_value.json.return_value = []
        with patch.object(ingest.httpx, "Client", return_value=client):
            with self.assertRaises(recovery.TemporaryFailure):
                ingest.embed(["one"])

    def test_dimensions_cannot_change_between_batches(self):
        client = self.client([])
        client.post.return_value.json.side_effect = [{"embeddings": [[1, 2]]}, {"embeddings": [[1, 2, 3]]}]
        with patch.dict(os.environ, {"INGEST_EMBED_BATCH_SIZE": "1"}), patch.object(ingest.httpx, "Client", return_value=client):
            with self.assertRaises(recovery.TemporaryFailure):
                ingest.embed(["one", "two"])

    def test_unicode_jsonl_is_preserved(self):
        self.assertEqual(ingest._jsonl_record_to_text({"text": "Sigrún\\nBifröst"}), "Sigrún\nBifröst")

    def test_api_text_preserves_characters_across_chunk_boundaries(self):
        text = "Sigrún 🌈\n  Þórr\tBifröst\n" * 200
        chunks = ingest._text_chunks(text)
        restored = chunks[0] + "".join(chunk[200:] for chunk in chunks[1:])
        self.assertEqual(restored, text)

    def test_help_does_not_require_credentials(self):
        result = subprocess.run([sys.executable, str(MODULE_PATH := Path(ingest.__file__)), "--help"], env={"PATH": os.environ["PATH"], "INGEST_ENV_FILE": str(MODULE_PATH.parent / "missing-test.env")}, capture_output=True, text=True, timeout=20)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("doctor", result.stdout)

    def test_invalid_jsonl_is_not_silently_partially_imported(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "invalid.jsonl"
            path.write_text('{"text":"first"}\n{"bad":\n')
            with patch.object(ingest, "_persist") as persist, self.assertRaisesRegex(recovery.InputFailure, "line 2"):
                ingest.add(str(path))
            persist.assert_not_called()

    def test_changed_source_is_detected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "changing.txt"
            path.write_text("first")
            signature = recovery.source_signature(str(path))
            path.write_text("replacement")
            with self.assertRaises(recovery.TemporaryFailure):
                recovery.check_source(str(path), signature)

    def test_existing_document_skips_embedding(self):
        with patch.object(ingest, "source_signature", return_value=None), patch.object(ingest, "parse_source", return_value=("title", "md", ["text"])), patch.object(ingest, "_existing_document", return_value=42), patch.object(ingest, "embed") as embed:
            ingest.add("test.md")
        embed.assert_not_called()

    def test_api_append_records_server_assigned_provenance(self):
        connection = MagicMock()
        connection.__enter__.return_value = connection
        cursor = connection.cursor.return_value.__enter__.return_value
        cursor.fetchone.return_value = (42,)
        env = {"INGEST_API_JOB_ID": "job123", "INGEST_API_CLIENT_ID": "client123", "INGEST_SUBMISSION_TITLE": "Submitted document"}
        with patch.dict(os.environ, env), patch.object(ingest, "source_signature", return_value=None), patch.object(ingest, "parse_source", return_value=("uuid.txt", "txt", ["text"])), patch.object(ingest, "_existing_document", return_value=None), patch.object(ingest, "_target_dimension", return_value=2), patch.object(ingest, "get_conn", return_value=connection), patch.object(ingest, "embed", return_value=[[1, 2]]):
            ingest.add("/private/payload.txt")
        insert = cursor.execute.call_args_list[0].args
        self.assertEqual(insert[1][0], "bifrost-api://client123/job123")
        self.assertEqual(insert[1][1], "Submitted document")
        self.assertEqual(insert[1][4].obj, {"api_job_id": "job123", "api_client_id": "client123"})
        connection.commit.assert_called_once()

    def test_wrong_model_dimension_never_reaches_insert(self):
        with patch.object(ingest, "source_signature", return_value=None), patch.object(ingest, "parse_source", return_value=("title", "txt", ["text"])), patch.object(ingest, "_existing_document", return_value=None), patch.object(ingest, "_target_dimension", return_value=768), patch.object(ingest, "embed", return_value=[[1, 2]]), patch.object(ingest, "_persist") as persist:
            with self.assertRaises(recovery.ConfigurationFailure):
                ingest.add("unused.txt")
        persist.assert_not_called()

    def test_transaction_retry_reuses_prepared_embeddings(self):
        with patch.object(ingest, "source_signature", return_value=None), patch.object(ingest, "parse_source", return_value=("title", "txt", ["text"])), patch.object(ingest, "_existing_document", return_value=None), patch.object(ingest, "_target_dimension", return_value=2), patch.object(ingest, "embed", return_value=[[1, 2]]) as embed, patch.object(ingest, "_persist", side_effect=[psycopg.errors.SerializationFailure(), 42]) as persist, patch.object(recovery, "delay"):
            ingest.add("unused.txt")
        embed.assert_called_once()
        self.assertEqual(persist.call_count, 2)
        self.assertEqual(persist.call_args_list[0], persist.call_args_list[1])

    def test_permanent_database_error_is_not_retried(self):
        operation = MagicMock(side_effect=psycopg.errors.InsufficientPrivilege())
        with self.assertRaises(psycopg.errors.InsufficientPrivilege):
            recovery.database_retry(operation)
        operation.assert_called_once()

    def test_misconfiguration_is_classified(self):
        with patch.dict(os.environ, {"INGEST_EMBED_BATCH_SIZE": "0"}):
            with self.assertRaises(recovery.ConfigurationFailure) as caught:
                recovery.setting("embed_batch_size")
        self.assertEqual(recovery.failure(caught.exception), (22, "configuration"))


if __name__ == "__main__":
    unittest.main()
