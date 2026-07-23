---
name: content-flow-setup
description: Initialize or improve private Content Flow creator context, voice guidance, approved lessons, source preferences, and LinkedIn format guidance. Use when onboarding a creator, selecting a Content Flow data root, analyzing supplied writing samples, or proposing evidence-based creator-context updates.
---

# Content Flow Setup

Build useful creator context without inventing preferences.

## Procedure

1. Run `bin/cf data-root` with any user-selected `--data-dir` and report its exact path. `DATA_ROOT.md` is the canonical selection rule; do not duplicate or improvise it. If setup is incomplete, initialize through `bin/cf init` with the same selection. Never initialize creator content by hand.
   Ensure `vault/items/`, `vault/assets/`, and generated `vault/index.md` exist by running
   `bin/cf vault rebuild-index` with the same selection. Explain briefly that the private
   vault retains reusable sources, ideas, completed-artifact provenance, and parked runs;
   successful use is history rather than consumption. Do not turn setup into a vault
   questionnaire.
2. Before any edit, list the exact paths under `<data-root>/creator` that you intend to modify. Inspect `profile.md`, `voice.md`, `lessons.md`, `sources.md`, and `formats/linkedin.md`; summarize populated, missing, uncertain, and conflicting fields.
3. Read [references/onboarding-questions.md](references/onboarding-questions.md). Ask one focused question at a time, prioritizing gaps that materially affect writing. Do not require every question.
4. If samples are supplied, confirm they are the creator's and whether they are representative. Analyze repeated textual evidence using [references/sample-analysis.md](references/sample-analysis.md). Separate:
   - **Observed:** supported by quoted or precisely located sample evidence.
   - **Creator-stated:** explicitly supplied preference.
   - **Assumption/proposal:** plausible but not established.
5. Offer a compact proposed patch or before/after summary before writing subjective conclusions. Ask the human to approve, reject, or edit it. Factual administrative details supplied directly may be written without framing them as inferred taste.
6. Apply only approved conclusions to the previously reported private paths. Preserve every existing approved lesson verbatim unless the human separately approves modifying or removing it.
7. If evidence is thin, use honest starter language such as “not established yet” and retain prompts for later refinement. Never fill a gap with a generic creator preference.
8. Re-read edited files, report what remains unknown, and suggest the smallest useful next step.

## File boundaries

- `profile.md`: identity, experience, audience, topics, goals, boundaries, and factual context.
- `voice.md`: evidence-backed writing patterns, preferences, anti-patterns, and uncertainty.
- `lessons.md`: only individually human-approved reusable lessons, with provenance.
- `sources.md`: permitted/preferred source types, trusted recurring sources, citation and confidentiality rules. This is not a list of invented authorities.
- `formats/linkedin.md`: format-specific constraints and creator-approved preferences.

Use [assets/creator-starter.md](assets/creator-starter.md) as a structural fallback, not content to copy blindly. Do not modify run artifacts during setup unless explicitly asked.

All active files are under `<data-root>/creator`. Tracked files under `templates/creator/` are public blank starters: never write personal facts, inferred preferences, sample conclusions, or approved lessons into them.

The vault is also private-root-only. Setup may ensure its directories/index exist, but must
not solicit source integrations, credentials, personal links, or seed content, and must
never copy private material into `templates/vault/`.
