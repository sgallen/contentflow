# Acceptance criteria

Run commands from the repository root.

## Skills and procedure

- [ ] `.agents/skills/content-flow-setup/SKILL.md` has valid frontmatter and onboarding resources.
- [ ] `.agents/skills/content-flow/SKILL.md` has valid frontmatter and supports new, resume, status, and semantic transition intents.
- [ ] `WORKFLOW.md` contains all nine stage contracts with entry, inputs, task, artifact, exit, routes, and human gate headings.
- [ ] The documented flow makes research conditional and routes weak drafts backward.
- [ ] The interview requires one question at a time and coverage-based completion.
- [ ] Council, revision application, finalization, and persistent lesson changes have explicit human gates.

Verify skills:

```bash
python3 /home/barney/.codex/skills/.system/skill-creator/scripts/quick_validate.py .agents/skills/content-flow-setup
python3 /home/barney/.codex/skills/.system/skill-creator/scripts/quick_validate.py .agents/skills/content-flow
```

## CLI and state

- [ ] `bin/cf new-run --title "Acceptance smoke" --format linkedin` creates `runs/<date>-acceptance-smoke` and never overwrites a collision.
- [ ] The created run contains `run.json` and `spike.md` and passes validation.
- [ ] `status` reports stage, status, research decision, pending action, and artifacts.
- [ ] `validate` rejects invalid enums, state/action inconsistency, unsafe paths, missing files, and missing stage artifacts.
- [ ] `count` reports Unicode code points without network access.

Automated verification:

```bash
python3 -m unittest discover -s tests -v
bin/cf validate examples/completed-run
```

## Vertical slice and boundaries

- [ ] `examples/completed-run/` contains a conditional research decision, research report, four-question adaptive interview, content brief, multi-option first draft, below-threshold Council review, approved plan, second draft, second review, approved final, and at most five pending lessons.
- [ ] Every example artifact is named in its valid `run.json`.
- [ ] No code imports non-standard-library packages.
- [ ] A repository search finds no implementation of OpenClaw, connectors, OpenAI API calls, LangGraph, Temporal, vector databases, a web UI, background work, autonomous publishing, or multi-agent infrastructure.
- [ ] `creator/lessons.md` does not contain unapproved example lessons.
- [ ] `ARCHITECTURE.md` explains procedure/state/artifacts, context scopes, responsibility boundaries, framework avoidance, and portability.

