"""Standard-library CLI for Content Flow run mechanics."""

from __future__ import annotations

import argparse
import hashlib
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

from .discovery import SOURCE_REF_PATTERN, FindResult, find_sources
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
SUPPORTED_FORMATS = ("linkedin", "x", "readme")
SOCIAL_FORMATS = ("linkedin", "x")
X_VARIANTS = ("single", "thread", "standalone")
X_POST_CHARACTER_LIMIT = 280
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
    "confirm_destination_variant",
    "none",
)
REQUIRED_FIELDS = (
    "schema_version",
    "id",
    "title",
    "requested_formats",
    "primary_format",
    "active_format",
    "status",
    "shared_state",
    "shared_artifacts",
    "format_states",
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
DEFAULT_SHARED_ARTIFACTS = {
    "spike": "spike.md",
    "research": None,
    "interview": None,
    "brief": None,
}
DEFAULT_FORMAT_ARTIFACTS = {
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
    Path("formats/x.md"),
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
    formats: str | Sequence[str],
    today: date | None = None,
    origin_vault_items: Sequence[str] = (),
    contributing_vault_items: Sequence[str] = (),
    derived_vault_items: Sequence[str] = (),
    primary_format: str | None = None,
    x_variant: str | None = None,
) -> Path:
    if not title.strip():
        raise CFError("title must not be empty")
    requested_formats = [formats] if isinstance(formats, str) else list(formats)
    if not requested_formats:
        raise CFError("at least one --format is required")
    unsupported = [name for name in requested_formats if name not in SUPPORTED_FORMATS]
    if unsupported:
        raise CFError(
            f"unsupported format '{unsupported[0]}'; choose one of: {', '.join(SUPPORTED_FORMATS)}"
        )
    if len(requested_formats) != len(set(requested_formats)):
        raise CFError("requested formats must not contain duplicates")
    if primary_format is not None and primary_format not in requested_formats:
        raise CFError("primary format must be included in requested formats")
    if (
        primary_format == "readme"
        and len(requested_formats) > 1
    ):
        raise CFError("README cannot be the primary format in a mixed social/document run")
    if x_variant is not None and "x" not in requested_formats:
        raise CFError("--x-variant requires X in requested formats")
    if x_variant is not None and x_variant not in X_VARIANTS:
        raise CFError(f"X variant must be one of: {', '.join(X_VARIANTS)}")
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
        "schema_version": 2,
        "id": run_dir.name,
        "title": title.strip(),
        "requested_formats": requested_formats,
        "primary_format": primary_format,
        "active_format": None,
        "status": "awaiting_human",
        "shared_state": {
            "stage": "selected_idea",
            "status": "awaiting_human",
            "research_required": None,
            "pending_human_action": "provide_idea_details",
        },
        "shared_artifacts": dict(DEFAULT_SHARED_ARTIFACTS),
        "format_states": {
            name: {
                "variant": x_variant if name == "x" else None,
                "angle": None,
                "stage": "pending",
                "status": "pending",
                "revision_round": 0,
                "pending_human_action": "none",
                "disposition": "active",
                "artifacts": dict(DEFAULT_FORMAT_ARTIFACTS),
                "final_artifact": None,
            }
            for name in requested_formats
        },
        "origin_vault_items": list(origin_vault_items),
        "contributing_vault_items": list(contributing_vault_items),
        "derived_vault_items": list(derived_vault_items),
        "linked_vault_items": list(
            dict.fromkeys((*origin_vault_items, *contributing_vault_items, *derived_vault_items))
        ),
        "parking_reason": None,
        "parked_at": None,
    }
    _write_json(run_dir / "run.json", state)
    if requested_formats == ["readme"]:
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
    for format_name in requested_formats:
        (run_dir / "formats" / format_name).mkdir(parents=True, exist_ok=True)
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


def _safe_artifact_path(run_dir: Path, value: Any, prefix: Path, key: str) -> list[str]:
    errors: list[str] = []
    if value is None:
        return errors
    if not isinstance(value, str) or not value:
        return [f"artifact '{key}' must be a non-empty relative path or null"]
    path = Path(value)
    if path.is_absolute() or ".." in path.parts:
        return [f"artifact '{key}' must stay inside the run directory"]
    expected_parent = prefix
    if path.parent != expected_parent:
        errors.append(f"artifact '{key}' must be under '{expected_parent.as_posix()}/'")
    artifact_path = run_dir / path
    try:
        artifact_path.resolve().relative_to(run_dir.resolve())
    except ValueError:
        errors.append(f"artifact '{key}' must resolve inside the run directory")
        return errors
    if not artifact_path.is_file():
        errors.append(f"artifact '{key}' points to missing file: {value}")
    return errors


def _validate_x_content(path: Path, variant: str) -> list[str]:
    try:
        content = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        return [f"cannot read X artifact {path}: {exc}"]
    marker = re.search(r"<!--\s*cf:x-variant:\s*([a-z]+)\s*-->", content)
    errors: list[str] = []
    if not marker:
        return [f"X artifact must declare '<!-- cf:x-variant: {variant} -->': {path.name}"]
    if marker.group(1) != variant:
        errors.append(f"X artifact variant marker '{marker.group(1)}' does not match '{variant}'")
    try:
        recommended = extract_markdown_section(content, "Recommended final version")
    except CFError as exc:
        return errors + [f"{path.name}: {exc}"]
    headings = list(re.finditer(r"^###\s+(.+?)\s*$", recommended, flags=re.MULTILINE))
    posts: list[tuple[str, str]] = []
    for index, match in enumerate(headings):
        start = match.end()
        end = headings[index + 1].start() if index + 1 < len(headings) else len(recommended)
        posts.append((match.group(1).strip(), recommended[start:end].strip()))
    expected = {
        "single": re.compile(r"Post"),
        "thread": re.compile(r"Post ([1-9]\d*)"),
        "standalone": re.compile(r"Standalone ([1-9]\d*)"),
    }[variant]
    if variant == "single" and len(posts) != 1:
        errors.append("X single variant requires exactly one '### Post'")
    if variant in ("thread", "standalone") and len(posts) < 2:
        errors.append(f"X {variant} variant requires at least two posts")
    numbers: list[int] = []
    for heading, body in posts:
        match = expected.fullmatch(heading)
        if not match:
            errors.append(f"unexpected X post heading for {variant}: {heading}")
            continue
        if match.lastindex:
            numbers.append(int(match.group(1)))
        count = len(body)
        if not body:
            errors.append(f"X post '{heading}' must not be empty")
        if count > X_POST_CHARACTER_LIMIT:
            errors.append(
                f"X post '{heading}' is {count} characters; limit is {X_POST_CHARACTER_LIMIT}"
            )
    if numbers and numbers != list(range(1, len(numbers) + 1)):
        errors.append(f"X {variant} post numbers must be sequential starting at 1")
    return errors


