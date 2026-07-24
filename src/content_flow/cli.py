"""Standard-library CLI for Content Flow run mechanics."""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import unicodedata
from datetime import date, datetime
from pathlib import Path
from typing import Any, Mapping, Sequence

from .vault import (
    ITEM_ID_PATTERN,
    VAULT_KINDS,
    VAULT_STATUSES,
    VaultFormatError,
    append_section,
    build_index,
    ensure_vault_dirs,
    item_body,
    load_item,
    read_all_items,
    resolve_item,
    section_text,
    utc_timestamp,
    valid_iso_date,
    validate_relationships,
    write_item,
)


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
STATUSES = ("active", "awaiting_human", "parked", "complete")
SUPPORTED_FORMATS = ("linkedin", "readme")
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
    # Human feedback may create a revision plan before any Council review.
    "revision": ("spike", "interview", "brief", "draft", "revision_plan"),
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
    "final": re.compile(r"final(?:-\d{2})?\.md"),
    "lessons": re.compile(r"lesson-candidates(?:-\d{2})?\.md"),
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
VAULT_RUN_FIELDS = (
    "origin_vault_items",
    "contributing_vault_items",
    "derived_vault_items",
    "linked_vault_items",
)
VAULT_STATUS_TRANSITIONS = {
    "inbox": {"ready", "developing", "parked", "archived"},
    "ready": {"inbox", "developing", "parked", "archived"},
    "developing": {"ready", "parked", "archived"},
    "parked": {"ready", "developing", "archived"},
    "archived": {"inbox"},
}
CREATOR_FILES = (
    Path("profile.md"),
    Path("voice.md"),
    Path("lessons.md"),
    Path("sources.md"),
    Path("formats/linkedin.md"),
    Path("formats/readme.md"),
)


class CFError(Exception):
    """Expected user-facing CLI failure."""


def resolve_data_root(
    explicit: str | None,
    repository_root: Path,
    environ: Mapping[str, str] | None = None,
) -> Path:
    """Resolve the active private root using the documented precedence."""
    environment = os.environ if environ is None else environ
    selected = explicit or environment.get("CONTENT_FLOW_HOME") or str(repository_root / ".content-flow")
    return Path(selected).expanduser().resolve()


def missing_creator_files(data_root: Path) -> list[Path]:
    creator_root = data_root / "creator"
    return [creator_root / relative for relative in CREATOR_FILES if not (creator_root / relative).is_file()]


def require_creator_setup(data_root: Path) -> None:
    missing = missing_creator_files(data_root)
    if missing:
        rendered = ", ".join(str(path) for path in missing)
        raise CFError(
            f"private creator setup is incomplete under {data_root}; missing: {rendered}. "
            "Run 'bin/cf init' with the same data-root selection."
        )


