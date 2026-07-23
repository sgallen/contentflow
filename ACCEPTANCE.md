# Acceptance criteria

Run commands from the repository root.

## Public/private boundary

- [ ] The tracked repository contains reusable skills, tooling, documentation, tests, blank templates, and fictional examples only.
- [ ] `templates/creator/` contains every required starter; no tracked `creator/`, `vault/`, or `runs/` directory acts as live data.
- [ ] `.content-flow/` is ignored and `bin/cf init` confirms Git safety before writing private files.
- [ ] `DATA_ROOT.md` defines CLI option, environment, and default precedence once; other files reference it.
- [ ] No automatic path copies private work into `examples/`, and creator source guidance warns against secrets.

## Skills and procedure

- [ ] Both skills have valid frontmatter and use `bin/cf` to resolve the private root.
- [ ] Setup reports intended private creator paths and never modifies templates.
- [ ] Orchestration reports the root, fails clearly before private setup, and stores real vault/run artifacts only under it.
- [ ] Research remains conditional; interview, Council, revision, finalization, and lessons retain human gates.

Verify skills:

```bash
python3 /home/barney/.codex/skills/.system/skill-creator/scripts/quick_validate.py .agents/skills/content-flow-setup
python3 /home/barney/.codex/skills/.system/skill-creator/scripts/quick_validate.py .agents/skills/content-flow
```

## CLI and state

- [ ] `bin/cf init` creates creator files, `vault/spikes/`, and `runs/` without overwriting.
- [ ] `--data-dir`, `CONTENT_FLOW_HOME`, and the repository-local default follow documented precedence.
- [ ] Bare run IDs resolve under the active root's `runs/`; explicit paths remain supported.
- [ ] `status` reports the active root and run state.
- [ ] `validate` retains enum, gate, revision, filename, presence, and path/symlink checks.
- [ ] `count` remains deterministic and offline.

## Verification

```bash
python3 -m unittest discover -s tests -v
bin/cf init
bin/cf validate examples/completed-run
bin/cf status examples/completed-run
bin/cf --help
git check-ignore .content-flow
git diff --check
```

Also initialize a temporary explicit directory and a temporary `CONTENT_FLOW_HOME`. Confirm the fictional completed example remains valid and `.content-flow/` is neither tracked nor staged.
