"""Offline integration checks for evidence-card publication and ownership.

Fixtures are synthetic contracts, not evidence of model quality or real videos.
No provider or PostgreSQL connection is used.
"""

import asyncio
import hashlib
import json
import tempfile
import unittest
import uuid
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from app.core.config import Settings
from app.runtime import library
from app.runtime.store import Store, StoreError
from app.runtime.worker import Worker
from app.schemas.structure_card import StructureCard
from app.schemas.video import VideoAnalysis
from app.services import retrieval


def evidence_card(*, status="pending", origin="vision_llm"):
    return StructureCard.model_validate(
        {
            "id": str(uuid.uuid4()),
            "schema_version": 2,
            "pattern_name": "Synthetic evidence fixture",
            "summary": "A fixture for publication and provenance checks.",
            "hook_type": "product-detail",
            "narrative_flow": "detail then invitation",
            "visual_style": "product close-up",
            "editing_atoms": [{"kind": "hook", "duration_seconds": 2}],
            "reusable_rules": ["Open with the product."],
            "source_video_job_id": "upload-fixture",
            "source_segments": ["scene_000"],
            "created_at": "2026-09-30T00:00:00Z",
            "origin": origin,
            "evidence_frames": [
                {
                    "index": 0,
                    "timestamp_seconds": 0,
                    "url": "https://untrusted.example/model-supplied.jpg",
                }
            ],
            "observations": [
                {
                    "id": "observation-1",
                    "aspect": "hook",
                    "start_seconds": 0,
                    "end_seconds": 2,
                    "frame_indices": [0],
                    "source_segments": ["scene_000"],
                    "observation": "A product fills the first frame.",
                }
            ],
            "rules": [
                {
                    "id": "rule-1",
                    "instruction": "Open with the product.",
                    "evidence_ids": ["observation-1"],
                }
            ],
            "review": {"status": status},
            "analysis": {
                "mode": "vision",
                "model": "offline-fixture",
                "frame_count": 1,
                "prompt_version": "reference-evidence-v2",
            },
        }
    )