def validate_x_artifact(path: Path, variant: str) -> list[str]:
    if variant not in X_VARIANTS:
        return [f"X variant must be one of: {', '.join(X_VARIANTS)}"]
    return _validate_x_content(path, variant)


def _validate_artifact_map(
    run_dir: Path,
    artifacts: Any,
    *,
    prefix: Path,
    revision_round: int,
    stage: str,
    research_required: bool | None = None,
    shared: bool = False,
) -> list[str]:
    errors: list[str] = []
    required_keys = DEFAULT_SHARED_ARTIFACTS if shared else DEFAULT_FORMAT_ARTIFACTS
    if not isinstance(artifacts, dict):
        return ["shared_artifacts must be a JSON object" if shared else "format artifacts must be a JSON object"]
    for key in required_keys:
        if key not in artifacts:
            errors.append(f"missing stable artifact key: {key}")
    for key, value in artifacts.items():
        errors.extend(_safe_artifact_path(run_dir, value, prefix, key))
        if value is None or not isinstance(value, str):
            continue
        path = Path(value)
        pattern = ARTIFACT_NAME_PATTERNS.get(key)
        if pattern is None:
            family = re.fullmatch(r"(draft|council|revision_plan|research)_\d+", key)
            if family:
                family_key = family.group(1)
                pattern = ARTIFACT_NAME_PATTERNS[family_key]
                version = int(key.rsplit("_", 1)[1])
                stem = "revision-plan" if family_key == "revision_plan" else (
                    "research-report" if family_key == "research" else family_key
                )
                if path.name != f"{stem}-{version:02d}.md":
                    errors.append(f"versioned artifact '{key}' has inconsistent filename: {value}")
            else:
                errors.append(f"unknown artifact key: {key}")
        if pattern is not None and not pattern.fullmatch(path.name):
            errors.append(f"artifact '{key}' has invalid filename: {value}")
    if shared:
        required = {
            "selected_idea": ("spike",),
            "research_decision": ("spike",),
            "research": ("spike", "research"),
            "interview": ("spike", "interview"),
            "content_brief": ("spike", "interview", "brief"),
            "complete": ("spike", "interview", "brief"),
        }.get(stage, ())
        for key in required:
            if not artifacts.get(key):
                errors.append(f"shared stage '{stage}' requires artifact '{key}'")
        if research_required is True and stage in ("interview", "content_brief", "complete") and not artifacts.get("research"):
            errors.append("research_required=true requires a shared research artifact")
        return errors
    required = {
        "draft": ("draft",),
        "council": ("draft", "council"),
        "revision": ("draft", "revision_plan"),
        "finalization": ("draft", "council", "final"),
        "lessons": ("draft", "council", "final", "lessons"),
        "complete": ("draft", "council", "final", "lessons"),
    }.get(stage, ())
    for key in required:
        if not artifacts.get(key):
            errors.append(f"format stage '{stage}' requires artifact '{key}'")
    revision = artifacts.get("revision")
    if revision_round == 0 and revision:
        errors.append("revision_round=0 requires artifact 'revision' to be null")
    if revision_round == 0 and artifacts.get("draft") and Path(artifacts["draft"]).name != "draft-01.md":
        errors.append("revision_round=0 requires current draft to be draft-01.md")
    if revision_round > 0:
        expected = f"draft-{revision_round + 1:02d}.md"
        if not revision:
            errors.append("revision_round greater than 0 requires artifact 'revision'")
        elif artifacts.get("draft") != revision or Path(revision).name != expected:
            errors.append("current draft/revision pointer must match revision_round")
    return errors


