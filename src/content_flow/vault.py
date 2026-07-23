"""Deterministic Markdown vault mechanics."""

from __future__ import annotations

import json
import re
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Iterable


VAULT_KINDS = ("source", "idea", "observation", "quote", "excerpt", "run-fragment")
VAULT_STATUSES = ("inbox", "ready", "developing", "parked", "used", "archived")
VAULT_SECTIONS = (
    "Why this was saved",
    "Source or raw material",
    "Summary",
    "Potential content angles",
    "Useful specifics or excerpts",
    "Open questions",
    "Development history",
    "Parking notes",
)
VAULT_REQUIRED_KEYS = (
    "id",
    "title",
    "kind",
    "status",
    "captured_at",
    "updated_at",
    "tags",
    "related_items",
    "related_runs",
)
VAULT_KEY_ORDER = (
    "id",
    "title",
    "kind",
    "status",
    "captured_at",
    "updated_at",
    "source_url",
    "source_type",
    "source_author",
    "source_published_at",
    "tags",
    "related_items",
    "related_runs",
    "revisit_after",
)
VAULT_LIST_KEYS = ("tags", "related_items", "related_runs")
ITEM_ID_PATTERN = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")
TIMESTAMP_PATTERN = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z")
DATE_PATTERN = re.compile(r"\d{4}-\d{2}-\d{2}")


class VaultFormatError(ValueError):
    """A vault item cannot be parsed or validated."""


