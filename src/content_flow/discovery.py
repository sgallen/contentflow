"""Deterministic lexical discovery for private Content Flow material."""

from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import asdict, dataclass
from datetime import date, timedelta
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, Iterable

from .vault import read_all_items


FORMAT_WORDS = {
    "linkedin": "linkedin",
    "x": "x",
    "twitter": "x",
}
QUERY_STOP_WORDS = {
    "a",
    "about",
    "adapt",
    "adaptation",
    "an",
    "article",
    "content",
    "create",
    "finished",
    "for",
    "from",
    "give",
    "into",
    "latest",
    "last",
    "make",
    "me",
    "most",
    "my",
    "of",
    "piece",
    "post",
    "posts",
    "recent",
    "standalone",
    "take",
    "that",
    "the",
    "thread",
    "three",
    "to",
    "turn",
    "version",
    "we",
    "work",
    "yesterday",
}
SOURCE_REF_PATTERN = re.compile(
    r"run:(?P<run>[a-z0-9]+(?:-[a-z0-9]+)*):"
    r"(?P<format>linkedin|x|readme):(?P<selection>final|draft)"
)


@dataclass(frozen=True)
class SourceMatch:
    source_ref: str
    title: str
    content_type: str
    status: str
    format: str | None
    finalization_state: str
    variant: str | None
    date: str
    private_path: str
    related_run: str | None
    score: int
    matched_on: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class FindResult:
    query: str
    resolution: str
    matches: tuple[SourceMatch, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "query": self.query,
            "resolution": self.resolution,
            "matches": [match.to_dict() for match in self.matches],
        }


def normalize(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value)
    ascii_value = decomposed.encode("ascii", "ignore").decode("ascii").lower()
    return " ".join(re.findall(r"[a-z0-9]+", ascii_value))


def _tokens(value: str) -> list[str]:
    return [token for token in normalize(value).split() if token]


def _safe_read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8") if path.is_file() else ""
    except (OSError, UnicodeDecodeError):
        return ""


def _run_date(run_id: str, artifact: Path | None = None) -> str:
    match = re.match(r"(\d{4}-\d{2}-\d{2})-", run_id)
    run_day = match.group(1) if match else "0001-01-01"
    if artifact is None or not artifact.is_file():
        return run_day
    try:
        artifact_day = date.fromtimestamp(artifact.stat().st_mtime).isoformat()
    except OSError:
        return run_day
    return max(run_day, artifact_day)


def _as_string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str) and item.strip()]


def _candidate_score(
    *,
    full_query_phrase: str,
    query_phrase: str,
    query_tokens: list[str],
    title: str,
    aliases: Iterable[str],
    tags: Iterable[str],
    body: str,
    finalized: bool,
    draft_requested: bool,
    recent_requested: bool,
    candidate_date: str,
    today: date,
    yesterday_requested: bool,
) -> tuple[int, str]:
    normalized_title = normalize(title)
    normalized_aliases = [normalize(alias) for alias in aliases]
    normalized_tags = " ".join(normalize(tag) for tag in tags)
    normalized_body = normalize(body)
    title_tokens = set(_tokens(" ".join((title, *aliases))))
    body_tokens = set(_tokens(" ".join((normalized_tags, normalized_body))))
    score = 0
    reason = "metadata"

    if query_tokens:
        if query_phrase == normalized_title:
            score, reason = 125, "exact title"
        elif query_phrase in normalized_aliases:
            score, reason = 120, "exact alias"
        elif query_phrase and query_phrase in normalized_title:
            score, reason = 108, "partial title"
        elif query_phrase and any(query_phrase in alias for alias in normalized_aliases):
            score, reason = 104, "partial alias"
        else:
            title_hits = sum(token in title_tokens for token in query_tokens)
            body_hits = sum(token in body_tokens for token in query_tokens)
            title_coverage = title_hits / len(query_tokens)
            body_coverage = body_hits / len(query_tokens)
            if title_coverage:
                score, reason = round(88 * title_coverage), "title words"
            recognizable = full_query_phrase or query_phrase
            if recognizable and recognizable in normalized_body and score < 92:
                score, reason = 92, "recognizable phrase"
            elif body_coverage and round(62 * body_coverage) > score:
                score, reason = round(62 * body_coverage), "content words"

            comparison_tokens = title_tokens | body_tokens
            fuzzy_scores = [
                max(
                    (SequenceMatcher(None, token, candidate).ratio() for candidate in comparison_tokens),
                    default=0.0,
                )
                for token in query_tokens
            ]
            if fuzzy_scores and min(fuzzy_scores) >= 0.78:
                fuzzy = round(82 * sum(fuzzy_scores) / len(fuzzy_scores))
                if fuzzy > score:
                    score, reason = fuzzy, "spelling variation"
    elif recent_requested:
        score, reason = 72, "recency"
    else:
        return 0, "no searchable terms"

    if yesterday_requested:
        expected = (today - timedelta(days=1)).isoformat()
        if candidate_date != expected:
            return 0, "outside requested date"
        score += 18
        reason += " and yesterday"
    if finalized:
        score += 18 if not draft_requested else -12
    else:
        score += 22 if draft_requested else -14
    return max(score, 0), reason