def validation_errors(
    run_dir: Path,
    state: dict[str, Any],
    data_root: Path | None = None,
) -> list[str]:
    errors: list[str] = []
    for field in REQUIRED_FIELDS:
        if field not in state:
            errors.append(f"missing required field: {field}")
    if state.get("schema_version") != 2:
        errors.append("schema_version must be 2; run 'bin/cf migrate-run <run>'")
        return errors
    if state.get("id") != run_dir.name:
        errors.append("id must match the run directory name")
    if not isinstance(state.get("title"), str) or not state.get("title", "").strip():
        errors.append("title must be a non-empty string")
    aliases = state.get("aliases")
    if aliases is not None and (
        not isinstance(aliases, list)
        or any(not isinstance(alias, str) or not alias.strip() for alias in aliases)
        or len(aliases) != len(set(aliases))
    ):
        errors.append("aliases must be a duplicate-free list of non-empty strings when present")
    requested = state.get("requested_formats")
    if not isinstance(requested, list) or not requested:
        errors.append("requested_formats must be a non-empty list")
        requested = []
    elif any(name not in SUPPORTED_FORMATS for name in requested):
        errors.append(f"requested_formats may contain only: {', '.join(SUPPORTED_FORMATS)}")
    if len(requested) != len(set(requested)):
        errors.append("requested_formats must not contain duplicates")
    primary = state.get("primary_format")
    if primary is not None and primary not in requested:
        errors.append("primary_format must be included in requested_formats")
    if primary == "readme" and len(requested) > 1:
        errors.append("README cannot be primary in a mixed social/document run")
    active_format = state.get("active_format")
    if active_format is not None and active_format not in requested:
        errors.append("active_format must be included in requested_formats")
    if state.get("status") not in STATUSES:
        errors.append(f"status must be one of: {', '.join(STATUSES)}")

    shared = state.get("shared_state")
    shared_artifacts = state.get("shared_artifacts")
    shared_stages = ("selected_idea", "research_decision", "research", "interview", "content_brief", "complete")
    if not isinstance(shared, dict):
        errors.append("shared_state must be a JSON object")
    else:
        stage = shared.get("stage")
        status = shared.get("status")
        action = shared.get("pending_human_action")
        research_required = shared.get("research_required")
        if stage not in shared_stages:
            errors.append(f"shared stage must be one of: {', '.join(shared_stages)}")
        if status not in ("active", "awaiting_human", "parked", "complete"):
            errors.append("shared status is invalid")
        if action not in PENDING_ACTIONS:
            errors.append("shared pending_human_action is invalid")
        if research_required is not None and not isinstance(research_required, bool):
            errors.append("research_required must be null or a Boolean")
        if stage in ("research", "interview", "content_brief", "complete") and research_required is None:
            errors.append("research_required must be decided before research/interview completion")
        if status == "awaiting_human" and action == "none":
            errors.append("shared awaiting_human status requires a pending action")
        if status in ("active", "complete", "parked") and action != "none":
            errors.append(f"shared {status} status requires no pending action")
        if stage == "complete" and status != "complete":
            errors.append("shared complete stage requires complete status")
        shared_allowed = {
            "selected_idea": {"provide_idea_details"},
            "research_decision": {"confirm_research_decision"},
            "research": {"resolve_research_scope"},
            "interview": {"answer_interview_question"},
            "content_brief": {"none"},
            "complete": {"none"},
        }
        if status == "awaiting_human" and action not in shared_allowed.get(stage, set()):
            errors.append(f"shared stage '{stage}' cannot await '{action}'")
        errors.extend(_validate_artifact_map(
            run_dir, shared_artifacts, prefix=Path("."), revision_round=0,
            stage=stage, research_required=research_required, shared=True,
        ))

    format_states = state.get("format_states")
    if not isinstance(format_states, dict):
        errors.append("format_states must be a JSON object")
        format_states = {}
    if set(format_states) != set(requested):
        errors.append("format_states keys must exactly match requested_formats")
    terminal = 0
    for name in requested:
        fmt = format_states.get(name)
        if not isinstance(fmt, dict):
            errors.append(f"format state '{name}' must be a JSON object")
            continue
        stage = fmt.get("stage")
        status = fmt.get("status")
        action = fmt.get("pending_human_action")
        revision_round = fmt.get("revision_round")
        disposition = fmt.get("disposition")
        variant = fmt.get("variant")
        if stage not in ("pending", "draft", "council", "revision", "finalization", "lessons", "complete", "declined", "parked"):
            errors.append(f"format '{name}' has invalid stage")
        if status not in ("pending", "active", "awaiting_human", "parked", "declined", "complete"):
            errors.append(f"format '{name}' has invalid status")
        if action not in PENDING_ACTIONS:
            errors.append(f"format '{name}' has invalid pending_human_action")
        if isinstance(revision_round, bool) or not isinstance(revision_round, int) or not 0 <= revision_round <= 2:
            errors.append(f"format '{name}' revision_round must be 0..2")
            revision_round = 0
        if disposition not in ("active", "finalized", "parked", "declined"):
            errors.append(f"format '{name}' has invalid disposition")
        if name == "x" and variant is not None and variant not in X_VARIANTS:
            errors.append(f"X variant must be one of: {', '.join(X_VARIANTS)}")
        if name != "x" and variant is not None:
            errors.append(f"format '{name}' must not define an X variant")
        if status == "awaiting_human" and action == "none":
            errors.append(f"format '{name}' awaiting_human requires a pending action")
        if status in ("pending", "active", "parked", "declined", "complete") and action != "none":
            errors.append(f"format '{name}' status '{status}' requires no pending action")
        if disposition == "finalized":
            terminal += 1
            if stage != "complete" or status != "complete":
                errors.append(f"finalized format '{name}' must have complete stage/status")
        elif disposition in ("parked", "declined"):
            terminal += 1
            if stage != disposition or status != disposition:
                errors.append(f"{disposition} format '{name}' must have matching stage/status")
        format_allowed = {
            "pending": {"confirm_destination_variant"},
            "draft": {"review_draft", "authorize_council"},
            "council": {"confirm_route", "approve_final"},
            "revision": {
                "approve_revision_plan", "resolve_revision_limit", "review_draft",
                "authorize_council", "approve_final",
            },
            "lessons": {"approve_lessons"},
        }
        if status == "awaiting_human" and action not in format_allowed.get(stage, set()):
            errors.append(f"format '{name}' stage '{stage}' cannot await '{action}'")
        artifacts = fmt.get("artifacts")
        errors.extend(_validate_artifact_map(
            run_dir, artifacts, prefix=Path("formats") / name,
            revision_round=revision_round, stage=stage,
        ))
        final = fmt.get("final_artifact")
        if final is not None:
            if not isinstance(final, str) or Path(final).parent != Path("formats") / name:
                errors.append(f"format '{name}' final_artifact must stay in its format directory")
            elif isinstance(artifacts, dict) and artifacts.get("final") != final:
                errors.append(f"format '{name}' final_artifact must match artifacts.final")
        if disposition == "finalized" and not final:
            errors.append(f"finalized format '{name}' requires a final artifact")
        if name == "x" and variant and isinstance(artifacts, dict):
            for key in ("draft", "final"):
                value = artifacts.get(key)
                if isinstance(value, str) and (run_dir / value).is_file():
                    errors.extend(f"format 'x' {key}: {error}" for error in validate_x_artifact(run_dir / value, variant))
    if active_format is not None:
        fmt = format_states.get(active_format, {})
        if fmt.get("disposition") != "active":
            errors.append("active_format must identify an active format")
        if primary and format_states.get(primary, {}).get("disposition") == "active" and active_format != primary:
            errors.append("primary format must be completed, parked, or declined before a secondary becomes active")
    if state.get("status") == "complete" and terminal != len(requested):
        errors.append("run cannot be complete while requested formats remain unfinished")
    if terminal == len(requested) and state.get("status") != "complete":
        errors.append("run status must be complete when every requested format is resolved")
    if state.get("status") == "parked":
        if not isinstance(state.get("parking_reason"), str) or not state.get("parking_reason", "").strip():
            errors.append("parked status requires a non-empty parking_reason")
        parked_at = state.get("parked_at")
        if not isinstance(parked_at, str) or not re.fullmatch(
            r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", parked_at
        ):
            errors.append("parked status requires parked_at")

    vault_lists: dict[str, list[str]] = {}
    for key in VAULT_RUN_FIELDS:
        value = state.get(key, [])
        if not isinstance(value, list) or any(not isinstance(v, str) or not ITEM_ID_PATTERN.fullmatch(v) for v in value):
            errors.append(f"{key} must be a list of safe vault item IDs")
            continue
        if len(value) != len(set(value)):
            errors.append(f"{key} must not contain duplicates")
        vault_lists[key] = value
    origins = vault_lists.get("origin_vault_items", [])
    contributors = vault_lists.get("contributing_vault_items", [])
    derived = vault_lists.get("derived_vault_items", [])
    linked = vault_lists.get("linked_vault_items", [])
    if (set(origins) & set(contributors)) | (set(origins) & set(derived)) | (set(contributors) & set(derived)):
        errors.append("vault items cannot have more than one run role")
    if linked != list(dict.fromkeys((*origins, *contributors, *derived))):
        errors.append("linked_vault_items must equal origins followed by contributing and derived items")
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
    adaptation = state.get("adaptation")
    if adaptation is not None:
        if not isinstance(adaptation, dict):
            errors.append("adaptation must be a JSON object or null")
        else:
            required_adaptation_fields = (
                "source_ref",
                "source_run",
                "source_title",
                "source_format",
                "source_artifact",
                "source_final_artifact",
                "source_artifact_sha256",
                "source_finalized",
                "destination_format",
                "destination_variant",
                "source_vault_items",
                "prior_adaptation_runs",
                "created_at",
            )
            for key in required_adaptation_fields:
                if key not in adaptation:
                    errors.append(f"adaptation is missing required field: {key}")
            source_run = adaptation.get("source_run")
            source_format = adaptation.get("source_format")
            destination_format = adaptation.get("destination_format")
            source_artifact = adaptation.get("source_artifact")
            source_final = adaptation.get("source_final_artifact")
            if not isinstance(source_run, str) or not ITEM_ID_PATTERN.fullmatch(source_run):
                errors.append("adaptation source_run must be a safe run ID")
            elif source_run == state.get("id"):
                errors.append("adaptation source_run must not reference the adaptation run itself")
            if source_format not in SUPPORTED_FORMATS:
                errors.append("adaptation source_format is invalid")
            if destination_format not in SOCIAL_FORMATS:
                errors.append("adaptation destination_format must be linkedin or x")
            elif requested != [destination_format]:
                errors.append("adaptation run must request only its destination format")
            destination_variant = adaptation.get("destination_variant")
            if destination_format == "x":
                if destination_variant is not None and destination_variant not in X_VARIANTS:
                    errors.append("adaptation destination_variant is invalid")
                x_state = format_states.get("x", {})
                if isinstance(x_state, dict) and x_state.get("variant") != destination_variant:
                    errors.append("adaptation destination_variant must match the X format state")
            elif destination_variant is not None:
                errors.append("LinkedIn adaptation must not define an X destination variant")
            for key, value in (
                ("source_vault_items", adaptation.get("source_vault_items")),
                ("prior_adaptation_runs", adaptation.get("prior_adaptation_runs")),
            ):
                if not isinstance(value, list) or any(
                    not isinstance(item, str) or not ITEM_ID_PATTERN.fullmatch(item)
                    for item in (value if isinstance(value, list) else [])
                ):
                    errors.append(f"adaptation {key} must be a list of safe IDs")
                elif len(value) != len(set(value)):
                    errors.append(f"adaptation {key} must not contain duplicates")
            if isinstance(adaptation.get("source_vault_items"), list):
                if adaptation["source_vault_items"] != linked:
                    errors.append("adaptation source_vault_items must match linked_vault_items")
            for key, value in (("source_artifact", source_artifact), ("source_final_artifact", source_final)):
                if value is None and key == "source_final_artifact":
                    continue
                if not isinstance(value, str) or not value:
                    errors.append(f"adaptation {key} must be a non-empty relative path")
                elif Path(value).is_absolute() or ".." in Path(value).parts:
                    errors.append(f"adaptation {key} must stay inside the source run")
            digest = adaptation.get("source_artifact_sha256")
            if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
                errors.append("adaptation source_artifact_sha256 must be a lowercase SHA-256 digest")
            if not isinstance(adaptation.get("source_finalized"), bool):
                errors.append("adaptation source_finalized must be Boolean")
            if adaptation.get("source_finalized") and source_final is None:
                errors.append("finalized adaptation source requires source_final_artifact")
            stamp = adaptation.get("created_at")
            if not isinstance(stamp, str) or not re.fullmatch(
                r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", stamp
            ):
                errors.append("adaptation created_at must be a UTC timestamp")
            if data_root is not None and isinstance(source_run, str) and isinstance(source_artifact, str):
                source_path = data_root / "runs" / source_run / source_artifact
                if not source_path.is_file():
                    errors.append(f"adaptation source artifact is missing: {source_path}")
                elif isinstance(digest, str) and re.fullmatch(r"[0-9a-f]{64}", digest):
                    actual = hashlib.sha256(source_path.read_bytes()).hexdigest()
                    if actual != digest:
                        errors.append("adaptation source artifact no longer matches its recorded SHA-256")
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
        args.format or ["linkedin"],
        origin_vault_items=origin_ids,
        contributing_vault_items=contributing_ids,
        primary_format=args.primary_format,
        x_variant=args.x_variant,
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


