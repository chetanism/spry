# AGENTS.md — the spry repository

This repository **is** spry: a Claude Code plugin (`plugins/spry/`) and its marketplace. `DESIGN.md`
is the source of truth for every decision; read the section you are changing first.

## Rules

- **No agent attribution** in commits, pull requests or issues — no `Co-Authored-By`, no session
  links, no "Generated with" lines.
- **Any change a project may want gets a `CH-n` entry** in `plugins/spry/CHANGELOG.md` and a version
  bump in `plugin.json`, `tool/spry.py` (`VERSION`), and the config template (`spry`,
  `spry_baseline`). `tests/test_spry.py` (`Kit`) fails when they disagree.
- **Tool:** Python standard library only, 3.10+. One file.
- **The worked example** (`docs/example/`) must pass `check` and `index --check` — it is what people
  read first.
- **The site** (`site/`, published to GitHub Pages) explains spry to newcomers in full. A change to
  how spry works updates the page that describes it. Plain HTML, CSS and JS — no build step; the
  navigation lives once, in `site/assets/site.js`.
- Replies follow `plugins/spry/process/chat.md`.

## Before committing

```bash
python3 tests/test_spry.py
python3 tests/test_site.py
python3 plugins/spry/tool/spry.py --root docs/example check
python3 plugins/spry/tool/spry.py --root docs/example index --check
claude plugin validate plugins/spry
```
