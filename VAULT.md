# Private content vault

## Mental model

Vault material is reusable. Usage is an event in an item's history; status is its current
availability. A source may support many ideas, an idea may support many runs, a proven
angle may be revisited, and completed content may become evidence or material for later
work.

```text
source or observation ──┬──> idea or angle ──┬──> Content Flow run ──┬──> completed asset
                        └──> idea or angle    └──> Content Flow run   └──> completed asset
completed asset ───────────────────────> later idea or run
```

Every arrow may be one-to-many. Finalization records a successful use; it does not consume
the source, idea, angle, or completed artifact.

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

Runtime parsing supports a small YAML subset: scalar strings, non-negative integers, and
string lists written either in JSON-compatible flow style (`["one", "two"]`) or as
indented `- item` entries. The CLI emits quoted strings and flow-style lists.

Required fields:

| Field | Rule |
| --- | --- |
| `id` | lowercase ASCII letters/digits with single hyphens; equals filename stem |
| `title` | non-empty supplied title |
| `kind` | `source`, `idea`, `observation`, `quote`, `excerpt`, or `run-fragment` |
| `status` | `inbox`, `ready`, `developing`, `parked`, or `archived` |
| `captured_at` | real UTC ISO timestamp ending in `Z` |
| `updated_at` | real UTC ISO timestamp ending in `Z` |
| `tags` | unique string list |
| `related_items` | unique safe IDs for all directly related items |
| `related_runs` | unique safe run IDs, including incomplete attempts |
| `successful_runs` | unique completed-use run IDs; subset of `related_runs` |
| `use_count` | non-negative integer equal to the number of `successful_runs` |
| `derived_items` | related item IDs derived from this item |
| `source_items` | related item IDs from which this item was derived |
| `final_artifacts` | unique safe `runs/<run-id>/<filename>` references |

`derived_items` and `source_items` are subsets of `related_items` and reciprocal. Optional
fields are `last_used_at`, `source_url`, `source_type`, `source_author`,
`source_published_at` (ISO date or UTC timestamp), and `revisit_after` (ISO date).
`last_used_at` is present only after a successful completed use. Omit unknown optional
metadata; never fabricate it. Exact supplied URLs are preserved.

The body supports these headings, which may be empty: `Why this was saved`, `Source or raw
material`, `Summary`, `Potential content angles`, `Useful specifics or excerpts`, `Open
questions`, `Mining notes`, `Development history`, and `Parking notes`.

`Mining notes` may preserve angles already explored or still worth exploring, audiences
addressed, formats produced, revisit triggers, unanswered questions, and related completed
assets. Quick capture does not have to populate it. Enrichment must label source evidence
separately from model interpretation.

## Availability lifecycle

```text
inbox      -> ready | developing | parked | archived
ready      -> inbox | developing | parked | archived
developing -> ready | parked | archived
parked     -> ready | developing | archived
archived   -> inbox
```

- `inbox`: captured but not sufficiently reviewed.
- `ready`: available for development or reuse.
- `developing`: linked to at least one unfinished active run.
- `parked`: preserved but not currently ready to develop.
- `archived`: deliberately removed from active consideration.

Starting or resuming a run sets its non-archived linked items `developing`. A parked or
previously successful item may be selected again. Parking normally sets direct origins and
derived ideas `parked`, while supporting contributors return to `ready`; another active
run keeps an item `developing`. Finalization records successful history for every linked
role and normally returns items to `ready`. It leaves archived items archived. Age and
prior success never cause archiving.

## Usage, run roles, and lineage

Runs distinguish:

- `origin_vault_items`: direct material whose selection initiated the run;
- `contributing_vault_items`: supporting sources or completed-content provenance;
- `derived_vault_items`: ideas captured during the run;
- `linked_vault_items`: their ordered, duplicate-free union.

Finalization adds the run to `successful_runs`, records its safe final path, updates
`last_used_at`, and derives `use_count` from successful runs. Repeating `finalize-run` is
idempotent. A parked or abandoned run stays in `related_runs` but does not increase
`use_count`.

The smallest completed-content reuse design is to keep final paths on their existing
origin and contributing items. Those items can later be selected as contributors, so the
later run sees the earlier final-artifact provenance without duplicating the whole run.
Content Flow may ask after finalization whether the human wants a separate discoverable
item, but it never creates one automatically.

Missing local run directories or final artifacts referenced only as history are warnings,
allowing deliberate pruning without erasing provenance. Missing active runs for a
`developing` item are errors.

## Generated index

`vault/index.md` is regenerated from canonical items and contains:

- Inbox
- Ready to develop
- Currently developing
- Parked
- Previously successful and reusable
- Rich sources with multiple related runs
- Revisit due
- Archived

Successful reuse views derive from history, not status. An item may therefore appear in a
status view and one or more history views. The index never determines canonical state.

## Quick and enriched capture

Quick capture is deliberately low-friction and remains `inbox`. Enriched capture is model
work performed only when requested: it may add a concise summary, source-derived facts or
excerpts with links, clearly labeled interpretation, possible angles, mining notes, and
unresolved questions. Proven ideas can record used audiences/formats, what resonated or
was approved, what remains unexplored, and whether timing is evergreen, event-driven, or
change-triggered. A model may propose a deeper, narrower, or contrarian version, another
audience or format, an evidence update, a reader-response follow-up, or repurposing from
completed content. Readiness and next-angle recommendations remain human/model judgments,
not CLI scores, and no idea is automatically declared exhausted.

This durable lineage can support a future Oracle by giving it explicit availability,
history, and provenance to reason over. No Oracle, automatic ranking, scheduling,
integration, semantic search, database, or background workflow is implemented.