def find_git_root(path: Path) -> Path | None:
    """Return the nearest Git root at or above path."""
    probe = path
    while not probe.exists() and probe != probe.parent:
        probe = probe.parent
    result = subprocess.run(
        ["git", "-C", str(probe), "rev-parse", "--show-toplevel"],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return None
    return Path(result.stdout.strip()).resolve()


def git_ignore_status(data_root: Path) -> tuple[Path | None, bool | None]:
    """Return the containing Git root and whether it ignores data_root.

    If data_root is itself a Git repository, inspect its parent instead. The
    data repository intentionally tracks its own contents; the relevant leak
    check is whether a containing public repository ignores the whole root.
    """
    git_root = find_git_root(data_root)
    if git_root == data_root.resolve():
        git_root = find_git_root(data_root.parent)
    if git_root is None:
        return None, None
    try:
        relative = data_root.relative_to(git_root)
    except ValueError:
        return None, None
    if not relative.parts:
        return git_root, False
    tracked = subprocess.run(
        ["git", "-C", str(git_root), "ls-files", "--", relative.as_posix()],
        check=False,
        capture_output=True,
        text=True,
    )
    if tracked.stdout.strip():
        return git_root, False
    candidates = (relative.as_posix(), (relative / ".cf-ignore-probe").as_posix())
    for candidate in candidates:
        ignored = subprocess.run(
            ["git", "-C", str(git_root), "check-ignore", "--no-index", "-q", "--", candidate],
            check=False,
            capture_output=True,
            text=True,
        )
        if ignored.returncode == 0:
            return git_root, True
    return git_root, False


def git_safety_description(data_root: Path) -> str:
    own_git_root = find_git_root(data_root)
    git_root, ignored = git_ignore_status(data_root)
    if own_git_root == data_root.resolve():
        if git_root is None:
            return f"data root is Git repository {own_git_root}; no parent Git repository"
        if ignored:
            return (
                f"data root is Git repository {own_git_root}; "
                f"ignored by parent Git repository {git_root}"
            )
        return (
            f"data root is Git repository {own_git_root}; "
            f"NOT ignored by parent Git repository {git_root}"
        )
    if git_root is None:
        return "outside a Git repository"
    if ignored:
        return f"ignored by Git repository {git_root}"
    return f"NOT ignored by Git repository {git_root}"


def initialize_data_root(data_root: Path, repository_root: Path) -> None:
    git_root, ignored = git_ignore_status(data_root)
    if git_root is not None and not ignored:
        raise CFError(
            f"selected data root {data_root} is inside Git repository {git_root} and is not ignored; "
            "add an ignore rule before initializing private files"
        )

    template_root = repository_root / "templates" / "creator"
    missing_templates = [template_root / relative for relative in CREATOR_FILES if not (template_root / relative).is_file()]
    if missing_templates:
        raise CFError(f"creator templates are incomplete: {', '.join(str(path) for path in missing_templates)}")

    creator_root = data_root / "creator"
    missing = [relative for relative in CREATOR_FILES if not (creator_root / relative).exists()]
    if not missing:
        existing = [creator_root / relative for relative in CREATOR_FILES]
        raise CFError(f"refusing to overwrite existing creator files: {', '.join(str(path) for path in existing)}")

    (creator_root / "formats").mkdir(parents=True, exist_ok=True)
    ensure_vault_dirs(data_root)
    (data_root / "runs").mkdir(parents=True, exist_ok=True)
    for relative in missing:
        shutil.copyfile(template_root / relative, creator_root / relative)
    index_path = data_root / "vault" / "index.md"
    if not index_path.exists():
        index_path.write_text(build_index([]), encoding="utf-8")


def slugify(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    ascii_value = normalized.encode("ascii", "ignore").decode("ascii").lower()
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_value).strip("-")
    return (slug[:60].rstrip("-") or "untitled")


def make_run(
    root: Path,
    title: str,
    format_name: str,
    today: date | None = None,
    origin_vault_items: Sequence[str] = (),
    contributing_vault_items: Sequence[str] = (),
    derived_vault_items: Sequence[str] = (),
) -> Path:
    if not title.strip():
        raise CFError("title must not be empty")
    if format_name not in SUPPORTED_FORMATS:
        raise CFError(f"unsupported format; choose one of: {', '.join(SUPPORTED_FORMATS)}")
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
        "origin_vault_items": list(origin_vault_items),
        "contributing_vault_items": list(contributing_vault_items),
        "derived_vault_items": list(derived_vault_items),
        "linked_vault_items": list(
            dict.fromkeys((*origin_vault_items, *contributing_vault_items, *derived_vault_items))
        ),
        "parking_reason": None,
        "parked_at": None,
        "final_artifact": None,
    }
    _write_json(run_dir / "run.json", state)
    if format_name == "readme":
        spike = (
            f"# {title.strip()}\n\n"
            "## Target project and README\n\n"
            "_Inspect and record the exact project root and target README path._\n\n"
            "## Project purpose\n\n_Unknown until repository inspection and owner input._\n\n"
            "## Repository evidence\n\n"
            "_Inspect source, directory structure, documentation, CLI help, tests, examples, "
            "and package metadata as relevant._\n\n"
            "## Documentation claims\n\n_Not assessed yet._\n\n"
            "## Owner intent\n\n_Not established yet._\n\n"
            "## Known assumptions\n\n- None recorded yet.\n\n"
            "## Unresolved questions\n\n"
            "- Who is the primary reader and what should they do first?\n\n"
            "## Confidentiality concerns\n\n"
            "_Assess the public/private boundary before recording repository material._\n"
        )
    else:
        spike = (
            f"# {title.strip()}\n\n"
            "## Idea\n\n_To be supplied._\n\n"
            "## Why it may be worth developing\n\n_Unknown._\n\n"
            "## Original source or provenance\n\n_Unknown._\n\n"
            "## Known assumptions\n\n- None recorded yet.\n\n"
            "## Unresolved questions\n\n- What is the precise idea?\n\n"
            "## Confidentiality concerns\n\n_Not assessed; ask the human._\n"
        )
    (run_dir / "spike.md").write_text(spike, encoding="utf-8")
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


