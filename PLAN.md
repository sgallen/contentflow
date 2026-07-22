# Implementation Plan

## Assumptions

- Codex discovers repository skills from `.agents/skills/<name>/SKILL.md`.
- Python 3.10 or newer is available; runtime code uses only the standard library.
- Git tracks procedure, creator context, and durable run artifacts; no publication or external service is involved.
- A run directory name is generated from the current local date plus a safe title slug. A numeric suffix avoids collisions within the same day.
- The CLI validates structural state and artifact presence. Codex and the human remain responsible for editorial quality and approvals.
- LinkedIn character counts use Python Unicode code points (`len`), which matches the requested deterministic Unicode character count but may differ from grapheme-cluster counts.

## Checklist

- [x] Write repository-wide operating instructions and user documentation.
- [x] Document every workflow stage with explicit contracts, routes, and gates.
- [x] Create the `content-flow-setup` skill with onboarding references and templates.
- [x] Create the `content-flow` orchestration skill with state and stage references.
- [x] Add starter creator context without inventing preferences.
- [x] Implement `bin/cf new-run`, `status`, `validate`, and `count`.
- [x] Validate state stages, statuses, pending actions, transitions, and required artifacts.
- [x] Add unit and CLI integration tests.
- [x] Add a concise completed example covering research, interview, review, revision, finalization, and lesson proposals.
- [x] Run all tests, skill validation, example validation, and smoke commands.
