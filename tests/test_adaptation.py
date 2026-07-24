from __future__ import annotations

import contextlib
import io
import json
import os
import tempfile
import unittest
from datetime import date, datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

import sys

sys.path.insert(0, str(ROOT / "src"))

from content_flow.cli import initialize_data_root, load_state, main, make_run, validation_errors
from content_flow.discovery import find_sources


class ConversationalAdaptationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.base = Path(self.temporary.name)
        self.data_root = self.base / "private"
        initialize_data_root(self.data_root, ROOT)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def source_run(
        self,
        title: str,
        run_date: date,
        *,
        format_name: str = "linkedin",
        x_variant: str = "single",
        final: bool = True,
        text: str | None = None,
        aliases: list[str] | None = None,
    ) -> Path:
        run = make_run(
            self.data_root,
            title,
            [format_name],
            today=run_date,
            x_variant=x_variant if format_name == "x" else None,
        )
        state = load_state(run)
        state["shared_state"].update(
            stage="complete",
            status="complete",
            research_required=False,
            pending_human_action="none",
        )
        (run / "interview.md").write_text("# Interview\n\nHuman input.\n", encoding="utf-8")
        (run / "content-brief.md").write_text(
            "# Content brief\n\nThe shared brief remains authoritative.\n",
            encoding="utf-8",
        )
        state["shared_artifacts"].update(interview="interview.md", brief="content-brief.md")
        if aliases:
            state["aliases"] = aliases
        fmt = state["format_states"][format_name]
        body = text or f"{title}. Recognizable source wording."
        if format_name == "x" and "<!-- cf:x-variant:" not in body:
            body = (
                f"<!-- cf:x-variant: {x_variant} -->\n\n"
                "## Recommended final version\n\n### Post\n\n"
                + body
                + "\n"
            )
        draft_path = run / "formats" / format_name / "draft-01.md"
        draft_path.write_text(body, encoding="utf-8")
        fmt["artifacts"]["draft"] = f"formats/{format_name}/draft-01.md"
        if final:
            final_path = run / "formats" / format_name / "final.md"
            final_path.write_text(body, encoding="utf-8")
            for name in ("council-01.md", "lesson-candidates.md"):
                (run / "formats" / format_name / name).write_text(name, encoding="utf-8")
            fmt.update(stage="complete", status="complete", disposition="finalized")
            fmt["artifacts"].update(
                council=f"formats/{format_name}/council-01.md",
                final=f"formats/{format_name}/final.md",
                lessons=f"formats/{format_name}/lesson-candidates.md",
            )
            fmt["final_artifact"] = f"formats/{format_name}/final.md"
            state["status"] = "complete"
            artifact = final_path
        else:
            fmt.update(
                stage="draft",
                status="awaiting_human",
                pending_human_action="review_draft",
            )
            state["active_format"] = format_name
            state["status"] = "awaiting_human"
            artifact = draft_path
        (run / "run.json").write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
        timestamp = datetime.combine(run_date, datetime.min.time()).timestamp()
        os.utime(artifact, (timestamp, timestamp))
        self.assertEqual(validation_errors(run, state), [])
        return run

    def run_cli(self, *arguments: str) -> tuple[int, str, str]:
        stdout, stderr = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            result = main([*arguments, "--data-dir", str(self.data_root)], root=ROOT)
        return result, stdout.getvalue(), stderr.getvalue()

    def test_one_clear_and_partial_title_match(self) -> None:
        self.source_run(
            "The Paperclip Maximizer Was Never About Paperclips",
            date(2026, 7, 23),
        )
        exact = find_sources(self.data_root, "The Paperclip Maximizer Was Never About Paperclips")
        partial = find_sources(self.data_root, "paperclip maximizer")
        self.assertEqual(exact.resolution, "clear")
        self.assertEqual(partial.resolution, "clear")
        self.assertEqual(partial.matches[0].finalization_state, "finalized")

    def test_recognizable_phrase_and_spelling_variation_match(self) -> None:
        self.source_run(
            "The Alignment Thought Experiment",
            date(2026, 7, 23),
            text="Nick Bostrom described a paperclip maximizer pursuing a narrow goal.",
        )
        phrase = find_sources(self.data_root, "pursuing a narrow goal")
        misspelling = find_sources(self.data_root, "Bostrum")
        self.assertEqual(phrase.resolution, "clear")
        self.assertEqual(phrase.matches[0].matched_on, "recognizable phrase")
        self.assertEqual(misspelling.resolution, "clear")
        self.assertEqual(misspelling.matches[0].matched_on, "spelling variation")

    def test_latest_finalized_linkedin_post_uses_recency_and_format(self) -> None:
        self.source_run("Older LinkedIn", date(2026, 7, 22))
        newest = self.source_run("Newest LinkedIn", date(2026, 7, 23))
        self.source_run("Newest X", date(2026, 7, 24), format_name="x")
        result = find_sources(
            self.data_root,
            "my latest LinkedIn post",
            today=date(2026, 7, 24),
        )
        self.assertEqual(result.resolution, "clear")
        self.assertEqual(result.matches[0].related_run, newest.name)
        self.assertEqual(result.matches[0].format, "linkedin")
        yesterday = find_sources(
            self.data_root,
            "the LinkedIn post from yesterday",
            today=date(2026, 7, 24),
        )
        self.assertEqual(yesterday.resolution, "clear")
        self.assertEqual(yesterday.matches[0].related_run, newest.name)

    def test_last_x_thread_filters_the_source_variant(self) -> None:
        thread = self.source_run(
            "Decision Log Thread",
            date(2026, 7, 23),
            format_name="x",
            x_variant="thread",
            text=(
                "<!-- cf:x-variant: thread -->\n\n"
                "## Recommended final version\n\n"
                "### Post 1\n\nFirst.\n\n### Post 2\n\nSecond.\n"
            ),
        )
        self.source_run("Newer X Single", date(2026, 7, 24), format_name="x")
        result = find_sources(
            self.data_root,
            "the last X thread we finished yesterday",
            today=date(2026, 7, 24),
        )
        self.assertEqual(result.resolution, "clear")
        self.assertEqual(result.matches[0].related_run, thread.name)
        self.assertEqual(result.matches[0].variant, "thread")

    def test_ambiguous_and_no_match_are_reported_without_guessing(self) -> None:
        self.source_run("Decision Logs for Teams", date(2026, 7, 22))
        self.source_run("Decision Logs for Agents", date(2026, 7, 22))
        ambiguous = find_sources(self.data_root, "decision logs")
        missing = find_sources(self.data_root, "marine biology field notes")
        self.assertEqual(ambiguous.resolution, "ambiguous")
        self.assertGreaterEqual(len(ambiguous.matches), 2)
        self.assertEqual(missing.resolution, "none")
        self.assertEqual(missing.matches, ())

    def test_finalized_content_is_preferred_unless_draft_is_explicit(self) -> None:
        finalized = self.source_run("Agent-First Workflows", date(2026, 7, 22))
        self.source_run("Agent-First Workflows Draft", date(2026, 7, 23), final=False)
        ordinary = find_sources(self.data_root, "agent first workflows")
        explicit = find_sources(self.data_root, "agent first workflows draft", drafts=True)
        self.assertEqual(ordinary.matches[0].related_run, finalized.name)
        self.assertEqual(ordinary.matches[0].finalization_state, "finalized")
        self.assertEqual(explicit.matches[0].finalization_state, "draft")
        self.assertTrue(explicit.matches[0].source_ref.endswith(":draft"))

    def test_aliases_are_searchable(self) -> None:
        run = self.source_run(
            "Unintended Consequences",
            date(2026, 7, 23),
            aliases=["The Benchmark Maximizer", "Bostrom post"],
        )
        result = find_sources(self.data_root, "Bostrom post")
        self.assertEqual(result.resolution, "clear")
        self.assertEqual(result.matches[0].related_run, run.name)

    def test_find_cli_returns_compact_ranked_metadata(self) -> None:
        run = self.source_run("Paperclip Systems", date(2026, 7, 23))
        result, stdout, stderr = self.run_cli("find", "paperclip", "--json")
        self.assertEqual((result, stderr), (0, ""))
        payload = json.loads(stdout)
        self.assertEqual(payload["resolution"], "clear")
        self.assertEqual(payload["matches"][0]["related_run"], run.name)
        self.assertIn("private_path", payload["matches"][0])

    def test_linkedin_to_x_adaptation_preserves_source_and_waits_for_variant(self) -> None:
        source = self.source_run("Bostrom and the Benchmark", date(2026, 7, 23))
        source_final = source / "formats" / "linkedin" / "final.md"
        before = source_final.read_bytes()
        result, stdout, stderr = self.run_cli(
            "adapt",
            f"run:{source.name}:linkedin:final",
            "--to",
            "x",
        )
        self.assertEqual((result, stderr), (0, ""))
        run = Path(next(line.split(": ", 1)[1] for line in stdout.splitlines() if line.startswith("run: ")))
        state = load_state(run)
        self.assertEqual(state["adaptation"]["source_run"], source.name)
        self.assertEqual(state["adaptation"]["source_final_artifact"], "formats/linkedin/final.md")
        self.assertEqual(state["format_states"]["x"]["pending_human_action"], "confirm_destination_variant")
        self.assertIsNone(state["format_states"]["x"]["variant"])
        self.assertEqual(source_final.read_bytes(), before)
        self.assertEqual(validation_errors(run, state, self.data_root), [])
        result, _, stderr = self.run_cli("set-x-variant", run.name, "single")
        self.assertEqual((result, stderr), (0, ""))
        self.assertEqual(load_state(run)["format_states"]["x"]["variant"], "single")

    def test_x_to_linkedin_adaptation_reuses_shared_material(self) -> None:
        source = self.source_run(
            "A Thread About Decision Logs",
            date(2026, 7, 23),
            format_name="x",
        )
        result, stdout, stderr = self.run_cli(
            "adapt",
            f"run:{source.name}:x:final",
            "--to",
            "linkedin",
        )
        self.assertEqual((result, stderr), (0, ""))
        run = Path(next(line.split(": ", 1)[1] for line in stdout.splitlines() if line.startswith("run: ")))
        state = load_state(run)
        self.assertEqual(state["requested_formats"], ["linkedin"])
        self.assertEqual(state["format_states"]["linkedin"]["status"], "active")
        self.assertEqual(
            (run / "content-brief.md").read_bytes(),
            (source / "content-brief.md").read_bytes(),
        )

    def test_repeated_adaptations_preserve_prior_outputs_and_lineage(self) -> None:
        source = self.source_run("Reusable Paperclip Post", date(2026, 7, 23))
        source_final = source / "formats" / "linkedin" / "final.md"
        before = source_final.read_bytes()
        runs: list[Path] = []
        for variant in ("single", "thread"):
            result, stdout, stderr = self.run_cli(
                "adapt",
                f"run:{source.name}:linkedin:final",
                "--to",
                "x",
                "--x-variant",
                variant,
            )
            self.assertEqual((result, stderr), (0, ""))
            runs.append(
                Path(next(line.split(": ", 1)[1] for line in stdout.splitlines() if line.startswith("run: ")))
            )
        self.assertNotEqual(runs[0], runs[1])
        self.assertTrue((runs[0] / "run.json").is_file())
        self.assertEqual(load_state(runs[1])["adaptation"]["prior_adaptation_runs"], [runs[0].name])
        self.assertEqual(source_final.read_bytes(), before)

    def test_adaptation_preserves_linked_vault_provenance(self) -> None:
        source = self.source_run("Vault-Backed Source", date(2026, 7, 23))
        result, stdout, stderr = self.run_cli(
            "vault",
            "capture",
            "--kind",
            "source",
            "--title",
            "Original interview source",
        )
        self.assertEqual((result, stderr), (0, ""))
        item_id = next(
            line.split(": ", 1)[1] for line in stdout.splitlines() if line.startswith("item_id: ")
        )
        result, _, stderr = self.run_cli(
            "vault",
            "link-run",
            item_id,
            source.name,
            "--role",
            "contributing",
        )
        self.assertEqual((result, stderr), (0, ""))
        result, stdout, stderr = self.run_cli(
            "adapt",
            f"run:{source.name}:linkedin:final",
            "--to",
            "x",
            "--x-variant",
            "single",
        )
        self.assertEqual((result, stderr), (0, ""))
        run = Path(next(line.split(": ", 1)[1] for line in stdout.splitlines() if line.startswith("run: ")))
        state = load_state(run)
        self.assertEqual(state["adaptation"]["source_vault_items"], [item_id])
        self.assertEqual(state["contributing_vault_items"], [item_id])
        item_text = (self.data_root / "vault" / "items" / f"{item_id}.md").read_text(encoding="utf-8")
        self.assertIn(run.name, item_text)

    def test_sparse_x_guidance_remains_a_calibration_state_and_private(self) -> None:
        source = self.source_run("Sparse Destination Evidence", date(2026, 7, 23))
        x_guidance = self.data_root / "creator" / "formats" / "x.md"
        x_guidance.write_text("# X\n\nPreferences: not established yet.\n", encoding="utf-8")
        before = x_guidance.read_bytes()
        templates_before = {
            path: path.read_bytes() for path in (ROOT / "templates").rglob("*") if path.is_file()
        }
        result, stdout, stderr = self.run_cli(
            "adapt",
            f"run:{source.name}:linkedin:final",
            "--to",
            "x",
        )
        self.assertEqual((result, stderr), (0, ""))
        run = Path(next(line.split(": ", 1)[1] for line in stdout.splitlines() if line.startswith("run: ")))
        self.assertEqual(x_guidance.read_bytes(), before)
        self.assertIsNone(load_state(run)["adaptation"]["destination_variant"])
        self.assertEqual(
            templates_before,
            {path: path.read_bytes() for path in (ROOT / "templates").rglob("*") if path.is_file()},
        )


if __name__ == "__main__":
    unittest.main()
