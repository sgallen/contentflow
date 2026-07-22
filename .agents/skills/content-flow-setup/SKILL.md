---
name: content-flow-setup
description: Build or improve this repository's creator profile, voice guidance, approved lessons, source preferences, and LinkedIn format guidance. Use when onboarding a creator, analyzing supplied writing samples, filling missing creator context, or proposing evidence-based updates to files under creator/.
---

# Content Flow Setup

Build useful creator context without inventing preferences.

## Procedure

1. Read `creator/README.md`, then inspect `creator/profile.md`, `voice.md`, `lessons.md`, `sources.md`, and `formats/linkedin.md`. Summarize populated, missing, uncertain, and internally conflicting fields.
2. Read [references/onboarding-questions.md](references/onboarding-questions.md). Ask one focused question at a time, prioritizing gaps that materially affect writing. Do not require every question.
3. If samples are supplied, confirm they are the creator's and whether they are representative. Analyze repeated textual evidence using [references/sample-analysis.md](references/sample-analysis.md). Separate:
   - **Observed:** supported by quoted or precisely located sample evidence.
   - **Creator-stated:** explicitly supplied preference.
   - **Assumption/proposal:** plausible but not established.
4. Offer a compact proposed patch or before/after summary before writing subjective conclusions. Ask the human to approve, reject, or edit it. Factual administrative details supplied directly may be written without framing them as inferred taste.
5. Apply only approved conclusions. Preserve every existing approved lesson verbatim unless the human separately approves modifying or removing it.
6. If evidence is thin, use honest starter language such as “not established yet” and retain prompts for later refinement. Never fill a gap with a generic creator preference.
7. Re-read edited files, report what remains unknown, and suggest the smallest useful next step.

## File boundaries

- `profile.md`: identity, experience, audience, topics, goals, boundaries, and factual context.
- `voice.md`: evidence-backed writing patterns, preferences, anti-patterns, and uncertainty.
- `lessons.md`: only individually human-approved reusable lessons, with provenance.
- `sources.md`: permitted/preferred source types, trusted recurring sources, citation and confidentiality rules. This is not a list of invented authorities.
- `formats/linkedin.md`: format-specific constraints and creator-approved preferences.

Use [assets/creator-starter.md](assets/creator-starter.md) as a structural fallback, not content to copy blindly. Do not modify run artifacts during setup unless explicitly asked.

