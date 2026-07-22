---
name: content-flow
description: Orchestrate the repository's local, file-backed content workflow. Use when starting a run from an idea, resuming or reporting run status, deciding on research, conducting the adaptive interview, drafting a LinkedIn post, running an authorized Writer's Council, applying an approved revision, finalizing an approved post, or proposing reusable lessons.
---

# Content Flow

Act as one capable orchestrator. Council and interviewer personas are functional reasoning lenses, never separate agents or processes.

## Start, resume, or report

1. For a new run, run `bin/cf new-run --title "..." --format linkedin`; report its path. Fill its `spike.md` from the supplied idea without inventing missing provenance, assumptions, or confidentiality facts.
2. For an existing run, read `<run>/run.json`, then read only artifacts relevant to its stage. Run `bin/cf validate <run>` before advancing. Treat disk state, not chat memory, as authoritative.
3. For status intent, run `bin/cf status <run>`, summarize the current artifact/state, pending human action, and valid next routes. Do not advance.
4. Read `WORKFLOW.md` for the active stage contract. Read [references/state-and-artifacts.md](references/state-and-artifacts.md) when creating/updating state, and [references/artifact-templates.md](references/artifact-templates.md) when starting an artifact.

## Advance safely

- Execute only the active stage or an explicitly valid route. Write the named artifact first, then update `run.json` atomically (temporary file plus rename), then validate.
- Research conditionally. Explain the decision briefly. Separate verified fact, citation, dispute, interpretation, and unresolved issue. Never use research to invent the creator's view.
- During interview, ask one question and stop for the answer. After each response record material obtained, material missing, and the functional lens needed next. Stop on coverage, normally after four to six questions.
- Load `creator/profile.md`, `voice.md`, `lessons.md`, and `formats/linkedin.md` only for drafting or later voice/format evaluation. Load `creator/sources.md` earlier only when its source policies matter.
- Run the six-lens Council only after clear human authorization. Produce one structured review and no automatic rewrite.
- After Council feedback, write a concrete revision plan and stop. Interpret “apply” or equivalent approval as permission only for the visible pending plan; preserve the prior draft.
- Limit normal revision to two rounds. Surface unresolved issues rather than polishing indefinitely.
- Interpret “finalize” or equivalent as final approval only when the human is responding to a visible final candidate. Create `final.md`; never publish it.
- Propose at most five evidence-linked lessons after finalization. Never edit `creator/lessons.md` until the human explicitly approves individual candidates.

## Intent is semantic, not keyword-based

Map natural-language intent to a transition only when state and the pending gate make it unambiguous. “Run the council,” “get the panel's review,” and similar requests authorize Council only when a draft is pending. “Apply” approves only a clearly stated pending plan. If context permits multiple consequential interpretations, ask a short clarifying question.

## Quality and routing

Use scores as diagnostic signals. If a draft lacks a distinctive thesis or lived example, route to interview. If it relies on an unsupported or time-sensitive claim, route to research. Prefer a justified backward route over endless surface polishing. Human decisions control taste, confidential material, factual responsibility, revision, final approval, and learning.

