# Workflow

## Vault intake and incubation

The vault precedes and outlives runs. Quick capture creates an `inbox` item without forcing
analysis. Requested enrichment may add source-derived summary/specifics and clearly labeled
interpretation, proposed angles, and open questions. Selecting one or more items creates a
normal run, moves selected items to `developing`, records bidirectional IDs, and preserves
useful material in `spike.md`. See `VAULT.md` for schema and lifecycle.

## Stage graph and format rendering

```text
vault -> shared idea -> research decision -> research? -> interview -> content brief
                                                               |
                                                               v
                         primary format: draft -> Council -> revision? -> final -> lessons
                                                               |
                                                               v
                       secondary format(s): native adaptation -> independent gates -> final
```

Research and interview are shared. For social runs, `content-brief.md` is channel-neutral:
thesis, examples, evidence, creator reasoning, tension, payoff, creator wording,
confidentiality, possible angles, and unresolved weaknesses. Rendering begins only after
that shared substance exists. A designated primary is rendered first. An approved primary
is useful selection evidence, but the brief and interview remain authoritative.

`linkedin`, `x`, and `readme` are supported. Repeat `--format` to request several outputs.
README remains a repository-document overlay and is not automatically repurposed with
social content. X supports `single`, `thread`, and `standalone`; an unspecified variant is
recommended from the material and confirmed by the human rather than defaulting to a
thread.

Format artifacts live under `formats/<format>/`. Every format owns its draft, Council,
revision plan, revision round, final, lessons, variant/angle, status, and pending approval.
No authorization crosses a format boundary. A run is complete only after every requested
format is finalized, declined, or explicitly format-parked.

## Conversational adaptation entry

The normal entry for reuse is a request such as “Let's adapt the Bostrom post for X.”
Content Flow resolves the active root, searches private run and vault material
deterministically, reports the selected source, and continues without requiring internal
identifiers. Exact and partial titles, topic words, recognizable phrases, people/concepts,
aliases, spelling variations, explicit drafts, and recency descriptions are supported.
Finalized content wins over unfinished drafts unless the human explicitly requests a
draft.

One clearly strongest match proceeds. Several plausible matches produce one concise
human-facing choice question. No credible match produces an honest summary of the private
locations searched and a request for a phrase, title, link, or approximate date. Raw run
IDs and private paths are reference details, not the main interaction.

An existing unfinished destination state may be activated only when doing so preserves
primary ordering and approvals. Otherwise `bin/cf adapt` creates a linked destination run.
It records immutable source provenance, copies reusable shared evidence, links originating
vault material, and creates a fresh independent format state. Repeating an adaptation
never overwrites an earlier destination or source final.

## Schema version 2

Top-level routing uses ordered `requested_formats`, optional `primary_format`, and
`active_format`. Shared development lives in `shared_state` and `shared_artifacts`.
Independent rendering lives in `format_states`:

```json
{
  "schema_version": 2,
  "id": "2026-07-24-example",
  "title": "Example",
  "requested_formats": ["linkedin", "x"],
  "primary_format": "linkedin",
  "active_format": null,
  "status": "awaiting_human",
  "shared_state": {
    "stage": "selected_idea",
    "status": "awaiting_human",
    "research_required": null,
    "pending_human_action": "provide_idea_details"
  },
  "shared_artifacts": {
    "spike": "spike.md",
    "research": null,
    "interview": null,
    "brief": null
  },
  "format_states": {
    "linkedin": {
      "variant": null,
      "angle": null,
      "stage": "pending",
      "status": "pending",
      "revision_round": 0,
      "pending_human_action": "none",
      "disposition": "active",
      "artifacts": {"draft": null, "council": null, "revision_plan": null,
                    "revision": null, "final": null, "lessons": null},
      "final_artifact": null
    },
    "x": {
      "variant": null,
      "angle": null,
      "stage": "pending",
      "status": "pending",
      "revision_round": 0,
      "pending_human_action": "none",
      "disposition": "active",
      "artifacts": {"draft": null, "council": null, "revision_plan": null,
                    "revision": null, "final": null, "lessons": null},
      "final_artifact": null
    }
  },
  "origin_vault_items": [],
  "contributing_vault_items": [],
  "derived_vault_items": [],
  "linked_vault_items": []
}
```

