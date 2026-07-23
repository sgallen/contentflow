# Repository Operating Instructions

This repository is a local-first personal content workflow. Codex is the interactive runtime; Markdown and Git are the durable record.

## Operating rules

1. Resolve the private data root through `bin/cf` as defined in `DATA_ROOT.md`. Read `run.json` and the artifacts named there before resuming a run. Never rely on conversation memory as state.
2. Follow the stage contracts in `WORKFLOW.md` and the orchestration instructions in `.agents/skills/content-flow/SKILL.md`.
3. Use `bin/cf` for run scaffolding, validation, status, and character counts. Keep scripts deterministic and offline.
4. Ask one interview question at a time. Do not pre-answer for the creator or manufacture their point of view.
5. Treat research as factual support, not as a substitute for the creator's judgment. Cite sources and separate fact, dispute, and interpretation.
6. Load persistent creator files only when a stage needs them. Drafting requires the creator context; early research does not.
7. Stop at every human gate. Council review, revision application, final approval, and persistent lesson updates require the specified authorization.
8. Treat `apply` as approval only for the clearly stated pending revision plan. Treat `finalize` as approval only when a final candidate is visibly pending.
9. Never publish, call an LLM API, use connectors, or create background or multi-agent infrastructure.
10. Never edit `<data-root>/creator/lessons.md` from lesson candidates without explicit, item-level human approval. Preserve all previously approved lessons unless their removal is separately approved.
11. Update `run.json` atomically after writing each meaningful artifact, then run `bin/cf validate <run>`.
12. Keep subjective claims labeled as observations, creator statements, proposals, or assumptions. Scores are diagnostic, not truth.

## Repository hygiene

- Use relative artifact paths within a run directory.
- Name sequential artifacts with two-digit revisions (`draft-01.md`, `council-01.md`).
- Never overwrite a human-approved artifact; create the next version.
- Keep private artifacts under the selected data root, never under `examples/`. Keep secrets and confidential details out of Git. Record a sanitized confidentiality warning instead.
- The selected data root may intentionally be its own private Git repository nested inside and wholly ignored by this public repository. Interpret `bin/cf data-root` Git safety relative to the containing repository; the private repository is expected to track its own contents.
- Run `python3 -m unittest discover -s tests -v` before considering workflow/tooling changes complete.
