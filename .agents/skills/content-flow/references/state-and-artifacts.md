# State and artifact update guide

Use the stage/action vocabulary in `WORKFLOW.md`. Artifact values are run-relative filenames, never absolute paths or `..` paths.

After producing an artifact:

1. Write the Markdown artifact completely.
2. Parse the current `run.json`; change only intended keys.
3. Write valid JSON with a trailing newline to `run.json.tmp`, then rename it to `run.json`.
4. Set `status` to `awaiting_human` whenever `pending_human_action` is not `none`; use `active` while Codex can proceed; use `complete` only with stage `complete`.
5. Run `bin/cf validate <run>` and fix structural errors before reporting success.

Never delete an earlier artifact merely because a new version exists. When routing backward, preserve history and record the gap that caused the route.

