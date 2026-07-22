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
    "none",
)
REQUIRED_FIELDS = (
    "id",
    "title",
    "format",
    "stage",
    "status",
    "research_required",
    "pending_human_action",
    "artifacts",
)
STAGE_ARTIFACTS = {
    "selected_idea": ("spike",),
    "research_decision": ("spike",),
    "research": ("spike", "research"),
    "interview": ("spike", "interview"),
    "draft": ("spike", "interview", "brief", "draft"),
    "council": ("spike", "brief", "draft", "council"),
    "revision": ("spike", "draft", "council", "revision_plan"),
    "finalization": ("spike", "draft", "final"),
    "lessons": ("spike", "draft", "final", "lessons"),
    "complete": ("spike", "draft", "final", "lessons"),
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
    "council_2": None,
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
    if research_required not in (None, True, False):
        errors.append("research_required must be null or a Boolean")
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

    if not isinstance(artifacts, dict):
        errors.append("artifacts must be a JSON object")
        return errors

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
        if not (run_dir / path).is_file():
            errors.append(f"artifact '{key}' points to missing file: {value}")

    if stage in STAGE_ARTIFACTS:
        for key in STAGE_ARTIFACTS[stage]:
            value = artifacts.get(key)
            if not value:
                errors.append(f"stage '{stage}' requires artifact '{key}'")
    if research_required is True and stage in STAGES[3:] and not artifacts.get("research"):
        errors.append("research_required=true requires a research artifact after research stage")
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
    print(f"pending_human_action: {state.get('pending_human_action', '<invalid>')}")
    existing = [key for key, value in state.get("artifacts", {}).items() if value]
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
    print(len(content))
    return 0


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
