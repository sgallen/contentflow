# Public framework and private data root

Content Flow keeps reusable framework material in this repository and active creator data in a separate private data root. Files under `templates/` are public starters, never the active creator configuration.

## Canonical data-root resolution

`bin/cf` is the canonical resolver. Every data-aware command uses exactly this precedence:

1. the command's `--data-dir <path>` option;
2. the `CONTENT_FLOW_HOME` environment variable;
3. `<repository>/.content-flow`.

The selected path expands `~` and is resolved to an absolute path. Relative CLI and environment paths are resolved from the current working directory. Use `bin/cf data-root [--data-dir <path>]` to report the exact selection, setup state, and Git-ignore status. Use the same `--data-dir` selection on subsequent commands, or set `CONTENT_FLOW_HOME` once.

## Classification

Public and shareable framework material includes skills, playbooks, rubrics, workflow contracts, CLI code, schemas and validation, blank creator templates, tests, general documentation, and explicitly fictional completed examples.

Private by default material includes the active creator profile, voice guide, approved
lessons, source and format configuration, real spikes, repository inspections, research
reports, interview transcripts, drafts, final content, run state, and workflow
retrospectives. Applying an approved README or publishing a post does not make its working
files public. A human may deliberately create a sanitized fictional/public example later,
but Content Flow never copies private work into `examples/` automatically.

The private layout is:

```text
<data-root>/
├── creator/
│   ├── profile.md
│   ├── voice.md
│   ├── lessons.md
│   ├── sources.md
│   └── formats/
│       ├── linkedin.md
│       └── readme.md
├── vault/
│   ├── items/
│   ├── assets/
│   └── index.md
└── runs/
```

Initialize it with `bin/cf init`. Initialization copies missing tracked starter files from
`templates/creator/` and never overwrites an existing private creator file. This lets an
older initialized root receive a newly supported format safely. Initialization refuses to
create private files inside a surrounding Git repository unless the selected root is
ignored. The default `.content-flow/` path is ignored by this repository.

`vault/items/*.md` are canonical, independently readable records. `vault/assets/<item-id>/`
is optional supporting material, created only when useful material is actually available.
`vault/index.md` is generated from item frontmatter and is never canonical.

Do not store credentials, API keys, cookies, authentication tokens, or other secrets in creator source files. Source guidance should contain policies and non-secret references only.

## Optional private versioning

The ignored data root does not need to be a Git repository. To version it separately, do this manually:

```bash
cd .content-flow
git init
git add vault runs creator
git commit -m "Capture Content Flow material"
```

The parent Content Flow repository continues to ignore `.content-flow/`; the nested repository can use a separate private remote. Content Flow does not initialize Git, commit, stage files, create a submodule, or perform any other Git write automatically.

When the data root is a nested Git repository, `bin/cf data-root` reports both facts:
the data root tracks its private contents in its own repository, and the containing
public repository ignores the entire data root. The root should not be ignored by its
own repository.
