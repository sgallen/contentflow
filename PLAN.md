# Implementation Plan

## Vault design and compatibility assumptions

- The vault is private state under the active data root: `vault/items/` contains canonical
  Markdown items, `vault/assets/<item-id>/` may contain genuinely useful large material,
  and `vault/index.md` is a deterministic projection that can always be rebuilt.
- Runtime code remains Python-standard-library-only. Vault frontmatter uses a documented,
  deliberately small YAML subset: scalar keys plus string lists. The CLI emits JSON-quoted
  YAML scalars and flow-style lists, while accepting those forms and ordinary YAML block
  lists. Unknown metadata keys are preserved by mechanical updates.
- Item IDs and filenames use `YYYY-MM-DD-<safe-slug>` with a numeric collision suffix.
  IDs contain only lowercase ASCII letters, digits, and single hyphens; filenames are
  exactly `<id>.md`. Capture timestamps are UTC ISO 8601 values ending in `Z`.
- Status transitions are explicit. Selection for a run is an intentional transition to
  `developing`; age never changes status. A parked item can be selected again.
- New run state contains `origin_vault_items`, `contributing_vault_items`, and
  `linked_vault_items`. These fields remain optional when validating legacy/public example
  states, but when present they are checked for safe, unique IDs and consistent unions.
- A missing run referenced by a `developing` item is an error because that run must be
  active locally. Missing historical runs referenced by `parked`, `used`, or `archived`
  items are reported as warnings rather than rejected, allowing deliberate history pruning.
- Parking preserves the run directory and current stage. It stores the prior status/gate so
  resume can restore them, and records the requested parking fields and assessment in the
  linked item. Parking a run with no origin creates exactly one `run-fragment` item.
- Deterministic commands perform filesystem/state mechanics only. The Content Flow skill
  remains responsible for source interpretation, summaries, angles, readiness judgment,
  parking assessments, and human gates.
- Existing non-vault runs continue to validate. No command commits, stages, initializes,
  or otherwise writes Git state.

## Checklist

- [x] Inspect data-root resolution, run state, workflow contracts, both skills, and tests.
- [x] Implement vault item parsing/rendering, capture, inspection, filtering, updates, and
  deterministic index generation.
- [x] Implement bidirectional run linkage, run creation from one or more items, parking,
  resume, and final-link updates.
- [x] Extend run and vault validation without invalidating legitimate legacy history.
- [x] Update initialization, public blank/fictional examples, schemas, workflow, architecture,
  CLI documentation, and optional private Git guidance.
- [x] Update both skills for natural-language vault capture, enrichment, selection, parking,
  resume, finalization, and setup boundaries.
- [x] Add offline deterministic tests for the complete vertical slice and privacy boundary.
- [x] Run the full test suite, requested smoke commands in temporary roots, example
  validation/status, both skill validators, help output, Git-ignore checks, and
  `git diff --check`.
