# Private content vault

## Canonical layout

All live material is under the active private data root resolved by `bin/cf`:

```text
vault/
├── items/<item-id>.md
├── assets/<item-id>/        # optional; only for available, useful large material
└── index.md                 # generated; never canonical
```

Items are independent Markdown files suitable for private Git history. Assets may hold
transcripts, long excerpts, imported notes, or related documents. A vault operation never
writes live material to the tracked framework repository.

## Frontmatter schema

Runtime parsing supports a small YAML subset: one scalar per line and string lists written
either in JSON-compatible flow style (`["one", "two"]`) or as indented `- item` entries.
The CLI emits quoted strings and flow-style lists.

Required fields:

| Field | Rule |
| --- | --- |
| `id` | lowercase ASCII letters/digits with single hyphens; equals filename stem |
| `title` | non-empty supplied title |
| `kind` | `source`, `idea`, `observation`, `quote`, `excerpt`, or `run-fragment` |
| `status` | `inbox`, `ready`, `developing`, `parked`, `used`, or `archived` |
| `captured_at` | real UTC ISO timestamp ending in `Z` |
| `updated_at` | real UTC ISO timestamp ending in `Z` |
| `tags` | unique string list |
| `related_items` | unique safe item-ID list |
| `related_runs` | unique safe run-ID list |

Optional fields are `source_url`, `source_type`, `source_author`,
`source_published_at` (ISO date or UTC timestamp), and `revisit_after` (ISO date). Omit
unknown optional metadata; never fabricate it. Exact supplied URLs are preserved.
Mechanical updates preserve unknown frontmatter keys.

The body supports these headings, which may be empty: `Why this was saved`, `Source or raw
material`, `Summary`, `Potential content angles`, `Useful specifics or excerpts`, `Open
questions`, `Development history`, and `Parking notes`.

## Status transitions

```text
inbox      -> ready | developing | archived
ready      -> inbox | developing | archived
developing -> ready | parked | used | archived
parked     -> ready | developing | archived
used       -> archived
archived   -> inbox
```

Starting or resuming a run intentionally sets an item `developing`. Parking sets direct
origins `parked`. Final linkage sets direct origins `used` unless the human chooses
otherwise. Linking supporting material alone never marks it used. Age has no transition.

## Relationships and historical removal

New runs record `origin_vault_items`, `contributing_vault_items`, and their ordered union
`linked_vault_items`. Items record run IDs in `related_runs`. `developing` items must have
an active local linked run. Missing local run directories referenced by developing items
are errors. Missing runs referenced only as parked, used, or archived history are warnings:
this permits intentional pruning of old run directories without erasing provenance.

## Quick and enriched capture

Quick capture is deliberately low-friction and remains `inbox`. Enriched capture is model
work performed only when requested: it may add a concise summary, source-derived facts or
excerpts with links, clearly labeled interpretation, possible angles, and unresolved
questions. Readiness remains a model/human judgment, not a CLI score.

The vault could become an input to a future Oracle, but no Oracle, automatic ranking,
scheduling, integration, database, or background workflow is implemented.
