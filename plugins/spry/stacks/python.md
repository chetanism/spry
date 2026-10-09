---
title: Python
summary: Test commands, parallelism, falsify runners and deploy exclusion for a Python project.
audience: 8
---
# Python

| Config key | pytest |
|---|---|
| `tests.match` | `["**/test_*.py", "**/*_test.py"]` |
| `tests.affected` | `pytest --testmon` (pytest-testmon) |
| `tests.retry` | `pytest --lf -p no:xdist` — only the tests that failed, one at a time |
| `tests.all` | `pytest -n auto` (pytest-xdist) |
| `tests.junit` | `reports/junit.xml` — the runner writes it with `--junitxml=reports/junit.xml` |
| falsify runner | `pytest -x -q {files}` |
| `checks.fast` | format `ruff format --check .` · lint `ruff check .` · types `mypy .` (if typed) |

- Tests cite criteria in a string: the docstring or a `@pytest.mark.parametrize` id containing
  `S-1/AC-1`. A function name (`def test_S_1_AC_1_lends…`) cannot hold it, and a `#` comment proves
  nothing.
- **Integration tests** on a shared database: separate runner, `-p no:xdist`, and
  `"parallel": false` so falsify never runs two of them at once.
- **Parallel falsify** shares `.venv` / `venv` into each worktree; a virtualenv elsewhere goes in
  `falsify.share`.
- **Deploy exclusion:** `spry/` in `.dockerignore`; exclude it from the package in `pyproject.toml`.
- **CI setup steps:** `actions/setup-python`; install with the project's tool and its cache.
