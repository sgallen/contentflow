"""Standard-library CLI for Content Flow run mechanics."""

from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from datetime import date
from pathlib import Path
from typing import Any, Sequence


STAGES = (
    "selected_idea",
    "research_decision",
    "research",
    "interview",
    "draft",
    "council",
    "revision",
    "finalization",
    "lessons",
    "complete",
)
STATUSES = ("active", "awaiting_human", "complete")
PENDING_ACTIONS = (
    "provide_idea_details",
    "confirm_research_decision",
    "answer_interview_question",
    "review_draft",
    "authorize_council",
    "approve_revision_plan",
    "resolve_revision_limit",
    "approve_final",
    "approve_lessons",
    "confirm_route",
    "resolve_research_scope",
    "none",
)
REQUIRED_FIELDS = (
    "id",
    "title",
    "format",
    "stage",
    "status",
    "research_required",
    "revision_round",
    "pending_human_action",
    "artifacts",
)
ARTIFACT_KEYS = (
    "spike",
    "research",
    "interview",
    "brief",
    "draft",
    "council",
    "revision_plan",
    "revision",
    "final",
    "lessons",
)
STAGE_ARTIFACTS = {
    "selected_idea": ("spike",),
    "research_decision": ("spike",),
    "research": ("spike", "research"),
    "interview": ("spike", "interview"),
    "draft": ("spike", "interview", "brief", "draft"),
    "council": ("spike", "interview", "brief", "draft", "council"),
    "revision": ("spike", "interview", "brief", "draft", "council", "revision_plan"),
    "finalization": ("spike", "interview", "brief", "draft", "council", "final"),
    "lessons": ("spike", "interview", "brief", "draft", "council", "final", "lessons"),
    "complete": ("spike", "interview", "brief", "draft", "council", "final", "lessons"),
}
ALLOWED_AWAITING_ACTIONS = {
    "selected_idea": {"provide_idea_details"},
    "research_decision": {"confirm_research_decision"},
    "research": {"resolve_research_scope"},
    "interview": {"answer_interview_question"},
    "draft": {"review_draft", "authorize_council"},
    "council": {"confirm_route", "approve_final"},
    "revision": {
        "approve_revision_plan",
        "resolve_revision_limit",
        "review_draft",
        "authorize_council",
        "approve_final",
    },
    "finalization": set(),
    "lessons": {"approve_lessons"},
    "complete": set(),
}
ARTIFACT_NAME_PATTERNS = {
    "spike": re.compile(r"spike\.md"),
    "research": re.compile(r"research-report(?:-\d{2})?\.md"),
    "interview": re.compile(r"interview\.md"),
    "brief": re.compile(r"content-brief\.md"),
    "draft": re.compile(r"draft-\d{2}\.md"),
    "council": re.compile(r"council-\d{2}\.md"),
    "revision_plan": re.compile(r"revision-plan-\d{2}\.md"),
    "revision": re.compile(r"draft-\d{2}\.md"),
    "final": re.compile(r"final\.md"),
    "lessons": re.compile(r"lesson-candidates\.md"),
}
DEFAULT_ARTIFACTS = {
    "spike": "spike.md",
    "research": None,
    "interview": None,
    "brief": None,
    "draft": None,
    "council": None,
    "revision_plan": None,
    "revision": None,
    "final": None,
    "lessons": None,
}


class CFError(Exception):
    """Expected user-facing CLI failure."""


def slugify(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    ascii_value = normalized.encode("ascii", "ignore").decode("ascii").lower()
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_value).strip("-")
    return (slug[:60].rstrip("-") or "untitled")


