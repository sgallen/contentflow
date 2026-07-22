# Workflow

## Stage graph

```text
selected_idea -> research_decision -> research? -> interview -> draft
                                                    ^          |
                                                    |          v
                                               council <-> revision
                                                  |  \-> research
                                                  v
                                             finalization -> lessons -> complete
```

Research is conditional. Council findings can route to revision, interview, research, or final human review. Revision normally runs at most twice; unresolved issues then go to the human. Every backward route records its reason in the new or updated artifact and `run.json`.

## State vocabulary

Valid `stage` values are `selected_idea`, `research_decision`, `research`, `interview`, `draft`, `council`, `revision`, `finalization`, `lessons`, and `complete`. Valid `status` values are `active`, `awaiting_human`, and `complete`.

Valid `pending_human_action` values are:

- `provide_idea_details`
- `confirm_research_decision`
- `answer_interview_question`
- `review_draft`
- `authorize_council`
- `approve_revision_plan`
- `resolve_revision_limit`
- `approve_final`
- `approve_lessons`
- `none`

The usual forward transitions are those in the graph. The only normal backward transitions are `draft|council|revision -> interview` and `draft|council|revision -> research`. `complete` is terminal unless the human explicitly reopens the run. `research_required` is `null` before a decision and a Boolean afterward.

The `artifacts` object uses these stable keys when applicable: `spike`, `research`, `interview`, `brief`, `draft`, `council`, `revision_plan`, `revision`, `council_2`, `final`, and `lessons`. Values are run-relative filenames or `null`. Additional versioned keys are allowed. Paths must remain inside the run directory.

A valid run begins with this shape (values evolve; fields remain):

```json
{
  "id": "2026-07-22-example",
  "title": "Example",
  "format": "linkedin",
  "stage": "selected_idea",
  "status": "awaiting_human",
  "research_required": null,
  "pending_human_action": "provide_idea_details",
  "artifacts": {
    "spike": "spike.md",
    "research": null,
    "interview": null,
    "brief": null,
    "draft": null,
    "council": null,
    "revision_plan": null,
    "revision": null,
    "council_2": null,
    "final": null,
    "lessons": null
  }
}
```

Use `status: awaiting_human` with a specific pending action, `active` with `pending_human_action: none` while Codex can continue, and `complete` only with the terminal stage. A stage is advanced after its required output artifact is durably written; while a human gate is pending, keep the last valid artifact-backed stage and record the pending action.

## Stage 1: Selected idea

### Entry condition

A run exists and the human has selected or supplied an idea.

### Inputs

The supplied idea, title, any source note or vault spike, and the human's initial confidentiality guidance.

### Task

Clarify only what is necessary and record the idea, why it may be worth developing, original source/provenance, known assumptions, unresolved questions, and confidentiality concerns. Do not silently upgrade an assumption to a fact.

### Output artifact

`spike.md`

### Exit condition

All six fields are present with honest “unknown” or “none identified” markers where needed.

### Possible routes

Proceed to `research_decision`; remain here for missing idea details.

### Human gate

The human supplies the idea and decides what confidential material may be recorded.

## Stage 2: Research decision

### Entry condition

`spike.md` is complete.

### Inputs

`spike.md` only; creator voice context is not needed.

### Task

Decide and briefly explain whether research is needed. Default to research for current facts, named people or organizations, quotations, numbers, potentially changed claims, material external disagreement, or unfamiliar subject matter. Research may be skipped for a clearly personal, non-factual reflection.

### Output artifact

A `## Research decision` section appended to `spike.md`, plus `research_required` in `run.json`.

### Exit condition

The decision, short rationale, and claims needing verification (if any) are explicit.

### Possible routes

Go to `research` when required; otherwise go directly to `interview`.

### Human gate

Ask for confirmation when research could expose confidential information, materially widen scope, or the human contests the decision; otherwise explain and continue.

## Stage 3: Research

### Entry condition

`research_required` is `true`, or a later stage explicitly routes back for a factual gap.

### Inputs

`spike.md`, identified claims/questions, and permitted sources from `creator/sources.md` only if source preferences are relevant.

### Task

Research only the material questions. Separate verified facts, citations/links, disputed claims, and interpretation. Note dates and source quality. Produce useful interview questions without inferring the creator's position.

### Output artifact

`research-report.md`

### Exit condition

Each material external claim is supported, marked disputed, or explicitly unresolved; the report contains interview questions.

### Possible routes

Proceed to `interview`; remain in research for blocking evidence; later return here from draft, Council, or revision.

### Human gate

The human resolves scope/confidentiality conflicts and owns whether unresolved claims may appear in the piece.

## Stage 4: Adaptive interview

### Entry condition

The research decision is recorded and any required initial research is complete.

### Inputs

`spike.md`, `research-report.md` when present, and the human's prior answers.

### Task

