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

**Other agents:** clone this repository, then in your project run
`python3 <clone>/plugins/spry/tool/spry.py install --agent generic` (or `claude`, `cursor`,
`gemini`). `generic` lists the skills in `AGENTS.md`, which most agents read.

## See it first

[A worked example](docs/example/README.md) — a small invented product taken from roadmap to slice.
Start at its [`spry/README.md`](docs/example/spry/README.md) and click down.

## The skills

| | |
|---|---|
| `/spry:init`, `/spry:adopt` | Set up: interview → plan, knowledge, `AGENTS.md`, CI |
| `/spry:milestone`, `epic`, `feature`, `story` | Define one level, in plain words, checked for conflicts |
| `/spry:slice`, `slice-open`, `slice-close` | Split a story; open a slice with its work order; close it with falsified tests |
| `/spry:review`, `/spry:merge` | A fresh pair of eyes on a slice, a plan or any PR, posted line by line with suggested changes; merge only when green, ready and current — then check the main branch |
| `/spry:bug`, `/spry:task` | Record a bug against what it breaks; plan technical work no story asks for |
| `/spry:test-scenarios` | The steps QA follows by hand for each acceptance criterion |
| `/spry:record` | A decision, a convention, or how an external service really behaves |
| `/spry:test-all`, `/spry:explore` | The whole suite on purpose; a seeded exploratory walk over a real, isolated instance — both report only |
| `/spry:compact` | A file back under its line budget, sections moved to where they belong, no fact lost |
| `/spry:security-audit`, `/spry:prelaunch` | Reviews that report and turn findings into bugs and tasks — never fix, never deploy |
| `/spry:process-change` | Change the process in every file it touches, kept through updates |
| `/spry:status`, `/spry:tone` | Where things stand, at your tone; how technical replies are for you |
| `/spry:update`, `/spry:contribute` | Take what spry gained since; offer back what your project built |

The design and every decision behind it: [`DESIGN.md`](DESIGN.md).

## Developing spry

```bash
python3 tests/test_spry.py
python3 plugins/spry/tool/spry.py --root docs/example check
```

MIT — see [LICENSE](LICENSE).