def make_run(root: Path, title: str, format_name: str, today: date | None = None) -> Path:
    if not title.strip():
        raise CFError("title must not be empty")
    if format_name != "linkedin":
        raise CFError("unsupported format; v0 supports only 'linkedin'")
    runs = root / "runs"
    runs.mkdir(parents=True, exist_ok=True)
    base = f"{(today or date.today()).isoformat()}-{slugify(title)}"
    run_dir = runs / base
    suffix = 2
    while run_dir.exists():
        run_dir = runs / f"{base}-{suffix}"
        suffix += 1
    run_dir.mkdir()

    state = {
        "id": run_dir.name,
        "title": title.strip(),
        "format": format_name,
        "stage": "selected_idea",
        "status": "awaiting_human",
        "research_required": None,
        "revision_round": 0,
        "pending_human_action": "provide_idea_details",
        "artifacts": dict(DEFAULT_ARTIFACTS),
    }
    _write_json(run_dir / "run.json", state)
    (run_dir / "spike.md").write_text(
        f"# {title.strip()}\n\n"
        "## Idea\n\n_To be supplied._\n\n"
        "## Why it may be worth developing\n\n_Unknown._\n\n"
        "## Original source or provenance\n\n_Unknown._\n\n"
        "## Known assumptions\n\n- None recorded yet.\n\n"
        "## Unresolved questions\n\n- What is the precise idea?\n\n"
        "## Confidentiality concerns\n\n_Not assessed; ask the human._\n",
        encoding="utf-8",
    )
    return run_dir


def _write_json(path: Path, data: dict[str, Any]) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    temporary.replace(path)