Ask exactly one question, wait, then append the answer to `interview.md`. After every answer, briefly record obtained material, missing coverage, and the next interviewing move. Choose among functional lenses: direct thesis, concrete example, strongest objection, uncomfortable/self-interested angle, personal significance, practical takeaway, and forward-looking implication. Persona labels are optional mnemonics; always state their functional purpose.

Normally ask four to six questions, but stop on coverage rather than count. Synthesize `content-brief.md` without fabricating a view.

### Output artifact

`interview.md` during the exchange, then `content-brief.md`.

### Exit condition

There is a distinctive thesis, at least one concrete example, specificity and causal detail, tension/disagreement/objection, and a useful payoff or implication.

### Possible routes

Proceed to `draft`; continue interviewing for gaps; return to `research` for a newly material factual question.

### Human gate

Every answer comes from the human. The human may decline a question or mark an answer off-record.

## Stage 5: Draft

### Entry condition

`content-brief.md` meets interview coverage.

### Inputs

Load at this stage: `creator/profile.md`, `creator/voice.md`, `creator/lessons.md`, `creator/formats/linkedin.md`, the brief, interview, and current research. Do not load unrelated runs or vault files.

### Task

Draft primarily from the creator's interview language and thinking. Offer three hook options, one body, three closing options, and a recommended assembly. Use `bin/cf count` for the approximate character count. Flag factual, confidentiality, and material uncertainty issues.

### Output artifact

`draft-01.md`

### Exit condition

All required alternatives, assembly, count, and flags exist, and the draft has been shown to the human.

### Possible routes

Wait for edits; on authorization proceed to `council`; route to `interview` or `research` if drafting exposes a substantive gap.

### Human gate

Pause for draft review. Do not run the Council without human authorization.

## Stage 6: Writer's Council

### Entry condition

A draft exists and the human authorizes Council review.

### Inputs

The current draft, content brief, research flags, and relevant creator voice/format guidance.

### Task

Run one structured review—not separate processes—through six lenses: (1) originality/depth, (2) clarity/structure, (3) specificity/evidence, (4) audience value/actionability, (5) voice authenticity, and (6) hook/payoff/LinkedIn fit. Identify what works, blockers, findings supported by at least two lenses, lens-specific observations, and a ranked revision plan. Score each lens and an overall diagnostic score; scores guide discussion rather than assert objective quality.

### Output artifact

`council-01.md` (and `council-02.md` only after a later authorized/requested re-score).

### Exit condition

The artifact contains every required section and recommends exactly one route: `revise`, `return to interview`, `return to research`, or `ready for final human review`.

### Possible routes

Go to `revision`, `interview`, `research`, or `finalization` as recommended and human-confirmed.

### Human gate

Authorization is required to run the Council. Do not revise automatically after review.

## Stage 7: Revision proposal and application

### Entry condition

Council or human feedback identifies changes to a current draft.

### Inputs

Current draft, Council findings, human feedback, and relevant source artifacts.

### Task

Write a concrete, bounded proposal explaining each intended change, its reason, and anything deliberately unchanged. Pause. Apply only the approved pending plan; `apply` means that plan and nothing unrelated. Preserve the previous draft. Re-score only when requested or when a blocking/route decision depends on it.

### Output artifact

`revision-plan-01.md`, then `draft-02.md`; optionally `council-02.md`. Use `-02` equivalents for one further round.

### Exit condition

The approved proposal is faithfully applied, deviations are disclosed, and the new draft is presented for review. Normally stop after two revision rounds.

### Possible routes

Go to Council re-score, finalization, interview, or research. After two rounds route unresolved issues to the human via `resolve_revision_limit`.

### Human gate

The human approves the stated plan before application and resolves any revision-limit impasse.

## Stage 8: Finalization

### Entry condition

A visible final candidate exists and the human explicitly approves it.

### Inputs

The approved draft, selected hook/closing, and remaining caveats.

### Task

Create an immutable final copy, count it deterministically, and record selection, caveats, and approval. Do not publish.

### Output artifact

`final.md`

### Exit condition

Selected hook/closing, final character count, remaining factual caveats, and approval status are recorded.

### Possible routes

Proceed to `lessons`; return to revision if approval is withheld.

### Human gate

Explicit final approval is required. Publication remains wholly outside this workflow.

## Stage 9: Lessons

### Entry condition

`final.md` is human-approved and at least one earlier generated draft exists.

### Inputs

The initial/generated draft, approved final, Council feedback, revision plan, and direct human feedback.

### Task

Compare generated work with the approved final. Propose no more than five reusable lessons. For each, state the observed edit/feedback, generalized lesson, applicability, non-applicability, and confidence. Avoid treating a one-off taste choice as universal.

### Output artifact

`lesson-candidates.md`

### Exit condition

Candidates are evidence-linked and shown individually for approval.

### Possible routes

Complete with no accepted lessons, or update `creator/lessons.md` only with individually approved candidates and then complete.

### Human gate

Explicit item-level approval is required before persistent lessons change. Rejection or silence leaves `creator/lessons.md` untouched.