def validation_errors(
    run_dir: Path,
    state: dict[str, Any],
    data_root: Path | None = None,
) -> list[str]:
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
    if state.get("format") not in SUPPORTED_FORMATS:
        errors.append(f"format must be one of: {', '.join(SUPPORTED_FORMATS)}")
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
    if status == "parked":
        if stage == "complete":
            errors.append("a complete run cannot have parked status")
        if action != "none":
            errors.append("parked status requires pending_human_action='none'")
        if not isinstance(state.get("parking_reason"), str) or not state.get("parking_reason", "").strip():
            errors.append("parked status requires a non-empty parking_reason")
        parked_at = state.get("parked_at")
        if not isinstance(parked_at, str) or not re.fullmatch(
            r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", parked_at
        ):
            errors.append("parked status requires a UTC parked_at timestamp")
        else:
            try:
                datetime.strptime(parked_at, "%Y-%m-%dT%H:%M:%SZ")
            except ValueError:
                errors.append("parked_at must be a real UTC calendar timestamp")
        parked_from_status = state.get("parked_from_status")
        parked_from_action = state.get("parked_from_pending_human_action")
        if parked_from_status not in ("active", "awaiting_human"):
            errors.append("parked status requires parked_from_status active or awaiting_human")
        if parked_from_action not in PENDING_ACTIONS:
            errors.append("parked status requires a valid parked_from_pending_human_action")
        elif parked_from_status == "active" and parked_from_action != "none":
            errors.append("parked_from_status active requires prior pending action none")
        elif parked_from_status == "awaiting_human" and stage in ALLOWED_AWAITING_ACTIONS:
            if parked_from_action not in ALLOWED_AWAITING_ACTIONS[stage]:
                errors.append("parked run's prior human action is invalid for its preserved stage")
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

    vault_lists: dict[str, list[str]] = {}
    for key in VAULT_RUN_FIELDS:
        value = state.get(key, [])
        if not isinstance(value, list) or any(
            not isinstance(item_id, str) or not ITEM_ID_PATTERN.fullmatch(item_id) for item_id in value
        ):
            errors.append(f"{key} must be a list of safe vault item IDs")
            continue
        if len(value) != len(set(value)):
            errors.append(f"{key} must not contain duplicates")
        vault_lists[key] = value
    origins = vault_lists.get("origin_vault_items", [])
    contributors = vault_lists.get("contributing_vault_items", [])
    derived = vault_lists.get("derived_vault_items", [])
    linked = vault_lists.get("linked_vault_items", [])
    overlap = sorted(
        (set(origins) & set(contributors))
        | (set(origins) & set(derived))
        | (set(contributors) & set(derived))
    )
    if overlap:
        errors.append(f"vault items cannot have more than one run role: {', '.join(overlap)}")
    expected_linked = list(dict.fromkeys((*origins, *contributors, *derived)))
    if linked != expected_linked:
        errors.append(
            "linked_vault_items must equal origins followed by contributing and derived items"
        )
    if status == "parked" and not linked:
        errors.append("parked status requires at least one linked vault item")
    if data_root is not None:
        for item_id in linked:
            item_path = data_root / "vault" / "items" / f"{item_id}.md"
            if not item_path.is_file():
                errors.append(f"run references missing vault item: {item_id}")
                continue
            try:
                metadata, _ = load_item(item_path)
            except VaultFormatError as exc:
                errors.append(f"linked vault item '{item_id}' is invalid: {exc}")
                continue
            if state.get("id") not in metadata["related_runs"]:
                errors.append(f"linked vault item '{item_id}' does not reference run '{state.get('id')}'")
    final_artifact = state.get("final_artifact")
    if final_artifact is not None:
        if not isinstance(final_artifact, str) or Path(final_artifact).name != final_artifact:
            errors.append("final_artifact must be a run-root filename or null")
        elif artifacts.get("final") != final_artifact:
            errors.append("final_artifact must match artifacts.final")

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


def resolve_run(value: str, data_root: Path) -> Path:
    path = Path(value).expanduser()
    if not path.is_absolute() and len(path.parts) == 1 and value not in {".", ".."}:
        path = data_root / "runs" / path
    return path.resolve()


def cmd_init(args: argparse.Namespace, repository_root: Path) -> int:
    data_root = resolve_data_root(args.data_dir, repository_root)
    initialize_data_root(data_root, repository_root)
    print(f"data_root: {data_root}")
    print(f"git_safety: {git_safety_description(data_root)}")
    return 0


def cmd_data_root(args: argparse.Namespace, repository_root: Path) -> int:
    data_root = resolve_data_root(args.data_dir, repository_root)
    print(f"data_root: {data_root}")
    print(f"creator_setup: {'complete' if not missing_creator_files(data_root) else 'incomplete'}")
    print(f"git_safety: {git_safety_description(data_root)}")
    return 0


def cmd_new_run(args: argparse.Namespace, repository_root: Path) -> int:
    data_root = resolve_data_root(args.data_dir, repository_root)
    require_creator_setup(data_root)
    origin_ids = list(dict.fromkeys(args.vault_item or []))
    contributing_ids = list(dict.fromkeys(args.contributing_vault_item or []))
    if set(origin_ids) & set(contributing_ids):
        raise CFError("the same vault item cannot be both origin and contributing")
    records: list[tuple[Path, dict[str, Any], str, str]] = []
    requested_links = [(item_id, "origin") for item_id in origin_ids]
    requested_links.extend((item_id, "contributing") for item_id in contributing_ids)
    for item_id, role in requested_links:
        path = _resolve_valid_item(item_id, data_root)
        metadata, body = _load_valid_item(path)
        if metadata["status"] == "archived":
            raise CFError(
                f"vault item '{metadata['id']}' is archived and must be "
                "explicitly moved back into active consideration first"
            )
        records.append((path, metadata, body, role))
    title = (args.title or "").strip()
    if not title and records:
        title = records[0][1]["title"]
    if not title:
        raise CFError("--title is required unless at least one --vault-item is supplied")
    run_dir = make_run(
        data_root,
        title,
        args.format,
        origin_vault_items=origin_ids,
        contributing_vault_items=contributing_ids,
    )
    if records:
        source_blocks = []
        for _, metadata, body, role in records:
            source = metadata.get("source_url") or "No external URL recorded."
            useful = "\n\n".join(
                text
                for section in (
                    "Why this was saved",
                    "Source or raw material",
                    "Summary",
                    "Potential content angles",
                    "Useful specifics or excerpts",
                    "Open questions",
                    "Mining notes",
                    "Development history",
                )
                if (text := section_text(body, section))
            )
            source_blocks.append(
                f"### {metadata['title']} ({role})\n\n"
                f"- Vault item: `{metadata['id']}`\n"
                f"- Source: {source}\n"
                f"- Prior status: {metadata['status']}\n\n"
                f"- Previous related runs: {', '.join(metadata['related_runs']) or 'none'}\n"
                f"- Previous final artifacts: {', '.join(metadata['final_artifacts']) or 'none'}\n"
                f"- Successful uses: {metadata['use_count']}\n\n"
                f"{useful or '_No developed body material recorded._'}"
            )
        (run_dir / "spike.md").write_text(
            f"# {title}\n\n"
            "## Idea\n\nDevelop from the linked vault material below; the creator's precise thesis "
            "has not yet been established.\n\n"
            "## Why it may be worth developing\n\nSee the creator-supplied reasons preserved below.\n\n"
            "## Original source or provenance\n\n"
            + "\n\n".join(source_blocks)
            + "\n\n## Known assumptions\n\n- Selection does not establish the creator's point of view.\n\n"
            "## Unresolved questions\n\n- What distinctive thesis should connect or develop this material?\n\n"
            "## Reuse and duplication check\n\n"
            "- Review prior runs, final artifacts, explored angles, and Mining notes above.\n"
            "- Reuse is allowed; confirm that the new audience, angle, evidence, or format is distinct enough.\n\n"
            "## Confidentiality concerns\n\n_Not assessed; ask the human._\n",
            encoding="utf-8",
        )
        stamp = utc_timestamp()
        for path, metadata, body, role in records:
            if run_dir.name not in metadata["related_runs"]:
                metadata["related_runs"].append(run_dir.name)
            metadata["status"] = "developing"
            metadata["updated_at"] = stamp
            body = append_section(
                body,
                "Development history",
                f"- {stamp}: linked as {role} material for run `{run_dir.name}`.",
            )
            write_item(path, metadata, body)
        _rebuild_vault_index(data_root)
    print(f"data_root: {data_root}")
    print(f"run: {run_dir}")
    return 0


