# Architecture

## Public framework and private state

```text
tracked framework repository                 selected private data root
├── .agents/skills/                          ├── creator/
├── src/content_flow/                        ├── vault/
├── bin/cf                                   │   ├── items/<id>.md
├── templates/                               │   ├── assets/<id>/ (optional)
│                                            │   └── index.md (generated)
│                                            └── runs/<id>/
├── templates/creator/
├── examples/completed-run/  (fictional)
├── tests/
└── documentation
```

`DATA_ROOT.md` is the single documented definition of root selection and public/private classification. `bin/cf` implements it. Templates are public input to initialization, not live configuration. Content Flow never promotes a private artifact into `examples/` automatically.

## Procedure, state, and artifacts

The **procedure** lives in `AGENTS.md`, `WORKFLOW.md`, and the two repository skills. **State** is the small `run.json` cursor in each private run. **Artifacts** are Markdown evidence: spike, research, interview, brief, drafts, reviews, final, and lesson candidates.

`run.json` aids resumption; it is not a workflow engine. An artifact holds substance while state points to it. A private data root may be unversioned or separately versioned; the framework repository never needs to track it.

Schema version 2 separates shared content development from channel rendering.
`requested_formats` is ordered, `primary_format` is optional, shared research/interview/
brief state appears once, and `format_states` owns independent LinkedIn, X, or README
rendering state. Social format artifacts live under `formats/<format>/`. README keeps its
repository-document overlay. Adding a future renderer means another format state and
guidance file, not another research/interview engine.

The **vault** is persistent intake and incubation: material may exist without a run and may
survive several development attempts. A **run** is one bounded attempt to develop selected
material. **Final content** is the human-approved artifact within a run; finalization never
deletes its vault provenance or consumes the underlying material. Availability status and
successful-use history remain independent.

## Persistent and per-run context

`<data-root>/creator/` holds approved reusable context. `<data-root>/vault/items/` holds
canonical source, idea, observation, quote, excerpt, and run-fragment records.
`<data-root>/runs/<id>/` holds one development attempt's context and decisions. Early stages
avoid creator files; drafting loads only relevant creator files and current-run artifacts.
Selection records vault IDs in `run.json`, copies or references useful material in
`spike.md`, and records the run ID back on every selected item.

Lineage is one-to-many: sources and observations may support multiple ideas or angles;
items may support multiple runs; runs produce completed assets; and an item carrying a
completed-asset reference may contribute to a later run. Run roles distinguish direct
origins, supporting contributors, and ideas derived during development.

A linked adaptation run adds an `adaptation` provenance record rather than mutating an
approved source run. It records the selected source run, format, artifact and SHA-256,
available original final, destination format/variant, originating vault items, and prior
adaptation runs. Reusable shared evidence is copied mechanically into the new private run;
the source remains the immutable historical record. Repeating the same adaptation creates
a collision-safe new run and preserves every earlier output.

## Responsibilities

### Model judgment

Codex decides whether research is warranted, adapts interview questions to missing coverage, synthesizes drafts, applies Council lenses, diagnoses weak material, and proposes lessons. Ambiguous editorial choices stay visible as judgment.

### Deterministic mechanics

The standard-library CLI resolves the data root, initializes private structure, checks
Git-ignore safety, creates collision-safe vault items and runs, maintains bidirectional
relationships and the generated index, parks/resumes run state, validates paths and state,
reports per-format status, performs deterministic index-on-read lexical source discovery,
initializes linked adaptation provenance, validates canonical X post structure and Unicode
character limits, migrates singular runs, and counts Unicode code points. Discovery uses
titles, aliases, phrases, topic words, modest spelling variation, format/finalization, and
artifact dates; it has no embeddings, persistent index, or database. The CLI does not
summarize, perform editorial adaptation, choose variants, or score ideas.
README repository inspection, adaptive interviewing, drafting, review, and approval remain
Codex procedure rather than new CLI subcommands.

### Human responsibility

The human owns taste, personal claims, confidentiality, factual responsibility, Council
authorization, revision approval, final approval, accepted lessons, and any deliberate
publication or public-example copy. For README runs, only explicit approval of the shown
final candidate authorizes updating the exact target README; Content Flow never commits it.

## Why no workflow framework

The graph is small, interactive, artifact-backed, and judgment-heavy. A state cursor, explicit contracts, filesystem checks, and optional private Git history provide enough reliability without deployment or orchestration infrastructure.

## Portability

Skills are Markdown, templates and artifacts are ordinary files, and tooling uses only the
Python standard library. A README run can inspect any locally available repository while
keeping its run artifacts in the selected Content Flow data root. Different users select
different private roots without modifying or forking public framework files.

## Future Oracle compatibility

The canonical item files provide a stable input source for a possible future Oracle that
could reason over explicit availability, successful history, lineage, and revisit notes.
No Oracle, scheduling, automatic selection, semantic search, database, connector, or
background process exists in this version.