def load_state(run_dir: Path) -> dict[str, Any]:
    state_path = run_dir / "run.json"
    if not run_dir.is_dir():
        raise CFError(f"run directory does not exist: {run_dir}")
    if not state_path.is_file():
        raise CFError(f"missing state file: {state_path}")
    try:
        data = json.loads(state_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise CFError(f"invalid JSON in {state_path}: {exc}") from exc
    if not isinstance(data, dict):
        raise CFError("run.json must contain a JSON object")
    return data


def validation_errors(run_dir: Path, state: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for field in REQUIRED_FIELDS:
        if field not in state:
            errors.append(f"missing required field: {field}")

    stage = state.get("stage")
    status = state.get("status")
    action = state.get("pending_human_action")
    research_required = state.get("research_required")
    revision_round = state.get("revision_round")
    artifacts = state.get("artifacts")

    if state.get("id") != run_dir.name:
        errors.append("id must match the run directory name")
    if not isinstance(state.get("title"), str) or not state.get("title", "").strip():
        errors.append("title must be a non-empty string")
    if state.get("format") != "linkedin":
        errors.append("format must be 'linkedin' in v0")
    if stage not in STAGES:
        errors.append(f"stage must be one of: {', '.join(STAGES)}")
    if status not in STATUSES:
        errors.append(f"status must be one of: {', '.join(STATUSES)}")
    if action not in PENDING_ACTIONS:
        errors.append(f"pending_human_action must be one of: {', '.join(PENDING_ACTIONS)}")
    if research_required is not None and not isinstance(research_required, bool):
        errors.append("research_required must be null or a Boolean")
    if isinstance(revision_round, bool) or not isinstance(revision_round, int) or not 0 <= revision_round <= 2:
        errors.append("revision_round must be an integer from 0 to 2")
    if stage in STAGES[2:] and research_required is None:
        errors.append("research_required must be decided by the research stage")
    if stage == "research" and research_required is not True:
        errors.append("research stage requires research_required=true")
    if status == "awaiting_human" and action == "none":
        errors.append("awaiting_human status requires a pending human action")
    if status == "active" and action != "none":
        errors.append("active status requires pending_human_action='none'")
    if stage == "complete" and (status != "complete" or action != "none"):
        errors.append("complete stage requires complete status and no pending action")
    if status == "complete" and stage != "complete":
        errors.append("complete status requires stage='complete'")
    if status == "awaiting_human" and stage in ALLOWED_AWAITING_ACTIONS:
        allowed = ALLOWED_AWAITING_ACTIONS[stage]
        if action not in allowed:
            choices = ", ".join(sorted(allowed)) or "none"
            errors.append(f"stage '{stage}' cannot await '{action}'; allowed actions: {choices}")
    if stage == "revision" and action == "approve_revision_plan" and revision_round == 2:
        errors.append("revision_round=2 cannot await another revision plan; resolve the revision limit")

    if not isinstance(artifacts, dict):
        errors.append("artifacts must be a JSON object")
        return errors

    for key in ARTIFACT_KEYS:
        if key not in artifacts:
            errors.append(f"missing stable artifact key: {key}")

    for key, value in artifacts.items():
        if value is None:
            continue
        if not isinstance(value, str) or not value:
            errors.append(f"artifact '{key}' must be a non-empty relative path or null")
            continue
        path = Path(value)
        if path.is_absolute() or ".." in path.parts:
            errors.append(f"artifact '{key}' must stay inside the run directory")
            continue
        artifact_path = run_dir / path
        try:
            artifact_path.resolve().relative_to(run_dir.resolve())
        except ValueError:
            errors.append(f"artifact '{key}' must resolve inside the run directory")
            continue
        pattern = ARTIFACT_NAME_PATTERNS.get(key)
        if pattern is None:
            family = re.fullmatch(r"(draft|council|revision_plan|research)_\d+", key)
            if family:
                family_key = family.group(1)
                pattern = ARTIFACT_NAME_PATTERNS[family_key]
                version = int(key.rsplit("_", 1)[1])
                prefix = "revision-plan" if family_key == "revision_plan" else (
                    "research-report" if family_key == "research" else family_key
                )
                expected_name = f"{prefix}-{version:02d}.md"
                if path.name != expected_name:
                    errors.append(
                        f"versioned artifact '{key}' must point to '{expected_name}', not '{value}'"
                    )
            else:
                errors.append(f"unknown artifact key: {key}")
        if pattern is not None and not pattern.fullmatch(path.name):
            errors.append(f"artifact '{key}' has invalid filename: {value}")
        if len(path.parts) != 1:
            errors.append(f"artifact '{key}' must be a filename at the run root")
        if not artifact_path.is_file():
            errors.append(f"artifact '{key}' points to missing file: {value}")

    if stage in STAGE_ARTIFACTS:
        for key in STAGE_ARTIFACTS[stage]:
            value = artifacts.get(key)
            if not value:
                errors.append(f"stage '{stage}' requires artifact '{key}'")
    if research_required is True and stage in STAGES[3:] and not artifacts.get("research"):
        errors.append("research_required=true requires a research artifact after research stage")
    revision = artifacts.get("revision")
    if revision_round == 0 and revision:
        errors.append("revision_round=0 requires artifact 'revision' to be null")
    if revision_round == 0 and artifacts.get("draft") and artifacts.get("draft") != "draft-01.md":
        errors.append("revision_round=0 requires current artifact 'draft' to be 'draft-01.md'")
    if isinstance(revision_round, int) and not isinstance(revision_round, bool) and revision_round > 0:
        if not revision:
            errors.append("revision_round greater than 0 requires artifact 'revision'")
        elif artifacts.get("draft") != revision:
            errors.append("current 'draft' must match 'revision' after an applied revision")
        elif revision != f"draft-{revision_round + 1:02d}.md":
            errors.append("artifact 'revision' filename must match revision_round")

    for family, current_key in (
        ("draft", "draft"),
        ("council", "council"),
        ("revision_plan", "revision_plan"),
        ("research", "research"),
    ):
        history_versions = [
            int(key.rsplit("_", 1)[1])
            for key in artifacts
            if re.fullmatch(fr"{family}_\d+", key)
        ]
        current_value = artifacts.get(current_key)
        if history_versions and not current_value:
            errors.append(f"artifact history for '{current_key}' requires a current pointer")
        if history_versions and current_value:
            current_match = re.search(r"-(\d{2})\.md$", current_value)
            current_version = int(current_match.group(1)) if current_match else 0
            if current_version < max(history_versions):
                errors.append(f"current artifact '{current_key}' is older than its recorded history")
        versions = list(history_versions)
        if current_value:
            current_match = re.search(r"-(\d{2})\.md$", current_value)
            if current_match:
                versions.append(int(current_match.group(1)))
        maximum = 3 if family == "draft" else 2 if family == "revision_plan" else None
        if maximum is not None and any(version > maximum for version in versions):
            errors.append(f"artifact family '{family}' exceeds its maximum version {maximum:02d}")
    return errors


def resolve_run(value: str, root: Path) -> Path:
    path = Path(value).expanduser()
    if not path.is_absolute() and not path.exists() and len(path.parts) == 1:
        path = root / "runs" / path
    return path.resolve()


def cmd_new_run(args: argparse.Namespace, root: Path) -> int:
    run_dir = make_run(root, args.title, args.format)
    print(run_dir.relative_to(root))
    return 0


def cmd_status(args: argparse.Namespace, root: Path) -> int:
    run_dir = resolve_run(args.run, root)
    state = load_state(run_dir)
    print(f"run: {state.get('id', '<invalid>')}")
    print(f"title: {state.get('title', '<invalid>')}")
    print(f"stage: {state.get('stage', '<invalid>')}")
    print(f"status: {state.get('status', '<invalid>')}")
    print(f"research_required: {json.dumps(state.get('research_required'))}")
    print(f"revision_round: {state.get('revision_round', '<invalid>')}")
    print(f"pending_human_action: {state.get('pending_human_action', '<invalid>')}")
    existing = [f"{key}={value}" for key, value in state.get("artifacts", {}).items() if value]
    print(f"artifacts: {', '.join(existing) if existing else 'none'}")
    errors = validation_errors(run_dir, state)
    print(f"validation: {'ok' if not errors else f'{len(errors)} error(s)'}")
    return 0 if not errors else 1


def cmd_validate(args: argparse.Namespace, root: Path) -> int:
    run_dir = resolve_run(args.run, root)
    state = load_state(run_dir)
    errors = validation_errors(run_dir, state)
    if errors:
        print(f"INVALID {run_dir}", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    print(f"OK {run_dir}")
    return 0


def cmd_count(args: argparse.Namespace, root: Path) -> int:
    del root
    path = Path(args.file).expanduser()
    if not path.is_file():
        raise CFError(f"file does not exist: {path}")
    try:
        content = path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise CFError(f"file is not valid UTF-8: {path}") from exc
    if args.section:
        content = extract_markdown_section(content, args.section)
    print(len(content))
    return 0


def extract_markdown_section(content: str, title: str) -> str:
    """Return one named Markdown section without its heading or outer blank lines."""
    matches: list[tuple[int, int]] = []
    lines = content.splitlines(keepends=True)
    for index, line in enumerate(lines):
        match = re.match(r"^(#{1,6})\s+(.+?)\s*#*\s*(?:\r?\n)?$", line)
        if match and match.group(2).strip() == title:
            matches.append((index, len(match.group(1))))
    if not matches:
        raise CFError(f"Markdown section not found: {title}")
    if len(matches) > 1:
        raise CFError(f"Markdown section is ambiguous: {title}")
    start, level = matches[0]
    end = len(lines)
    for index in range(start + 1, len(lines)):
        match = re.match(r"^(#{1,6})\s+", lines[index])
        if match and len(match.group(1)) <= level:
            end = index
            break
    return "".join(lines[start + 1 : end]).strip("\r\n")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="cf", description="Content Flow run mechanics")
    subparsers = parser.add_subparsers(dest="command", required=True)

    new_run = subparsers.add_parser("new-run", help="create a new run without overwriting")
    new_run.add_argument("--title", required=True)
    new_run.add_argument("--format", default="linkedin")
    new_run.set_defaults(handler=cmd_new_run)

    status = subparsers.add_parser("status", help="show run state and validation summary")
    status.add_argument("run")
    status.set_defaults(handler=cmd_status)

    validate = subparsers.add_parser("validate", help="validate run state and artifacts")
    validate.add_argument("run")
    validate.set_defaults(handler=cmd_validate)

    count = subparsers.add_parser("count", help="count Unicode code points in a UTF-8 file")
    count.add_argument("file")
    count.add_argument("--section", help="count only the body of one exact Markdown heading")
    count.set_defaults(handler=cmd_count)
    return parser


def main(argv: Sequence[str] | None = None, root: Path | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    repository_root = root or Path(__file__).resolve().parents[2]
    try:
        return args.handler(args, repository_root)
    except CFError as exc:
        print(f"cf: error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
