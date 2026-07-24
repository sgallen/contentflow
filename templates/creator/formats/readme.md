# README format guidance

## Reader and outcome

Establish these before drafting:

- Primary reader and any important secondary readers.
- Reader problem and why this project is relevant to it.
- The project's strongest supportable promise.
- The first action the reader should take.
- Project maturity, prerequisites, and expected technical context.
- Current scope, explicit non-goals, and contribution posture.
- Trust, privacy, or public/private data boundaries when relevant.
- Inspiration or attribution that a reader should understand.

Treat the repository as source material. Keep separate:

- What source, tests, package metadata, examples, and CLI behavior prove.
- What existing documentation claims.
- What the project owner explicitly wants the README to communicate.
- What remains uncertain or needs factual verification.

Do not invent capabilities, commands, screenshots, maturity, compatibility, or results.

## Opening

The first screen should quickly answer:

1. What is this?
2. Why should the reader care?
3. How can the reader try it?

Use a strong one-line description and a visible TL;DR near the top. Put the shortest
successful setup path before deep architecture. Distinguish user value from implementation
detail.

## Useful content

Include only sections that help the intended reader. Useful material often includes:

- Project name and one-line description.
- TL;DR.
- Why the project exists.
- How it works or its core mental model.
- Quick start with prerequisites and accurate, copyable commands.
- A representative workflow or concrete example.
- Important concepts.
- Public versus private data behavior.
- Repository structure when it aids navigation.
- Common commands.
- Current scope, limitations, and non-goals.
- Inspiration or attribution.
- Development and validation.
- Project maturity or status.

Link to deeper documentation instead of duplicating it. Prefer short sections, concrete
language, useful examples, and honest limitations.

## Drafting standards

- Verify every command against repository behavior, help output, tests, or other direct
  evidence.
- Make setup steps copyable and order them as a new reader would perform them.
- State prerequisites before commands that depend on them.
- Use character counting only as an informational utility, never as a README quality score.
- Preserve valid project-specific information intentionally retained from the current
  README.
- Use plain ASCII punctuation. Do not use em dashes or typographic apostrophes.

## Avoid

- Long philosophical openings.
- Inflated AI claims or calling every model action an agent.
- Vague marketing language and unsupported claims.
- Giant undifferentiated feature lists.
- Architecture before the product is explained.
- Fictional commands.
- Excessive verbosity.
- Unnecessary badges.
- Screenshots that do not exist.

## README Writer's Council

Review one draft through six functional lenses:

1. **Positioning:** Can a new reader understand what the project is and why it matters?
2. **First-minute comprehension:** Do the opening, TL;DR, and early structure work?
3. **Onboarding:** Can a new user complete the documented setup?
4. **Technical accuracy:** Are commands, paths, capabilities, limitations, and claims
   supported by repository evidence?
5. **Trust and credibility:** Is maturity, privacy, human responsibility, and scope
   represented honestly?
6. **Voice and readability:** Is the writing concise, direct, natural, and consistent with
   approved creator guidance?

Record what works, blockers, consensus findings, optional taste suggestions, exact
inaccurate claims or commands, a ranked revision plan, and exactly one recommended route.
Scores are diagnostic only. Do not revise automatically.

## Final application gate

Keep the run and every proposed README private under the active Content Flow data root
during inspection, interview, drafting, Council review, and revision.

Before changing a target README:

1. Report its exact path.
2. Show the complete final candidate or an exact diff.
3. Ask for explicit final approval.
4. Update only that approved README file.
5. Do not commit automatically.

Do not treat Council authorization, revision-plan approval, or general encouragement as
final approval to update the target repository.
