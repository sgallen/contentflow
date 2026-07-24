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
    SUPPORTED_FORMATS,
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
        self.assertEqual(state["schema_version"], 2)
        self.assertEqual(state["requested_formats"], ["linkedin"])
        self.assertEqual(state["shared_state"]["pending_human_action"], "provide_idea_details")
        self.assertEqual(state["format_states"]["linkedin"]["revision_round"], 0)
        self.assertEqual(validation_errors(run, state), [])
        self.assertTrue((run / "spike.md").is_file())

    def test_readme_is_supported_without_changing_linkedin_default(self) -> None:
        self.assertEqual(SUPPORTED_FORMATS, ("linkedin", "x", "readme"))
        readme_run = make_run(self.root, "Project README", "readme", date(2026, 7, 22))
        linkedin_run = make_run(self.root, "LinkedIn default", "linkedin", date(2026, 7, 22))

        readme_state = load_state(readme_run)
        self.assertEqual(readme_state["requested_formats"], ["readme"])
        self.assertEqual(validation_errors(readme_run, readme_state), [])
        self.assertIn(
            "## Repository evidence",
            (readme_run / "spike.md").read_text(encoding="utf-8"),
        )
        self.assertEqual(load_state(linkedin_run)["requested_formats"], ["linkedin"])
        self.assertIn("## Idea", (linkedin_run / "spike.md").read_text(encoding="utf-8"))

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

    def test_init_adds_missing_readme_format_without_overwriting_existing_private_files(self) -> None:
        data_root = self.root / "private"
        creator_root = data_root / "creator"
        (creator_root / "formats").mkdir(parents=True)
        private_readme = creator_root / "formats" / "readme.md"
        private_readme.write_text("custom private README guidance\n", encoding="utf-8")
        profile = creator_root / "profile.md"
        profile.write_text("custom private profile\n", encoding="utf-8")

        initialize_data_root(data_root, ROOT)

        self.assertEqual(private_readme.read_text(encoding="utf-8"), "custom private README guidance\n")
        self.assertEqual(profile.read_text(encoding="utf-8"), "custom private profile\n")
        self.assertEqual(missing_creator_files(data_root), [])

    def test_init_upgrades_older_root_with_only_missing_readme_format(self) -> None:
        data_root = self.root / "private"
        initialize_data_root(data_root, ROOT)
        readme_format = data_root / "creator" / "formats" / "readme.md"
        readme_format.unlink()
        linkedin_format = data_root / "creator" / "formats" / "linkedin.md"
        linkedin_before = linkedin_format.read_text(encoding="utf-8")

        initialize_data_root(data_root, ROOT)

        self.assertEqual(
            readme_format.read_text(encoding="utf-8"),
            (ROOT / "templates" / "creator" / "formats" / "readme.md").read_text(encoding="utf-8"),
        )
        self.assertEqual(linkedin_format.read_text(encoding="utf-8"), linkedin_before)

    def test_init_adds_x_guidance_without_overwriting_existing_x_file(self) -> None:
        data_root = self.root / "private"
        initialize_data_root(data_root, ROOT)
        x_format = data_root / "creator" / "formats" / "x.md"
        x_format.write_text("private X preferences\n", encoding="utf-8")
        with self.assertRaisesRegex(CFError, "refusing to overwrite"):
            initialize_data_root(data_root, ROOT)
        self.assertEqual(x_format.read_text(encoding="utf-8"), "private X preferences\n")

        older = self.root / "older"
        initialize_data_root(older, ROOT)
        (older / "creator" / "formats" / "x.md").unlink()
        linkedin_before = (older / "creator" / "formats" / "linkedin.md").read_bytes()
        initialize_data_root(older, ROOT)
        self.assertTrue((older / "creator" / "formats" / "x.md").is_file())
        self.assertEqual(
            (older / "creator" / "formats" / "linkedin.md").read_bytes(),
            linkedin_before,
        )

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

    def test_readme_run_status_validation_and_resume_from_disk(self) -> None:
        data_root = self.root / "explicit"
        initialize_data_root(data_root, ROOT)
        run = make_run(data_root, "Reusable README", "readme", date(2026, 7, 22))

        first_output = io.StringIO()
        with contextlib.redirect_stdout(first_output):
            self.assertEqual(main(["status", run.name, "--data-dir", str(data_root)], root=ROOT), 0)
            self.assertEqual(main(["validate", run.name, "--data-dir", str(data_root)], root=ROOT), 0)

        resumed = load_state(resolve_run(run.name, data_root))
        self.assertEqual(resumed["requested_formats"], ["readme"])
        self.assertEqual(resumed["shared_state"]["pending_human_action"], "provide_idea_details")
        self.assertIn("requested_formats: readme", first_output.getvalue())

    def test_new_run_cli_accepts_readme(self) -> None:
        data_root = self.root / "explicit"
        initialize_data_root(data_root, ROOT)
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            result = main(
                [
                    "new-run",
                    "--title",
                    "CLI README",
                    "--format",
                    "readme",
                    "--data-dir",
                    str(data_root),
                ],
                root=ROOT,
            )
        self.assertEqual(result, 0)
        run = next((data_root / "runs").iterdir())
        self.assertEqual(load_state(run)["requested_formats"], ["readme"])

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

    def _finish_shared(self, run: Path) -> dict:
        state = load_state(run)
        for name, text in (("interview.md", "answer"), ("content-brief.md", "brief")):
            (run / name).write_text(text, encoding="utf-8")
        state["shared_state"].update(
            stage="complete", status="complete", research_required=False,
            pending_human_action="none",
        )
        state["shared_artifacts"].update(interview="interview.md", brief="content-brief.md")
        return state

    def test_repeatable_formats_and_primary_create_independent_states(self) -> None:
        data_root = self.root / "private"
        initialize_data_root(data_root, ROOT)
        result = main([
            "new-run", "--title", "Both", "--format", "linkedin", "--format", "x",
            "--primary-format", "linkedin", "--x-variant", "thread",
            "--data-dir", str(data_root),
        ], root=ROOT)
        self.assertEqual(result, 0)
        run = next((data_root / "runs").iterdir())
        state = load_state(run)
        self.assertEqual(state["requested_formats"], ["linkedin", "x"])
        self.assertEqual(state["primary_format"], "linkedin")
        self.assertEqual(state["format_states"]["x"]["variant"], "thread")
        self.assertIsNot(state["format_states"]["linkedin"], state["format_states"]["x"])
        self.assertEqual(validation_errors(run, state), [])

    def test_duplicate_and_invalid_primary_are_rejected(self) -> None:
        with self.assertRaisesRegex(CFError, "duplicates"):
            make_run(self.root, "Duplicate", ["x", "x"])
        with self.assertRaisesRegex(CFError, "included"):
            make_run(self.root, "Bad primary", ["x"], primary_format="linkedin")

    def test_x_only_and_x_primary_runs_do_not_require_linkedin(self) -> None:
        x_only = make_run(self.root, "X only", ["x"], x_variant="single")
        self.assertEqual(set(load_state(x_only)["format_states"]), {"x"})
        x_primary = make_run(self.root, "X first", ["x", "linkedin"], primary_format="x")
        self.assertEqual(load_state(x_primary)["primary_format"], "x")

    def test_shared_artifacts_and_format_artifacts_are_separate(self) -> None:
        run = make_run(self.root, "Separate", ["linkedin", "x"], primary_format="linkedin")
        state = self._finish_shared(run)
        state["active_format"] = "linkedin"
        linkedin = state["format_states"]["linkedin"]
        linkedin.update(stage="draft", status="awaiting_human", pending_human_action="authorize_council")
        path = run / "formats" / "linkedin" / "draft-01.md"
        path.write_text("draft", encoding="utf-8")
        linkedin["artifacts"]["draft"] = "formats/linkedin/draft-01.md"
        self.assertEqual(validation_errors(run, state), [])
        self.assertIsNone(state["format_states"]["x"]["artifacts"]["draft"])

    def test_primary_must_resolve_before_secondary_activation(self) -> None:
        run = make_run(self.root, "Order", ["linkedin", "x"], primary_format="linkedin")
        state = self._finish_shared(run)
        state["active_format"] = "x"
        errors = validation_errors(run, state)
        self.assertIn("primary format must be completed, parked, or declined before a secondary becomes active", errors)

    def test_both_adaptation_directions_activate_an_empty_secondary(self) -> None:
        for primary, secondary in (("linkedin", "x"), ("x", "linkedin")):
            data_root = self.root / f"private-{primary}"
            initialize_data_root(data_root, ROOT)
            run = make_run(
                data_root, f"{primary} anchor", [primary, secondary],
                primary_format=primary, x_variant="single",
            )
            state = self._finish_shared(run)
            primary_dir = run / "formats" / primary
            social_copy = (
                "<!-- cf:x-variant: single -->\n\n## Recommended final version\n\n"
                "### Post\n\nApproved X framing.\n"
                if primary == "x" else "Approved LinkedIn framing."
            )
            for name, content in (
                ("draft-01.md", social_copy),
                ("council-01.md", "council"),
                ("final.md", social_copy),
                ("lesson-candidates.md", "lessons"),
            ):
                (primary_dir / name).write_text(content, encoding="utf-8")
            fmt = state["format_states"][primary]
            fmt.update(stage="complete", status="complete", disposition="finalized")
            fmt["artifacts"].update(
                draft=f"formats/{primary}/draft-01.md",
                council=f"formats/{primary}/council-01.md",
                final=f"formats/{primary}/final.md",
                lessons=f"formats/{primary}/lesson-candidates.md",
            )
            fmt["final_artifact"] = f"formats/{primary}/final.md"
            state["status"] = "awaiting_human"
            (run / "run.json").write_text(json.dumps(state), encoding="utf-8")
            with contextlib.redirect_stdout(io.StringIO()):
                result = main(
                    ["format-action", run.name, secondary, "activate", "--data-dir", str(data_root)],
                    root=ROOT,
                )
            self.assertEqual(result, 0)
            resumed = load_state(run)
            self.assertEqual(resumed["active_format"], secondary)
            self.assertIsNone(resumed["format_states"][secondary]["artifacts"]["draft"])

    def test_independent_human_gates_and_revision_rounds(self) -> None:
        run = make_run(self.root, "Gates", ["linkedin", "x"])
        state = self._finish_shared(run)
        state["active_format"] = "linkedin"
        li = state["format_states"]["linkedin"]
        li.update(stage="revision", status="awaiting_human", pending_human_action="approve_revision_plan")
        for name in ("draft-01.md", "revision-plan-01.md"):
            (run / "formats" / "linkedin" / name).write_text(name, encoding="utf-8")
        li["artifacts"].update(
            draft="formats/linkedin/draft-01.md",
            revision_plan="formats/linkedin/revision-plan-01.md",
        )
        self.assertEqual(validation_errors(run, state), [])
        self.assertEqual(state["format_states"]["x"]["revision_round"], 0)
        state["format_states"]["x"]["pending_human_action"] = "approve_final"
        self.assertIn("format 'x' status 'pending' requires no pending action", validation_errors(run, state))

    def test_x_single_thread_and_standalone_validation(self) -> None:
        samples = {
            "single": "<!-- cf:x-variant: single -->\n\n## Recommended final version\n\n### Post\n\nOne clear post.\n",
            "thread": "<!-- cf:x-variant: thread -->\n\n## Recommended final version\n\n### Post 1\n\nOpening.\n\n### Post 2\n\nPayoff.\n",
            "standalone": "<!-- cf:x-variant: standalone -->\n\n## Recommended final version\n\n### Standalone 1\n\nAngle one.\n\n### Standalone 2\n\nAngle two.\n",
        }
        for variant, content in samples.items():
            path = self.root / f"{variant}.md"
            path.write_text(content, encoding="utf-8")
            stderr = io.StringIO()
            with contextlib.redirect_stderr(stderr):
                self.assertEqual(main(["validate-x", str(path), "--variant", variant], root=ROOT), 0)
        too_long = self.root / "long.md"
        too_long.write_text(
            "<!-- cf:x-variant: single -->\n\n## Recommended final version\n\n### Post\n\n" + "x" * 281,
            encoding="utf-8",
        )
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(main(["validate-x", str(too_long), "--variant", "single"], root=ROOT), 1)

    def test_invalid_x_thread_structure_is_rejected_by_run_validation(self) -> None:
        run = make_run(self.root, "Bad thread", ["x"], x_variant="thread")
        state = self._finish_shared(run)
        state["active_format"] = "x"
        fmt = state["format_states"]["x"]
        fmt.update(stage="draft", status="awaiting_human", pending_human_action="review_draft")
        draft = run / "formats" / "x" / "draft-01.md"
        draft.write_text("<!-- cf:x-variant: thread -->\n\n## Recommended final version\n\n### Post 1\n\nOnly one.", encoding="utf-8")
        fmt["artifacts"]["draft"] = "formats/x/draft-01.md"
        self.assertTrue(any("at least two posts" in error for error in validation_errors(run, state)))

    def test_unfinished_secondary_prevents_completion_and_decline_resolves_it(self) -> None:
        data_root = self.root / "private"
        initialize_data_root(data_root, ROOT)
        run = make_run(data_root, "Completion", ["linkedin", "x"])
        state = self._finish_shared(run)
        li = state["format_states"]["linkedin"]
        li.update(stage="complete", status="complete", disposition="finalized")
        for name in ("draft-01.md", "council-01.md", "final.md", "lesson-candidates.md"):
            (run / "formats" / "linkedin" / name).write_text(name, encoding="utf-8")
        li["artifacts"].update(
            draft="formats/linkedin/draft-01.md",
            council="formats/linkedin/council-01.md",
            final="formats/linkedin/final.md",
            lessons="formats/linkedin/lesson-candidates.md",
        )
        li["final_artifact"] = "formats/linkedin/final.md"
        state["status"] = "complete"
        self.assertIn("run cannot be complete while requested formats remain unfinished", validation_errors(run, state))
        (run / "run.json").write_text(json.dumps({**state, "status": "awaiting_human"}), encoding="utf-8")
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(main(["format-action", run.name, "x", "decline", "--data-dir", str(data_root)], root=ROOT), 0)
        self.assertEqual(load_state(run)["status"], "complete")

    def test_migration_moves_only_format_artifacts_and_adds_no_x(self) -> None:
        run = self.root / "runs" / "legacy"
        run.mkdir(parents=True)
        for name in ("spike.md", "interview.md", "content-brief.md", "draft-01.md"):
            (run / name).write_text(name, encoding="utf-8")
        legacy = {
            "id": "legacy", "title": "Legacy", "format": "linkedin", "stage": "draft",
            "status": "awaiting_human", "research_required": False, "revision_round": 0,
            "pending_human_action": "review_draft", "artifacts": {
                "spike": "spike.md", "research": None, "interview": "interview.md",
                "brief": "content-brief.md", "draft": "draft-01.md", "council": None,
                "revision_plan": None, "revision": None, "final": None, "lessons": None,
            }, "origin_vault_items": [], "contributing_vault_items": [],
            "derived_vault_items": [], "linked_vault_items": [], "parking_reason": None,
            "parked_at": None, "final_artifact": None,
        }
        (run / "run.json").write_text(json.dumps(legacy), encoding="utf-8")
        self.assertEqual(main(["migrate-run", str(run)], root=ROOT), 0)
        self.assertTrue((run / "draft-01.md").is_file())
        self.assertEqual(main(["migrate-run", str(run), "--apply"], root=ROOT), 0)
        state = load_state(run)
        self.assertEqual(state["requested_formats"], ["linkedin"])
        self.assertNotIn("x", state["format_states"])
        self.assertTrue((run / "formats" / "linkedin" / "draft-01.md").is_file())
        self.assertTrue((run / "content-brief.md").is_file())

    def test_readme_target_gate_remains_procedural_and_private(self) -> None:
        skill = (ROOT / ".agents" / "skills" / "content-flow" / "SKILL.md").read_text(encoding="utf-8")
        normalized = " ".join(skill.split())
        self.assertIn("show the complete candidate or exact diff", normalized)
        self.assertIn("Ask for explicit final approval", normalized)
        run = make_run(self.root, "Private README", ["readme"])
        self.assertTrue((run / "formats" / "readme").is_dir())

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
