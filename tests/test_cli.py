from __future__ import annotations

import contextlib
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from content_flow.cli import (
    CFError,
    CREATOR_FILES,
    extract_markdown_section,
    git_safety_description,
    initialize_data_root,
    load_state,
    main,
    make_run,
    missing_creator_files,
    resolve_data_root,
    resolve_run,
    slugify,
    validation_errors,
)


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
        self.assertEqual(state["revision_round"], 0)
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

    def test_data_root_precedence(self) -> None:
        environment_root = self.root / "environment"
        explicit_root = self.root / "explicit"
        self.assertEqual(
            resolve_data_root(str(explicit_root), ROOT, {"CONTENT_FLOW_HOME": str(environment_root)}),
            explicit_root.resolve(),
        )
        self.assertEqual(
            resolve_data_root(None, ROOT, {"CONTENT_FLOW_HOME": str(environment_root)}),
            environment_root.resolve(),
        )
        self.assertEqual(resolve_data_root(None, ROOT, {}), (ROOT / ".content-flow").resolve())

    def test_init_copies_templates_and_creates_private_structure(self) -> None:
        data_root = self.root / "private"
        initialize_data_root(data_root, ROOT)
        self.assertEqual(missing_creator_files(data_root), [])
        for relative in CREATOR_FILES:
            self.assertEqual(
                (data_root / "creator" / relative).read_text(encoding="utf-8"),
                (ROOT / "templates" / "creator" / relative).read_text(encoding="utf-8"),
            )
        self.assertTrue((data_root / "vault" / "items").is_dir())
        self.assertTrue((data_root / "vault" / "assets").is_dir())
        self.assertTrue((data_root / "vault" / "index.md").is_file())
        self.assertTrue((data_root / "runs").is_dir())

    def test_init_refuses_to_overwrite_creator_files(self) -> None:
        data_root = self.root / "private"
        initialize_data_root(data_root, ROOT)
        profile = data_root / "creator" / "profile.md"
        profile.write_text("keep me", encoding="utf-8")
        with self.assertRaisesRegex(CFError, "refusing to overwrite"):
            initialize_data_root(data_root, ROOT)
        self.assertEqual(profile.read_text(encoding="utf-8"), "keep me")

    def test_init_fails_for_unignored_root_inside_git_repository(self) -> None:
        repository = self.root / "repository"
        repository.mkdir()
        subprocess.run(["git", "init", "-q", str(repository)], check=True)
        with self.assertRaisesRegex(CFError, "is not ignored"):
            initialize_data_root(repository / "private-data", ROOT)

    def test_init_rejects_tracked_root_even_if_ignore_rule_was_added_later(self) -> None:
        repository = self.root / "repository"
        data_root = repository / "private-data"
        data_root.mkdir(parents=True)
        (data_root / "tracked.txt").write_text("already tracked", encoding="utf-8")
        subprocess.run(["git", "init", "-q", str(repository)], check=True)
        subprocess.run(["git", "-C", str(repository), "add", "private-data/tracked.txt"], check=True)
        (repository / ".gitignore").write_text("private-data/\n", encoding="utf-8")
        with self.assertRaisesRegex(CFError, "is not ignored"):
            initialize_data_root(data_root, ROOT)

    def test_nested_data_repository_is_checked_against_ignored_parent(self) -> None:
        repository = self.root / "repository"
        data_root = repository / "private-data"
        data_root.mkdir(parents=True)
        subprocess.run(["git", "init", "-q", str(repository)], check=True)
        (repository / ".gitignore").write_text("private-data/\n", encoding="utf-8")
        subprocess.run(["git", "init", "-q", str(data_root)], check=True)

        initialize_data_root(data_root, ROOT)

        self.assertEqual(missing_creator_files(data_root), [])
        self.assertEqual(
            git_safety_description(data_root),
            f"data root is Git repository {data_root.resolve()}; "
            f"ignored by parent Git repository {repository.resolve()}",
        )

    def test_nested_data_repository_must_be_ignored_by_parent(self) -> None:
        repository = self.root / "repository"
        data_root = repository / "private-data"
        data_root.mkdir(parents=True)
        subprocess.run(["git", "init", "-q", str(repository)], check=True)
        subprocess.run(["git", "init", "-q", str(data_root)], check=True)

        with self.assertRaisesRegex(CFError, "is not ignored"):
            initialize_data_root(data_root, ROOT)
        self.assertEqual(
            git_safety_description(data_root),
            f"data root is Git repository {data_root.resolve()}; "
            f"NOT ignored by parent Git repository {repository.resolve()}",
        )

    def test_default_private_root_is_git_ignored(self) -> None:
        result = subprocess.run(
            ["git", "check-ignore", "-q", ".content-flow/.cf-ignore-probe"],
            cwd=ROOT,
            check=False,
        )
        self.assertEqual(result.returncode, 0)

    def test_init_and_new_run_support_explicit_data_dir(self) -> None:
        data_root = self.root / "explicit"
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            self.assertEqual(main(["init", "--data-dir", str(data_root)], root=ROOT), 0)
            self.assertEqual(
                main(
                    [
                        "new-run",
                        "--title",
                        "Explicit root",
                        "--data-dir",
                        str(data_root),
                    ],
                    root=ROOT,
                ),
                0,
            )
        run = next((data_root / "runs").iterdir())
        self.assertTrue((run / "run.json").is_file())
        self.assertIn(f"data_root: {data_root.resolve()}", output.getvalue())

    def test_status_and_validate_use_explicit_data_dir_for_bare_id(self) -> None:
        data_root = self.root / "explicit"
        initialize_data_root(data_root, ROOT)
        run = make_run(data_root, "Selected root", "linkedin", date(2026, 7, 22))
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            self.assertEqual(main(["status", run.name, "--data-dir", str(data_root)], root=ROOT), 0)
            self.assertEqual(main(["validate", run.name, "--data-dir", str(data_root)], root=ROOT), 0)
        self.assertIn(f"run_path: {run.resolve()}", output.getvalue())
        self.assertIn(f"OK {run.resolve()}", output.getvalue())

    def test_content_flow_home_selects_data_root(self) -> None:
        data_root = self.root / "environment"
        previous = os.environ.get("CONTENT_FLOW_HOME")
        os.environ["CONTENT_FLOW_HOME"] = str(data_root)
        try:
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(main(["init"], root=ROOT), 0)
                self.assertEqual(
                    main(["new-run", "--title", "Environment root"], root=ROOT),
                    0,
                )
        finally:
            if previous is None:
                os.environ.pop("CONTENT_FLOW_HOME", None)
            else:
                os.environ["CONTENT_FLOW_HOME"] = previous
        self.assertEqual(len(list((data_root / "runs").iterdir())), 1)

    def test_new_run_fails_clearly_before_private_setup(self) -> None:
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            result = main(
                ["new-run", "--title", "Not initialized", "--data-dir", str(self.root / "missing")],
                root=ROOT,
            )
        self.assertEqual(result, 2)
        self.assertIn("private creator setup is incomplete", stderr.getvalue())

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

    def test_validate_rejects_symlink_artifact_escape(self) -> None:
        run = make_run(self.root, "Symlink", "linkedin", date(2026, 7, 22))
        outside = self.root / "outside.md"
        outside.write_text("secret", encoding="utf-8")
        (run / "draft-01.md").symlink_to(outside)
        state = load_state(run)
        state["artifacts"]["draft"] = "draft-01.md"
        self.assertIn(
            "artifact 'draft' must resolve inside the run directory",
            validation_errors(run, state),
        )

    def test_validate_rejects_stage_action_mismatch(self) -> None:
        run = make_run(self.root, "Wrong gate", "linkedin", date(2026, 7, 22))
        state = load_state(run)
        state["pending_human_action"] = "approve_final"
        self.assertIn(
            "stage 'selected_idea' cannot await 'approve_final'; allowed actions: provide_idea_details",
            validation_errors(run, state),
        )

    def test_validate_rejects_non_boolean_research_decision(self) -> None:
        run = make_run(self.root, "Wrong type", "linkedin", date(2026, 7, 22))
        state = load_state(run)
        state["research_required"] = 0
        self.assertIn("research_required must be null or a Boolean", validation_errors(run, state))

    def test_validate_requires_stable_artifact_keys(self) -> None:
        run = make_run(self.root, "Missing key", "linkedin", date(2026, 7, 22))
        state = load_state(run)
        del state["artifacts"]["lessons"]
        self.assertIn("missing stable artifact key: lessons", validation_errors(run, state))

    def test_validate_rejects_semantically_wrong_artifact_filename(self) -> None:
        run = make_run(self.root, "Wrong file", "linkedin", date(2026, 7, 22))
        state = load_state(run)
        state["artifacts"]["research"] = "notes.md"
        (run / "notes.md").write_text("notes", encoding="utf-8")
        self.assertIn(
            "artifact 'research' has invalid filename: notes.md",
            validation_errors(run, state),
        )

    def test_validate_allows_versioned_final_and_lessons_after_reopen(self) -> None:
        run = make_run(self.root, "Reopened final", "linkedin", date(2026, 7, 22))
        state = load_state(run)
        state["artifacts"]["final"] = "final-02.md"
        state["artifacts"]["lessons"] = "lesson-candidates-02.md"
        state["final_artifact"] = "final-02.md"
        (run / "final-02.md").write_text("final", encoding="utf-8")
        (run / "lesson-candidates-02.md").write_text("lessons", encoding="utf-8")

        self.assertEqual(validation_errors(run, state), [])

    def test_validate_enforces_cumulative_council_artifacts(self) -> None:
        run = make_run(self.root, "Council history", "linkedin", date(2026, 7, 22))
        state = load_state(run)
        state.update(
            stage="council",
            status="awaiting_human",
            research_required=False,
            pending_human_action="approve_final",
        )
        for key, filename in {
            "brief": "content-brief.md",
            "draft": "draft-01.md",
            "council": "council-01.md",
        }.items():
            state["artifacts"][key] = filename
            (run / filename).write_text(key, encoding="utf-8")
        self.assertIn("stage 'council' requires artifact 'interview'", validation_errors(run, state))

    def test_validate_enforces_revision_round_and_current_pointer(self) -> None:
        run = make_run(self.root, "Revision pointer", "linkedin", date(2026, 7, 22))
        state = load_state(run)
        state["revision_round"] = 1
        self.assertIn(
            "revision_round greater than 0 requires artifact 'revision'",
            validation_errors(run, state),
        )

    def test_revision_plan_from_human_feedback_does_not_require_council(self) -> None:
        run = make_run(self.root, "Human feedback", "linkedin", date(2026, 7, 22))
        state = load_state(run)
        state.update(
            stage="revision",
            status="awaiting_human",
            research_required=False,
            pending_human_action="approve_revision_plan",
        )
        state["artifacts"].update(
            interview="interview.md",
            brief="content-brief.md",
            draft="draft-01.md",
            draft_1="draft-01.md",
            revision_plan="revision-plan-01.md",
            revision_plan_1="revision-plan-01.md",
        )
        for filename in (
            "interview.md",
            "content-brief.md",
            "draft-01.md",
            "revision-plan-01.md",
        ):
            (run / filename).write_text(filename, encoding="utf-8")

        self.assertEqual(validation_errors(run, state), [])

    def test_validate_rejects_stale_current_artifact_pointer(self) -> None:
        run = make_run(self.root, "Stale pointer", "linkedin", date(2026, 7, 22))
        state = load_state(run)
        state["artifacts"].update(council="council-01.md", council_2="council-02.md")
        (run / "council-01.md").write_text("first", encoding="utf-8")
        (run / "council-02.md").write_text("second", encoding="utf-8")
        self.assertIn(
            "current artifact 'council' is older than its recorded history",
            validation_errors(run, state),
        )

    def test_validate_rejects_third_revision_plan(self) -> None:
        run = make_run(self.root, "Revision cap", "linkedin", date(2026, 7, 22))
        state = load_state(run)
        state.update(
            stage="revision",
            status="awaiting_human",
            research_required=False,
            revision_round=2,
            pending_human_action="approve_revision_plan",
        )
        state["artifacts"].update(
            interview="interview.md",
            brief="content-brief.md",
            draft="draft-03.md",
            council="council-02.md",
            revision_plan="revision-plan-02.md",
            revision="draft-03.md",
        )
        for filename in (
            "interview.md",
            "content-brief.md",
            "draft-03.md",
            "council-02.md",
            "revision-plan-02.md",
        ):
            (run / filename).write_text(filename, encoding="utf-8")
        self.assertIn(
            "revision_round=2 cannot await another revision plan; resolve the revision limit",
            validation_errors(run, state),
        )

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

    def test_count_can_select_exact_markdown_section(self) -> None:
        path = self.root / "post.md"
        path.write_text("# Draft\n\n## Post\n\nA🙂é\n\n## Notes\n\nIgnore\n", encoding="utf-8")
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            result = main(["count", str(path), "--section", "Post"], root=self.root)
        self.assertEqual(result, 0)
        self.assertEqual(output.getvalue(), "3\n")
        self.assertEqual(extract_markdown_section(path.read_text(encoding="utf-8"), "Post"), "A🙂é")

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
