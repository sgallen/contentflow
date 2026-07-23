# Content Flow v0

Content Flow is a reusable, local-first Codex workflow for turning a selected idea into a human-approved LinkedIn post. Codex conducts conditional research, an adaptive interview, drafting, a structured Writer's Council review, approved revision, finalization, and lesson extraction. Files in Git—not chat history—are the source of truth.

It is intentionally **not** an agent service, web app, publishing system, workflow server, or OpenAI API integration. It has no connectors, background jobs, vector database, OpenClaw, LangGraph, Temporal, or multi-agent runtime.

## Requirements and setup

- Git
- Python 3.10+
- Codex opened at this repository root

No package install is required. Optionally make the CLI executable if the checkout loses its mode:

```bash
chmod +x bin/cf
```

Creator files begin as honest, sparse templates. In Codex, invoke the repository setup skill with a request such as:

```text
Use $content-flow-setup to onboard my creator context. Ask me one focused question at a time and propose subjective conclusions before writing them.
```

Add writing samples only when you are comfortable storing them in this Git repository.

## Start a run

Create a safe run directory:

```bash
bin/cf new-run --title "Why small teams need decision logs" --format linkedin
```

The command prints the created path. Use this first-run example prompt:

```text
Use $content-flow to start the run in runs/<run-id>.

The idea is: Small teams often mistake more communication for better coordination, when the real problem is that important decisions have no clear owner or revisit condition.

Guide me through the workflow one human gate at a time. Do not invent my point of view, and ask interview questions one at a time.
```

Codex fills `spike.md`, assesses whether research is needed, and stops at required human gates.

## Resume or inspect a run

```bash
bin/cf status runs/<run-id>
bin/cf validate runs/<run-id>
```

A bare ID such as `bin/cf status <run-id>` also resolves under `runs/`.

Then ask:

```text
Use $content-flow to resume runs/<run-id>.
```

Natural requests such as “run the council,” “apply the pending plan,” “finalize this,” and “propose lessons” work when valid for the recorded stage. Exact phrases are not required; the skill checks intent against state and gates.

## Tests and utilities

```bash
python3 -m unittest discover -s tests -v
bin/cf validate examples/completed-run
bin/cf count examples/completed-run/final.md
bin/cf count examples/completed-run/final.md --section "Approved post"
```

See `WORKFLOW.md` for the stage graph, `ARCHITECTURE.md` for design boundaries, and `ACCEPTANCE.md` for verifiable completion criteria.
