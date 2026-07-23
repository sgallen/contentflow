from __future__ import annotations

import contextlib
import io
import json
import os
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

import sys

sys.path.insert(0, str(ROOT / "src"))

from content_flow.cli import initialize_data_root, load_state, main
from content_flow.vault import load_item, render_item


class VaultCLITests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.base = Path(self.temporary.name)
        self.data_root = self.base / "private"
        initialize_data_root(self.data_root, ROOT)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def run_cli(self, *arguments: str) -> tuple[int, str, str]:
        stdout, stderr = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            result = main([*arguments, "--data-dir", str(self.data_root)], root=ROOT)
        return result, stdout.getvalue(), stderr.getvalue()

    def capture(self, title: str = "Example idea", *extra: str) -> str:
        result, stdout, stderr = self.run_cli(
            "vault",
            "capture",
            "--kind",
            "idea",
            "--title",
            title,
            *extra,
        )
        self.assertEqual((result, stderr), (0, ""))
        return next(line.split(": ", 1)[1] for line in stdout.splitlines() if line.startswith("item_id: "))

    def finalize(self, run_path: Path) -> None:
        (run_path / "final.md").write_text("# Final\n", encoding="utf-8")
        state_path = run_path / "run.json"
        state = json.loads(state_path.read_text(encoding="utf-8"))
        state["artifacts"]["final"] = "final.md"
        state_path.write_text(json.dumps(state), encoding="utf-8")
        result, _, stderr = self.run_cli("vault", "finalize-run", run_path.name)
        self.assertEqual((result, stderr), (0, ""))

    def start(self, *arguments: str) -> Path:
        result, stdout, stderr = self.run_cli("new-run", *arguments)
        self.assertEqual((result, stderr), (0, ""))
        return Path(next(line.split(": ", 1)[1] for line in stdout.splitlines() if line.startswith("run: ")))

    def test_quick_capture_preserves_url_reason_and_minimal_metadata(self) -> None:
        exact_url = "https://example.test/watch?v=A%2FB&x=1"
        item_id = self.capture(
            "Useful video",
            "--url",
            exact_url,
            "--note",
            "It may explain a recurring team problem.",
        )
        path = self.data_root / "vault" / "items" / f"{item_id}.md"
        metadata, body = load_item(path)
        self.assertEqual(metadata["source_url"], exact_url)
        self.assertEqual(metadata["status"], "inbox")
        self.assertEqual(metadata["use_count"], 0)
        self.assertEqual(metadata["successful_runs"], [])
        self.assertEqual(metadata["final_artifacts"], [])
        self.assertIn("It may explain a recurring team problem.", body)
        self.assertIn(exact_url, body)
        self.assertIn("## Mining notes", body)

    def test_item_filename_and_id_are_safe_and_capture_never_overwrites(self) -> None:
        first = self.capture(" Café / 東京 ")
        second = self.capture(" Café / 東京 ")
        self.assertRegex(first, r"^\d{4}-\d{2}-\d{2}-cafe$")
        self.assertEqual(second, first + "-2")
        self.assertTrue((self.data_root / "vault" / "items" / f"{first}.md").is_file())
        self.assertTrue((self.data_root / "vault" / "items" / f"{second}.md").is_file())

    def test_capture_uses_content_flow_home(self) -> None:
        environment_root = self.base / "environment"
        initialize_data_root(environment_root, ROOT)
        previous = os.environ.get("CONTENT_FLOW_HOME")
        os.environ["CONTENT_FLOW_HOME"] = str(environment_root)
        try:
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                result = main(
                    ["vault", "capture", "--kind", "observation", "--title", "Environment item"],
                    root=ROOT,
                )
        finally:
            if previous is None:
                os.environ.pop("CONTENT_FLOW_HOME", None)
            else:
                os.environ["CONTENT_FLOW_HOME"] = previous
        self.assertEqual(result, 0)
        self.assertEqual(len(list((environment_root / "vault" / "items").glob("*.md"))), 1)
        self.assertEqual(len(list((self.data_root / "vault" / "items").glob("*.md"))), 0)

    def test_list_filters_by_status_kind_and_tag(self) -> None:
        ready = self.capture("Ready source", "--tag", "teams")
        self.capture("Other idea", "--tag", "other")
        self.run_cli("vault", "update", ready, "--status", "ready")
        result, stdout, _ = self.run_cli(
            "vault",
            "list",
            "--status",
            "ready",
            "--kind",
            "idea",
            "--tag",
            "teams",
        )
        self.assertEqual(result, 0)
        self.assertIn(ready, stdout)
        self.assertNotIn("Other idea", stdout)
        self.assertIn("SUCCESSFUL_USES", stdout)

    def test_status_and_revisit_updates_reject_invalid_values_and_transitions(self) -> None:
        item_id = self.capture()
        result, _, _ = self.run_cli(
            "vault", "update", item_id, "--status", "ready", "--revisit-after", "2026-08-10"
        )
        self.assertEqual(result, 0)
        metadata, _ = load_item(self.data_root / "vault" / "items" / f"{item_id}.md")
        self.assertEqual(metadata["status"], "ready")
        self.assertEqual(metadata["revisit_after"], "2026-08-10")
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaisesRegex(SystemExit, "2"):
            main(
                [
                    "vault",
                    "update",
                    item_id,
                    "--status",
                    "ancient",
                    "--data-dir",
                    str(self.data_root),
                ],
                root=ROOT,
            )

    def test_index_is_generated_deterministically_and_detects_staleness(self) -> None:
        item_id = self.capture("Indexed")
        result, _, _ = self.run_cli("vault", "rebuild-index")
        self.assertEqual(result, 0)
        index = self.data_root / "vault" / "index.md"
        first = index.read_text(encoding="utf-8")
        self.run_cli("vault", "rebuild-index")
        self.assertEqual(index.read_text(encoding="utf-8"), first)
        self.assertIn(f"(items/{item_id}.md)", first)
        index.write_text("# manually damaged\n", encoding="utf-8")
        result, _, stderr = self.run_cli("vault", "validate")
        self.assertEqual(result, 1)
        self.assertIn("malformed or stale", stderr)

    def test_malformed_item_and_duplicate_id_are_detected(self) -> None:
        first = self.capture("First")
        path = self.data_root / "vault" / "items" / f"{first}.md"
        metadata, body = load_item(path)
        metadata["kind"] = "unsupported"
        path.write_text(render_item(metadata, body), encoding="utf-8")
        result, _, stderr = self.run_cli("vault", "rebuild-index")
        self.assertEqual(result, 2)
        self.assertIn("vault kind must be one of", stderr)

        metadata["kind"] = "idea"
        duplicate = self.data_root / "vault" / "items" / "different.md"
        duplicate.write_text(render_item(metadata, body), encoding="utf-8")
        path.write_text(render_item(metadata, body), encoding="utf-8")
        result, _, stderr = self.run_cli("vault", "rebuild-index")
        self.assertEqual(result, 2)
        self.assertIn("duplicate vault item id", stderr)

    def test_validation_detects_bad_timestamp_duplicate_links_and_missing_active_run(self) -> None:
        item_id = self.capture("Broken relationships")
        path = self.data_root / "vault" / "items" / f"{item_id}.md"
        metadata, body = load_item(path)
        metadata["updated_at"] = "2026-99-99T99:99:99Z"
        metadata["status"] = "developing"
        metadata["related_runs"] = ["missing-run", "missing-run"]
        path.write_text(render_item(metadata, body), encoding="utf-8")
        result, _, stderr = self.run_cli("vault", "validate")
        self.assertEqual(result, 1)
        self.assertIn("real UTC calendar timestamp", stderr)
        self.assertIn("related_runs must not contain duplicates", stderr)

        metadata["updated_at"] = metadata["captured_at"]
        metadata["related_runs"] = ["missing-run"]
        path.write_text(render_item(metadata, body), encoding="utf-8")
        self.run_cli("vault", "rebuild-index")
        result, _, stderr = self.run_cli("vault", "validate")
        self.assertEqual(result, 1)
        self.assertIn("developing item references missing active run", stderr)

    def test_run_validation_detects_missing_item_and_invalid_parked_state(self) -> None:
        _, stdout, _ = self.run_cli("new-run", "--title", "Bad parked run")
        run_path = Path(next(line.split(": ", 1)[1] for line in stdout.splitlines() if line.startswith("run: ")))
        state_path = run_path / "run.json"
        state = json.loads(state_path.read_text(encoding="utf-8"))
        state["origin_vault_items"] = ["missing-item"]
        state["linked_vault_items"] = ["missing-item"]
        state["status"] = "parked"
        state["pending_human_action"] = "none"
        state["parking_reason"] = ""
        state["parked_at"] = "not-a-time"
        state_path.write_text(json.dumps(state), encoding="utf-8")
        result, _, stderr = self.run_cli("validate", run_path.name)
        self.assertEqual(result, 1)
        self.assertIn("parking_reason", stderr)
        self.assertIn("parked_at", stderr)
        self.assertIn("run references missing vault item", stderr)

    def test_start_run_from_one_item_preserves_bidirectional_provenance(self) -> None:
        item_id = self.capture("Run source", "--material", "A useful raw detail")
        result, stdout, stderr = self.run_cli("new-run", "--vault-item", item_id)
        self.assertEqual((result, stderr), (0, ""))
        run_path = Path(next(line.split(": ", 1)[1] for line in stdout.splitlines() if line.startswith("run: ")))
        state = load_state(run_path)
        self.assertEqual(state["origin_vault_items"], [item_id])
        self.assertEqual(state["linked_vault_items"], [item_id])
        metadata, _ = load_item(self.data_root / "vault" / "items" / f"{item_id}.md")
        self.assertEqual(metadata["status"], "developing")
        self.assertIn(run_path.name, metadata["related_runs"])
        self.assertIn(item_id, (run_path / "spike.md").read_text(encoding="utf-8"))
        result, _, _ = self.run_cli("validate", run_path.name)
        self.assertEqual(result, 0)

    def test_start_run_from_multiple_items_records_roles(self) -> None:
        origin = self.capture("Origin")
        contributor = self.capture("Contributor")
        result, stdout, _ = self.run_cli(
            "new-run",
            "--title",
            "Combined",
            "--vault-item",
            origin,
            "--contributing-vault-item",
            contributor,
        )
        self.assertEqual(result, 0)
        run_path = Path(next(line.split(": ", 1)[1] for line in stdout.splitlines() if line.startswith("run: ")))
        state = load_state(run_path)
        self.assertEqual(state["origin_vault_items"], [origin])
        self.assertEqual(state["contributing_vault_items"], [contributor])
        self.assertEqual(state["linked_vault_items"], [origin, contributor])

    def test_park_origin_run_updates_existing_item_without_duplicate(self) -> None:
        item_id = self.capture("Park me")
        _, stdout, _ = self.run_cli("new-run", "--vault-item", item_id)
        run_path = Path(next(line.split(": ", 1)[1] for line in stdout.splitlines() if line.startswith("run: ")))
        assessment = self.base / "assessment.md"
        assessment.write_text(
            "## What remains promising\n\nThe example.\n\n"
            "## Strongest material collected\n\nA concrete phrase.\n\n"
            "## Why it is not being completed\n\nNot distinctive yet.\n\n"
            "## What is missing\n\nLived experience.\n\n"
            "## Recommended next step\n\nRevisit after the project.\n\n"
            "## Resume or reconsider\n\nReconsider from a new angle.\n",
            encoding="utf-8",
        )
        result, _, _ = self.run_cli(
            "vault",
            "park-run",
            run_path.name,
            "--reason",
            "Needs lived experience",
            "--assessment-file",
            str(assessment),
        )
        self.assertEqual(result, 0)
        self.assertEqual(len(list((self.data_root / "vault" / "items").glob("*.md"))), 1)
        state = load_state(run_path)
        self.assertEqual(state["status"], "parked")
        self.assertEqual(state["pending_human_action"], "none")
        metadata, body = load_item(self.data_root / "vault" / "items" / f"{item_id}.md")
        self.assertEqual(metadata["status"], "parked")
        self.assertIn("Needs lived experience", body)

    def test_park_unlinked_run_creates_one_run_fragment_and_resume_restores_state(self) -> None:
        result, stdout, _ = self.run_cli("new-run", "--title", "Unlinked")
        self.assertEqual(result, 0)
        run_path = Path(next(line.split(": ", 1)[1] for line in stdout.splitlines() if line.startswith("run: ")))
        result, _, _ = self.run_cli("vault", "park-run", run_path.name, "--reason", "Timing")
        self.assertEqual(result, 0)
        items = list((self.data_root / "vault" / "items").glob("*.md"))
        self.assertEqual(len(items), 1)
        metadata, _ = load_item(items[0])
        self.assertEqual((metadata["kind"], metadata["status"]), ("run-fragment", "parked"))
        result, _, _ = self.run_cli("vault", "resume-run", run_path.name)
        self.assertEqual(result, 0)
        state = load_state(run_path)
        self.assertEqual((state["status"], state["pending_human_action"]), ("awaiting_human", "provide_idea_details"))
        metadata, _ = load_item(items[0])
        self.assertEqual(metadata["status"], "developing")

    def test_finalize_returns_all_linked_items_ready_and_records_successful_usage(self) -> None:
        origin = self.capture("Direct")
        contributor = self.capture("Supporting")
        run_path = self.start(
            "--title",
            "Final link",
            "--vault-item",
            origin,
            "--contributing-vault-item",
            contributor,
        )
        self.finalize(run_path)
        origin_meta, _ = load_item(self.data_root / "vault" / "items" / f"{origin}.md")
        contributor_meta, _ = load_item(self.data_root / "vault" / "items" / f"{contributor}.md")
        self.assertEqual(origin_meta["status"], "ready")
        self.assertEqual(contributor_meta["status"], "ready")
        for metadata in (origin_meta, contributor_meta):
            self.assertEqual(metadata["successful_runs"], [run_path.name])
            self.assertEqual(metadata["use_count"], 1)
            self.assertEqual(
                metadata["final_artifacts"],
                [f"runs/{run_path.name}/final.md"],
            )
            self.assertIsNotNone(metadata["last_used_at"])
        result, _, stderr = self.run_cli("vault", "finalize-run", run_path.name)
        self.assertEqual((result, stderr), (0, ""))
        origin_meta, _ = load_item(self.data_root / "vault" / "items" / f"{origin}.md")
        self.assertEqual((origin_meta["use_count"], len(origin_meta["successful_runs"])), (1, 1))
        self.assertEqual(load_state(run_path)["final_artifact"], "final.md")
        result, _, _ = self.run_cli("vault", "validate")
        self.assertEqual(result, 0)

    def test_same_source_and_idea_can_complete_multiple_distinct_runs(self) -> None:
        source = self.capture("Reusable source")
        first = self.start("--title", "First angle", "--vault-item", source)
        self.finalize(first)
        metadata, _ = load_item(self.data_root / "vault" / "items" / f"{source}.md")
        self.assertEqual((metadata["status"], metadata["use_count"]), ("ready", 1))

        second = self.start("--title", "Second angle", "--vault-item", source)
        metadata, _ = load_item(self.data_root / "vault" / "items" / f"{source}.md")
        self.assertEqual((metadata["status"], metadata["use_count"]), ("developing", 1))
        self.finalize(second)
        metadata, _ = load_item(self.data_root / "vault" / "items" / f"{source}.md")
        self.assertEqual(metadata["status"], "ready")
        self.assertEqual(metadata["related_runs"], [first.name, second.name])
        self.assertEqual(metadata["successful_runs"], [first.name, second.name])
        self.assertEqual(metadata["use_count"], 2)
        self.assertEqual(
            metadata["final_artifacts"],
            [f"runs/{first.name}/final.md", f"runs/{second.name}/final.md"],
        )
        result, _, _ = self.run_cli("vault", "validate")
        self.assertEqual(result, 0)

    def test_successful_item_can_be_parked_and_resumed_without_losing_history(self) -> None:
        item_id = self.capture("Proven idea")
        completed = self.start("--title", "Completed angle", "--vault-item", item_id)
        self.finalize(completed)
        parked = self.start("--title", "Third angle", "--vault-item", item_id)
        result, _, _ = self.run_cli("vault", "park-run", parked.name, "--reason", "Needs evidence")
        self.assertEqual(result, 0)
        metadata, _ = load_item(self.data_root / "vault" / "items" / f"{item_id}.md")
        self.assertEqual((metadata["status"], metadata["use_count"]), ("parked", 1))
        self.assertEqual(metadata["successful_runs"], [completed.name])
        result, _, _ = self.run_cli("vault", "resume-run", parked.name)
        self.assertEqual(result, 0)
        metadata, _ = load_item(self.data_root / "vault" / "items" / f"{item_id}.md")
        self.assertEqual((metadata["status"], metadata["use_count"]), ("developing", 1))

    def test_parked_or_abandoned_run_does_not_increase_use_count(self) -> None:
        item_id = self.capture("Attempted angle")
        run_path = self.start("--vault-item", item_id)
        result, _, _ = self.run_cli("vault", "park-run", run_path.name, "--reason", "Not ready")
        self.assertEqual(result, 0)
        metadata, _ = load_item(self.data_root / "vault" / "items" / f"{item_id}.md")
        self.assertEqual(metadata["related_runs"], [run_path.name])
        self.assertEqual(metadata["successful_runs"], [])
        self.assertEqual(metadata["use_count"], 0)
        self.assertNotIn("last_used_at", metadata)

    def test_completed_content_can_contribute_to_a_later_run(self) -> None:
        item_id = self.capture("Completed-content provenance")
        completed = self.start("--title", "Original content", "--vault-item", item_id)
        self.finalize(completed)
        later = self.start(
            "--title",
            "Follow-up",
            "--contributing-vault-item",
            item_id,
        )
        state = load_state(later)
        self.assertEqual(state["contributing_vault_items"], [item_id])
        spike = (later / "spike.md").read_text(encoding="utf-8")
        self.assertIn(f"runs/{completed.name}/final.md", spike)
        self.assertIn("Successful uses: 1", spike)

    def test_archived_item_remains_archived_when_linked_run_is_finalized(self) -> None:
        item_id = self.capture("Archive after selection")
        run_path = self.start("--vault-item", item_id)
        result, _, _ = self.run_cli("vault", "update", item_id, "--status", "archived")
        self.assertEqual(result, 0)
        self.finalize(run_path)
        metadata, _ = load_item(self.data_root / "vault" / "items" / f"{item_id}.md")
        self.assertEqual(metadata["status"], "archived")
        self.assertEqual(metadata["use_count"], 1)

    def test_index_and_list_surface_successful_reusable_and_rich_sources(self) -> None:
        result, stdout, stderr = self.run_cli(
            "vault",
            "capture",
            "--kind",
            "source",
            "--title",
            "Rich source",
        )
        self.assertEqual((result, stderr), (0, ""))
        item_id = next(line.split(": ", 1)[1] for line in stdout.splitlines() if line.startswith("item_id: "))
        for title in ("Angle one", "Angle two"):
            run_path = self.start("--title", title, "--vault-item", item_id)
            self.finalize(run_path)
        index = (self.data_root / "vault" / "index.md").read_text(encoding="utf-8")
        self.assertIn("## Previously successful and reusable", index)
        self.assertIn("## Rich sources with multiple related runs", index)
        self.assertGreaterEqual(index.count(f"(items/{item_id}.md)"), 3)
        result, stdout, _ = self.run_cli("vault", "list", "--successful", "yes")
        self.assertEqual(result, 0)
        self.assertIn(item_id, stdout)

    def test_link_run_supports_derived_items_as_a_distinct_role(self) -> None:
        derived = self.capture("Idea discovered in run")
        run_path = self.start("--title", "Parent run")
        result, _, stderr = self.run_cli(
            "vault",
            "link-run",
            derived,
            run_path.name,
            "--role",
            "derived",
        )
        self.assertEqual((result, stderr), (0, ""))
        state = load_state(run_path)
        self.assertEqual(state["derived_vault_items"], [derived])
        self.assertEqual(state["linked_vault_items"], [derived])
        metadata, _ = load_item(self.data_root / "vault" / "items" / f"{derived}.md")
        self.assertEqual(metadata["status"], "developing")

    def test_validation_rejects_inconsistent_usage_and_unsafe_artifacts(self) -> None:
        item_id = self.capture("Bad history")
        path = self.data_root / "vault" / "items" / f"{item_id}.md"
        metadata, body = load_item(path)
        metadata["successful_runs"] = ["missing-run"]
        metadata["use_count"] = -1
        metadata["last_used_at"] = metadata["updated_at"]
        metadata["final_artifacts"] = ["../outside.md"]
        path.write_text(render_item(metadata, body), encoding="utf-8")
        result, _, stderr = self.run_cli("vault", "validate")
        self.assertEqual(result, 1)
        self.assertIn("use_count must be a non-negative integer", stderr)
        self.assertIn("successful_runs must also be present in related_runs", stderr)
        self.assertIn("unsafe final artifact path", stderr)

    def test_no_capture_writes_into_public_framework_locations(self) -> None:
        before = {
            path.relative_to(ROOT)
            for root_name in ("examples", "templates")
            for path in (ROOT / root_name).rglob("*")
            if path.is_file()
        }
        self.capture("Private only")
        after = {
            path.relative_to(ROOT)
            for root_name in ("examples", "templates")
            for path in (ROOT / root_name).rglob("*")
            if path.is_file()
        }
        self.assertEqual(before, after)
        self.assertTrue(str(next((self.data_root / "vault" / "items").glob("*.md"))).startswith(str(self.data_root)))


if __name__ == "__main__":
    unittest.main()
