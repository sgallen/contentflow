---
name: content-flow
description: Orchestrate the repository's local, file-backed content workflow and private vault. Use when capturing or enriching material, inspecting saved or parked ideas, starting or resuming a run, parking unfinished work, researching, interviewing, drafting, reviewing, revising, finalizing, or proposing reusable lessons.
---

# Content Flow

Act as one capable orchestrator. Council and interviewer personas are functional reasoning lenses, never separate agents or processes.

## Start, resume, or report

1. Run `bin/cf data-root` (or pass the user's `--data-dir` selection) and report the exact active data root. `DATA_ROOT.md` defines the canonical selection; do not reimplement it. If creator setup is incomplete, stop and direct the human to `$content-flow-setup` or `bin/cf init`.
2. For a new run from supplied material, run `bin/cf new-run --title "..." --format <linkedin|readme>` with the same data-root selection; report its path. Fill its `spike.md` from the supplied idea or inspected project without inventing missing provenance, assumptions, capabilities, or confidentiality facts. For vault origins use the vault procedure below instead.
3. For an existing run, read `<run>/run.json`, then read only artifacts relevant to its stage. Run `bin/cf validate <run>` with the same selection before advancing. A bare run ID belongs under `<data-root>/runs/`; an explicit path may identify a fictional example. Treat disk state, not chat memory, as authoritative.
4. For status intent, run `bin/cf status <run>`, summarize the current artifact/state, pending human action, and valid next routes. Do not advance.
5. Read `WORKFLOW.md` for the active stage contract. Read [references/state-and-artifacts.md](references/state-and-artifacts.md) when creating/updating state, and [references/artifact-templates.md](references/artifact-templates.md) when starting an artifact.

## Capture, enrich, and inspect the private vault

Interpret intent semantically: requests to save, capture, keep for later, add a video, park
an idea, put work back, start from saved material, or show promising parked ideas do not
require exact phrases.

1. Resolve and report the active root. Live items belong only in
   `<data-root>/vault/items/`; never put them in templates or examples.
2. **Quick capture:** use `bin/cf vault capture` with the most accurate supported `--kind`,
   a concise supplied-or-neutral title, exact `--url` when given, short `--material` when
   given, and the human's `--note` reason when supplied. Preserve unknown metadata as
   unknown. Stop after reporting the ID/path unless enrichment was requested. Do not force
   analysis or a reason.
3. **Enriched capture:** first quick-capture. Read the complete item and any actually
   available source. Add only requested/useful Summary, Useful specifics or excerpts,
   Potential content angles, Open questions, and optional Mining notes. Mining notes may
   distinguish explored and unexplored angles, prior audiences/formats, revisit triggers,
   unanswered questions, and related completed assets. Label source evidence separately
   from model interpretation; cite authoritative sources for current/factual claims;
   observe quotation limits; never invent the creator's view or missing usage history.
   Suggested tags and mining opportunities are proposals. After editing, run
   `bin/cf vault update <id> --status <unchanged-status>` to refresh `updated_at`, then
   `bin/cf vault rebuild-index` and `bin/cf vault validate`.
4. Do not create an asset directory unless a useful large transcript, excerpt, imported
   note, or document is actually available. Put it only under
   `<data-root>/vault/assets/<item-id>/` and reference it from the item.
5. For inspection, use `bin/cf vault list` filters, then `vault show` on plausible
   candidates. “Promising” is a model/human assessment based on the canonical items, never
   an index score. Clearly label the assessment.

## Start or resume from vault material

1. Resolve each requested ID with `bin/cf vault show`; read the complete item and report
   title, status, exact source, related and successful runs, final artifacts, explored
   angles, Mining notes, parking notes, known remaining opportunities, and potential
   duplication risks. If a description matches more than one item, show the candidates and
   ask for confirmation. Prior success never blocks reuse.
2. Create through the normal deterministic mechanism:
   `bin/cf new-run --vault-item <origin-id>`; repeat `--vault-item` for multiple direct
   origins and use repeated `--contributing-vault-item` for supporting items. Pass
   `--format readme` when the intended output is a README.
3. Report the run path, verify reciprocal provenance with `bin/cf validate <run>` and
   `bin/cf vault validate`, then continue through the ordinary research decision and
   one-question-at-a-time interview. Never duplicate an existing item to start a run.
4. For a parked run, read its state and relevant artifacts, report the prior assessment,
   use `bin/cf vault resume-run <run>`, validate both sides, and resume at the preserved
   stage rather than creating a new run.
5. A source or idea may start multiple runs. A completed artifact may participate in later
   work through an existing item whose `final_artifacts` preserves its provenance; select
   that item as contributing material rather than copying the earlier run. Parked items and
   unexplored angles may be selected deliberately.
6. For a proven idea, model-labeled opportunities may include a deeper, narrower, or
   contrarian version; another audience or format; an update from new evidence; a
   reader-response follow-up; or repurposing from completed content. Treat these as
   judgments, not CLI facts, and never declare the idea exhausted automatically.

## Park a run

Parking is a valid human-controlled route, not failure. Before parking, read current state
and relevant artifacts and write the next `parking-assessment-NN.md` in the run. It must
honestly summarize: what remains promising, strongest material collected, why the run is
not being completed, what is missing, conditions that may make it worth revisiting,
recommended next angle or action, and whether to resume or reconsider from a new angle. Do
not manufacture strengths or gaps. Preserve previous successful uses and completed assets.

Run `bin/cf vault park-run <run> --reason "..." --assessment-file <path>` with the same
data-root selection, then validate the run and vault. The command updates existing origins
instead of duplicating them; for an unlinked run it creates one parked `run-fragment`.
Preserve every run artifact and stop.

## Advance safely

- Execute only the active stage or an explicitly valid route. Write the named artifact first, then update `run.json` atomically (temporary file plus rename), then validate.
- Branch on `run.json` format while retaining the same stage graph, artifact names, and human gates. Load only the matching `creator/formats/<format>.md`.
- Research conditionally. Explain the decision briefly. Separate verified fact, citation, dispute, interpretation, and unresolved issue. Never use research to invent the creator's view.
- During interview, choose one question, persist it in `interview.md` with its functional lens, obtained/missing coverage, and an `Answer: pending` marker, update and validate `run.json`, then ask it and stop. After the response, replace the pending marker with the answer and record material obtained, material missing, and the functional lens needed next. Stop on coverage rather than a fixed question count.
- Load creator files only from `<data-root>/creator`: `profile.md`, `voice.md`, `lessons.md`, and the active `formats/<format>.md` for drafting or later voice/format evaluation; `sources.md` earlier only when its source policies matter.
- Create real captured items only under `<data-root>/vault/items/`, optional available large material only under `<data-root>/vault/assets/<item-id>/`, and real runs only under `<data-root>/runs/`. Never write real content or copy private artifacts into tracked templates or `examples/`.
- Run the six-lens Council only after clear human authorization. Produce one structured review and no automatic rewrite.
- After Council feedback, write a concrete revision plan and stop. Interpret “apply” or equivalent approval as permission only for the visible pending plan; preserve the prior draft.
- Increment `revision_round` only after an approved plan is applied. Limit revision to two rounds and use `resolve_revision_limit` rather than polishing indefinitely.
- Interpret “finalize” or equivalent as final approval only when the human is responding
  to a visible final candidate. Create `final.md`; never publish it. After validating it,
  report direct origins, contributing sources, and ideas derived during the run, then run
  `bin/cf vault finalize-run <run>`. This records successful history for every linked role,
  preserves all prior history, and normally returns non-archived items to `ready` without
  implying exhaustion. Ask whether the human wants the final piece independently
  discoverable as reusable content, but do not create another item without approval.
- Propose at most five evidence-linked lessons after finalization. Never edit `<data-root>/creator/lessons.md` until the human explicitly approves individual candidates.

## README runs

Use this overlay only when `run.json` has `format: readme`. It specializes the shared
workflow rather than replacing it.

1. Before interviewing, inspect the target project, current README if present, source tree,
   documentation, CLI help, tests, examples, and package metadata as relevant. Record the
   exact project root and target README path in `spike.md`. The repository is source
   material, not automatic proof of every documentation claim.
2. Keep four evidence categories distinct in artifacts: repository-proven behavior,
   documentation claims, explicit project-owner intent, and unresolved uncertainty. Use
   external research only when a material factual claim cannot be verified from the
   repository or owner.
3. Interview adaptively, one focused question at a time, starting with the most important
   gap after inspection. Useful lenses include primary audience, core problem, strongest
   value proposition, first reader action, maturity, differentiation, non-goals, trust or
   privacy, tone, and contribution posture. Do not use a fixed questionnaire. Stop when the
   README can be accurate and useful.
4. Make `content-brief.md` record target readers, primary promise, reader problem, desired
   action, key proof, required sections, important commands, claims needing verification,
   tone, avoidances, limitations, and unresolved questions.
5. Make each `draft-NN.md` a proposed README, shaped by the active README format guidance.
   The opening should quickly answer what the project is, why it matters, and how to try it.
   Character counting remains available but is not a quality metric.
6. After human authorization, run one README Council through these lenses: positioning,
   first-minute comprehension, onboarding, technical accuracy, trust and credibility, and
   voice and readability. Record what works, blockers, consensus, optional taste
   suggestions, exact inaccurate claims or commands, a ranked revision plan, and one
   recommended route. Do not revise automatically.
7. Keep the proposed README and all run artifacts under the active private data root
   through drafting, review, and revision. Do not edit the target README during an
   unfinished run.
8. Treat revision approval only as permission for the visible revision plan. When a final
   candidate is pending, report the exact target path and show the complete candidate or
   exact diff. Ask for explicit final approval. Only then create the approved `final.md`,
   update and validate `run.json`, confirm the final artifact still matches the approved
   candidate, and update that one target README. Do not commit. Preserve intentionally
   retained project-specific information.
9. After finalization, propose evidence-linked README lessons under the ordinary lesson
   gate. Never add them to persistent creator guidance automatically.

## Intent is semantic, not keyword-based

Map natural-language intent to a transition only when state and the pending gate make it unambiguous. “Run the council,” “get the panel's review,” and similar requests authorize Council only when a draft is pending. “Apply” approves only a clearly stated pending plan. If context permits multiple consequential interpretations, ask a short clarifying question.

## Quality and routing

Use scores as diagnostic signals. For LinkedIn, route to interview when a draft lacks a
distinctive thesis or lived example. For README, route to interview when the audience,
promise, desired action, maturity, scope, or owner intent remains materially unclear;
reinspect the repository before drafting or revision when commands or capabilities are
unsupported. If either format relies on an unsupported or time-sensitive external claim,
route to research.
Prefer a justified backward route over endless surface polishing. Human decisions control
taste, confidential material, factual responsibility, revision, final approval, and
learning.
