# Implementation Plan

## Reusable README content format

- Extend the existing `format` field from LinkedIn-only validation to the closed set
  `linkedin` and `readme`; retain the same run state, stages, artifact filenames, vault
  relationships, revision limit, and human gates.
- Add a public generic README format starter and let initialization add any missing creator
  starters without overwriting existing private files. This also upgrades an older private
  root by adding only `creator/formats/readme.md`.
- Specialize orchestration by format: a README run inspects repository evidence first,
  interviews adaptively, creates a README-specific brief and proposed README, and uses the
  specified six Council lenses only after authorization.
- Keep drafts and reviews in the private run. Treat revision approval as approval only for
  the pending plan. Before changing the target README, show the exact path and final
  content or diff, then require explicit final approval; change no other target file and
  never commit.
- Update workflow, architecture, data-root, setup, acceptance, and concise root
  documentation in place. Do not rewrite the root README or add an application, service,
  connector, workflow engine, or agent infrastructure.
- Add offline deterministic tests for initialization and upgrade safety, README run
  creation/status/validation/resume shape, Council and revision gates, target-file
  non-modification, tracked/private boundaries, and unchanged LinkedIn behavior.
- Run the full unit suite, validate both skills, exercise a temporary private root, inspect
  CLI help, run `git diff --check`, and confirm no temporary or private artifact is tracked
  or staged.

## Focused vault reuse and lineage refinement

- Keep canonical vault items as Markdown under the active private data root and keep
  `vault/index.md` a deterministic, non-authoritative projection.
- Replace the availability lifecycle with `inbox`, `ready`, `developing`, `parked`, and
  `archived`. Usage is independent history, never a terminal state. Selection may reuse a
  previously successful item, and finalization normally returns it to `ready` unless
  another linked run is active. Archived items are never changed by run completion.
- Add compact frontmatter history and lineage using only the documented scalar/string-list
  subset: `successful_runs`, `last_used_at`, `use_count`, `related_items`,
  `derived_items`, `source_items`, and `final_artifacts`, alongside `related_runs`.
  Successful runs are a subset of related runs; final artifact references use safe
  `runs/<run-id>/<filename>` paths.
- Preserve the distinct run roles `origin`, `contributing`, and `derived`. Their ordered
  union remains `linked_vault_items`. All linked contributors retain successful history
  when a run is finalized, without implying exhaustion.
- Add optional `Mining notes` to item bodies. Enrichment and parking remain model/human
  work; deterministic commands only preserve relationships, statuses, timestamps, and
  artifact references.
- Permit parked and previously successful items to start new runs. Include prior runs,
  final artifacts, explored angles, mining notes, and duplication cautions in the new
  run's provenance material rather than blocking reuse.
- Generate status views plus history-derived views for successful reusable material, rich
  multi-run sources, and revisit dates. Validation checks independent state/history,
  duplicate and safe relationships, active-run requirements, and repeated finalization.
- Use an existing origin or contributing item as the provenance record for completed
  artifacts and permit that item to contribute to later runs. Do not automatically create
  a separate content item; the skill may ask whether a human wants independent discovery.
- The active private vault contains one parked item and no item with status `used`.
  Therefore no `used` migration alias or automatic migration is required. The existing
  private item has no completed run, so its new empty history fields can be added without
  inventing usage.
- Keep the implementation Python-standard-library-only, deterministic, offline, and
  scoped to vault lifecycle and lineage. Do not add an Oracle, publishing, scheduling,
  connectors, semantic search, a database, or background infrastructure.

## Checklist

- [x] Inspect current schema, active private statuses, finalization, parking, resume,
  validation, tests, documentation, and both skills.
- [x] Determine that no old-`used` private-item migration is necessary.
- [x] Update schema, CLI lifecycle, role linkage, index generation, and validation.
- [x] Update the active private item's empty history shape and rebuild its private index.
- [x] Update templates, fictional examples, workflow documentation, and both skills.
- [x] Add deterministic tests for repeated successful reuse, parking/resume, contributors,
  completed-artifact reuse, archived preservation, and index views.
- [x] Run the full requested verification and a temporary-root multi-run mining scenario.
- [x] Validate both skills and confirm no private verification data is tracked or staged.
