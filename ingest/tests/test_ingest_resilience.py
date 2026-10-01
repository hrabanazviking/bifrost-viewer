"""Local ingest regressions; mocks avoid modifying the knowledge store."""
import os
import importlib.util
from pathlib import Path
import unittest
from unittest.mock import MagicMock, patch

spec = importlib.util.spec_from_file_location("bifrost_ingest_test", Path(__file__).resolve().parents[1] / "ingest.py")
ingest = importlib.util.module_from_spec(spec)
with patch.dict(os.environ, {"INGEST_DB_URL": "postgresql:///unused", "OLLAMA_URL": "http://127.0.0.1:9", "INGEST_EMBED_MODEL": "test-model"}):
    spec.loader.exec_module(ingest)


class IngestResilienceTests(unittest.TestCase):
    def client(self, vectors):
        client = MagicMock()
        client.__enter__.return_value = client
        client.post.return_value.json.return_value = {"embeddings": vectors}
        return client

    def test_incomplete_embedding_batch_is_rejected(self):
        with patch.object(ingest.httpx, "Client", return_value=self.client([[1, 2]])):
            with self.assertRaises(ValueError):
                ingest.embed(["one", "two"])

    def test_nonfinite_embedding_is_rejected(self):
        with patch.object(ingest.httpx, "Client", return_value=self.client([[float("nan"), 1]])):
            with self.assertRaises(ValueError):
                ingest.embed(["one"])

    def test_batches_preserve_count_and_order(self):
        client = self.client([[1, 2]])
        client.post.return_value.json.side_effect = [
            {"embeddings": [[1, 2], [3, 4]]}, {"embeddings": [[5, 6]]},
        ]
        with patch.dict(os.environ, {"INGEST_EMBED_BATCH_SIZE": "2"}), patch.object(ingest.httpx, "Client", return_value=client):
            self.assertEqual(ingest.embed(["one", "two", "three"]), [[1, 2], [3, 4], [5, 6]])
        self.assertEqual(client.post.call_count, 2)

    def test_unicode_jsonl_is_preserved(self):
        self.assertEqual(ingest._jsonl_record_to_text({"text": "Sigrún\\nBifröst"}), "Sigrún\nBifröst")

    def test_existing_document_skips_embedding(self):
        connection = MagicMock()
        connection.__enter__.return_value = connection
        cursor = connection.cursor.return_value.__enter__.return_value
        cursor.fetchone.return_value = (42,)
        with patch.object(ingest, "parse_source", return_value=("title", "md", ["text"])), patch.object(ingest, "get_conn", return_value=connection), patch.object(ingest, "embed") as embed:
            ingest.add("test.md")
        embed.assert_not_called()
        cursor.executemany.assert_not_called()


if __name__ == "__main__":
    unittest.main()