def _print_find_result(result: FindResult, *, as_json: bool) -> None:
    if as_json:
        print(json.dumps(result.to_dict(), indent=2, ensure_ascii=False))
        return
    print(f"resolution: {result.resolution}")
    if not result.matches:
        print("searched: run titles and artifacts, shared briefs/spikes, linked vault material, and vault items")
        return
    print("SOURCE_REF\tTITLE\tTYPE\tSTATUS\tFORMAT\tFINALIZATION\tDATE\tPATH\tSCORE\tMATCH")
    for match in result.matches:
        print(
            "\t".join(
                (
                    match.source_ref,
                    match.title,
                    match.content_type,
                    match.status,
                    match.format or "-",
                    match.finalization_state,
                    match.date,
                    match.private_path,
                    str(match.score),
                    match.matched_on,
                )
            )
        )


def cmd_find(args: argparse.Namespace, repository_root: Path) -> int:
    data_root = resolve_data_root(args.data_dir, repository_root)
    require_creator_setup(data_root)
    result = find_sources(
        data_root,
        args.query,
        format_name=args.format,
        variant_name=args.variant,
        latest=args.latest,
        drafts=args.drafts,
        limit=args.limit,
    )
    _print_find_result(result, as_json=args.json)
    return 0


def _source_ref_from_vault(value: str, data_root: Path) -> str:
    item_id = value.removeprefix("vault:")
    item_path = _resolve_valid_item(item_id, data_root)
    metadata, _ = _load_valid_item(item_path)
    references = []
    for artifact in metadata["final_artifacts"]:
        path = Path(artifact)
        if (
            len(path.parts) == 5
            and path.parts[0] == "runs"
            and path.parts[2] == "formats"
            and path.parts[3] in SUPPORTED_FORMATS
        ):
            references.append(f"run:{path.parts[1]}:{path.parts[3]}:final")
    references = list(dict.fromkeys(references))
    if not references:
        raise CFError(
            f"vault source '{metadata['title']}' has no local finalized format artifact; "
            "start a normal run from the vault item instead"
        )
    if len(references) > 1:
        raise CFError(
            f"vault source '{metadata['title']}' has several finalized artifacts; "
            "use the SOURCE_REF from 'bin/cf find' to select one"
        )
    return references[0]