def _artifact_selection(
    run_dir: Path,
    format_state: dict[str, Any],
    *,
    draft_requested: bool,
) -> tuple[str | None, str, bool]:
    artifacts = format_state.get("artifacts")
    if not isinstance(artifacts, dict):
        artifacts = {}
    draft = artifacts.get("draft")
    final = format_state.get("final_artifact") or artifacts.get("final")
    if draft_requested and isinstance(draft, str) and (run_dir / draft).is_file():
        return draft, "draft", False
    if isinstance(final, str) and (run_dir / final).is_file():
        return final, "final", True
    if isinstance(draft, str) and (run_dir / draft).is_file():
        return draft, "draft", False
    return None, "unfinished", False


def find_sources(
    data_root: Path,
    query: str,
    *,
    format_name: str | None = None,
    variant_name: str | None = None,
    latest: bool = False,
    drafts: bool = False,
    limit: int = 8,
    today: date | None = None,
) -> FindResult:
    """Search private data at read time and return compact ranked candidates."""
    current_date = today or date.today()
    normalized_query = normalize(query)
    raw_tokens = normalized_query.split()
    inferred_format = next(
        (mapped for token in raw_tokens if (mapped := FORMAT_WORDS.get(token))),
        None,
    )
    selected_format = format_name or inferred_format
    inferred_variant = next(
        (variant for variant in ("thread", "standalone") if variant in raw_tokens),
        None,
    )
    selected_variant = variant_name or inferred_variant
    recent_requested = latest or any(
        phrase in normalized_query for phrase in ("latest", "most recent", "last", "yesterday")
    )
    yesterday_requested = "yesterday" in raw_tokens
    draft_requested = drafts or "draft" in raw_tokens
    query_tokens = [
        token
        for token in raw_tokens
        if token not in QUERY_STOP_WORDS and token not in FORMAT_WORDS
    ]
    query_phrase = " ".join(query_tokens)

    vault_records, _ = read_all_items(data_root)
    vault_by_id = {metadata["id"]: (metadata, body) for _, metadata, body in vault_records}
    represented_vault_ids: set[str] = set()
    matches: list[SourceMatch] = []
    runs_root = data_root / "runs"

    if runs_root.is_dir():
        for run_dir in sorted(path for path in runs_root.iterdir() if path.is_dir()):
            state_path = run_dir / "run.json"
            try:
                state = json.loads(state_path.read_text(encoding="utf-8"))
            except (OSError, UnicodeDecodeError, json.JSONDecodeError):
                continue
            if not isinstance(state, dict):
                continue
            title = state.get("title")
            if not isinstance(title, str) or not title.strip():
                continue
            shared_artifacts = state.get("shared_artifacts")
            if not isinstance(shared_artifacts, dict):
                shared_artifacts = {}
            shared_text = "\n".join(
                _safe_read(run_dir / value)
                for value in shared_artifacts.values()
                if isinstance(value, str)
            )
            run_aliases = _as_string_list(state.get("aliases"))
            linked_ids = _as_string_list(state.get("linked_vault_items"))
            linked_text: list[str] = []
            linked_aliases: list[str] = []
            linked_tags: list[str] = []
            for item_id in linked_ids:
                record = vault_by_id.get(item_id)
                if record is None:
                    continue
                metadata, body = record
                represented_vault_ids.add(item_id)
                linked_text.extend((metadata["title"], body))
                linked_aliases.extend(_as_string_list(metadata.get("aliases")))
                linked_aliases.extend(_as_string_list(metadata.get("alternate_titles")))
                linked_tags.extend(_as_string_list(metadata.get("tags")))

            format_states = state.get("format_states")
            if not isinstance(format_states, dict):
                continue
            for candidate_format, format_state in format_states.items():
                if selected_format and candidate_format != selected_format:
                    continue
                if not isinstance(format_state, dict):
                    continue
                if selected_variant and (
                    candidate_format != "x" or format_state.get("variant") != selected_variant
                ):
                    continue
                artifact_value, selection, finalized = _artifact_selection(
                    run_dir,
                    format_state,
                    draft_requested=draft_requested,
                )
                if draft_requested and selection != "draft":
                    continue
                artifact_path = run_dir / artifact_value if artifact_value else None
                format_text = "\n".join(
                    _safe_read(run_dir / value)
                    for value in format_state.get("artifacts", {}).values()
                    if isinstance(value, str)
                )
                body = "\n".join((shared_text, format_text, *linked_text))
                candidate_date = _run_date(run_dir.name, artifact_path)
                score, reason = _candidate_score(
                    full_query_phrase=normalized_query,
                    query_phrase=query_phrase,
                    query_tokens=query_tokens,
                    title=title,
                    aliases=(*run_aliases, *linked_aliases),
                    tags=linked_tags,
                    body=body,
                    finalized=finalized,
                    draft_requested=draft_requested,
                    recent_requested=recent_requested,
                    candidate_date=candidate_date,
                    today=current_date,
                    yesterday_requested=yesterday_requested,
                )
                if score < 45:
                    continue
                private_path = (
                    str(Path("runs") / run_dir.name / artifact_value)
                    if artifact_value
                    else str(Path("runs") / run_dir.name / "run.json")
                )
                source_ref = f"run:{run_dir.name}:{candidate_format}:{selection}"
                matches.append(
                    SourceMatch(
                        source_ref=source_ref,
                        title=title,
                        content_type="run artifact" if artifact_value else "run",
                        status=str(state.get("status", "unknown")),
                        format=candidate_format,
                        finalization_state="finalized" if finalized else selection,
                        variant=format_state.get("variant")
                        if isinstance(format_state.get("variant"), str)
                        else None,
                        date=candidate_date,
                        private_path=private_path,
                        related_run=run_dir.name,
                        score=score,
                        matched_on=reason,
                    )
                )

    for path, metadata, body in vault_records:
        if metadata["id"] in represented_vault_ids:
            continue
        inferred_vault_format = None
        source_type = normalize(str(metadata.get("source_type", "")))
        if "linkedin" in source_type:
            inferred_vault_format = "linkedin"
        elif re.search(r"\b(x|twitter)\b", source_type):
            inferred_vault_format = "x"
        if selected_format and inferred_vault_format not in (selected_format, None):
            continue
        aliases = (
            *_as_string_list(metadata.get("aliases")),
            *_as_string_list(metadata.get("alternate_titles")),
        )
        candidate_date = str(metadata.get("updated_at", "0001-01-01"))[:10]
        finalized = bool(metadata.get("final_artifacts"))
        score, reason = _candidate_score(
            full_query_phrase=normalized_query,
            query_phrase=query_phrase,
            query_tokens=query_tokens,
            title=metadata["title"],
            aliases=aliases,
            tags=_as_string_list(metadata.get("tags")),
            body=body,
            finalized=finalized,
            draft_requested=draft_requested,
            recent_requested=recent_requested,
            candidate_date=candidate_date,
            today=current_date,
            yesterday_requested=yesterday_requested,
        )
        if score < 45:
            continue
        matches.append(
            SourceMatch(
                source_ref=f"vault:{metadata['id']}",
                title=metadata["title"],
                content_type=f"vault {metadata['kind']}",
                status=metadata["status"],
                format=inferred_vault_format,
                finalization_state="finalized" if finalized else "source",
                variant=None,
                date=candidate_date,
                private_path=str(Path("vault") / "items" / path.name),
                related_run=metadata["related_runs"][-1] if metadata["related_runs"] else None,
                score=score,
                matched_on=reason,
            )
        )

    matches.sort(
        key=lambda match: (
            match.score,
            match.finalization_state == "finalized",
            match.date,
            match.title.casefold(),
        ),
        reverse=True,
    )
    if recent_requested and matches:
        preferred = [match for match in matches if match.finalization_state == "finalized"]
        if preferred and not draft_requested:
            matches = preferred
        newest = max(match.date for match in matches)
        matches = [match for match in matches if match.date == newest]
    matches = matches[: max(limit, 1)]

    if not matches:
        resolution = "none"
    elif len(matches) == 1:
        resolution = "clear"
    else:
        margin = matches[0].score - matches[1].score
        resolution = "clear" if matches[0].score >= 90 and margin >= 18 else "ambiguous"
    return FindResult(query=query, resolution=resolution, matches=tuple(matches))
