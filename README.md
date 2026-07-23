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

Initialization reports the exact absolute root and confirms Git-ignore status. It copies blank tracked starters from `templates/creator/`, creates `vault/items/`, `vault/assets/`, generated `vault/index.md`, and `runs/`, and never overwrites existing creator files.

Select another private root either per command or through the environment:

```bash
bin/cf init --data-dir ~/private/content-flow
CONTENT_FLOW_HOME=~/private/content-flow bin/cf data-root
```

Do not put credentials or authentication tokens in creator source guidance. The private root need not be a Git repository; `DATA_ROOT.md` describes optional separate private versioning.

To personalize the initialized files later, invoke `$content-flow-setup`. That skill reports every private path before it changes anything. Files under `templates/creator/` are never active configuration.

## Capture material without starting a run

Quick capture records only supplied material, its reason, known metadata, and an `inbox`
timestamp:

```bash
bin/cf vault capture \
  --kind source \
  --title "A useful fictional article" \
  --url "https://example.com/fictional-article" \
  --note "Its distinction between activity and progress may be useful later"
```

Use `--material` instead of or in addition to `--url` for a quote, observation, transcript
excerpt, or rough idea. Repeat `--tag` as needed. Supported kinds are `source`, `idea`,
`observation`, `quote`, `excerpt`, and `run-fragment`.

An enriched capture starts from the same scaffold, then the Content Flow skill may add a
concise summary, source-supported specifics, proposed angles, and open questions. It labels
source-derived information separately from interpretation and does not manufacture the
creator's view. Enrichment is optional.

```bash
bin/cf vault list --status parked --tag leadership
bin/cf vault show <item-id>
bin/cf vault update <item-id> --status ready --revisit-after 2026-09-01
bin/cf vault rebuild-index
bin/cf vault validate
```

`vault/index.md` is a deterministic grouped view, not source of truth. Item age never
changes status automatically.

## Start a run

```bash
bin/cf new-run --title "Why small teams need decision logs" --format linkedin
bin/cf new-run --vault-item <item-id>
bin/cf new-run --vault-item <origin-id> --contributing-vault-item <source-id>
```

The command reports the active data root and absolute run path. A first-run prompt can be:

```text
Use $content-flow to start a new run.

The idea is: Small teams often mistake more communication for better coordination, when the real problem is that important decisions have no clear owner or revisit condition.

Guide me through the workflow one human gate at a time. Do not invent my point of view, and ask interview questions one at a time.
```

Real spikes and runs are written only under the active private root. `examples/` remains fictional and tracked.

Selecting a vault item changes it to `developing`, links both sides, and preserves item
provenance in `spike.md`. Multiple items may contribute to one run.

## Park, resume, and complete linked work

`$content-flow` prepares a written parking assessment before using the mechanical route:

```bash
bin/cf vault park-run <run-id> --reason "Needs a lived example" \
  --assessment-file <run-path>/parking-assessment-01.md
bin/cf vault resume-run <run-id>
```

Parking preserves the entire run. An originating item is updated rather than duplicated;
an unlinked run creates one `run-fragment`. Parking preserves prior successful uses and
records the assessment for later mining. When a final artifact exists,
`bin/cf vault finalize-run <run-id>` records successful history for each linked origin,
contributor, and derived idea. Non-archived items normally return to `ready`; another
unfinished active run keeps them `developing`.

## Resume or inspect

```bash
bin/cf status <run-id>
bin/cf validate <run-id>
```

A bare run ID resolves under `<data-root>/runs/`. An explicit absolute or multi-component relative path can address a run elsewhere, such as the fictional `examples/completed-run`.

Use `--data-dir <path>` on `new-run`, `status`, or `validate`, or set `CONTENT_FLOW_HOME`, to select the same non-default root.

## Vault lifecycle

`inbox` is captured but unreviewed; `ready` is available for development or reuse;
`developing` has an unfinished active run; `parked` preserves value that is not currently
ready; and `archived` is intentionally out of active consideration. Usage is separate
history (`successful_runs`, `use_count`, `last_used_at`, and `final_artifacts`), not an
availability state. Sources, ideas, successful angles, and completed artifacts may all
support later runs. Nothing ages or succeeds automatically into `archived`.

Useful inspection commands include:

```bash
bin/cf vault list --status ready
bin/cf vault list --successful yes
bin/cf vault show <item-id>
```

The generated index surfaces successful reusable items and multi-run rich sources without
removing them from their current availability views. See `VAULT.md` for the one-to-many
lineage model and validation rules.

## Tests and utilities

```bash
python3 -m unittest discover -s tests -v
bin/cf validate examples/completed-run
bin/cf count examples/completed-run/final.md
bin/cf count examples/completed-run/final.md --section "Approved post"
```

See `WORKFLOW.md` for stage contracts, `ARCHITECTURE.md` for design boundaries, and `ACCEPTANCE.md` for verifiable completion criteria.

The private root may be its own Git repository. Content Flow works without Git and never
commits automatically. A normal manual snapshot is:

```bash
cd .content-flow
git add vault runs creator
git commit -m "Capture Content Flow material"
```