def _resolve_adaptation_source(
    source_ref: str,
    data_root: Path,
) -> tuple[Path, dict[str, Any], str, str, str, str | None, bool]:
    if source_ref.startswith("vault:"):
        source_ref = _source_ref_from_vault(source_ref, data_root)
    match = SOURCE_REF_PATTERN.fullmatch(source_ref)
    if not match:
        raise CFError(
            "adapt source must be a resolved SOURCE_REF such as "
            "'run:2026-07-24-example:linkedin:final'"
        )
    run_id = match.group("run")
    source_format = match.group("format")
    selection = match.group("selection")
    run_dir = resolve_run(run_id, data_root)
    state = load_state(run_dir)
    format_state = state.get("format_states", {}).get(source_format)
    if not isinstance(format_state, dict):
        raise CFError(f"source run does not contain format '{source_format}'")
    artifacts = format_state.get("artifacts", {})
    final_artifact = format_state.get("final_artifact") or artifacts.get("final")
    selected_artifact = final_artifact if selection == "final" else artifacts.get("draft")
    if not isinstance(selected_artifact, str) or not (run_dir / selected_artifact).is_file():
        raise CFError(f"source run has no available {selection} artifact for '{source_format}'")
    if final_artifact is not None and (
        not isinstance(final_artifact, str) or not (run_dir / final_artifact).is_file()
    ):
        raise CFError("source run records a missing final artifact")
    return (
        run_dir,
        state,
        source_ref,
        source_format,
        selected_artifact,
        final_artifact,
        selection == "final",
    )


