# spry

**Agent-first development a human team can follow.** A Claude Code plugin — usable from other
agents too — that runs a project the way an agile team already thinks about it:

- **Plan in plain words, one level at a time:** milestone → epic → feature → story. Each step is a
  short interview; each document is written for the person who reads it, not for the agent.
- **Build in slices:** a work order before any code, a conflict check against everything it could
  clash with, a draft pull request, and a close summary — with the slice's safeguards *falsified* to
  prove its tests notice them.
- **Progress is derived, never typed:** a story is done when its slices are merged and every
  acceptance criterion is proven by a test or a QA check. The folders *are* the hierarchy, so the
  plan is browsable on GitHub by anyone.

> **Status: untried.** The tool is tested; the process has not yet run a real milestone.
> Inspired by [writ](https://github.com/chetanism/writ).

## Install

```bash
claude plugin marketplace add chetanism/spry
claude plugin install spry@spry
cd ~/projects/your-project && claude
> /spry:init       # new project — or /spry:adopt for existing code
```

## See it first

[A worked example](docs/example/README.md) — a small invented product taken from roadmap to slice.
Start at its [`spry/README.md`](docs/example/spry/README.md) and click down.

## The skills

| | |
|---|---|
| `/spry:init`, `/spry:adopt` | Set up: interview → plan, knowledge, `AGENTS.md`, CI |
| `/spry:milestone`, `epic`, `feature`, `story` | Define one level, in plain words, checked for conflicts |
| `/spry:slice`, `slice-open`, `slice-close` | Split a story; open a slice with its work order; close it with falsified tests |
| `/spry:status`, `/spry:tone` | Where things stand, at your tone; how technical replies are for you |
| `/spry:update`, `/spry:contribute` | Take what spry gained since; offer back what your project built |

The design and every decision behind it: [`DESIGN.md`](DESIGN.md).

## Developing spry

```bash
python3 tests/test_spry.py
python3 plugins/spry/tool/spry.py --root docs/example check
```

MIT — see [LICENSE](LICENSE).