def _resolve_valid_item(value: str, data_root: Path) -> Path:
    try:
        return resolve_item(value, data_root)
    except VaultFormatError as exc:
        raise CFError(str(exc)) from exc


def _load_valid_item(path: Path) -> tuple[dict[str, Any], str]:
    try:
        return load_item(path)
    except VaultFormatError as exc:
        raise CFError(f"invalid vault item {path}: {exc}") from exc


def _rebuild_vault_index(data_root: Path) -> Path:
    ensure_vault_dirs(data_root)
    records, errors = read_all_items(data_root)
    if errors:
        raise CFError("cannot rebuild vault index:\n- " + "\n- ".join(errors))
    content = build_index((path, metadata) for path, metadata, _ in records)
    index = data_root / "vault" / "index.md"
    temporary = index.with_suffix(".md.tmp")
    temporary.write_text(content, encoding="utf-8")
    temporary.replace(index)
    return index


def _unique_item_path(data_root: Path, title: str, captured_at: str) -> tuple[str, Path]:
    base = f"{captured_at[:10]}-{slugify(title)}"
    item_id = base
    suffix = 2
    items = data_root / "vault" / "items"
    while (items / f"{item_id}.md").exists():
        item_id = f"{base}-{suffix}"
        suffix += 1
    return item_id, items / f"{item_id}.md"


def _capture_item(
    data_root: Path,
    *,
    title: str,
    kind: str,
    source_url: str | None = None,
    source_type: str | None = None,
    source_author: str | None = None,
    source_published_at: str | None = None,
    tags: Sequence[str] = (),
    note: str | None = None,
    material: str | None = None,
    status: str = "inbox",
) -> tuple[Path, dict[str, Any], str]:
    if not title.strip():
        raise CFError("title must not be empty")
    if kind not in VAULT_KINDS:
        raise CFError(f"kind must be one of: {', '.join(VAULT_KINDS)}")
    ensure_vault_dirs(data_root)
    stamp = utc_timestamp()
    item_id, path = _unique_item_path(data_root, title, stamp)
    metadata: dict[str, Any] = {
        "id": item_id,
        "title": title.strip(),
        "kind": kind,
        "status": status,
        "captured_at": stamp,
        "updated_at": stamp,
        "tags": list(dict.fromkeys(tag.strip() for tag in tags if tag.strip())),
        "related_items": [],
        "related_runs": [],
        "successful_runs": [],
        "use_count": 0,
        "derived_items": [],
        "source_items": [],
        "final_artifacts": [],
    }
    for key, value in (
        ("source_url", source_url),
        ("source_type", source_type),
        ("source_author", source_author),
        ("source_published_at", source_published_at),
    ):
        if value:
            metadata[key] = value
    body = item_body(reason=note, material=material, source_url=source_url)
    try:
        write_item(path, metadata, body, overwrite=False)
    except (VaultFormatError, FileExistsError) as exc:
        raise CFError(f"could not capture vault item: {exc}") from exc
    return path, metadata, body


def cmd_vault_capture(args: argparse.Namespace, repository_root: Path) -> int:
    data_root = resolve_data_root(args.data_dir, repository_root)
    require_creator_setup(data_root)
    # Refuse to hide a pre-existing malformed canonical item behind a partial index.
    _, existing_errors = read_all_items(data_root)
    if existing_errors:
        raise CFError("vault contains malformed items:\n- " + "\n- ".join(existing_errors))
    path, metadata, _ = _capture_item(
        data_root,
        title=args.title,
        kind=args.kind,
        source_url=args.url,
        source_type=args.source_type,
        source_author=args.source_author,
        source_published_at=args.source_published_at,
        tags=args.tag or (),
        note=args.note,
        material=args.material,
    )
    _rebuild_vault_index(data_root)
    print(f"data_root: {data_root}")
    print(f"item_id: {metadata['id']}")
    print(f"item: {path}")
    return 0


