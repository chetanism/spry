---
title: Writing rules
summary: How every spry document is written — template order, bullets, one term per concept, audience.
audience: 7
---
# Writing rules

Applies to every document under `spry/` and to `AGENTS.md`. `spry check` enforces the rules marked ✓.

## Form

- Start from the document's template in `spry/process/templates/`; keep its section order.
- Bullets, one fact per line. A table where rows share columns. No prose paragraphs.
- Remove every `<!-- guide: … -->` comment and `<placeholder>` before the document leaves `draft`. ✓
- An empty optional section is deleted, not left with "None" or "TBD".
- Front-matter: only `key: value` and `key: [a, b]`. ✓

## Words

- **One term per concept.** Use the term in `spry/knowledge/glossary.md`; never one of its banned
  synonyms (code, the glossary itself and `Conflict check`
  sections are exempt — they quote words to correct them). ✓ A new concept gets a glossary row in the same change.
- Different words only for different things. If two phrases mean the same, pick one and ban the
  other.
- Absolute dates (`2026-10-08`), never "today" or "next week".
- No hedging ("should probably", "might want to"). State the rule, or ask.
- At audience ≤ 5, an ID always appears with its title on first mention in a document.

## Audience

The template's `audience` sets how technical the document is.

| Level | Reader | Allowed |
|---|---|---|
| 1–3 | product, QA, stakeholders | plain words; what a person sees and does |
| 4–6 | QA, support, designers | screens, fields, data, error messages |
| 7–10 | developers | paths, types, commands, internals |

## Size

- Each document type has a line budget in `spry.config.json`. ✓
- Over budget → split into `INDEX.md` + one file per item; the index holds one line per item,
  generated from each item's `title` and `summary`. ✓
- Never restate another document — link it. A restatement is a second copy that will drift.
