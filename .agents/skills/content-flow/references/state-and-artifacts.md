# State and artifact update guide

Use schema version 2 and the vocabulary in `WORKFLOW.md`. Shared artifact values are
run-root filenames. Format artifact values are run-relative paths under
`formats/<format>/`. Paths are never absolute and never contain `..`.

After producing an artifact:

1. Write the Markdown artifact completely.
2. Parse the current `run.json`; change only intended keys.
3. Write valid JSON with a trailing newline to `run.json.tmp`, then rename it to `run.json`.
4. Update either `shared_state` or exactly one `format_states.<format>` entry. Never copy a
   pending action, approval, revision round, or final pointer across formats.
5. Keep each format's `revision_round` at `0` until its approved plan has produced a new
   draft. Increment after writing and never above `2`.
6. Run `bin/cf validate <run>` and fix structural errors before reporting success.

Never delete an earlier artifact merely because a new version exists. When routing backward, preserve history and record the gap that caused the route.

For existing-content reuse, resolve the source with `bin/cf find` and create a linked run
with `bin/cf adapt` unless a safe unfinished destination state already exists in the
source run. Do not hand-construct adaptation provenance. The initializer records
`adaptation.source_run`, source format/artifact/final/hash, destination format/variant,
source vault items, prior adaptations, and timestamp; copies the source interview, brief,
and available research without changing them; and creates a fresh format state. An
unspecified X destination may wait at `pending` with
`confirm_destination_variant`; use `bin/cf set-x-variant` before drafting. The adaptation
run's destination final and approvals never replace the source final or approvals.

New runs also carry `origin_vault_items`, `contributing_vault_items`,
`derived_vault_items`, and their ordered, duplicate-free union `linked_vault_items`. Use
`bin/cf new-run`/`bin/cf vault link-run` rather than hand-editing relationships. A parked
run has `status: parked`, a non-empty `parking_reason`, UTC `parked_at`, and at least
one linked item. The parking command preserves pre-park status/action for resume.

Before presenting an interview question, persist it in shared `interview.md`, point
`shared_artifacts.interview` at that file, and set the matching values in `shared_state`.