Shared stages are `selected_idea`, `research_decision`, `research`, `interview`,
`content_brief`, and `complete`. Format stages are `pending`, `draft`, `council`,
`revision`, `finalization`, `lessons`, `complete`, `declined`, and `parked`. Each format
revision round starts at zero, increments only after an approved concrete plan creates the
next draft, and stops at two.

Shared paths are run-root filenames. Format paths must resolve under the matching
`formats/<format>/` directory. History pointers use the same numbered families as before.
`bin/cf migrate-run <run>` reports the singular-schema migration; `--apply` moves only
format-specific artifacts, preserves shared files, rewrites state and local vault final
paths, and never fabricates another requested format.

Pending actions retain their meanings: idea details, research decision/scope, one
interview answer, draft review, Council authorization, route confirmation, revision-plan
approval, revision-limit resolution, final approval, and lesson approval. The pending
state is stored only in the shared state or active format that owns the gate.

### Adaptation

Adaptation reloads the shared brief, useful research/interview evidence, approved primary,
and destination guidance. It identifies the approved central framing, selects only useful
examples, preserves factual/confidentiality constraints, and creates a native destination
draft. Mechanical truncation, expansion, paragraph splitting, or reformatting is not
adaptation. A secondary format gets its own Council, revision, final, and lessons.

A linked adaptation run has one requested destination format and an `adaptation` object
with the source reference, run/title/format, selected artifact and SHA-256, available
source final, finalization state, destination and optional variant, source vault items,
prior adaptation runs, and creation timestamp. Its copied interview and brief put shared
development in `complete`; rendering starts fresh at `pending`. An unspecified X variant
uses pending action `confirm_destination_variant` until the human approves the
recommendation. `bin/cf set-x-variant` records that choice before any draft exists.

Sparse destination guidance is a calibration state, not evidence of durable preference.
Use creator-wide voice plus established format constraints, keep run conclusions
tentative, and never promote them to persistent lessons without item-level approval.

### X deterministic structure

The canonical format specification is `creator/formats/x.md`; the mechanical command is
`bin/cf validate-x FILE --variant <single|thread|standalone>`. The limit is defined once in
the deterministic layer and surfaced by the template. Drafts/finals declare a variant and
place validated posts under `## Recommended final version`. Threads use sequential posts;
standalone outputs contain distinct self-contained angles.

## Explicit parking route

A human may park a run because its idea lacks substance, the interview did not establish a
distinctive view, more lived experience or evidence is needed, timing is wrong, the angle
overlaps existing work, or they simply do not want to finish now. Parking is not failure.

Before the mechanical transition, write `parking-assessment-NN.md` in the run with: what
remains promising, strongest collected material, why work is stopping, what is missing,
conditions that could make it worth revisiting, recommended next angle or action, and
whether to resume or reconsider from a new angle. Then use
`bin/cf vault park-run`. If origins exist, update them in place; otherwise create one
`run-fragment`. Set run status `parked`, pending action `none`, link IDs, reason, and UTC
timestamp. Preserve the whole run directory and all earlier successful-use history.

`bin/cf vault resume-run` restores the pre-park status/gate and sets non-archived linked
items back to `developing`. Resume at the preserved stage after reading and validating disk
state.

## Stage 1: Selected idea

### Entry condition

A run exists and the human has selected or supplied an idea.

### Inputs

For social content, the supplied idea, title, any source note or vault item, and the human's
initial confidentiality guidance. For README, the target project, exact target README path,
repository evidence, existing documentation, and initial confidentiality guidance.

### Task

Clarify only what is necessary. For social content, record the idea, why it may be worth
developing, provenance, assumptions, unresolved questions, and confidentiality concerns.
For README, inspect first and record the project and target path, project purpose,
repository evidence, documentation claims, owner intent, assumptions, unresolved questions,
and the public/private boundary. Do not silently upgrade an assumption or documentation
claim to a proven fact.

### Output artifact

`spike.md`

### Exit condition

