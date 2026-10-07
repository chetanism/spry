---
name: init
description: Set up spry in a new project — interview the team about the product, people, roadmap, security, performance, external services and stack, then write the plan, knowledge files, AGENTS.md and CI. Use once, at the start of a new project.
argument-hint: "[high-level description, or a path to one]"
disable-model-invocation: true
---

# spry — init

Set up spry in a project that has little or no code yet. For existing code, stop and use
`/spry:adopt` instead.

- **Plugin root:** two folders above this file's folder (`…/plugins/spry`).
- **Procedure:** `<plugin root>/process/setup.md` §0–§4. Read it, and `interview.md`, `chat.md`
  and `writing.md` beside it, before the first question.
- **Already set up?** If `spry/spry.config.json` exists, stop: say so, and offer `/spry:status`.
- **Resuming:** if `spry/` exists without a config, an earlier run stopped part-way — read what was
  written and continue from the first topic in setup.md §2 that has no answer.
- **Starting point:** `$ARGUMENTS` if given (text, or a file to read); otherwise ask for it.
