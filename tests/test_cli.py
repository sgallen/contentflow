from __future__ import annotations

import contextlib
import io
import json
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from content_flow.cli import load_state, main, make_run, resolve_run, slugify, validation_errors


class ContentFlowCLITests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_slugify_is_safe_and_predictable(self) -> None:
        self.assertEqual(slugify("  Café: Decisions & Logs! "), "cafe-decisions-logs")
        self.assertEqual(slugify("東京"), "untitled")

    def test_new_run_creates_valid_state_and_spike(self) -> None:
        run = make_run(self.root, "Decision Logs", "linkedin", date(2026, 7, 22))
        self.assertEqual(run.name, "2026-07-22-decision-logs")
        state = load_state(run)
        self.assertEqual(state["pending_human_action"], "provide_idea_details")
        self.assertEqual(validation_errors(run, state), [])
        self.assertTrue((run / "spike.md").is_file())

    def test_new_run_never_overwrites(self) -> None:
        first = make_run(self.root, "Same title", "linkedin", date(2026, 7, 22))
        second = make_run(self.root, "Same title", "linkedin", date(2026, 7, 22))
        self.assertNotEqual(first, second)
        self.assertEqual(second.name, "2026-07-22-same-title-2")
        self.assertTrue((first / "run.json").is_file())

    def test_bare_run_id_resolves_under_runs(self) -> None:
        run = make_run(self.root, "Resolvable", "linkedin", date(2026, 7, 22))
        self.assertEqual(resolve_run(run.name, self.root), run.resolve())

    def test_validate_detects_missing_stage_artifact(self) -> None:
        run = make_run(self.root, "Missing brief", "linkedin", date(2026, 7, 22))
        state = load_state(run)
        state.update(
            stage="draft",
            status="awaiting_human",
            research_required=False,
            pending_human_action="review_draft",
        )
        state["artifacts"].update(interview="interview.md", draft="draft-01.md")
        (run / "interview.md").write_text("answer", encoding="utf-8")
        (run / "draft-01.md").write_text("draft", encoding="utf-8")
        errors = validation_errors(run, state)
        self.assertIn("stage 'draft' requires artifact 'brief'", errors)

    def test_validate_rejects_unsafe_artifact_path(self) -> None:
        run = make_run(self.root, "Unsafe", "linkedin", date(2026, 7, 22))
        state = load_state(run)
        state["artifacts"]["extra"] = "../secret.md"
        self.assertIn("artifact 'extra' must stay inside the run directory", validation_errors(run, state))

    def test_validate_enforces_research_artifact(self) -> None:
        run = make_run(self.root, "Research", "linkedin", date(2026, 7, 22))
        state = load_state(run)
        state.update(
            stage="interview",
            status="awaiting_human",
            research_required=True,
            pending_human_action="answer_interview_question",
        )
        state["artifacts"]["interview"] = "interview.md"
        (run / "interview.md").write_text("Q1", encoding="utf-8")
        errors = validation_errors(run, state)
        self.assertIn("research_required=true requires a research artifact after research stage", errors)

    def test_count_counts_unicode_code_points_including_newline(self) -> None:
        path = self.root / "unicode.txt"
        path.write_text("A🙂é\n", encoding="utf-8")
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            result = main(["count", str(path)], root=self.root)
        self.assertEqual(result, 0)
        self.assertEqual(output.getvalue(), "4\n")

    def test_validate_command_returns_nonzero_for_invalid_json_state(self) -> None:
        run = make_run(self.root, "Invalid", "linkedin", date(2026, 7, 22))
        state = json.loads((run / "run.json").read_text(encoding="utf-8"))
        state["status"] = "mystery"
        (run / "run.json").write_text(json.dumps(state), encoding="utf-8")
        with contextlib.redirect_stderr(io.StringIO()):
            result = main(["validate", str(run)], root=self.root)
        self.assertEqual(result, 1)


if __name__ == "__main__":
    unittest.main()