The shared spike fields are present with honest "unknown" or "none identified"
markers where needed.

### Possible routes

Proceed to `research_decision`; remain here for missing idea details.

### Human gate

The human supplies the idea or identifies the target project and decides what confidential
material may be recorded.

## Stage 2: Research decision

### Entry condition

`spike.md` is complete.

### Inputs

`spike.md` only; creator voice context is not needed.

### Task

Decide and briefly explain whether research is needed. Default to research for current
facts, named people or organizations, quotations, numbers, potentially changed claims,
material external disagreement, or unfamiliar subject matter. Research may be skipped for
a clearly personal, non-factual reflection. For README, repository inspection is ordinary
source work rather than external research; research only when a material claim still needs
factual verification.

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

`spike.md`, identified claims/questions, and permitted sources from `<data-root>/creator/sources.md` only if source preferences are relevant.

### Task

Research only the material questions. For README, prefer repository evidence and owner
input; use external research only when factual verification is materially needed. Separate
verified facts, citations/links, disputed claims, unresolved claims, and interpretation.
Note dates and source quality. Produce useful interview questions without inferring the
creator's position. If scope or confidentiality blocks progress, persist `research` +
`awaiting_human` + `resolve_research_scope`.

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

Choose exactly one next question based on the most important unresolved issue. Before
showing it, append a pending-question record to `interview.md` containing the question,
functional lens, material already obtained, missing coverage it targets, and
`Answer: pending`; atomically set `interview` + `awaiting_human` +
`answer_interview_question` in `run.json`, then validate. Show that question and stop.
After the human answers, replace the pending marker with the answer and record obtained
material, remaining gaps, and the next interviewing move.

For social content, useful lenses include direct thesis, concrete example, strongest objection,
uncomfortable/self-interested angle, personal significance, practical takeaway, and
forward-looking implication. For README, useful lenses include primary audience, core
problem, strongest value proposition, first reader action, maturity, differentiation,
non-goals, trust or privacy, tone, and contribution posture. Do not use a fixed README
questionnaire. Persona labels are optional mnemonics; always state their functional purpose.

Stop on coverage rather than question count. Synthesize channel-neutral social
`content-brief.md` without fabricating a view or channel structure. A README brief records target readers, primary promise, reader problem,
desired action, key proof, required sections, important commands, public claims requiring
verification, tone, avoidances, limitations, and unresolved questions.

### Output artifact

`interview.md` during the exchange, then `content-brief.md`.

### Exit condition

Social content has a distinctive thesis, at least one concrete example, specificity and causal
detail, tension/disagreement/objection, and a useful payoff or implication. README has a
supported project description, target reader, reader problem, primary promise, desired
action, verified setup path, scope, limitations, and no blocking unresolved claim.

### Possible routes

Proceed to `draft`; continue interviewing for gaps; return to `research` for a newly material factual question.

### Human gate

Every answer comes from the human. The human may decline a question or mark an answer off-record.

## Stage 5: Draft

### Entry condition

`content-brief.md` meets interview coverage.

### Inputs

Load at this stage: `<data-root>/creator/profile.md`, `voice.md`, `lessons.md`, the active
`formats/<format>.md`, the brief, interview, and current research. For README also use the
inspected repository evidence recorded for this run. Do not load unrelated runs or vault
files.

### Task

For LinkedIn, draft primarily from the creator's interview language and thinking. Offer
three hook options, one body, three closing options, and a recommended assembly. Use
`bin/cf count draft-NN.md --section "Recommended assembled version"` for the post-body
character count.

For X, confirm `single`, `thread`, or `standalone` first. Use the canonical structure in
`creator/formats/x.md`, validate every recommended post with `bin/cf validate-x`, identify
thread-post functions or standalone angles, and report factual/confidentiality flags.

For README, produce a complete proposed README grounded in repository evidence and owner
input. The first screen should answer what the project is, why the reader should care, and
how to try it. Include only useful sections from the format guidance. Verify copyable
commands. Character counting remains available but is not a quality metric. For every
format, flag factual, confidentiality, and material uncertainty issues.

### Output artifact

`draft-01.md`

### Exit condition

