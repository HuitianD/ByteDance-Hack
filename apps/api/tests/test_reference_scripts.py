"""Offline crash recovery and immutable-provenance checks for reference tools."""

import importlib.util
import json
import os
import stat
import tempfile
import unittest
from datetime import timedelta
from pathlib import Path
from unittest.mock import Mock, patch

import httpx

from app.runtime.store import Store
from app.schemas.structure_card import StructureCard
from app.schemas.video import VideoAnalysis

ROOT = Path(__file__).resolve().parents[3]


def load_script(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


builder = load_script("build_reference_library")
reviewer = load_script("review_reference")


def fixture(root):
    store = Store(root / "data")
    store.put_resource("alice", "upload", {"id": "source", "saved_path": "unused.mp4"})
    state = {
        "token": "offline-private-token",
        "items": {"showcase": {"upload_id": "source", "sha256": "fixture"}},
    }
    path = root / "state.private.json"
    builder.save(path, state, True)
    return store, state, path


def completed_job(store, *, owner="alice", upload="source", kind="learn", failed=False):
    job = store.enqueue(owner, kind, {"resource_id": upload}, 3, 3, 2)
    store.finish(
        job["id"],
        owner,
        result={"fixture": True},
        error="offline failure" if failed else None,
    )
    return job["id"]


def response(job_id):
    return httpx.Response(
        202,
        json={"id": job_id},
        request=httpx.Request("POST", "https://example.test/api/jobs"),
    )


class ReferenceScriptTests(unittest.TestCase):
    def test_private_json_replace_is_atomic_restricted_and_cleans_failed_temporary(
        self,
    ):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "state.private.json"
            builder.save(path, {"token": "old-secret"}, True)
            replace = os.replace

            def inspect_and_replace(source, destination):
                self.assertEqual(stat.S_IMODE(Path(source).stat().st_mode), 0o600)
                self.assertEqual(json.loads(path.read_text())["token"], "old-secret")
                self.assertEqual(
                    json.loads(Path(source).read_text())["token"], "new-secret"
                )
                replace(source, destination)

            with patch.object(builder.os, "replace", side_effect=inspect_and_replace):
                builder.save(path, {"token": "new-secret"}, True)
            self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)
            self.assertEqual(json.loads(path.read_text())["token"], "new-secret")
            with patch.object(
                builder.os, "replace", side_effect=OSError("interrupted")
            ):
                with self.assertRaises(OSError):
                    builder.save(path, {"token": "partial-secret"}, True)
            self.assertEqual(json.loads(path.read_text())["token"], "new-secret")
            self.assertEqual(list(path.parent.glob(".*.tmp")), [])

    def test_intent_is_durable_before_post_and_completed_job_is_not_resubmitted(self):
        with tempfile.TemporaryDirectory() as temp:
            store, state, path = fixture(Path(temp))
            client = Mock()

            def post(*args, **kwargs):
                disk = json.loads(path.read_text())
                self.assertEqual(
                    disk["items"]["showcase"]["submission_state"], "submitting"
                )
                self.assertNotIn("job_id", disk["items"]["showcase"])
                self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)
                return response(completed_job(store))

            client.post.side_effect = post
            item = state["items"]["showcase"]
            jid = builder.ensure_learn_job(
                client, store, "alice", item, state, path, allow_paid=True
            )
            self.assertEqual(
                builder.ensure_learn_job(
                    client, store, "alice", item, state, path, allow_paid=False
                ),
                jid,
            )
            client.post.assert_called_once()
            self.assertEqual(
                json.loads(path.read_text())["items"]["showcase"]["job_id"], jid
            )

    def test_lost_post_response_or_final_save_recovers_terminal_task_without_post(self):
        for interrupted_at in ("response", "save"):
            for failed in (False, True):
                with self.subTest(
                    interrupted_at=interrupted_at, failed=failed
                ), tempfile.TemporaryDirectory() as temp:
                    store, state, path = fixture(Path(temp))
                    client = Mock()
                    accepted = []

                    def post(*args, **kwargs):
                        jid = completed_job(store, failed=failed)
                        accepted.append(jid)
                        if interrupted_at == "response":
                            raise httpx.ReadTimeout("lost response")
                        return response(jid)

                    client.post.side_effect = post
                    original_save = builder.save
                    saves = 0

                    def save_until_interruption(*args, **kwargs):
                        nonlocal saves
                        saves += 1
                        if interrupted_at == "save" and saves == 2:
                            raise OSError("exit before saving accepted ID")
                        return original_save(*args, **kwargs)

                    with patch.object(
                        builder, "save", side_effect=save_until_interruption
                    ):
                        with self.assertRaises((httpx.ReadTimeout, OSError)):
                            builder.ensure_learn_job(
                                client,
                                store,
                                "alice",
                                state["items"]["showcase"],
                                state,
                                path,
                                allow_paid=True,
                            )
                    recovered = json.loads(path.read_text())
                    self.assertEqual(
                        recovered["items"]["showcase"]["submission_state"], "submitting"
                    )
                    no_post = Mock()
                    jid = builder.ensure_learn_job(
                        no_post,
                        store,
                        "alice",
                        recovered["items"]["showcase"],
                        recovered,
                        path,
                        allow_paid=False,
                    )
                    self.assertEqual(jid, accepted[0])
                    no_post.post.assert_not_called()
                    client.post.assert_called_once()

    def test_uncertain_unmatched_or_ambiguous_submission_never_posts(self):
        for scenario in ("unmatched", "ambiguous", "foreign_cached_id"):
            with self.subTest(scenario=scenario), tempfile.TemporaryDirectory() as temp:
                store, state, path = fixture(Path(temp))
                item = state["items"]["showcase"]
                client = Mock()
                # None of these may be mistaken for this owner's source learn task.
                foreign_id = completed_job(store, owner="bob")
                completed_job(store, upload="other-source")
                completed_job(store, kind="analyze")
                if scenario == "unmatched":
                    item["submission_state"] = "submitting"
                elif scenario == "ambiguous":
                    completed_job(store)
                    completed_job(store)
                else:
                    item["job_id"] = foreign_id
                builder.save(path, state, True)
                with self.assertRaises(SystemExit):
                    builder.ensure_learn_job(
                        client, store, "alice", item, state, path, allow_paid=True
                    )
                client.post.assert_not_called()

    def test_matching_terminal_job_recovers_even_without_old_submission_marker(self):
        with tempfile.TemporaryDirectory() as temp:
            store, state, path = fixture(Path(temp))
            jid = completed_job(store)
            client = Mock()
            actual = builder.ensure_learn_job(
                client,
                store,
                "alice",
                state["items"]["showcase"],
                state,
                path,
                allow_paid=False,
            )
            self.assertEqual(actual, jid)
            client.post.assert_not_called()

    def test_review_edits_cannot_rewrite_extraction_provenance(self):
        catalog = ROOT / "packages/reference-library"
        original = StructureCard.model_validate_json(
            (catalog / "extractions/showcase.json").read_text()
        )
        analysis = VideoAnalysis.model_validate_json(
            (catalog / "analyses/showcase.json").read_text()
        )
        edits = {
            "id": "forged-id",
            "source_video_job_id": "another-upload",
            "origin": "curated",
            "schema_version": 1,
            "version": original.version + 1,
            "created_at": original.created_at + timedelta(seconds=1),
            "source": original.source.model_copy(update={"title": "unrelated source"}),
            "evidence_frames": [],
            "analysis": original.analysis.model_copy(
                update={"model": "different-model"}
            ),
            "review": original.review.model_copy(
                update={"status": "approved", "method": "human"}
            ),
        }
        for field, value in edits.items():
            with self.subTest(field=field):
                altered = original.model_copy(update={field: value}, deep=True)
                with self.assertRaises(SystemExit):
                    reviewer.validate_review_provenance(altered, original, analysis)
        # Interpretation edits remain possible without a new extraction or model call.
        interpretation = original.model_copy(
            update={"summary": "Reviewed interpretation."}, deep=True
        )
        reviewer.validate_review_provenance(interpretation, original, analysis)
        wrong_analysis = analysis.model_copy(update={"job_id": "another-upload"})
        with self.assertRaises(SystemExit):
            reviewer.validate_review_provenance(original, original, wrong_analysis)

    def test_approve_current_preserves_corrections_and_increments_only_temporary_catalog(
        self,
    ):
        source_catalog = ROOT / "packages/reference-library"
        raw_bytes = (source_catalog / "extractions/showcase.json").read_bytes()
        analysis_bytes = (source_catalog / "analyses/showcase.json").read_bytes()
        current = StructureCard.model_validate_json(
            (source_catalog / "cards/showcase.json").read_text()
        )
        current.rules[0].instruction = "Keep this corrected, evidence-backed rule."
        current.reusable_rules = [rule.instruction for rule in current.rules]
        current.summary = "Corrected interpretation that must survive another review."
        with tempfile.TemporaryDirectory() as temp:
            catalog = Path(temp)
            for directory in ("extractions", "analyses", "cards", "reviews/showcase"):
                (catalog / directory).mkdir(parents=True)
            (catalog / "extractions/showcase.json").write_bytes(raw_bytes)
            (catalog / "analyses/showcase.json").write_bytes(analysis_bytes)
            previous_body = current.model_dump_json()
            (catalog / "cards/showcase.json").write_text(previous_body)
            old_history = catalog / "reviews/showcase" / f"v{current.version}.json"
            old_history.write_text(previous_body)
            arguments = [
                "review_reference.py",
                "showcase",
                "--approve-current",
                "--method",
                "human",
                "--reviewer",
                "Offline reviewer fixture",
                "--notes",
                "Offline test only.",
                "--status",
                "approved",
            ]
            with (
                patch.object(reviewer, "CATALOG", catalog),
                patch.object(reviewer.sys, "argv", arguments),
                patch("builtins.print"),
            ):
                reviewer.main()
            published = StructureCard.model_validate_json(
                (catalog / "cards/showcase.json").read_text()
            )
            self.assertEqual(published.rules, current.rules)
            self.assertEqual(published.reusable_rules, current.reusable_rules)
            self.assertEqual(published.summary, current.summary)
            self.assertEqual(published.version, current.version + 1)
            self.assertEqual(published.id, current.id)
            self.assertEqual(published.source, current.source)
            self.assertEqual(published.analysis, current.analysis)
            self.assertEqual(published.evidence_frames, current.evidence_frames)
            self.assertEqual(published.review.method, "human")
            self.assertEqual(published.review.reviewer, "Offline reviewer fixture")
            self.assertEqual(
                (catalog / "extractions/showcase.json").read_bytes(), raw_bytes
            )
            self.assertEqual(old_history.read_text(), previous_body)
            self.assertTrue(
                (catalog / "reviews/showcase" / f"v{published.version}.json").is_file()
            )


if __name__ == "__main__":
    unittest.main()