def cmd_vault_list(args: argparse.Namespace, repository_root: Path) -> int:
    data_root = resolve_data_root(args.data_dir, repository_root)
    records, errors = read_all_items(data_root)
    if errors:
        raise CFError("vault contains malformed items:\n- " + "\n- ".join(errors))
    selected = []
    for path, metadata, body in records:
        del path, body
        if args.status and metadata["status"] != args.status:
            continue
        if args.kind and metadata["kind"] != args.kind:
            continue
        if args.tag and args.tag not in metadata["tags"]:
            continue
        if args.successful == "yes" and metadata["use_count"] == 0:
            continue
        if args.successful == "no" and metadata["use_count"] > 0:
            continue
        selected.append(metadata)
    selected.sort(key=lambda item: (item["updated_at"], item["id"]), reverse=True)
    print("ID\tTITLE\tKIND\tSTATUS\tSUCCESSFUL_USES\tUPDATED")
    for metadata in selected:
        print(
            f"{metadata['id']}\t{metadata['title']}\t{metadata['kind']}\t"
            f"{metadata['status']}\t{metadata['use_count']}\t{metadata['updated_at'][:10]}"
        )
    return 0


def cmd_vault_show(args: argparse.Namespace, repository_root: Path) -> int:
    data_root = resolve_data_root(args.data_dir, repository_root)
    path = _resolve_valid_item(args.item, data_root)
    metadata, _ = _load_valid_item(path)
    print(f"path: {path}")
    print(
        "usage: "
        f"{metadata['use_count']} successful use(s); "
        f"last used {metadata.get('last_used_at') or 'never'}"
    )
    print(f"related_runs: {', '.join(metadata['related_runs']) or 'none'}")
    print(f"successful_runs: {', '.join(metadata['successful_runs']) or 'none'}")
    print(f"final_artifacts: {', '.join(metadata['final_artifacts']) or 'none'}")
    print(f"source_items: {', '.join(metadata['source_items']) or 'none'}")
    print(f"derived_items: {', '.join(metadata['derived_items']) or 'none'}")
    print("--- canonical item ---")
    print(path.read_text(encoding="utf-8"), end="")
    return 0


def cmd_vault_update(args: argparse.Namespace, repository_root: Path) -> int:
    data_root = resolve_data_root(args.data_dir, repository_root)
    path = _resolve_valid_item(args.item, data_root)
    metadata, body = _load_valid_item(path)
    if args.status is None and args.revisit_after is None and not args.clear_revisit_after:
        raise CFError("vault update requires --status, --revisit-after, or --clear-revisit-after")
    if args.status is not None and args.status != metadata["status"]:
        if args.status not in VAULT_STATUS_TRANSITIONS[metadata["status"]]:
            raise CFError(f"invalid vault status transition: {metadata['status']} -> {args.status}")
        metadata["status"] = args.status
    if args.revisit_after is not None:
        if not valid_iso_date(args.revisit_after):
            raise CFError("revisit-after must be a real ISO date like 2026-08-01")
        metadata["revisit_after"] = args.revisit_after
    if args.clear_revisit_after:
        metadata.pop("revisit_after", None)
    metadata["updated_at"] = utc_timestamp()
    write_item(path, metadata, body)
    _rebuild_vault_index(data_root)
    print(f"updated: {path}")
    return 0


def _load_run_for_data_root(value: str, data_root: Path) -> tuple[Path, dict[str, Any]]:
    run_dir = resolve_run(value, data_root)
    if run_dir.parent != data_root / "runs":
        raise CFError("vault/run linkage requires a run inside the active data root")
    return run_dir, load_state(run_dir)