def _prior_adaptation_runs(
    data_root: Path,
    source_run: str,
    source_artifact: str,
    destination_format: str,
) -> list[str]:
    matches: list[str] = []
    runs_root = data_root / "runs"
    if not runs_root.is_dir():
        return matches
    for state_path in sorted(runs_root.glob("*/run.json")):
        try:
            state = json.loads(state_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            continue
        adaptation = state.get("adaptation") if isinstance(state, dict) else None
        if not isinstance(adaptation, dict):
            continue
        if (
            adaptation.get("source_run") == source_run
            and adaptation.get("source_artifact") == source_artifact
            and adaptation.get("destination_format") == destination_format
        ):
            matches.append(state_path.parent.name)
    return matches


def cmd_adapt(args: argparse.Namespace, repository_root: Path) -> int:
    data_root = resolve_data_root(args.data_dir, repository_root)
    require_creator_setup(data_root)
    (
        source_run,
        source_state,
        source_ref,
        source_format,
        source_artifact,
        source_final_artifact,
        source_finalized,
    ) = _resolve_adaptation_source(args.source, data_root)
    if args.to not in SOCIAL_FORMATS:
        raise CFError("adaptation destination must be linkedin or x")
    if args.x_variant is not None and args.to != "x":
        raise CFError("--x-variant requires '--to x'")

    shared = source_state.get("shared_artifacts")
    if not isinstance(shared, dict):
        raise CFError("source run has no reusable shared artifact metadata")
    for key in ("interview", "brief"):
        value = shared.get(key)
        if not isinstance(value, str) or not (source_run / value).is_file():
            raise CFError(
                f"source run lacks reusable {key} material; resume it through the normal "
                "workflow rather than manufacturing adaptation context"
            )

    origins = list(source_state.get("origin_vault_items", []))
    contributors = list(source_state.get("contributing_vault_items", []))
    derived = list(source_state.get("derived_vault_items", []))
    source_vault_items = list(dict.fromkeys((*origins, *contributors, *derived)))
    title = args.title or f"{source_state['title']} — {args.to.upper() if args.to == 'x' else 'LinkedIn'} adaptation"
    run_dir = make_run(
        data_root,
        title,
        [args.to],
        origin_vault_items=origins,
        contributing_vault_items=contributors,
        derived_vault_items=derived,
        x_variant=args.x_variant,
    )
    item_backups: dict[Path, bytes] = {}
    try:
        state = load_state(run_dir)
        copied: dict[str, str | None] = {
            "spike": "spike.md",
            "research": None,
            "interview": None,
            "brief": None,
        }
        for key, canonical_name in (
            ("research", "research-report.md"),
            ("interview", "interview.md"),
            ("brief", "content-brief.md"),
        ):
            source_value = shared.get(key)
            if isinstance(source_value, str) and (source_run / source_value).is_file():
                shutil.copyfile(source_run / source_value, run_dir / canonical_name)
                copied[key] = canonical_name

        stamp = utc_timestamp()
        source_relative = Path("runs") / source_run.name / source_artifact
        final_relative = (
            str(Path("runs") / source_run.name / source_final_artifact)
            if source_final_artifact
            else "none"
        )
        (run_dir / "spike.md").write_text(
            f"# {title}\n\n"
            "## Adaptation request\n\n"
            f"- Source title: {source_state['title']}\n"
            f"- Source format: {source_format}\n"
            f"- Selected source artifact: `{source_relative}`\n"
            f"- Original final artifact: `{final_relative}`\n"
            f"- Destination format: {args.to}\n"
            f"- Destination variant: {args.x_variant or 'pending human confirmation'}\n\n"
            "## Authority and reuse\n\n"
            "The copied shared brief and original human interview remain authoritative. "
            "The selected source-format artifact is evidence of approved framing and wording, "
            "not a conversion template or a substitute for the creator's judgment.\n\n"
            "## Linked vault material\n\n"
            f"{', '.join(source_vault_items) or 'None recorded on the source run.'}\n\n"
            "## Safety\n\n"
            "Create a native destination rendering. Do not overwrite or invalidate the source "
            "artifact, copy approval state, or infer durable destination preferences.\n",
            encoding="utf-8",
        )
        source_research_required = source_state.get("shared_state", {}).get("research_required")
        if not isinstance(source_research_required, bool):
            source_research_required = copied["research"] is not None
        state["shared_state"] = {
            "stage": "complete",
            "status": "complete",
            "research_required": source_research_required,
            "pending_human_action": "none",
        }
        state["shared_artifacts"] = copied
        state["active_format"] = args.to
        destination = state["format_states"][args.to]
        destination["stage"] = "pending"
        if args.to == "x" and args.x_variant is None:
            destination["status"] = "awaiting_human"
            destination["pending_human_action"] = "confirm_destination_variant"
            state["status"] = "awaiting_human"
        else:
            destination["status"] = "active"
            destination["pending_human_action"] = "none"
            state["status"] = "active"
        state["adaptation"] = {
            "source_ref": source_ref,
            "source_run": source_run.name,
            "source_title": source_state["title"],
            "source_format": source_format,
            "source_artifact": source_artifact,
            "source_final_artifact": source_final_artifact,
            "source_artifact_sha256": hashlib.sha256(
                (source_run / source_artifact).read_bytes()
            ).hexdigest(),
            "source_finalized": source_finalized,
            "destination_format": args.to,
            "destination_variant": args.x_variant,
            "source_vault_items": source_vault_items,
            "prior_adaptation_runs": _prior_adaptation_runs(
                data_root, source_run.name, source_artifact, args.to
            ),
            "created_at": stamp,
        }
        errors = validation_errors(run_dir, state)
        if errors:
            raise CFError("adaptation initializer produced invalid state: " + "; ".join(errors))
        _write_json(run_dir / "run.json", state)

        for item_id in source_vault_items:
            item_path = _resolve_valid_item(item_id, data_root)
            item_backups[item_path] = item_path.read_bytes()
            metadata, body = _load_valid_item(item_path)
            if run_dir.name not in metadata["related_runs"]:
                metadata["related_runs"].append(run_dir.name)
            if metadata["status"] != "archived":
                metadata["status"] = "developing"
            metadata["updated_at"] = stamp
            body = append_section(
                body,
                "Development history",
                f"- {stamp}: source material linked for `{args.to}` adaptation run "
                f"`{run_dir.name}` from `{source_run.name}`.",
            )
            write_item(item_path, metadata, body)
        if source_vault_items:
            _rebuild_vault_index(data_root)
        errors = validation_errors(run_dir, state, data_root)
        if errors:
            raise CFError("adaptation provenance validation failed: " + "; ".join(errors))
    except Exception:
        for item_path, content in item_backups.items():
            item_path.write_bytes(content)
        if item_backups:
            try:
                _rebuild_vault_index(data_root)
            except CFError:
                pass
        shutil.rmtree(run_dir, ignore_errors=True)
        raise

    print(f"data_root: {data_root}")
    print(f"source: {source_state['title']} ({source_format}, {source_artifact})")
    print(f"run: {run_dir}")
    print(f"destination: {args.to}")
    print(f"variant: {args.x_variant or 'pending'}")
    return 0


def cmd_set_x_variant(args: argparse.Namespace, repository_root: Path) -> int:
    data_root = resolve_data_root(args.data_dir, repository_root)
    run_dir, state = _load_run_for_data_root(args.run, data_root)
    adaptation = state.get("adaptation")
    if not isinstance(adaptation, dict) or adaptation.get("destination_format") != "x":
        raise CFError("set-x-variant applies only to an X adaptation run")
    format_state = state.get("format_states", {}).get("x")
    if not isinstance(format_state, dict):
        raise CFError("run has no X format state")
    if any(format_state.get("artifacts", {}).get(key) for key in ("draft", "final")):
        raise CFError("cannot change the X variant after drafting has begun")
    format_state["variant"] = args.variant
    format_state["stage"] = "pending"
    format_state["status"] = "active"
    format_state["pending_human_action"] = "none"
    adaptation["destination_variant"] = args.variant
    state["active_format"] = "x"
    state["status"] = "active"
    errors = validation_errors(run_dir, state, data_root)
    if errors:
        raise CFError("X variant selection produced invalid state: " + "; ".join(errors))
    _write_json(run_dir / "run.json", state)
    print(f"run: {run_dir}")
    print(f"x_variant: {args.variant}")
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
    state["status"] = "parked"
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
    if restored_status not in ("active", "awaiting_human"):
        raise CFError("parked run is missing valid pre-park status")
    state["status"] = restored_status
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
    requested = state.get("requested_formats", [])
    format_name = args.format
    if format_name is None:
        if state.get("active_format") in requested:
            format_name = state["active_format"]
        elif len(requested) == 1:
            format_name = requested[0]
        else:
            raise CFError("--format is required when a multi-format run has no active format")
    if format_name not in requested:
        raise CFError("format was not requested by this run")
    format_state = state.get("format_states", {}).get(format_name, {})
    final_value = format_state.get("artifacts", {}).get("final")
    if not isinstance(final_value, str) or not (run_dir / final_value).is_file():
        raise CFError(f"format '{format_name}' does not have a valid final artifact")
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
        detail = f"format {format_name}"
        if format_name == "x" and format_state.get("variant"):
            detail += f", variant {format_state['variant']}"
        if format_state.get("angle"):
            detail += f", angle {format_state['angle']}"
        body = append_section(
            body,
            "Development history",
            f"- {stamp}: run `{run_dir.name}` produced final artifact `{artifact_reference}` "
            f"({detail}); the item remains available for reuse.",
        )
        write_item(path, metadata, body)
    format_state["final_artifact"] = final_value
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
    requested = state.get("requested_formats", [])
    print(f"requested_formats: {', '.join(requested) if isinstance(requested, list) else '<invalid>'}")
    print(f"primary_format: {state.get('primary_format') or 'none'}")
    print(f"active_format: {state.get('active_format') or 'shared'}")
    print(f"status: {state.get('status', '<invalid>')}")
    shared = state.get("shared_state", {})
    print(f"shared: stage={shared.get('stage', '<invalid>')}, status={shared.get('status', '<invalid>')}, "
          f"pending={shared.get('pending_human_action', '<invalid>')}")
    for name in requested if isinstance(requested, list) else []:
        fmt = state.get("format_states", {}).get(name, {})
        print(
            f"format[{name}]: stage={fmt.get('stage', '<invalid>')}, "
            f"status={fmt.get('status', '<invalid>')}, variant={fmt.get('variant') or 'none'}, "
            f"revision_round={fmt.get('revision_round', '<invalid>')}, "
            f"pending={fmt.get('pending_human_action', '<invalid>')}, "
            f"final={fmt.get('final_artifact') or 'none'}"
        )
    linked = state.get("linked_vault_items", [])
    print(f"linked_vault_items: {', '.join(linked) if isinstance(linked, list) and linked else 'none'}")
    existing = [f"shared.{key}={value}" for key, value in state.get("shared_artifacts", {}).items() if value]
    for name, fmt in state.get("format_states", {}).items():
        existing.extend(f"{name}.{key}={value}" for key, value in fmt.get("artifacts", {}).items() if value)
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



def _legacy_migration_state(run_dir: Path, legacy: dict[str, Any]) -> tuple[dict[str, Any], dict[Path, Path]]:
    format_name = legacy.get("format")
    if format_name not in ("linkedin", "readme"):
        raise CFError("legacy run format must be linkedin or readme")
    old_artifacts = legacy.get("artifacts")
    if not isinstance(old_artifacts, dict):
        raise CFError("legacy run has no valid artifacts object")
    shared_artifacts = dict(DEFAULT_SHARED_ARTIFACTS)
    format_artifacts = dict(DEFAULT_FORMAT_ARTIFACTS)
    moves: dict[Path, Path] = {}
    for key, value in old_artifacts.items():
        if key in ("spike", "research", "interview", "brief") or key.startswith("research_"):
            shared_artifacts[key] = value
            continue
        format_artifacts[key] = value
        if isinstance(value, str):
            source = run_dir / value
            target = run_dir / "formats" / format_name / Path(value).name
            if source != target:
                format_artifacts[key] = target.relative_to(run_dir).as_posix()
                if source.exists():
                    moves[source] = target
    # Preserve historical canonical rendering artifacts even when an older state pointer
    # references only the latest version (for example final-02.md after a reopen).
    format_name_pattern = re.compile(
        r"(?:draft|council|revision-plan)-\d{2}(?:-[a-z0-9-]+)?\.md|"
        r"final(?:-\d{2})?\.md|lesson-candidates(?:-\d{2})?\.md"
    )
    for source in run_dir.iterdir():
        if source.is_file() and format_name_pattern.fullmatch(source.name):
            moves.setdefault(source, run_dir / "formats" / format_name / source.name)
    stage = legacy.get("stage")
    early = stage in ("selected_idea", "research_decision", "research", "interview")
    if early:
        shared_stage = stage
        shared_status = legacy.get("status")
        shared_action = legacy.get("pending_human_action", "none")
        format_stage, format_status, format_action = "pending", "pending", "none"
    else:
        shared_stage, shared_status, shared_action = "complete", "complete", "none"
        format_stage = stage if stage in ("draft", "council", "revision", "finalization", "lessons", "complete") else "pending"
        format_status = legacy.get("status")
        format_action = legacy.get("pending_human_action", "none")
    if shared_status == "parked":
        shared_action = "none"
    disposition = "finalized" if format_stage == "complete" else "active"
    final_value = legacy.get("final_artifact")
    if isinstance(final_value, str):
        final_value = (Path("formats") / format_name / Path(final_value).name).as_posix()
    migrated = {
        "schema_version": 2,
        "id": legacy.get("id"),
        "title": legacy.get("title"),
        "requested_formats": [format_name],
        "primary_format": None,
        "active_format": None if early or disposition == "finalized" else format_name,
        "status": legacy.get("status"),
        "shared_state": {
            "stage": shared_stage,
            "status": shared_status,
            "research_required": legacy.get("research_required"),
            "pending_human_action": shared_action,
        },
        "shared_artifacts": shared_artifacts,
        "format_states": {
            format_name: {
                "variant": None,
                "angle": None,
                "stage": format_stage,
                "status": format_status,
                "revision_round": legacy.get("revision_round", 0),
                "pending_human_action": format_action,
                "disposition": disposition,
                "artifacts": format_artifacts,
                "final_artifact": final_value,
            }
        },
    }
    for key in (
        "origin_vault_items", "contributing_vault_items", "derived_vault_items",
        "linked_vault_items", "parking_reason", "parked_at", "parked_from_status",
        "resumed_at",
    ):
        if key in legacy:
            migrated[key] = legacy[key]
    for key in VAULT_RUN_FIELDS:
        migrated.setdefault(key, [])
    migrated.setdefault("parking_reason", None)
    migrated.setdefault("parked_at", None)
    return migrated, moves


def _rewrite_vault_final_paths(data_root: Path, run_id: str, format_name: str) -> None:
    records, errors = read_all_items(data_root)
    if errors:
        raise CFError("cannot migrate vault references while vault items are invalid")
    old_prefix = f"runs/{run_id}/"
    for path, metadata, body in records:
        changed = False
        rewritten: list[str] = []
        for value in metadata["final_artifacts"]:
            if value.startswith(old_prefix) and len(Path(value).parts) == 3:
                value = f"runs/{run_id}/formats/{format_name}/{Path(value).name}"
                changed = True
            rewritten.append(value)
        if changed:
            metadata["final_artifacts"] = rewritten
            write_item(path, metadata, body)


def cmd_migrate_run(args: argparse.Namespace, repository_root: Path) -> int:
    data_root = resolve_data_root(args.data_dir, repository_root)
    run_dir = resolve_run(args.run, data_root)
    legacy = load_state(run_dir)
    if legacy.get("schema_version") == 2:
        print(f"already schema_version 2: {run_dir}")
        return 0
    migrated, moves = _legacy_migration_state(run_dir, legacy)
    format_name = migrated["requested_formats"][0]
    print(f"run: {run_dir}")
    print(f"migration: singular {format_name} -> requested_formats=[{format_name}] (no added formats)")
    for source, target in sorted(moves.items(), key=lambda pair: str(pair[0])):
        print(f"move: {source.relative_to(run_dir)} -> {target.relative_to(run_dir)}")
    if not args.apply:
        print("dry_run: use --apply to migrate")
        return 0
    (run_dir / "formats" / format_name).mkdir(parents=True, exist_ok=True)
    for source, target in moves.items():
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            raise CFError(f"migration target already exists: {target}")
        source.replace(target)
    _write_json(run_dir / "run.json", migrated)
    if run_dir.parent == data_root / "runs":
        _rewrite_vault_final_paths(data_root, run_dir.name, format_name)
        _rebuild_vault_index(data_root)
    errors = validation_errors(run_dir, migrated, data_root if run_dir.parent == data_root / "runs" else None)
    if errors:
        raise CFError("migrated run is invalid: " + "; ".join(errors))
    print(f"migrated: {run_dir}")
    return 0


def cmd_validate_x(args: argparse.Namespace, repository_root: Path) -> int:
    del repository_root
    path = Path(args.file).expanduser().resolve()
    if not path.is_file():
        raise CFError(f"file does not exist: {path}")
    errors = validate_x_artifact(path, args.variant)
    if errors:
        print(f"INVALID {path}", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    print(f"OK {path} ({args.variant}, limit={X_POST_CHARACTER_LIMIT})")
    content = path.read_text(encoding="utf-8")
    recommended = extract_markdown_section(content, "Recommended final version")
    headings = list(re.finditer(r"^###\s+(.+?)\s*$", recommended, flags=re.MULTILINE))
    for index, match in enumerate(headings):
        end = headings[index + 1].start() if index + 1 < len(headings) else len(recommended)
        print(f"{match.group(1).strip()}: {len(recommended[match.end():end].strip())}")
    print(f"post_count: {len(headings)}")
    return 0


def cmd_format_action(args: argparse.Namespace, repository_root: Path) -> int:
    data_root = resolve_data_root(args.data_dir, repository_root)
    run_dir = resolve_run(args.run, data_root)
    state = load_state(run_dir)
    if args.format not in state.get("requested_formats", []):
        raise CFError("format was not requested by this run")
    fmt = state["format_states"][args.format]
    action = args.action
    if action == "activate":
        if state["shared_state"]["stage"] != "complete":
            raise CFError("shared content development must be complete before format rendering")
        primary = state.get("primary_format")
        if primary and primary != args.format and state["format_states"][primary]["disposition"] == "active":
            raise CFError("the primary format must be resolved before activating a secondary")
        if fmt["disposition"] not in ("active", "parked"):
            raise CFError("declined or finalized formats cannot be activated")
        if fmt["disposition"] == "parked":
            previous = fmt.pop("parked_from", None) or {"stage": "pending", "status": "pending", "pending_human_action": "none"}
            fmt.update(previous)
            fmt["disposition"] = "active"
        state["active_format"] = args.format
    elif action in ("park", "decline"):
        if fmt["disposition"] == "finalized":
            raise CFError("a finalized format cannot be parked or declined")
        if action == "park":
            fmt["parked_from"] = {key: fmt[key] for key in ("stage", "status", "pending_human_action")}
        fmt["stage"] = "parked" if action == "park" else "declined"
        fmt["status"] = fmt["stage"]
        fmt["pending_human_action"] = "none"
        fmt["disposition"] = fmt["stage"]
        if state.get("active_format") == args.format:
            state["active_format"] = None
    else:
        raise CFError("unsupported format action")
    resolved = all(item["disposition"] in ("finalized", "parked", "declined") for item in state["format_states"].values())
    state["status"] = "complete" if resolved else "awaiting_human"
    _write_json(run_dir / "run.json", state)
    errors = validation_errors(run_dir, state, data_root if run_dir.parent == data_root / "runs" else None)
    if errors:
        raise CFError("format action produced invalid state: " + "; ".join(errors))
    print(f"format {args.format}: {fmt['disposition']}")
    print(f"run_status: {state['status']}")
    return 0

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
    new_run.add_argument(
        "--format",
        action="append",
        choices=SUPPORTED_FORMATS,
        help="requested output format; repeat for multiple formats (default: linkedin)",
    )
    new_run.add_argument(
        "--primary-format",
        choices=SUPPORTED_FORMATS,
        help="optional anchor format; it must also be requested with --format",
    )
    new_run.add_argument(
        "--x-variant",
        choices=X_VARIANTS,
        help="optional X rendering variant; otherwise it is recommended and confirmed later",
    )
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

    find = subparsers.add_parser(
        "find",
        help="search private runs and vault material for reusable content",
    )
    find.add_argument("query", help="title, topic, phrase, person, concept, or recency description")
    find.add_argument("--format", choices=SUPPORTED_FORMATS, help="limit source format")
    find.add_argument("--variant", choices=X_VARIANTS, help="limit an X source variant")
    find.add_argument("--latest", action="store_true", help="return the most recent matching content")
    find.add_argument(
        "--drafts",
        action="store_true",
        help="select current draft artifacts instead of preferring finals",
    )
    find.add_argument("--limit", type=int, default=8, help="maximum matches to report (default: 8)")
    find.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    find.add_argument("--data-dir", help="private data root (overrides CONTENT_FLOW_HOME)")
    find.set_defaults(handler=cmd_find)

    adapt = subparsers.add_parser(
        "adapt",
        help="create a linked destination-format run from a resolved source",
    )
    adapt.add_argument("source", help="SOURCE_REF returned by 'bin/cf find'")
    adapt.add_argument("--to", required=True, choices=SOCIAL_FORMATS)
    adapt.add_argument("--x-variant", choices=X_VARIANTS)
    adapt.add_argument("--title", help="optional adaptation run title")
    adapt.add_argument("--data-dir", help="private data root (overrides CONTENT_FLOW_HOME)")
    adapt.set_defaults(handler=cmd_adapt)

    set_x_variant = subparsers.add_parser(
        "set-x-variant",
        help="record the human-confirmed variant for a pending X adaptation",
    )
    set_x_variant.add_argument("run")
    set_x_variant.add_argument("variant", choices=X_VARIANTS)
    set_x_variant.add_argument("--data-dir", help="private data root (overrides CONTENT_FLOW_HOME)")
    set_x_variant.set_defaults(handler=cmd_set_x_variant)

    status = subparsers.add_parser("status", help="show run state and validation summary")
    status.add_argument("run")
    status.add_argument("--data-dir", help="private data root (overrides CONTENT_FLOW_HOME)")
    status.set_defaults(handler=cmd_status)

    validate = subparsers.add_parser("validate", help="validate run state and artifacts")
    validate.add_argument("run")
    validate.add_argument("--data-dir", help="private data root (overrides CONTENT_FLOW_HOME)")
    validate.set_defaults(handler=cmd_validate)

    migrate = subparsers.add_parser(
        "migrate-run",
        help="report or apply the singular-format to schema-version-2 migration",
    )
    migrate.add_argument("run")
    migrate.add_argument("--apply", action="store_true", help="apply the reported migration")
    migrate.add_argument("--data-dir", help="private data root (overrides CONTENT_FLOW_HOME)")
    migrate.set_defaults(handler=cmd_migrate_run)

    format_action = subparsers.add_parser(
        "format-action",
        help="activate, park, or decline one requested format",
    )
    format_action.add_argument("run")
    format_action.add_argument("format", choices=SUPPORTED_FORMATS)
    format_action.add_argument("action", choices=("activate", "park", "decline"))
    format_action.add_argument("--data-dir", help="private data root (overrides CONTENT_FLOW_HOME)")
    format_action.set_defaults(handler=cmd_format_action)

    count = subparsers.add_parser("count", help="count Unicode code points in a UTF-8 file")
    count.add_argument("file")
    count.add_argument("--section", help="count only the body of one exact Markdown heading")
    count.set_defaults(handler=cmd_count)

    validate_x = subparsers.add_parser(
        "validate-x",
        help="validate the recommended X posts and canonical per-post character limit",
    )
    validate_x.add_argument("file")
    validate_x.add_argument("--variant", required=True, choices=X_VARIANTS)
    validate_x.set_defaults(handler=cmd_validate_x)

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
    finalize.add_argument("--format", choices=SUPPORTED_FORMATS)
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
