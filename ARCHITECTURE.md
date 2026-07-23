# Architecture

## Procedure, state, and artifacts

The **procedure** lives in `AGENTS.md`, `WORKFLOW.md`, and the two repository skills. It tells Codex how to reason and where humans must decide. **State** is the small `run.json` cursor in each run. It records the current stage, status, pending human action, research decision, revision round, and current/history artifact paths. **Artifacts** are named Markdown evidence of what happened: spike, research, interview, brief, drafts, reviews, final, and lesson candidates.

`run.json` aids resumption; it is not a workflow engine. An artifact holds substance while state points to it. Git versions both.

## Persistent and per-run context

`creator/` holds approved, reusable context: profile, observed voice guidance, accepted lessons, source preferences, and format guidance. It changes deliberately and relatively slowly. `runs/<id>/` holds a single idea's context and decisions. Early stages avoid creator files; drafting loads only the creator files relevant to writing plus current run artifacts. This progressive disclosure reduces accidental cross-run assumptions.

`vault/spikes/` may hold unselected ideas. Selection copies or distills an idea into a run's `spike.md`, preserving provenance.

## Three kinds of responsibility

### Model judgment

Codex decides whether research is warranted, adapts interview questions to missing coverage, synthesizes drafts, applies the six Council lenses, diagnoses weak material, and proposes generalizable lessons. Ambiguous editorial choices stay visible as judgment rather than being hidden in code.

### Deterministic mechanics

The standard-library CLI creates collision-safe directories, writes initial state, validates enums and expected files, prevents unsafe artifact paths, reports state, and counts Unicode code points. These repeatable operations do not benefit from model discretion.

### Human responsibility

The human owns taste, personal claims, confidentiality, responsibility for factual assertions, Council authorization, revision approval, final approval, and acceptance of reusable lessons. The workflow stops at these boundaries instead of assuming consent.

## Why no workflow framework

The graph is small, interactive, artifact-backed, and deliberately judgment-heavy. A state cursor, explicit contracts, filesystem checks, and Git provide enough reliability. A workflow framework would add deployment, serialization, operational, and debugging complexity without improving the key activity: a human and Codex reasoning over inspectable text.

Backward routes are normal rather than exceptional. A weak draft can return to interview for a missing example or to research for a shaky claim. Those choices need a reason in the artifact and a small state update, not orchestration infrastructure.

## Portability and generalization

The pattern generalizes to proposals, talks, decision memos, or case studies by replacing format guidance, stage references, and review lenses while retaining:

1. a concise procedural skill;
2. an explicit state cursor;
3. named evidence artifacts;
4. deterministic scaffolding and validation;
5. human gates for taste, responsibility, and learning.

Because skills are Markdown, assets are ordinary files, and tooling is Python standard library, the workflow can later be repackaged for another skill/plugin system without coupling domain logic to an API or server.
