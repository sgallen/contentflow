# State and artifact update guide

Use the stage/action vocabulary in `WORKFLOW.md`. Artifact values are run-relative filenames, never absolute paths or `..` paths.

After producing an artifact:

1. Write the Markdown artifact completely.
2. Parse the current `run.json`; change only intended keys.
3. Write valid JSON with a trailing newline to `run.json.tmp`, then rename it to `run.json`.
4. Set `status` to `awaiting_human` whenever `pending_human_action` is not `none`; use `active` while Codex can proceed; use `parked` only through the explicit parking route; use `complete` only with stage `complete`.
5. Keep `revision_round` at `0` until an approved plan has produced a new draft. Increment it after writing that draft and never above `2`.
6. Run `bin/cf validate <run>` and fix structural errors before reporting success.

Never delete an earlier artifact merely because a new version exists. When routing backward, preserve history and record the gap that caused the route.

New runs also carry `origin_vault_items`, `contributing_vault_items`, and their ordered,
duplicate-free union `linked_vault_items`. Use `bin/cf new-run`/`bin/cf vault link-run`
rather than hand-editing relationships. A parked run has `status: parked`,
`pending_human_action: none`, a non-empty `parking_reason`, UTC `parked_at`, and at least
one linked item. The parking command preserves pre-park status/action for resume.

Before presenting an interview question, persist the unanswered question in `interview.md`, point the `interview` artifact at that file, set `stage: interview`, `status: awaiting_human`, and `pending_human_action: answer_interview_question`, then validate. This makes the exact pending question resumable without chat history.