def _status_after_closing_run(
    data_root: Path,
    metadata: dict[str, Any],
    closing_run_id: str,
    *,
    inactive_status: str,
) -> str:
    """Keep an item developing only while another unfinished linked run is active."""
    for run_id in metadata["related_runs"]:
        if run_id == closing_run_id:
            continue
        state_path = data_root / "runs" / run_id / "run.json"
        if not state_path.is_file():
            continue
        try:
            state = json.loads(state_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            continue
        if state.get("final_artifact"):
            continue
        if state.get("status") in ("active", "awaiting_human"):
            return "developing"
    return inactive_status


def _link_item_and_run(
    data_root: Path,
    item_path: Path,
    metadata: dict[str, Any],
    body: str,
    run_dir: Path,
    state: dict[str, Any],
    role: str,
) -> None:
    origin = list(state.get("origin_vault_items", []))
    contributing = list(state.get("contributing_vault_items", []))
    derived = list(state.get("derived_vault_items", []))
    roles = {"origin": origin, "contributing": contributing, "derived": derived}
    target = roles[role]
    other_roles = [name for name, values in roles.items() if name != role and metadata["id"] in values]
    if other_roles:
        raise CFError(
            f"vault item is already linked to the run with role '{other_roles[0]}'"
        )
    if metadata["id"] not in target:
        target.append(metadata["id"])
    linked = list(dict.fromkeys((*origin, *contributing, *derived)))
    state["origin_vault_items"] = origin
    state["contributing_vault_items"] = contributing
    state["derived_vault_items"] = derived
    state["linked_vault_items"] = linked
    if run_dir.name not in metadata["related_runs"]:
        metadata["related_runs"].append(run_dir.name)
    stamp = utc_timestamp()
    if metadata["status"] == "archived":
        raise CFError(
            f"vault item '{metadata['id']}' is archived and must be explicitly restored before linking"
        )
    if state.get("status") in ("active", "awaiting_human"):
        metadata["status"] = "developing"
    metadata["updated_at"] = stamp
    body = append_section(
        body,
        "Development history",
        f"- {stamp}: linked as {role} material for run `{run_dir.name}`.",
    )
    write_item(item_path, metadata, body)
    _write_json(run_dir / "run.json", state)


def cmd_vault_link_run(args: argparse.Namespace, repository_root: Path) -> int:
    data_root = resolve_data_root(args.data_dir, repository_root)
    item_path = _resolve_valid_item(args.item, data_root)
    metadata, body = _load_valid_item(item_path)
    run_dir, state = _load_run_for_data_root(args.run, data_root)
    _link_item_and_run(data_root, item_path, metadata, body, run_dir, state, args.role)
    _rebuild_vault_index(data_root)
    print(f"linked: {metadata['id']} -> {run_dir.name} ({args.role})")
    return 0


def cmd_vault_rebuild_index(args: argparse.Namespace, repository_root: Path) -> int:
    data_root = resolve_data_root(args.data_dir, repository_root)
    require_creator_setup(data_root)
    index = _rebuild_vault_index(data_root)
    print(f"index: {index}")
    return 0


def cmd_vault_validate(args: argparse.Namespace, repository_root: Path) -> int:
    data_root = resolve_data_root(args.data_dir, repository_root)
    errors, warnings = validate_relationships(data_root)
    runs_root = data_root / "runs"
    if runs_root.is_dir():
        for run_dir in sorted(path for path in runs_root.iterdir() if path.is_dir()):
            try:
                state = load_state(run_dir)
            except CFError as exc:
                errors.append(str(exc))
                continue
            errors.extend(f"{run_dir}: {error}" for error in validation_errors(run_dir, state, data_root))
    for warning in warnings:
        print(f"WARNING: {warning}", file=sys.stderr)
    if errors:
        print(f"INVALID {data_root / 'vault'}", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    print(f"OK {data_root / 'vault'}")
    return 0


def cmd_vault_park_run(args: argparse.Namespace, repository_root: Path) -> int:
    data_root = resolve_data_root(args.data_dir, repository_root)
    run_dir, state = _load_run_for_data_root(args.run, data_root)
    if state.get("status") in ("parked", "complete"):
        raise CFError(f"cannot park a run with status '{state.get('status')}'")
    assessment = ""
    if args.assessment_file:
        assessment_path = Path(args.assessment_file).expanduser()
        if not assessment_path.is_file():
            raise CFError(f"assessment file does not exist: {assessment_path}")
        assessment = assessment_path.read_text(encoding="utf-8").strip()
    stamp = utc_timestamp()
    origins = list(state.get("origin_vault_items", []))
    if not origins:
        path, metadata, body = _capture_item(
            data_root,
            title=f"Parked: {state['title']}",
            kind="run-fragment",
            note=args.reason,
            material=f"Preserved in run `{run_dir.name}` at `{run_dir}`.",
            status="parked",
        )
        origins = [metadata["id"]]
        state["origin_vault_items"] = origins
        state["linked_vault_items"] = list(
            dict.fromkeys(
                (
                    *origins,
                    *state.get("contributing_vault_items", []),
                    *state.get("derived_vault_items", []),
                )
            )
        )
    for item_id in state["linked_vault_items"]:
        if not (data_root / "vault" / "items" / f"{item_id}.md").is_file():
            continue
        path = _resolve_valid_item(item_id, data_root)
        metadata, body = _load_valid_item(path)
        if run_dir.name not in metadata["related_runs"]:
            metadata["related_runs"].append(run_dir.name)
        if metadata["status"] != "archived":
            role_is_parked = item_id in origins or item_id in state.get("derived_vault_items", [])
            metadata["status"] = _status_after_closing_run(
                data_root,
                metadata,
                run_dir.name,
                inactive_status="parked" if role_is_parked else "ready",
            )
        metadata["updated_at"] = stamp
        body = append_section(
            body,
            "Development history",
            f"- {stamp}: run `{run_dir.name}` was parked. Reason: {args.reason}",
        )
        parking_entry = f"### {stamp} — run `{run_dir.name}`\n\nReason: {args.reason}"
        if assessment:
            parking_entry += f"\n\n{assessment}"
        body = append_section(body, "Parking notes", parking_entry)
        write_item(path, metadata, body)
    state["parked_from_status"] = state["status"]
    state["parked_from_pending_human_action"] = state["pending_human_action"]
    state["status"] = "parked"
    state["pending_human_action"] = "none"
    state["parking_reason"] = args.reason
    state["parked_at"] = stamp
    _write_json(run_dir / "run.json", state)
    _rebuild_vault_index(data_root)
    print(f"parked: {run_dir}")
    print(f"vault_items: {', '.join(state['linked_vault_items'])}")
    return 0


def cmd_vault_resume_run(args: argparse.Namespace, repository_root: Path) -> int:
    data_root = resolve_data_root(args.data_dir, repository_root)
    run_dir, state = _load_run_for_data_root(args.run, data_root)
    if state.get("status") != "parked":
        raise CFError("only a parked run can be resumed")
    restored_status = state.get("parked_from_status")
    restored_action = state.get("parked_from_pending_human_action")
    if restored_status not in ("active", "awaiting_human") or restored_action not in PENDING_ACTIONS:
        raise CFError("parked run is missing valid pre-park status")
    state["status"] = restored_status
    state["pending_human_action"] = restored_action
    state["resumed_at"] = utc_timestamp()
    stamp = state["resumed_at"]
    for item_id in state.get("linked_vault_items", []):
        path = _resolve_valid_item(item_id, data_root)
        metadata, body = _load_valid_item(path)
        if metadata["status"] != "archived":
            metadata["status"] = "developing"
        metadata["updated_at"] = stamp
        body = append_section(body, "Development history", f"- {stamp}: resumed run `{run_dir.name}`.")
        write_item(path, metadata, body)
    _write_json(run_dir / "run.json", state)
    _rebuild_vault_index(data_root)
    print(f"resumed: {run_dir}")
    return 0


def cmd_vault_finalize_run(args: argparse.Namespace, repository_root: Path) -> int:
    data_root = resolve_data_root(args.data_dir, repository_root)
    run_dir, state = _load_run_for_data_root(args.run, data_root)
    final_value = state.get("artifacts", {}).get("final")
    if not isinstance(final_value, str) or not (run_dir / final_value).is_file():
        raise CFError("run does not have a valid final artifact")
    stamp = utc_timestamp()
    artifact_reference = f"runs/{run_dir.name}/{final_value}"
    for item_id in state.get("linked_vault_items", []):
        path = _resolve_valid_item(item_id, data_root)
        metadata, body = _load_valid_item(path)
        if run_dir.name not in metadata["related_runs"]:
            metadata["related_runs"].append(run_dir.name)
        new_success = run_dir.name not in metadata["successful_runs"]
        if new_success:
            metadata["successful_runs"].append(run_dir.name)
        if artifact_reference not in metadata["final_artifacts"]:
            metadata["final_artifacts"].append(artifact_reference)
        metadata["use_count"] = len(metadata["successful_runs"])
        if new_success:
            metadata["last_used_at"] = stamp
        if metadata["status"] != "archived":
            metadata["status"] = _status_after_closing_run(
                data_root, metadata, run_dir.name, inactive_status="ready"
            )
        metadata["updated_at"] = stamp
        if new_success:
            body = append_section(
                body,
                "Development history",
                f"- {stamp}: run `{run_dir.name}` produced final artifact `{artifact_reference}`; "
                "the item remains available for reuse.",
            )
        write_item(path, metadata, body)
    state["final_artifact"] = final_value
    _write_json(run_dir / "run.json", state)
    _rebuild_vault_index(data_root)
    print(f"linked final: {run_dir / final_value}")
    return 0


def cmd_status(args: argparse.Namespace, repository_root: Path) -> int:
    data_root = resolve_data_root(args.data_dir, repository_root)
    run_dir = resolve_run(args.run, data_root)
    state = load_state(run_dir)
    print(f"data_root: {data_root}")
    print(f"run_path: {run_dir}")
    print(f"run: {state.get('id', '<invalid>')}")
    print(f"title: {state.get('title', '<invalid>')}")
    print(f"format: {state.get('format', '<invalid>')}")
    print(f"stage: {state.get('stage', '<invalid>')}")
    print(f"status: {state.get('status', '<invalid>')}")
    print(f"research_required: {json.dumps(state.get('research_required'))}")
    print(f"revision_round: {state.get('revision_round', '<invalid>')}")
    print(f"pending_human_action: {state.get('pending_human_action', '<invalid>')}")
    linked = state.get("linked_vault_items", [])
    print(f"linked_vault_items: {', '.join(linked) if isinstance(linked, list) and linked else 'none'}")
    existing = [f"{key}={value}" for key, value in state.get("artifacts", {}).items() if value]
    print(f"artifacts: {', '.join(existing) if existing else 'none'}")
    relationship_root = data_root if run_dir.parent == data_root / "runs" else None
    errors = validation_errors(run_dir, state, relationship_root)
    print(f"validation: {'ok' if not errors else f'{len(errors)} error(s)'}")
    return 0 if not errors else 1


def cmd_validate(args: argparse.Namespace, repository_root: Path) -> int:
    data_root = resolve_data_root(args.data_dir, repository_root)
    run_dir = resolve_run(args.run, data_root)
    state = load_state(run_dir)
    relationship_root = data_root if run_dir.parent == data_root / "runs" else None
    errors = validation_errors(run_dir, state, relationship_root)
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
    parser = argparse.ArgumentParser(
        prog="cf",
        description="Content Flow run mechanics",
        epilog="See DATA_ROOT.md for private data-root selection and safety policy.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    init = subparsers.add_parser("init", help="initialize the private data root from creator templates")
    init.add_argument("--data-dir", help="private data root (overrides CONTENT_FLOW_HOME)")
    init.set_defaults(handler=cmd_init)

    data_root = subparsers.add_parser("data-root", help="report the resolved private data root")
    data_root.add_argument("--data-dir", help="private data root (overrides CONTENT_FLOW_HOME)")
    data_root.set_defaults(handler=cmd_data_root)

    new_run = subparsers.add_parser("new-run", help="create a new run without overwriting")
    new_run.add_argument("--title")
    new_run.add_argument("--format", choices=SUPPORTED_FORMATS, default="linkedin")
    new_run.add_argument(
        "--vault-item",
        action="append",
        help="origin vault item ID (repeat for multiple origins)",
    )
    new_run.add_argument(
        "--contributing-vault-item",
        action="append",
        help="contributing vault item ID (repeat as needed)",
    )
    new_run.add_argument("--data-dir", help="private data root (overrides CONTENT_FLOW_HOME)")
    new_run.set_defaults(handler=cmd_new_run)

    status = subparsers.add_parser("status", help="show run state and validation summary")
    status.add_argument("run")
    status.add_argument("--data-dir", help="private data root (overrides CONTENT_FLOW_HOME)")
    status.set_defaults(handler=cmd_status)

    validate = subparsers.add_parser("validate", help="validate run state and artifacts")
    validate.add_argument("run")
    validate.add_argument("--data-dir", help="private data root (overrides CONTENT_FLOW_HOME)")
    validate.set_defaults(handler=cmd_validate)

    count = subparsers.add_parser("count", help="count Unicode code points in a UTF-8 file")
    count.add_argument("file")
    count.add_argument("--section", help="count only the body of one exact Markdown heading")
    count.set_defaults(handler=cmd_count)

    vault = subparsers.add_parser("vault", help="capture and manage private vault material")
    vault_subparsers = vault.add_subparsers(dest="vault_command", required=True)

    capture = vault_subparsers.add_parser("capture", help="quick-capture a canonical vault item")
    capture.add_argument("--kind", required=True, choices=VAULT_KINDS)
    capture.add_argument("--title", required=True)
    capture.add_argument("--url", help="exact source URL")
    capture.add_argument("--source-type")
    capture.add_argument("--source-author")
    capture.add_argument("--source-published-at")
    capture.add_argument("--tag", action="append", help="tag (repeat as needed)")
    capture.add_argument("--note", help="creator-supplied reason for saving")
    capture.add_argument("--material", help="short raw material when there is no URL or in addition to it")
    capture.add_argument("--data-dir", help="private data root (overrides CONTENT_FLOW_HOME)")
    capture.set_defaults(handler=cmd_vault_capture)

    vault_list = vault_subparsers.add_parser("list", help="list vault items in compact form")
    vault_list.add_argument("--status", choices=VAULT_STATUSES)
    vault_list.add_argument("--kind", choices=VAULT_KINDS)
    vault_list.add_argument("--tag")
    vault_list.add_argument(
        "--successful",
        choices=("yes", "no"),
        help="filter by whether the item has prior successful completed uses",
    )
    vault_list.add_argument("--data-dir", help="private data root (overrides CONTENT_FLOW_HOME)")
    vault_list.set_defaults(handler=cmd_vault_list)

    show = vault_subparsers.add_parser("show", help="show one canonical vault item")
    show.add_argument("item", help="item ID or explicit path under vault/items")
    show.add_argument("--data-dir", help="private data root (overrides CONTENT_FLOW_HOME)")
    show.set_defaults(handler=cmd_vault_show)

    update = vault_subparsers.add_parser("update", help="make safe mechanical metadata changes")
    update.add_argument("item")
    update.add_argument("--status", choices=VAULT_STATUSES)
    revisit_group = update.add_mutually_exclusive_group()
    revisit_group.add_argument("--revisit-after")
    revisit_group.add_argument("--clear-revisit-after", action="store_true")
    update.add_argument("--data-dir", help="private data root (overrides CONTENT_FLOW_HOME)")
    update.set_defaults(handler=cmd_vault_update)

    link = vault_subparsers.add_parser("link-run", help="record a bidirectional item/run link")
    link.add_argument("item")
    link.add_argument("run")
    link.add_argument(
        "--role",
        choices=("origin", "contributing", "derived"),
        default="contributing",
    )
    link.add_argument("--data-dir", help="private data root (overrides CONTENT_FLOW_HOME)")
    link.set_defaults(handler=cmd_vault_link_run)

    rebuild = vault_subparsers.add_parser("rebuild-index", help="regenerate index.md from item metadata")
    rebuild.add_argument("--data-dir", help="private data root (overrides CONTENT_FLOW_HOME)")
    rebuild.set_defaults(handler=cmd_vault_rebuild_index)

    vault_validate = vault_subparsers.add_parser("validate", help="validate all vault items and relationships")
    vault_validate.add_argument("--data-dir", help="private data root (overrides CONTENT_FLOW_HOME)")
    vault_validate.set_defaults(handler=cmd_vault_validate)

    park = vault_subparsers.add_parser("park-run", help="preserve and link a run as parked material")
    park.add_argument("run")
    park.add_argument("--reason", required=True)
    park.add_argument("--assessment-file", help="Markdown parking assessment prepared by the orchestrator")
    park.add_argument("--data-dir", help="private data root (overrides CONTENT_FLOW_HOME)")
    park.set_defaults(handler=cmd_vault_park_run)

    resume = vault_subparsers.add_parser("resume-run", help="restore a parked run and its origin items")
    resume.add_argument("run")
    resume.add_argument("--data-dir", help="private data root (overrides CONTENT_FLOW_HOME)")
    resume.set_defaults(handler=cmd_vault_resume_run)

    finalize = vault_subparsers.add_parser(
        "finalize-run",
        help="record successful usage and return reusable linked items to ready",
    )
    finalize.add_argument("run")
    finalize.add_argument("--data-dir", help="private data root (overrides CONTENT_FLOW_HOME)")
    finalize.set_defaults(handler=cmd_vault_finalize_run)
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