The active format's required content and flags exist, and the draft has been shown to the
human. The target README remains unchanged.

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

Run one structured review, not separate processes. For LinkedIn use: (1)
originality/depth, (2) clarity/structure, (3) specificity/evidence, (4) audience
value/actionability, (5) voice authenticity, and (6) hook/payoff/LinkedIn fit.

For README use: (1) positioning, (2) first-minute comprehension, (3) onboarding, (4)
technical accuracy, (5) trust and credibility, and (6) voice and readability. Identify
what works, blocking findings, consensus findings, optional taste suggestions, exact
inaccurate claims or commands, and a ranked revision plan. Score each lens and an overall
diagnostic score; scores guide discussion rather than assert objective quality.

For X use: (1) immediate clarity, (2) strength of point of view, (3) compression, (4)
specificity and credibility, (5) voice authenticity, and (6) platform fit. Explicitly
separate unnecessary cleverness, generic engagement bait, unsupported claims, and
repetition inherited from a primary format.

### Output artifact

`council-01.md` (and `council-02.md` only after a later authorized/requested re-score). Record the human authorization/request in each Council artifact.

### Exit condition

The artifact contains every required section and recommends exactly one route: `revise`, `return to interview`, `return to research`, or `ready for final human review`.

### Possible routes

Go to `revision`, `interview`, `research`, or `finalization` as recommended and human-confirmed. When a backward route needs confirmation, persist `council` + `awaiting_human` + `confirm_route`.

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

Round 1 writes `revision-plan-01.md`, then `draft-02.md`; an optional requested re-score writes `council-02.md`. Round 2 writes `revision-plan-02.md`, then `draft-03.md`; an optional requested re-score writes `council-03.md` under an additional versioned artifact key.

### Exit condition

The approved proposal is faithfully applied, deviations are disclosed, `revision_round` is incremented only after the new draft is durably written, and the new draft is presented for review. Stop after two revision rounds.

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

For LinkedIn, create an immutable final copy, count its post body with
`bin/cf count final.md --section "Approved post"`, and record selection, caveats, and
approval. Do not publish.

For X, preserve the confirmed variant and mechanically valid recommended-post structure.
Re-run `bin/cf validate-x` and record per-post counts, flags, and explicit approval.

For README, while the visible candidate still awaits `approve_final`, report the exact
target path and show the complete final proposed content or exact diff. Only explicit
approval of that candidate permits finalization. Then create `final.md` with the exact
approved README content, update `run.json` atomically, and validate the private run. Confirm
that `final.md` still matches the approved candidate before updating only the approved
target README. Preserve intentionally retained repository-specific information and do not
commit. Council authorization, revision-plan approval, or approval of a different
candidate is not final approval.

After writing and validating the final artifact, preserve all linked items and record the
final path with `bin/cf vault finalize-run <run> --format <format>`. Record the run in each linked item's
`successful_runs`, update `last_used_at`, preserve prior final paths, and count only
successful completed uses. Non-archived origins, contributors, and derived ideas normally
return to `ready`; another unfinished active run keeps them `developing`. Archived items
remain archived. No item is consumed, exhausted, archived, or deleted by finalization.

After finalization, Content Flow may ask whether the final piece should be independently
discoverable as reusable content. It must not create a new vault item without human
approval. Existing linked items already preserve the completed artifact and can contribute
to a later run without copying the earlier run.

### Output artifact

`final.md`

### Exit condition

For LinkedIn, selected hook/closing, final character count, remaining factual caveats, and
approval status are recorded. For X, the variant and every post validate. For README, `final.md` exactly matches the approved target
README content, the approval and target path are recorded in the preceding Council or
revision artifact, and the approved target file alone has been updated.

### Possible routes

Proceed to `lessons`; return to revision if approval is withheld.

### Human gate

Explicit final approval is required. README application is the only supported target-file
write; publication and commits remain wholly outside this workflow.

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

Complete with no accepted lessons, or update `<data-root>/creator/lessons.md` only with individually approved candidates and then complete.

### Human gate

Explicit item-level approval is required before persistent lessons change. Rejection or silence leaves `<data-root>/creator/lessons.md` untouched.
