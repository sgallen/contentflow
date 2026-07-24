---
name: content-flow
description: Orchestrate the repository's local, file-backed content workflow and private vault. Use when capturing or enriching material, inspecting saved or parked ideas, starting or resuming a run, parking unfinished work, researching, interviewing, drafting, reviewing, revising, finalizing, or proposing reusable lessons.
---

# Content Flow

Act as one capable orchestrator. Council and interviewer personas are functional reasoning lenses, never separate agents or processes.

## Start, resume, or report

1. Run `bin/cf data-root` (or pass the user's `--data-dir` selection) and report the exact active data root. `DATA_ROOT.md` defines the canonical selection; do not reimplement it. If creator setup is incomplete, stop and direct the human to `$content-flow-setup` or `bin/cf init`.
2. For a new run from supplied material, run `bin/cf new-run --title "..." --format
   <linkedin|x|readme>`; repeat `--format` for several outputs and optionally pass
   `--primary-format <linkedin|x>`. Pass `--x-variant <single|thread|standalone>` only
   when the human has selected it. Report the path. Fill shared `spike.md` without
   inventing provenance, assumptions, capabilities, preferences, or confidentiality facts.
3. For an existing run, read `<run>/run.json`, then read only artifacts relevant to its stage. Run `bin/cf validate <run>` with the same selection before advancing. A bare run ID belongs under `<data-root>/runs/`; an explicit path may identify a fictional example. Treat disk state, not chat memory, as authoritative.
4. For status intent, run `bin/cf status <run>`, summarize the current artifact/state, pending human action, and valid next routes. Do not advance.
5. Read `WORKFLOW.md` for the active stage contract. Read [references/state-and-artifacts.md](references/state-and-artifacts.md) when creating/updating state, and [references/artifact-templates.md](references/artifact-templates.md) when starting an artifact.

## Adapt existing content conversationally

Treat requests such as “adapt the Bostrom post for X,” “turn my latest LinkedIn post into
an X thread,” or “create three standalone X posts from the agent-first piece” as complete
adaptation intents. Do not ask for a run ID, artifact path, command, schema version, or
workflow prompt.

1. Resolve and report the active data root. Infer the requested destination and any
   explicit variant from ordinary language. X, Twitter, single post, thread, and several
   standalone posts are semantic intents, not required keywords. Ask one short question
   only if the destination itself is genuinely ambiguous.
2. Extract the human's source description and run `bin/cf find "<description>" --json`,
   adding `--format`, `--variant`, `--latest`, or `--drafts` only when the request supplies that
   constraint. Search results cover run titles/aliases, final and prior format artifacts,
   spikes, briefs, linked vault titles/content/aliases, final-artifact lineage, and
   development history. Do not substitute `vault list` or conversation memory for this
   discovery step.
3. If resolution is `clear`, briefly report the selected human-facing title, source
   format, finalization state, and useful date. Do not expose the SOURCE_REF, run ID, or
   private path unless it helps distinguish candidates. If resolution is `ambiguous`,
   present only the likely human-readable candidates and ask one concise choice question.
   If it is `none`, say that private runs, finalized/draft artifacts, briefs/spikes, and
   vault material were searched, then ask for a title phrase, recognizable line, link, or
   approximate date. Never guess or silently broaden to an unrelated topic.
4. Read the selected source `run.json` and the artifacts it names. Load the shared brief,
   research report, interview material, selected source-format final or explicitly
   requested draft, linked vault material/provenance, useful prior Council findings, and
   previous adaptations. The brief and original human input remain authoritative; the
   approved source final is evidence of accepted framing and wording, not idea truth.
5. If the destination is already an unfinished requested format in the source run and can
   be activated without crossing approvals or invalidating a primary, use
   `bin/cf format-action ... activate`. Otherwise use the selected SOURCE_REF with
   `bin/cf adapt ... --to <linkedin|x>` after any required variant confirmation. The
   linked initializer copies reusable shared evidence, records source/final/vault
   provenance and prior adaptations, creates fresh destination state, and never changes
   the source final. The human never chooses this storage mechanism.
6. When X is requested without a variant, inspect the material and recommend `single`,
   `thread`, or `standalone` in no more than a few sentences, then ask for confirmation
   and stop. After confirmation, either pass `--x-variant` while initializing or use
   `bin/cf set-x-variant <run> <variant>` on a pending adaptation. If the human explicitly
   requested a variant, follow it unless the material clearly cannot support it; surface
   that concern instead of silently changing formats.
7. Before drafting, load `<data-root>/creator/profile.md`, `voice.md`, `lessons.md`, and
   `formats/<destination>.md`. If destination evidence is sparse, say the platform voice
   is still being calibrated, use the creator's general voice plus established platform
   constraints, keep conclusions tentative, and propose no persistent lesson without
   item-level approval. Unless private evidence establishes otherwise, stronger LinkedIn
   evidence does not become an X rule.
8. Draft natively for the destination from the shared substance and creator judgment. Do
   not merely shorten, expand, split, or reformat the source final. Preserve factual and
   confidentiality boundaries. Then stop for draft review and continue through the normal
   independent Council authorization, revision-plan approval, final approval, and lesson
   gates without asking the human to restate them.

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
   every requested `--format`; use `--format readme` alone for the ordinary README workflow.
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
- Treat schema-version-2 disk state as authoritative. Shared development uses
  `shared_state` and `shared_artifacts`; rendering uses only the selected entry in
  `format_states`. Respect `primary_format` ordering and `active_format`. Never infer an
  unrequested format or copy one format's approval state to another.
- Research conditionally. Explain the decision briefly. Separate verified fact, citation, dispute, interpretation, and unresolved issue. Never use research to invent the creator's view.
- During interview, choose one question, persist it in `interview.md` with its functional lens, obtained/missing coverage, and an `Answer: pending` marker, update and validate `run.json`, then ask it and stop. After the response, replace the pending marker with the answer and record material obtained, material missing, and the functional lens needed next. Stop on coverage rather than a fixed question count.
- Load creator files only from `<data-root>/creator`: `profile.md`, `voice.md`, `lessons.md`,
  and the active `formats/<format>.md` for drafting or later evaluation; `sources.md`
  earlier only when its policies matter. LinkedIn observations are not X rules.
- Create real captured items only under `<data-root>/vault/items/`, optional available large material only under `<data-root>/vault/assets/<item-id>/`, and real runs only under `<data-root>/runs/`. Never write real content or copy private artifacts into tracked templates or `examples/`.
- Run the six-lens Council only after clear human authorization. Produce one structured review and no automatic rewrite.
- After Council feedback, write a concrete revision plan and stop. Interpret “apply” or equivalent approval as permission only for the visible pending plan; preserve the prior draft.
- Increment only the active format's `revision_round` after its approved plan is applied.
  Limit each format independently to two rounds.
- Interpret “finalize” or equivalent as final approval only when the human is responding
  to a visible final candidate. Create `final.md`; never publish it. After validating it,
  report direct origins, contributing sources, and ideas derived during the run, then run
  `bin/cf vault finalize-run <run> --format <format>`. This records successful history for every linked role,
  preserves all prior history, and normally returns non-archived items to `ready` without
  implying exhaustion. Ask whether the human wants the final piece independently
  discoverable as reusable content, but do not create another item without approval.
- Propose at most five evidence-linked lessons after finalization. Never edit `<data-root>/creator/lessons.md` until the human explicitly approves individual candidates.

## Shared development and social rendering

For social runs, research and interview once. Keep `spike.md`, `research-report.md`,
`interview.md`, and `content-brief.md` at the run root. The brief is channel-neutral and
records the central thesis, strongest examples, factual support, creator reasoning,
tension or objection, payoff, important interview wording, confidentiality constraints,
possible angles, and unresolved weaknesses. It must not prescribe a LinkedIn hook,
thread shape, or other channel structure.

Render only requested formats under `formats/<format>/`. Each format owns drafts, Council
reviews, revision plans, revisions, final, lessons, variant/angle, revision round, and
human gate. The primary format, when present, is resolved first. The run completes only
after every requested format is finalized, format-parked, or declined.

When adapting from an approved primary or a linked prior run:

1. Reload the shared brief and useful research/interview material.
2. Load the approved primary as evidence of selected framing and language, not idea truth.
3. Load destination guidance and identify the central idea that survived approval.
4. For unspecified X output, recommend `single`, `thread`, or `standalone`, explain briefly,
   ask for confirmation, persist the selection, and stop.
5. Draft natively for the destination. Do not merely shorten, expand, split, or reformat;
   do not add a point of view; preserve facts and confidentiality constraints.
6. Run the destination's review, revisions, final approval, and lessons independently.

For X, follow `creator/formats/x.md` and validate the recommended draft/final with
`bin/cf validate-x <file> --variant <variant>`. A single may offer openings and an
alternate close. A thread identifies each post's argumentative function and validates
every post. Standalone posts use distinct angles and each stands alone. Run one authorized
X Council through immediate clarity, point of view, compression, specificity/credibility,
voice authenticity, and platform fit; distinguish blockers, consensus, taste,
unnecessary cleverness, engagement bait, unsupported claims, inherited repetition, and
diagnostic scores. Never revise automatically.

Lesson candidates must declare one scope: creator-wide voice, social workflow, LinkedIn,
X, README, or this run only. Never promote a format-specific preference to creator-wide
guidance without item-level approval.

## README runs

Use this overlay only for a requested README output. A normal README run requests README
alone; never treat it as a social adaptation unless the human explicitly requested the
mixed run. It specializes the shared workflow rather than replacing it.

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
