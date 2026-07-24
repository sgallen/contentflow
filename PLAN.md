# Implementation Plan

## Conversational content adaptation

- Add one deterministic, offline `bin/cf find "<description>"` index-on-read search across
  private run titles, aliases, finalized and draft format artifacts, shared spike/brief
  material, linked vault titles/content/aliases, final-artifact lineage, and development
  history. Rank lexical, phrase, modest spelling-variation, finalization, format, and
  recency evidence without embeddings, a database, or a persistent search index.
- Return compact source metadata plus a mechanical `clear`, `ambiguous`, or `none`
  resolution signal. Prefer finalized work by default, allow explicit draft selection,
  understand format and recency filters such as latest/yesterday, and leave the concise
  human clarification or no-match question to the skill.
- Add a safe `bin/cf adapt <resolved-source> --to <linkedin|x>` initializer for linked
  adaptation runs. It will preserve the source run and final artifact, copy reusable shared
  evidence without modifying it, carry originating/contributing vault lineage, record
  source/destination provenance, create a fresh destination format state and artifact
  directory, and allow repeated adaptations without overwriting prior output.
- Keep variant choice editorial: an unspecified X request initializes a calibration-ready
  destination with no variant, then the skill recommends single/thread/standalone and
  persists the human's choice before drafting. An explicit variant is recorded directly.
- Update the Content Flow skill so natural requests resolve sources, briefly name the
  selected content, ask only for genuine source/destination ambiguity, recommend an
  unspecified X variant, load the source brief/research/interview/final plus creator and
  destination guidance, calibrate sparse destination evidence honestly, draft natively,
  and retain all ordinary Council/revision/final/lesson gates.
- Update primary user documentation with request examples and keep run IDs/CLI mechanics in
  reference sections. Document search ranking, linked adaptation state, independent
  approvals, repeated reuse, and limitations without adding publishing or integrations.
- Add deterministic offline tests for clear/partial/phrase/fuzzy/recency matches,
  ambiguity/no-match, final-over-draft and explicit-draft behavior, both adaptation
  directions, immutable source finals, repeated output, provenance, sparse X guidance,
  private/tracked boundaries, and existing workflow regressions.
- Verify with a fictional temporary private root, the full unit suite, both skill
  validators, every private and fictional run, `bin/cf --help`, `git diff --check`, and Git
  status/staging checks. Do not add semantic search, a database, publishing, scheduling,
  analytics, integrations, or unrelated workflow features.

Completed:

- [x] Inspected lookup/vault behavior, adaptation procedure, private run titles/finals,
  linked vault development history, and existing tests before implementation.
- [x] Added deterministic lexical/metadata discovery with clear/ambiguous/none resolution,
  final/draft preference, spelling variation, format/variant, and recency handling.
- [x] Added linked adaptation initialization, source hashing, copied shared evidence,
  vault/prior-adaptation lineage, independent destination state, and X variant persistence.
- [x] Updated the orchestration skill and reusable user/reference documentation.
- [x] Added offline discovery/adaptation/calibration/private-boundary tests.
- [x] Ran the complete suite, temporary-root scenarios, both skill validators, all private
  and fictional validation, CLI help, diff checks, and Git hygiene checks.

## First-class LinkedIn and X formats

- Replace singular run-level `format`, editorial stage, revision round, approval action,
  artifacts, and final pointer with schema version 2: ordered `requested_formats`, optional
  `primary_format`, shared development state/artifacts, `active_format`, and independent
  `format_states`. Keep README-only runs on the same schema while preserving their
  repository-document overlay.
- Keep `spike.md`, research, interview, and the channel-neutral social `content-brief.md`
  once at the run root. Put social rendering artifacts under
  `formats/<format>/`; each format owns its variant, angle, stage, status, pending human
  action, revision round, current/history pointers, disposition, and final artifact.
- Accept repeatable `--format` options and optional `--primary-format`. Preserve request
  order, reject duplicates and invalid primaries, never add an unrequested format, and
  draft an explicit primary first. A run completes only when every requested format is
  finalized, declined, or format-parked.
- Add tracked and safely initialized X guidance. Canonically support `single`, `thread`,
  and `standalone` variants without inventing creator preferences. Add one deterministic
  X validator with a single canonical per-post character limit and machine-readable
  recommended-version sections; do not scatter limits through orchestration prose.
- Make adaptation an orchestration route, not mechanical conversion: reload the shared
  brief and useful evidence, treat an approved primary as selection evidence rather than
  idea truth, load the destination guidance, confirm an unspecified X variant, and create
  a native destination draft with independent Council, revision, final, and lesson gates.
- Extend vault final lineage to format-qualified artifact paths and record format, X
  variant, and any explicitly captured angle in development history. Keep a vault item
  reusable after any one output and allow several final artifacts for one run.
- Provide a deterministic schema migration command with dry-run reporting. Migrate
  singular LinkedIn and README runs to one requested format only; move their
  format-specific artifacts into the matching format directory without changing content,
  keep shared artifacts at the run root, and never fabricate X output.
- Update the workflow, architecture, data-root guidance, acceptance notes, both skills,
  artifact references, and only the minimal root README facts needed for X support.
- Add offline tests for all run selections, migration, independent states/gates/finals,
  format parking/decline, adaptation-ready ordering, all X variants and character checks,
  qualified vault lineage, unchanged README safeguards, and private/tracked boundaries.
- Verify both skills, all fictional and private runs, the complete temporary-root matrix,
  CLI help, full unit suite, `git diff --check`, and Git hygiene. Add no publishing,
  scheduling, analytics, API, UI, Oracle, or multi-agent infrastructure.

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

- [x] Inspect singular state, LinkedIn/README behavior, vault final lineage, fictional
  example, and all seven private runs before editing.
- [x] Report that migration would preserve six LinkedIn-only runs and one README-only run,
  add no X requests, move rendering artifacts without changing content, and preserve the
  pre-existing private Git changes.
- [x] Implement schema version 2, repeatable formats, primary ordering, shared development,
  independent format states/artifacts/gates/revisions/finals/lessons, X variants and
  deterministic validation, explicit format park/decline, and format-qualified lineage.
- [x] Migrate the fictional example and private runs; add only missing private X guidance;
  validate every migrated run and the private vault.
- [x] Update workflow, architecture, data-root/vault/acceptance documentation, templates,
  setup/orchestration skills, and minimal README facts.
- [x] Add deterministic tests for format selection, X initialization/variants/limits,
  independent state/gates, ordering, completion, migration, README safety, and multi-format
  vault lineage.
- [x] Run the complete unit suite, both skill validators, temporary selection/adaptation
  matrix, fictional/private validation, CLI help, vault validation, and `git diff --check`.
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
