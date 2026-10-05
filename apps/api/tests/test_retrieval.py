"""Real pgvector integration; explicitly synthetic vectors test SQL, not semantics."""

import asyncio
import os
import tempfile
import unittest
import uuid
from pathlib import Path
from unittest.mock import patch
import psycopg
from app.core.config import Settings
from app.runtime.store import Store
from app.services import retrieval
from app.services.storyboard import generate_storyboard
from app.schemas.structure_card import StructureCard
from app.llm.mock_client import MockClient
from test_core import make_card


@unittest.skipUnless(
    os.getenv("TEST_DATABASE_URL"), "Isolated pgvector test database not configured"
)
class RetrievalTests(unittest.TestCase):
    def test_migration_upsert_cosine_permissions_and_storyboard_lineage(self):
        settings = Settings(
            _env_file=None,
            database_url=os.environ["TEST_DATABASE_URL"],
            embedding_api_key="contract-only",
            embedding_model="test-" + str(uuid.uuid4()),
        )
        retrieval.migrate(settings)
        a, b, c, private = [make_card().model_dump(mode="json") for _ in range(4)]
        vectors = [
            [1.0, 0.0] + [0.0] * 1022,
            [0.9, 0.1] + [0.0] * 1022,
            [0.0, 1.0] + [0.0] * 1022,
            [1.0, 0.0] + [0.0] * 1022,
        ]
        try:
            for card, owner, v in zip(
                [a, b, c, private], ["__public__", "alice", "alice", "bob"], vectors
            ):
                retrieval.upsert(settings, card, owner, v, "test-hash")
            hits = retrieval.query(settings, "alice", vectors[0])
            self.assertEqual([r["id"] for r in hits], [a["id"], b["id"], c["id"]])
            self.assertNotIn(private["id"], [r["id"] for r in hits])
            self.assertEqual(
                retrieval.query(settings, "alice", vectors[2])[0]["id"], c["id"]
            )
            # An attempted ownership change cannot replace another user's card.
            retrieval.upsert(
                settings,
                {**private, "summary": "forged"},
                "alice",
                vectors[0],
                "forged",
            )
            self.assertEqual(
                retrieval.existing_hash(settings, private["id"])[0], "test-hash"
            )
            board = asyncio.run(
                generate_storyboard(
                    user_prompt="Coffee",
                    target_duration_seconds=15,
                    cards=[StructureCard.model_validate(x) for x in hits],
                    llm_client=MockClient(),
                    target_media_job_id=str(uuid.uuid4()),
                )
            )
            self.assertTrue(
                set(board.source_structure_card_ids).issubset({x["id"] for x in hits})
            )
            self.assertTrue(
                all(
                    s.source_structure_card_id in {x["id"] for x in hits}
                    for s in board.scenes
                )
            )
        finally:
            with psycopg.connect(settings.database_url) as db:
                db.execute(
                    "DELETE FROM viralcraft_cards WHERE embedding_model=%s",
                    (settings.embedding_model,),
                )


class RetrievalFallbackTests(unittest.TestCase):
    def test_unconfigured_and_unavailable_fallback_to_owned_and_public_cards(self):
        with tempfile.TemporaryDirectory() as t:
            store = Store(Path(t))
            a = make_card().model_dump(mode="json")
            b = make_card().model_dump(mode="json")
            store.put_resource("alice", "card", a)
            store.put_resource("bob", "card", b)
            settings = Settings(_env_file=None)
            result = asyncio.run(
                retrieval.search_cards(
                    settings, store, {"id": "alice", "quota": 3}, "coffee"
                )
            )
            self.assertEqual(result["mode"], "manual")
            self.assertEqual([x["id"] for x in result["cards"]], [a["id"]])
            configured = settings.model_copy(
                update={"database_url": "test", "embedding_api_key": "test"}
            )
            with patch.object(
                retrieval, "existing_hash", side_effect=RuntimeError("database down")
            ):
                result = asyncio.run(
                    retrieval.search_cards(
                        configured, store, {"id": "alice", "quota": 3}, "coffee"
                    )
                )
                self.assertEqual(result["mode"], "manual")