def utc_timestamp(now: datetime | None = None) -> str:
    value = now or datetime.now(timezone.utc)
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).replace(microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ")


def ensure_vault_dirs(data_root: Path) -> None:
    (data_root / "vault" / "items").mkdir(parents=True, exist_ok=True)
    (data_root / "vault" / "assets").mkdir(parents=True, exist_ok=True)


def _parse_scalar(raw: str) -> Any:
    value = raw.strip()
    if value in ("", "null", "~"):
        return None
    if value == "[]":
        return []
    if value.startswith(('"', "[", "{")):
        try:
            return json.loads(value)
        except json.JSONDecodeError as exc:
            raise VaultFormatError(f"invalid quoted or flow-style YAML value: {value}") from exc
    if value in ("true", "false"):
        return value == "true"
    return value


def parse_item(content: str) -> tuple[dict[str, Any], str]:
    """Parse the documented frontmatter subset and return metadata and body."""
    lines = content.splitlines(keepends=True)
    if not lines or lines[0].strip() != "---":
        raise VaultFormatError("item must begin with YAML frontmatter delimiter '---'")
    end = next((index for index in range(1, len(lines)) if lines[index].strip() == "---"), None)
    if end is None:
        raise VaultFormatError("item frontmatter is missing its closing '---' delimiter")

    metadata: dict[str, Any] = {}
    index = 1
    while index < end:
        line = lines[index].rstrip("\r\n")
        if not line.strip() or line.lstrip().startswith("#"):
            index += 1
            continue
        match = re.fullmatch(r"([A-Za-z_][A-Za-z0-9_-]*):(?:\s*(.*))?", line)
        if not match:
            raise VaultFormatError(f"unsupported frontmatter line {index + 1}: {line}")
        key, raw = match.group(1), match.group(2) or ""
        if key in metadata:
            raise VaultFormatError(f"duplicate frontmatter key: {key}")
        if not raw.strip():
            values: list[str] = []
            probe = index + 1
            while probe < end:
                child = lines[probe].rstrip("\r\n")
                child_match = re.fullmatch(r"\s+-\s+(.+)", child)
                if not child_match:
                    break
                parsed = _parse_scalar(child_match.group(1))
                if not isinstance(parsed, str):
                    raise VaultFormatError(f"list '{key}' must contain strings")
                values.append(parsed)
                probe += 1
            metadata[key] = values if probe > index + 1 else None
            index = probe
            continue
        metadata[key] = _parse_scalar(raw)
        index += 1
    return metadata, "".join(lines[end + 1 :]).lstrip("\r\n")


def _yaml_value(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, list):
        return json.dumps(value, ensure_ascii=False)
    if isinstance(value, str):
        return json.dumps(value, ensure_ascii=False)
    if isinstance(value, bool):
        return "true" if value else "false"
    return json.dumps(value, ensure_ascii=False)


def render_item(metadata: dict[str, Any], body: str) -> str:
    keys = [key for key in VAULT_KEY_ORDER if key in metadata]
    keys.extend(sorted(key for key in metadata if key not in keys))
    frontmatter = "\n".join(f"{key}: {_yaml_value(metadata[key])}" for key in keys)
    return f"---\n{frontmatter}\n---\n\n{body.strip()}\n"


def item_body(
    *,
    reason: str | None = None,
    material: str | None = None,
    source_url: str | None = None,
) -> str:
    values = {
        "Why this was saved": reason or "",
        "Source or raw material": material or (source_url or ""),
    }
    chunks: list[str] = []
    for section in VAULT_SECTIONS:
        chunks.append(f"## {section}\n\n{values.get(section, '')}".rstrip())
    return "\n\n".join(chunks)


def section_text(body: str, title: str) -> str:
    pattern = re.compile(
        rf"^## {re.escape(title)}\s*$\n?(.*?)(?=^##\s|\Z)",
        flags=re.MULTILINE | re.DOTALL,
    )
    match = pattern.search(body)
    return match.group(1).strip() if match else ""


def append_section(body: str, title: str, entry: str) -> str:
    heading = f"## {title}"
    if heading not in body:
        return body.rstrip() + f"\n\n{heading}\n\n{entry.strip()}\n"
    pattern = re.compile(
        rf"(^## {re.escape(title)}\s*$\n?)(.*?)(?=^##\s|\Z)",
        flags=re.MULTILINE | re.DOTALL,
    )
    match = pattern.search(body)
    if not match:
        return body
    existing = match.group(2).strip()
    replacement = match.group(1) + ("\n" if not existing else f"\n{existing}\n\n") + entry.strip() + "\n\n"
    return body[: match.start()] + replacement + body[match.end() :].lstrip("\n")


def validate_metadata(metadata: dict[str, Any], path: Path | None = None) -> list[str]:
    errors: list[str] = []
    for key in VAULT_REQUIRED_KEYS:
        if key not in metadata:
            errors.append(f"missing required vault field: {key}")
    item_id = metadata.get("id")
    if not isinstance(item_id, str) or not ITEM_ID_PATTERN.fullmatch(item_id):
        errors.append("vault id must contain only lowercase ASCII letters, digits, and single hyphens")
    elif path is not None and path.name != f"{item_id}.md":
        errors.append(f"vault filename must be '{item_id}.md'")
    title = metadata.get("title")
    if not isinstance(title, str) or not title.strip():
        errors.append("vault title must be a non-empty string")
    if metadata.get("kind") not in VAULT_KINDS:
        errors.append(f"vault kind must be one of: {', '.join(VAULT_KINDS)}")
    if metadata.get("status") not in VAULT_STATUSES:
        errors.append(f"vault status must be one of: {', '.join(VAULT_STATUSES)}")
    for key in ("captured_at", "updated_at"):
        value = metadata.get(key)
        if not isinstance(value, str) or not TIMESTAMP_PATTERN.fullmatch(value):
            errors.append(f"{key} must be a UTC timestamp like 2026-07-23T12:34:56Z")
        else:
            try:
                datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")
            except ValueError:
                errors.append(f"{key} is not a real UTC calendar timestamp")
    published = metadata.get("source_published_at")
    if published is not None and (
        not isinstance(published, str)
        or not (DATE_PATTERN.fullmatch(published) or TIMESTAMP_PATTERN.fullmatch(published))
    ):
        errors.append("source_published_at must be an ISO date or UTC timestamp")
    elif isinstance(published, str):
        try:
            if "T" in published:
                datetime.strptime(published, "%Y-%m-%dT%H:%M:%SZ")
            else:
                date.fromisoformat(published)
        except ValueError:
            errors.append("source_published_at is not a real calendar date")
    revisit = metadata.get("revisit_after")
    if revisit is not None:
        if not isinstance(revisit, str) or not DATE_PATTERN.fullmatch(revisit):
            errors.append("revisit_after must be an ISO date like 2026-08-01")
        else:
            try:
                date.fromisoformat(revisit)
            except ValueError:
                errors.append("revisit_after is not a real calendar date")
    for key in VAULT_LIST_KEYS:
        values = metadata.get(key)
        if not isinstance(values, list) or any(not isinstance(value, str) or not value for value in values):
            errors.append(f"{key} must be a list of non-empty strings")
            continue
        if len(values) != len(set(values)):
            errors.append(f"{key} must not contain duplicates")
    related_items = metadata.get("related_items")
    if isinstance(related_items, list):
        for value in related_items:
            if not ITEM_ID_PATTERN.fullmatch(value):
                errors.append(f"unsafe related item id: {value}")
    related_runs = metadata.get("related_runs")
    if isinstance(related_runs, list):
        for value in related_runs:
            if not ITEM_ID_PATTERN.fullmatch(value):
                errors.append(f"unsafe related run id: {value}")
    for key in ("source_url", "source_type", "source_author"):
        if key in metadata and (not isinstance(metadata[key], str) or not metadata[key]):
            errors.append(f"{key} must be a non-empty string when present")
    return errors


def load_item(path: Path) -> tuple[dict[str, Any], str]:
    if not path.is_file():
        raise VaultFormatError(f"vault item does not exist: {path}")
    try:
        metadata, body = parse_item(path.read_text(encoding="utf-8"))
    except UnicodeDecodeError as exc:
        raise VaultFormatError(f"vault item is not valid UTF-8: {path}") from exc
    errors = validate_metadata(metadata, path)
    if errors:
        raise VaultFormatError("; ".join(errors))
    return metadata, body


def iter_item_paths(data_root: Path) -> list[Path]:
    items = data_root / "vault" / "items"
    if not items.is_dir():
        return []
    return sorted(path for path in items.iterdir() if path.is_file() and path.suffix == ".md")


def resolve_item(value: str, data_root: Path) -> Path:
    items_root = (data_root / "vault" / "items").resolve()
    candidate = Path(value).expanduser()
    if candidate.is_absolute() or len(candidate.parts) > 1:
        candidate = candidate.resolve()
    else:
        candidate = (items_root / (value if value.endswith(".md") else f"{value}.md")).resolve()
    try:
        candidate.relative_to(items_root)
    except ValueError as exc:
        raise VaultFormatError("vault item path must stay inside the active data root's vault/items") from exc
    return candidate


def write_item(path: Path, metadata: dict[str, Any], body: str, *, overwrite: bool = True) -> None:
    if not overwrite and path.exists():
        raise FileExistsError(path)
    errors = validate_metadata(metadata, path)
    if errors:
        raise VaultFormatError("; ".join(errors))
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(render_item(metadata, body), encoding="utf-8")
    temporary.replace(path)


def build_index(items: Iterable[tuple[Path, dict[str, Any]]]) -> str:
    records = sorted(items, key=lambda record: (record[1]["updated_at"], record[1]["id"]), reverse=True)
    lines = [
        "# Content Flow vault index",
        "",
        "<!-- Generated by `bin/cf vault rebuild-index`; edit item files, not this index. -->",
        "",
    ]
    for status in VAULT_STATUSES:
        lines.extend((f"## {status}", ""))
        selected = [record for record in records if record[1]["status"] == status]
        if not selected:
            lines.extend(("_No items._", ""))
            continue
        for _, metadata in selected:
            tags = ", ".join(metadata["tags"]) if metadata["tags"] else "none"
            lines.append(
                f"- [{metadata['id']}](items/{metadata['id']}.md) — "
                f"{metadata['title']} | {metadata['kind']} | updated {metadata['updated_at'][:10]} | tags: {tags}"
            )
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def read_all_items(data_root: Path) -> tuple[list[tuple[Path, dict[str, Any], str]], list[str]]:
    records: list[tuple[Path, dict[str, Any], str]] = []
    errors: list[str] = []
    ids: dict[str, Path] = {}
    for path in iter_item_paths(data_root):
        try:
            path.resolve().relative_to((data_root / "vault" / "items").resolve())
        except ValueError:
            errors.append(f"{path}: unsafe item path resolves outside vault/items")
            continue
        try:
            metadata, body = load_item(path)
        except VaultFormatError as exc:
            errors.append(f"{path}: {exc}")
            try:
                claimed, _ = parse_item(path.read_text(encoding="utf-8"))
            except (VaultFormatError, UnicodeDecodeError):
                continue
            item_id = claimed.get("id")
            if isinstance(item_id, str):
                if item_id in ids:
                    errors.append(f"duplicate vault item id '{item_id}' in {ids[item_id]} and {path}")
                else:
                    ids[item_id] = path
            continue
        item_id = metadata["id"]
        if item_id in ids:
            errors.append(f"duplicate vault item id '{item_id}' in {ids[item_id]} and {path}")
        else:
            ids[item_id] = path
        records.append((path, metadata, body))
    return records, errors


def validate_relationships(data_root: Path) -> tuple[list[str], list[str]]:
    records, errors = read_all_items(data_root)
    warnings: list[str] = []
    known_ids = {metadata["id"] for _, metadata, _ in records}
    runs_root = data_root / "runs"
    for path, metadata, _ in records:
        for related in metadata["related_items"]:
            if related not in known_ids:
                errors.append(f"{path}: related item does not exist locally: {related}")
        missing_runs = [run_id for run_id in metadata["related_runs"] if not (runs_root / run_id / "run.json").is_file()]
        if metadata["status"] == "developing" and missing_runs:
            errors.extend(f"{path}: developing item references missing active run: {run_id}" for run_id in missing_runs)
        else:
            warnings.extend(f"{path}: historical run is not present locally: {run_id}" for run_id in missing_runs)
        if metadata["status"] == "developing":
            active = False
            for run_id in metadata["related_runs"]:
                state_path = runs_root / run_id / "run.json"
                if not state_path.is_file():
                    continue
                try:
                    state = json.loads(state_path.read_text(encoding="utf-8"))
                except (json.JSONDecodeError, UnicodeDecodeError):
                    continue
                if state.get("status") in ("active", "awaiting_human"):
                    active = True
            if not active:
                errors.append(f"{path}: developing item requires at least one active linked run")
    index = data_root / "vault" / "index.md"
    if not index.exists():
        errors.append(f"{index}: generated index is missing")
    elif not index.is_file():
        errors.append(f"{index}: generated index must be a regular file")
    elif index.is_file() and not errors:
        expected = build_index((path, metadata) for path, metadata, _ in records)
        try:
            actual = index.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            errors.append(f"{index}: generated index is not valid UTF-8")
        else:
            if actual != expected:
                errors.append(f"{index}: generated index is malformed or stale; rebuild it")
    return errors, warnings


def valid_iso_date(value: str) -> bool:
    if not DATE_PATTERN.fullmatch(value):
        return False
    try:
        date.fromisoformat(value)
    except ValueError:
        return False
    return True
