# Acceptance criteria

Run commands from the repository root.

## Public/private boundary

- [ ] The tracked repository contains reusable skills, tooling, documentation, tests, blank templates, and fictional examples only.
- [ ] `templates/creator/` contains every required starter; tracked vault files are blank or explicitly fictional, and no tracked `creator/`, `vault/`, or `runs/` directory acts as live data.
- [ ] `.content-flow/` is ignored and `bin/cf init` confirms Git safety before writing private files.
- [ ] `DATA_ROOT.md` defines CLI option, environment, and default precedence once; other files reference it.
- [ ] No automatic path copies private work into `examples/`, and creator source guidance warns against secrets.

## Skills and procedure

- [ ] Both skills have valid frontmatter and use `bin/cf` to resolve the private root.
- [ ] Setup reports intended private creator paths and never modifies templates.
- [ ] Orchestration reports the root, fails clearly before private setup, and stores real vault/run artifacts only under it.
- [ ] Research remains conditional; interview, Council, revision, finalization, and lessons retain human gates.
- [ ] Natural-language quick/enriched capture, vault selection, parking, resume, and linked finalization preserve their documented gates and provenance.

Verify skills:

```bash
python3 /home/barney/.codex/skills/.system/skill-creator/scripts/quick_validate.py .agents/skills/content-flow-setup
python3 /home/barney/.codex/skills/.system/skill-creator/scripts/quick_validate.py .agents/skills/content-flow
```

## CLI and state

- [ ] `bin/cf init` creates creator files, `vault/items/`, `vault/assets/`, generated `vault/index.md`, and `runs/` without overwriting.
- [ ] `--data-dir`, `CONTENT_FLOW_HOME`, and the repository-local default follow documented precedence.
- [ ] Bare run IDs resolve under the active root's `runs/`; explicit paths remain supported.
- [ ] `status` reports the active root and run state.
- [ ] `validate` retains enum, gate, revision, filename, presence, and path/symlink checks.
- [ ] `count` remains deterministic and offline.
- [ ] Vault capture/show/list/update/rebuild/validate work under every data-root selector.
- [ ] One or more vault items can start a run; run and item state link bidirectionally.
- [ ] Parking preserves history and updates origins or creates one run-fragment; resume restores state; final linkage records successful usage and returns reusable items to ready.
- [ ] Sources and ideas can support repeated completed runs, completed artifacts can contribute later, and archived items remain archived.
- [ ] Generated index views surface successful reusable items and multi-run rich sources independently from status.
- [ ] Validation detects malformed items, duplicate IDs/relations, unsafe paths, stale index, missing required relationships, developing-without-active-run, and invalid parked state.

## Verification

```bash
python3 -m unittest discover -s tests -v
bin/cf init
bin/cf vault capture --kind idea --title "Example vault idea" --note "Fictional verification item"
bin/cf vault list
bin/cf vault show <created-item-id>
bin/cf vault rebuild-index
bin/cf vault validate
bin/cf validate examples/completed-run
bin/cf status examples/completed-run
bin/cf --help
git check-ignore .content-flow
git diff --check
```

Also initialize a temporary explicit directory and a temporary `CONTENT_FLOW_HOME`. Confirm the fictional completed example remains valid and `.content-flow/` is neither tracked nor staged.
