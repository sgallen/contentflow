# Content Flow v0

Content Flow is a reusable, local-first Codex framework for turning a selected idea into a human-approved LinkedIn post. The tracked repository contains workflow instructions, deterministic tooling, blank templates, tests, and fictional examples. Active creator context and real work stay in an ignored private data root.

It is intentionally **not** an agent service, web app, publishing system, workflow server, or OpenAI API integration. It has no connectors, background jobs, vector database, or multi-agent runtime.

## Requirements

- Git
- Python 3.10+
- Codex opened at this repository root

No package install is required. See `DATA_ROOT.md` for the canonical data-root rule and strict public/private classification.

## Initialize private data

The default private root is `<repository>/.content-flow`:

```bash
bin/cf init
```

Initialization reports the exact absolute root and confirms Git-ignore status. It copies blank tracked starters from `templates/creator/`, creates `vault/spikes/` and `runs/`, and never overwrites existing creator files.

Select another private root either per command or through the environment:

```bash
bin/cf init --data-dir ~/private/content-flow
CONTENT_FLOW_HOME=~/private/content-flow bin/cf data-root
```

Do not put credentials or authentication tokens in creator source guidance. The private root need not be a Git repository; `DATA_ROOT.md` describes optional separate private versioning.

To personalize the initialized files later, invoke `$content-flow-setup`. That skill reports every private path before it changes anything. Files under `templates/creator/` are never active configuration.

## Start a run

```bash
bin/cf new-run --title "Why small teams need decision logs" --format linkedin
```

The command reports the active data root and absolute run path. A first-run prompt can be:

```text
Use $content-flow to start a new run.

The idea is: Small teams often mistake more communication for better coordination, when the real problem is that important decisions have no clear owner or revisit condition.

Guide me through the workflow one human gate at a time. Do not invent my point of view, and ask interview questions one at a time.
```

Real spikes and runs are written only under the active private root. `examples/` remains fictional and tracked.

## Resume or inspect

```bash
bin/cf status <run-id>
bin/cf validate <run-id>
```

A bare run ID resolves under `<data-root>/runs/`. An explicit absolute or multi-component relative path can address a run elsewhere, such as the fictional `examples/completed-run`.

Use `--data-dir <path>` on `new-run`, `status`, or `validate`, or set `CONTENT_FLOW_HOME`, to select the same non-default root.

## Tests and utilities

```bash
python3 -m unittest discover -s tests -v
bin/cf validate examples/completed-run
bin/cf count examples/completed-run/final.md
bin/cf count examples/completed-run/final.md --section "Approved post"
```

See `WORKFLOW.md` for stage contracts, `ARCHITECTURE.md` for design boundaries, and `ACCEPTANCE.md` for verifiable completion criteria.
