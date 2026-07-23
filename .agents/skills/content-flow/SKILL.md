---
name: content-flow
description: Orchestrate the repository's local, file-backed content workflow and private vault. Use when capturing or enriching material, inspecting saved or parked ideas, starting or resuming a run, parking unfinished work, researching, interviewing, drafting, reviewing, revising, finalizing, or proposing reusable lessons.
---

# Content Flow

Act as one capable orchestrator. Council and interviewer personas are functional reasoning lenses, never separate agents or processes.

## Start, resume, or report

1. Run `bin/cf data-root` (or pass the user's `--data-dir` selection) and report the exact active data root. `DATA_ROOT.md` defines the canonical selection; do not reimplement it. If creator setup is incomplete, stop and direct the human to `$content-flow-setup` or `bin/cf init`.
2. For a new run from supplied material, run `bin/cf new-run --title "..." --format linkedin` with the same data-root selection; report its path. Fill its `spike.md` from the supplied idea without inventing missing provenance, assumptions, or confidentiality facts. For vault origins use the vault procedure below instead.
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
   Potential content angles, and Open questions. Label source-derived material separately
   from model interpretation; cite authoritative sources for current/factual claims;
   observe quotation limits; never invent the creator's view. Suggested tags are proposals.
   After editing, run `bin/cf vault update <id> --status <unchanged-status>` to refresh
   `updated_at`, then `bin/cf vault rebuild-index` and `bin/cf vault validate`.
4. Do not create an asset directory unless a useful large transcript, excerpt, imported
   note, or document is actually available. Put it only under
   `<data-root>/vault/assets/<item-id>/` and reference it from the item.
5. For inspection, use `bin/cf vault list` filters, then `vault show` on plausible
   candidates. “Promising” is a model/human assessment based on the canonical items, never
   an index score. Clearly label the assessment.

## Start or resume from vault material

1. Resolve each requested ID with `bin/cf vault show`; read the complete item and report
   title, status, exact source, development history, and parking notes. If a description
   matches more than one item, show the candidates and ask for confirmation.
2. Create through the normal deterministic mechanism:
   `bin/cf new-run --vault-item <origin-id>`; repeat `--vault-item` for multiple direct
   origins and use repeated `--contributing-vault-item` for supporting items.
3. Report the run path, verify reciprocal provenance with `bin/cf validate <run>` and
   `bin/cf vault validate`, then continue through the ordinary research decision and
   one-question-at-a-time interview. Never duplicate an existing item to start a run.
4. For a parked run, read its state and relevant artifacts, report the prior assessment,
   use `bin/cf vault resume-run <run>`, validate both sides, and resume at the preserved
   stage rather than creating a new run.

## Park a run

Parking is a valid human-controlled route, not failure. Before parking, read current state
and relevant artifacts and write the next `parking-assessment-NN.md` in the run. It must
honestly summarize: what remains promising, strongest material collected, why the run is
not being completed, what is missing, recommended next step, and whether to resume or
reconsider from a new angle. Do not manufacture strengths or gaps.

Run `bin/cf vault park-run <run> --reason "..." --assessment-file <path>` with the same
data-root selection, then validate the run and vault. The command updates existing origins
instead of duplicating them; for an unlinked run it creates one parked `run-fragment`.
Preserve every run artifact and stop.

## Advance safely

- Execute only the active stage or an explicitly valid route. Write the named artifact first, then update `run.json` atomically (temporary file plus rename), then validate.
- Research conditionally. Explain the decision briefly. Separate verified fact, citation, dispute, interpretation, and unresolved issue. Never use research to invent the creator's view.
- During interview, choose one question, persist it in `interview.md` with its functional lens, obtained/missing coverage, and an `Answer: pending` marker, update and validate `run.json`, then ask it and stop. After the response, replace the pending marker with the answer and record material obtained, material missing, and the functional lens needed next. Stop on coverage, normally after four to six questions.
- Load creator files only from `<data-root>/creator`: `profile.md`, `voice.md`, `lessons.md`, and `formats/linkedin.md` for drafting or later voice/format evaluation; `sources.md` earlier only when its source policies matter.
- Create real captured items only under `<data-root>/vault/items/`, optional available large material only under `<data-root>/vault/assets/<item-id>/`, and real runs only under `<data-root>/runs/`. Never write real content or copy private artifacts into tracked templates or `examples/`.
- Run the six-lens Council only after clear human authorization. Produce one structured review and no automatic rewrite.
- After Council feedback, write a concrete revision plan and stop. Interpret “apply” or equivalent approval as permission only for the visible pending plan; preserve the prior draft.
- Increment `revision_round` only after an approved plan is applied. Limit revision to two rounds and use `resolve_revision_limit` rather than polishing indefinitely.
- Interpret “finalize” or equivalent as final approval only when the human is responding to a visible final candidate. Create `final.md`; never publish it. After validating it, report linked origins and contributors, ask only if the human wants a direct origin not marked `used`, then run `bin/cf vault finalize-run <run>` (or `--keep-origin-status`). This preserves all items, records the final path, marks only direct origins used by default, and never marks every contributor used.
- Propose at most five evidence-linked lessons after finalization. Never edit `<data-root>/creator/lessons.md` until the human explicitly approves individual candidates.

## Intent is semantic, not keyword-based

Map natural-language intent to a transition only when state and the pending gate make it unambiguous. “Run the council,” “get the panel's review,” and similar requests authorize Council only when a draft is pending. “Apply” approves only a clearly stated pending plan. If context permits multiple consequential interpretations, ask a short clarifying question.

## Quality and routing

Use scores as diagnostic signals. If a draft lacks a distinctive thesis or lived example, route to interview. If it relies on an unsupported or time-sensitive claim, route to research. Prefer a justified backward route over endless surface polishing. Human decisions control taste, confidential material, factual responsibility, revision, final approval, and learning.
