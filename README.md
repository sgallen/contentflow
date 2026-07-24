# Content Flow

Content Flow is a local-first workflow for turning rough ideas into content you are
actually willing to put your name on.

## TL;DR

AI can write a decent-looking post from almost nothing.

That's the problem.

The research can be thin. The point of view can be generic. The writing can look finished
before the thinking has started.

Content Flow makes the model do the work first. Bring it a source or rough idea. It
researches when the facts need work, interviews you to establish what you actually think,
drafts from that material, reviews the result through several editorial lenses, and stops
when your judgment is required.

```text
Capture -> Develop -> Research if needed -> Interview -> Draft -> Review -> Revise -> Reuse
```

You talk to Codex. The workflow records the research, answers, decisions, drafts, and
approvals as files, so the work can survive the chat.

Research supplies facts. The creator supplies the point of view.

Content Flow supports LinkedIn, X, and project READMEs. It does not require an LLM API
integration, workflow server, database, custom UI, or background agent system.

## How it works

Start with something messy: a link, quote, observation, completed post, or idea you are
not ready to defend yet.

If the piece depends on current facts, disputed claims, numbers, or quotations, Content
Flow researches the gaps. If it doesn't, it moves on.

Then it interviews you. One useful question at a time. The next question depends on what
the piece still needs, not a canned questionnaire.

Once there is enough substance, Content Flow drafts from the evidence, your answers, your
creator profile, your voice guidance, and lessons you have explicitly approved.

The Writer's Council reviews the result through distinct editorial lenses. It is one
orchestrator, not a pretend room full of independent experts. The scores are diagnostic,
not truth.

Feedback becomes a revision plan. You approve the plan before the draft changes and the
final piece before it is finalized.

And if the draft has no real point?

Another rewrite is probably not progress. Go back for better evidence or ask the question
that should have been asked in the first place.

## Quick start

You need Git, Python 3.10+, a local checkout of this repository, and Codex opened at the
repository root. No Python package installation, API key, database, or service deployment
is required.

### 1. Set it up

```text
Use $content-flow-setup.

Initialize Content Flow in the default private data root, tell me its exact path, and guide
me through the minimum creator setup for LinkedIn and X.
```

Content Flow creates the private structure, reports where your data lives, and shows you
subjective guidance before writing it.

### 2. Save something

```text
Use $content-flow to save this idea for later:

More communication did not help the project because nobody owned the decision.
```

A link, quote, excerpt, observation, or half-formed idea works too.

### 3. Develop it

```text
Use $content-flow to develop the idea I just saved into a LinkedIn post.

Guide me through the workflow one human gate at a time.
```

That is enough. Content Flow decides whether research is warranted, starts the interview,
and stops at each human gate.

### 4. Reuse it

```text
Use $content-flow to turn my latest LinkedIn post into an X thread.
```

Content Flow finds the private source and reuses its research, interview, brief, approved
framing, and provenance. Then it drafts for X. It does not chop a LinkedIn post into
280-character pieces and call that adaptation.

You do not need to memorize run IDs, artifact paths, or CLI commands.

## Work that compounds

Chat history is a weak durable record for work you care about.

The private vault keeps sources, ideas, observations, parked work, and completed-content
provenance as readable Markdown. Runs preserve the research, interview, brief, drafts,
Council feedback, approved revisions, final content, and current state.

Status and history answer different questions:

- **Can I use this now?** That is status.
- **What have I already done with it?** That is history.

A source that produced one strong piece may be more valuable afterward, not less. Use it
for another angle, audience, format, or follow-up. Finalizing one post does not consume the
source or exhaust the idea. That would be a terrible content system.

LinkedIn and X can share research, interviewing, and a brief while keeping their drafts,
reviews, revisions, approvals, and lessons independent. X supports a single post, thread,
or several standalone posts.

README runs use the same human-controlled workflow with repository inspection and
README-specific review. Content Flow cannot change the target README until it shows the
complete candidate or exact diff and receives explicit approval.

## Public framework, private work

The reusable machinery belongs in the public repository. Your actual work does not.

| Shareable framework | Private by default |
| --- | --- |
| Skills and CLI | Creator profile and voice guide |
| Schemas and blank templates | Approved lessons and source configuration |
| Tests and fictional examples | Real vault items and research |
| Documentation | Interviews, drafts, final content, and run state |

The default private path is `.content-flow/`.

Under the hood, `bin/cf` checks `--data-dir`, then `CONTENT_FLOW_HOME`, then the default.
Most users can let the skills handle it.

This repository ignores `.content-flow/`, which helps prevent accidental tracking.

Git ignore is not encryption. It is not access control. Protect the directory and its
backups like any other private work.

The private data root can be its own private Git repository. Content Flow will not
initialize it, stage files, commit, publish, or create a remote automatically.

## Simple on purpose

You talk. Codex orchestrates. A deterministic, standard-library Python CLI handles the
boring but important work underneath: private-root resolution, scaffolding, discovery,
state transitions, validation, lineage, migration, and character counts.

The CLI does not decide what is worth saying. Good.

The architecture is Markdown, JSON, skills, and local tooling. There is no workflow server
hiding behind the repository.

Content Flow does not require:

- a separate LLM API integration
- LangGraph or Temporal
- a database or vector store
- a custom UI
- Notion or OpenClaw
- background scheduling
- automatic publishing
- multiple independent agents

It also does not scan LinkedIn, X, websites, private accounts, or inspiration feeds to
generate ideas automatically.

The project is useful today for someone comfortable opening a repository in Codex. The
design is portable in principle, but Codex is the implemented runtime. Support for Claude
or another runtime is not verified.

## Inspiration

Credit where it's due.

[Alex Lieberman showed off his Content Machine on the How I AI podcast](https://youtu.be/1_jlukb7gm4?si=jUw_dz4LX8YUt3zC).
It is a Claude Code desktop plugin he and his team use at Tenex. The demo walked through
an Oracle, interview panel, voice files, Writer's Council, and a loop that learns from
feedback.

I watched that and built Content Flow.

The useful insight was not that content needed more AI. It was that a strong workflow
could come from simple ingredients: skills, persistent files, adaptive interviewing,
editorial review, and human checkpoints.

## Documentation

- [`WORKFLOW.md`](WORKFLOW.md) defines stages, artifacts, and human gates.
- [`DATA_ROOT.md`](DATA_ROOT.md) defines private-root selection and the public/private
  boundary.
- [`VAULT.md`](VAULT.md) describes capture, availability, reuse, and lineage.
- [`ARCHITECTURE.md`](ARCHITECTURE.md) explains the deliberately simple design.
- [`ACCEPTANCE.md`](ACCEPTANCE.md) lists verifiable project criteria.