class ReferenceLibraryTests(unittest.TestCase):
    def test_only_approved_evidence_cards_are_published_from_catalog(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            catalog = root / "packages/reference-library/cards"
            catalog.mkdir(parents=True)
            cards = [
                evidence_card(status=s) for s in ("approved", "pending", "rejected")
            ]
            for card in cards:
                (catalog / f"{card.id}.json").write_text(card.model_dump_json())
            store = Store(root / "data")
            with patch.object(library, "REPO_ROOT", root):
                library.seed_library(store)
                library.seed_library(store)
            public = store.resources("", "card", True)
            public_ids = {card["id"] for card in public}
            self.assertIn(cards[0].id, public_ids)
            self.assertNotIn(cards[1].id, public_ids)
            self.assertNotIn(cards[2].id, public_ids)
            self.assertEqual(len(public), len(library.PATTERNS) + 1)
            self.assertEqual(store.card_index_owner("alice", cards[0].id), "__public__")
            with self.assertRaises(StoreError):
                store.resource("alice", cards[0].id, "card", allow_public=False)

    def test_withdrawn_or_deleted_catalog_cards_lose_visibility_only_when_managed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            catalog = root / "packages/reference-library/cards"
            catalog.mkdir(parents=True)
            cards = [evidence_card(status="approved") for _ in range(4)]
            for card in cards:
                (catalog / f"{card.id}.json").write_text(card.model_dump_json())
            store = Store(root / "data")
            with patch.object(library, "REPO_ROOT", root):
                library.seed_library(store)
                starter_ids = {
                    card["id"]
                    for card in store.resources("", "card", True)
                    if card["origin"] == "curated"
                }
                # Neither an independently published card nor a private card
                # is owned by the bundled catalog, even with a similar origin.
                manual = evidence_card(status="approved").model_dump(mode="json")
                store.put_resource("__public__", "card", manual, public=True)
                private = evidence_card().model_dump(mode="json")
                private["_reference_catalog"] = library._CATALOG_MARKER
                store.put_resource("alice", "card", private)
                for card, status in zip(cards[:2], ("pending", "rejected")):
                    card.review.status = status
                    (catalog / f"{card.id}.json").write_text(card.model_dump_json())
                (catalog / f"{cards[2].id}.json").unlink()
                library.seed_library(store)
            visible = {card["id"] for card in store.resources("", "card", True)}
            self.assertEqual(visible, starter_ids | {cards[3].id, manual["id"]})
            self.assertEqual(store.resource("alice", private["id"], "card"), private)
            for withdrawn in cards[:3]:
                with self.assertRaises(StoreError):
                    store.resource("bob", withdrawn.id, "card", allow_public=True)
                with self.assertRaises(StoreError):
                    store.card_index_owner("bob", withdrawn.id)

            # Simulate pgvector still returning the former public IDs. SQLite
            # must revoke access immediately, without needing the remote DB.
            settings = Settings(
                _env_file=None,
                data_dir=str(root / "data"),
                database_url="offline-not-connected",
                embedding_api_key="offline-fixture",
                embedding_model="offline-fixture",
            )
            stale_hits = [card.model_dump(mode="json") for card in cards]
            with (
                patch.object(retrieval, "existing_hash", return_value=None),
                patch.object(
                    retrieval,
                    "embed",
                    new=AsyncMock(return_value=([1.0] + [0.0] * 1023, {})),
                ),
                patch.object(retrieval, "upsert"),
                patch.object(retrieval, "query", return_value=stale_hits),
            ):
                result = asyncio.run(
                    retrieval.search_cards(
                        settings, store, {"id": "bob", "quota": 3}, "coffee"
                    )
                )
            self.assertEqual(result["mode"], "semantic")
            self.assertEqual([card["id"] for card in result["cards"]], [cards[3].id])

    def test_search_uses_stored_visibility_and_discards_stale_private_hits(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = Store(Path(tmp))
            public = evidence_card(status="approved").model_dump(mode="json")
            # A private card's descriptive origin must never grant public access.
            own = evidence_card(origin="curated").model_dump(mode="json")
            other = evidence_card().model_dump(mode="json")
            store.put_resource("__public__", "card", public, public=True)
            store.put_resource("alice", "card", own)
            store.put_resource("bob", "card", other)
            with self.assertRaises(StoreError):
                store.card_index_owner("alice", other["id"])
            settings = Settings(
                _env_file=None,
                data_dir=tmp,
                database_url="offline-not-connected",
                embedding_api_key="offline-fixture",
                embedding_model="offline-fixture",
            )
            vector = [1.0] + [0.0] * 1023
            with (
                patch.object(retrieval, "existing_hash", return_value=None),
                patch.object(
                    retrieval, "embed", new=AsyncMock(return_value=(vector, {}))
                ),
                patch.object(retrieval, "upsert") as upsert,
                patch.object(retrieval, "query", return_value=[other, public, own]),
            ):
                result = asyncio.run(
                    retrieval.search_cards(
                        settings, store, {"id": "alice", "quota": 3}, "coffee"
                    )
                )
            self.assertEqual(result["mode"], "semantic")
            self.assertEqual(
                [c["id"] for c in result["cards"]], [public["id"], own["id"]]
            )
            indexed_owners = {
                call.args[1]["id"]: call.args[2] for call in upsert.call_args_list
            }
            self.assertEqual(
                indexed_owners, {public["id"]: "__public__", own["id"]: "alice"}
            )

    def test_learning_passes_local_frames_and_archives_each_owned_extraction(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            store = Store(root)
            source = root / "uploads/upload-fixture/original.mp4"
            source.parent.mkdir(parents=True)
            source.write_bytes(b"fixture bytes; video decoding is mocked")
            analysis = VideoAnalysis(
                id="analysis-fixture",
                job_id="upload-fixture",
                source_video_path=source.relative_to(root).as_posix(),
                duration_seconds=2,
                fps=30,
                width=64,
                height=64,
                total_frames=60,
                file_size_bytes=source.stat().st_size,
                frames=[
                    {
                        "index": 0,
                        "timestamp_seconds": 0,
                        "path": "frames/upload-fixture/frame_000.jpg",
                    }
                ],
                scenes=[{"id": "scene_000", "start_seconds": 0, "end_seconds": 2}],
                scene_detection_method="time_based",
                created_at="2026-09-30T00:00:00Z",
            )
            store.put_resource(
                "alice",
                "upload",
                {
                    "id": analysis.job_id,
                    "original_filename": "My private product.mp4",
                    "saved_path": analysis.source_video_path,
                    "frames": [
                        {"timestamp_seconds": 0, "url": "/api/media/owned-frame"}
                    ],
                },
            )
            settings = Settings(
                _env_file=None, data_dir=tmp, seed_model="offline-vision"
            )
            worker = Worker(settings, store)
            cards = [evidence_card(), evidence_card()]
            client = SimpleNamespace(last_usage={"total_tokens": 1}, aclose=AsyncMock())
            job = {
                "owner": "alice",
                "kind": "learn",
                "payload": {"resource_id": analysis.job_id},
            }
            with (
                patch.object(worker, "analyze", new=AsyncMock(return_value=analysis)),
                patch("app.runtime.worker.get_llm_client", return_value=client),
                patch(
                    "app.runtime.worker.extract_structure_card",
                    new=AsyncMock(side_effect=cards),
                ) as extract,
            ):
                first = asyncio.run(worker.execute(job))
                archive = (
                    root
                    / "knowledge_base"
                    / analysis.job_id
                    / "cards"
                    / f"{first['id']}.json"
                )
                first_bytes = archive.read_bytes()
                second = asyncio.run(worker.execute(job))
            self.assertEqual(extract.await_count, 2)
            for call in extract.await_args_list:
                self.assertEqual(call.args, (analysis, client))
                self.assertEqual(
                    call.kwargs, {"data_dir": root, "model_name": "offline-vision"}
                )
            self.assertEqual(client.aclose.await_count, 2)
            self.assertEqual(archive.read_bytes(), first_bytes)
            second_archive = archive.with_name(f"{second['id']}.json")
            self.assertTrue(second_archive.is_file())
            compatibility = (
                root / "knowledge_base" / analysis.job_id / "structure_card.json"
            )
            self.assertEqual(json.loads(compatibility.read_text())["id"], second["id"])
            self.assertEqual(first["source"]["media_url"], "/api/media/upload-fixture")
            self.assertEqual(
                first["source"]["sha256"],
                hashlib.sha256(source.read_bytes()).hexdigest(),
            )
            self.assertEqual(
                first["evidence_frames"][0]["url"], "/api/media/owned-frame"
            )
            self.assertEqual(
                store.resource("alice", first["id"], "card")["review"]["status"],
                "pending",
            )
            self.assertEqual(store.resources("bob", "card", True), [])
