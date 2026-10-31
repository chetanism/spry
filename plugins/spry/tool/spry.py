#!/usr/bin/env python3
"""spry — the project tool. Standard library only, Python 3.10+.

    python3 spry/tool/spry.py check              # is the tree consistent? exit 1 if not
    python3 spry/tool/spry.py status [ID] [--level story | --all]
    python3 spry/tool/spry.py index [--check]    # regenerate marker blocks and INDEX.md files (CI on main)
    python3 spry/tool/spry.py index --restore origin/main   # on a branch: undo generated blocks it changed
    python3 spry/tool/spry.py coverage           # defined vs done, and what is built but not proven
    python3 spry/tool/spry.py backlog            # in progress, ready to build, needs slicing, blocked, needs planning
    python3 spry/tool/spry.py done               # finished stories, tasks and bugs, newest first
    python3 spry/tool/spry.py work <owner> --since <day> [--until <day>] [--json]   # what one person built
    python3 spry/tool/spry.py owners --from-prs <file|-> [--replace] [--dry-run]   # once: slice owners from PR authors
    python3 spry/tool/spry.py view [--since <commit>]   # the generated pages for this working tree → .spry/view/
    python3 spry/tool/spry.py serve [--port N] [--no-open]   # browse the plan in a browser, read-only, local only
    python3 spry/tool/spry.py hooks [--remove]   # refresh .spry/view/ after each checkout and pull
    python3 spry/tool/spry.py related <file>     # candidates for a conflict check
    python3 spry/tool/spry.py next <type>        # next free ID: milestone, story, slice, decision …
    python3 spry/tool/spry.py new <type> --parent <ID> --title "…" [--owner …]   # mint: main → ID taken on the main branch
    python3 spry/tool/spry.py claim <slice> [--owner …] [--no-switch]   # take a slice, then cut its branch
    python3 spry/tool/spry.py release <slice>    # give back a claimed slice nobody is building
    python3 spry/tool/spry.py pr-body <slice ID> [--base origin/main]   # for the PR: reviewer page + work order
    python3 <plugin>/tool/spry.py vendor --root <project>   # copy process/ and the tool into a project
    python3 <plugin>/tool/spry.py vendor --diff --root <project>   # what differs from the plugin
    python3 spry/tool/spry.py scrub <file>       # private words left in text about to leave the project
    python3 spry/tool/spry.py falsify suggest <slice> [--base main]   # draft a plan from the diff
    python3 spry/tool/spry.py falsify run <plan.json> [--dry-run] [--record <slice>] [--jobs N]
    python3 spry/tool/spry.py find "<words>"     # search spry/ and AGENTS.md, best sections first
    python3 spry/tool/spry.py check --base origin/main   # also warn on criteria changed under tests or manual checks
    python3 spry/tool/spry.py codeowners [--check]       # .github/CODEOWNERS from team.review
    python3 spry/tool/spry.py tests --slowest    # from the JUnit report in tests.junit
    python3 spry/tool/spry.py draw --seed        # a fresh seed for an exploratory walk
    python3 spry/tool/spry.py draw <seed> <n> --pick < choices   # the same choice for ever, per (seed, n)
    python3 spry/tool/spry.py merge-check <slice> [--base origin/main]   # ready to merge? exit 1 if not
    python3 spry/tool/spry.py link <slice> [--branch B] [--pr N] [--issue N] [--owner [NAME]]   # set them in the slice's front-matter
    python3 spry/tool/spry.py issue-body <slice> [--close]   # the slice's issue (slices.issue): work order, or close summary
    python3 spry/tool/spry.py merge-message <slice> [--ci-local REASON]   # the squash commit: subject, summary, trailers
    python3 spry/tool/spry.py gate [--force] [--fast] [--full]   # check, fast checks, affected tests — or only the changed ones when the branch adds only tests (--full: affected anyway) — then tests.always (--fast: no tests, no stamp); skipped while no code changed
    python3 spry/tool/spry.py changed --base <ref>   # for CI: code=true when anything but docs changed
    python3 spry/tool/spry.py agent-hook <name> < payload.json   # one Claude Code hook call (hooks/hooks.json); `hooks` in the config turns each on
    python3 spry/tool/spry.py review-check <payload.json> --diff <file|-> [--own]   # would GitHub take this review?
    python3 <plugin>/tool/spry.py install --agent <generic|claude|cursor|gemini> [--root <project>]

Run from anywhere inside the project, or pass --root. The project root is the nearest directory
above the current one holding `spry/spry.config.json`.

**The plan is the folder tree** under `spry/plan/`: an item is a folder named `<PREFIX>-<n>-<slug>`
holding a `README.md`; a slice is a file `SL-<n>-<slug>.md` inside its story, task or bug; tasks
sit in a `tasks/` folder and bugs in a `bugs/` folder under their parent. The path is the parent.

**Status is derived, never typed** (DESIGN.md §6). A slice is done when `closed`. A story is done
when every slice is done and every acceptance criterion is proven — by a test whose source line
contains `S-1/AC-1`, or by the latest row for that criterion in the story's `checks.md` reading
`pass`; a later `fail` row un-proves it, test or not. Anything above a story is done when every
counted child is.
"""

from __future__ import annotations

import argparse
import filecmp
import glob
import hashlib
import json
import math
import ntpath
import os
import posixpath
import re
import shlex
import shutil
import signal
import subprocess
import sys
import tempfile
import threading
import time
import urllib.parse
from datetime import date
from dataclasses import dataclass, field

VERSION = "0.35.0"

DEFAULT_LEVELS = ["milestone", "epic", "feature", "story"]
DEFAULT_IDS = {"milestone": "M", "epic": "E", "feature": "F", "story": "S",
               "slice": "SL", "task": "T", "bug": "B", "decision": "D"}
DEFAULT_TEST_MATCH = ["**/*.test.*", "**/*.spec.*", "**/*_test.*", "**/test_*.py", "**/tests/**"]
# A test file by its name alone. Anything else `tests.match` takes — a conftest, a Go `_test.go`
# helper its package shares unnamed — may feed tests that never mention it.
TEST_FILE_NAME = re.compile(r"^(test_.+\.py|.+_test\.py|.+\.(test|spec)\.[^./]+)$")
SKIP_DIRS = {".git", "node_modules", ".spry", "dist", "build", "__pycache__", ".venv", "venv",
             ".idea", ".turbo", "coverage", ".next", "target"}
CONTAINERS = {"tasks": "task", "bugs": "bug"}
# A change to these alone never needs a test run: the gate skips, and CI skips its test jobs.
DEFAULT_DOCS = ["spry/**", "**/*.md"]
# A repository path longer than this leaves under 60 characters for the clone's own folder on Windows.
LONG_PATH = 200

PLAN_STATES = {"draft", "ready", "dropped"}
SLICE_STATES = {"planned", "open", "closed", "dropped"}
PLURAL = {"milestone": "milestones", "epic": "epics", "feature": "features", "story": "stories",
          "slice": "slices", "task": "tasks", "bug": "bugs"}
HTML_TAGS = {"br", "details", "summary", "sub", "sup", "kbd", "img", "a", "b", "i", "em", "strong",
             "p", "div", "span", "code", "pre", "table", "tr", "td", "th", "ul", "li", "ol", "hr"}
STOPWORDS = set("""about above after again against also because been before being below between
both cannot could does doing down during each from further have having here hers herself himself
into itself just more most must never only other ought ours same should some such than that their
theirs them then there these they this those through under until very were what when where which
while whom will with would your yours that this from with have will been each them when then than
into only also what shows show""".split())

CHECKED_LINE = re.compile(r"^\s*-\s*Checked \d{4}-\d{2}-\d{2} against: \S")
OPEN_FINDING = re.compile(r"(→|->)\s*open\b")
LINK = re.compile(r"\[[^\]]*\]\(([^)\s]+)\)")
SCENARIO_ACS = re.compile(r"(AC-\d+(?:\s*,\s*AC-\d+)*)\b")   # `### AC-1, AC-3 · …` checks both
PLACEHOLDER = re.compile(r"<([a-zA-Z][a-zA-Z0-9 ,/|.'_-]*)>")
FENCE = re.compile(r"^\s*(```|~~~)")
HEADING = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")
DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
SCALAR_KEYS = {"id", "title", "summary", "state", "owner", "audience", "branch", "pr", "issue", "closed"}
# A citation on one of these lines proves nothing: the test is skipped or not written yet.
NOT_RUN = re.compile(r"\b(?:it|test|describe|context)\.(?:skip|todo)\b|\bx(?:it|test|describe)\s*\(|"
                     r"@pytest\.mark\.(?:skip|xfail)\b|@unittest\.skip|\bt\.Skip\(")
# A citation on a comment line proves nothing: only a test's name says what the test checks.
COMMENT_LINE = re.compile(r"^\s*(#|//|/\*|\*|--|;|<!--)")


# ---------------------------------------------------------------- text helpers

def natural_key(name: str):
    return [int(p) if p.isdigit() else p.lower() for p in re.split(r"(\d+)", name)]


WINDOWS = os.name == "nt"  # a name, so tests can take the Windows paths on any machine


def shell_quote(arg: str) -> str:
    """One argument for `shell=True`: POSIX quoting for sh, double quotes for cmd.exe, which takes
    single quotes literally."""
    if not WINDOWS:
        return shlex.quote(arg)
    if "%" in arg or '"' in arg:  # cmd expands %…% even inside quotes
        raise PlanError(f"cmd.exe cannot be given {arg} safely — rename it without % or \"")
    return f'"{arg}"' if any(c in arg for c in " \t&|<>^()") else arg


def long_path(path: str) -> str:
    r"""`path` absolute behind `\\?\`, which Windows opens past 260 characters whatever
    LongPathsEnabled says. A plan six folders deep passes 260 easily."""
    full = ntpath.abspath(path)
    return "\\\\?\\UNC\\" + full[2:] if full.startswith("\\\\") else "\\\\?\\" + full


def native(path: str) -> str:
    r"""What every file call takes. The real system, not `WINDOWS`: no other one reads `\\?\`."""
    return long_path(path) if os.name == "nt" and not path.startswith("\\\\?\\") else path


def walk_dir(top: str):
    """`os.walk`, past 260 characters on Windows, its folders named from `top` as given."""
    long = native(top)
    for dirpath, dirnames, filenames in os.walk(long):
        yield top + dirpath[len(long):], dirnames, filenames


def read(path: str) -> str:
    with open(native(path), encoding="utf-8") as handle:
        return handle.read()


def write(path: str, text: str) -> None:
    with open(native(path), "w", encoding="utf-8", newline="\n") as handle:  # LF on Windows too
        handle.write(text)


def parse_front_matter(text: str):
    """(fields, first body line index, [(line, error)]). Only `key: value` and `key: [a, b]`."""
    lines = text.split("\n")
    if not lines or lines[0].lstrip("\ufeff").strip() != "---":
        return None, 0, [(1, "no front-matter — the file must start with `---`")]
    fields, errors = {}, []
    for i in range(1, len(lines)):
        line = lines[i]
        if line.strip() == "---":
            return fields, i + 1, errors
        if not line.strip():
            continue
        m = re.match(r"^([a-z_][a-z0-9_]*):(?:\s+(.*))?$", line)
        if not m:
            errors.append((i + 1, "front-matter line is not `key: value`: " + line.strip()))
            continue
        key, value = m.group(1), (m.group(2) or "").strip()
        if value.startswith("[") and key not in SCALAR_KEYS:
            if not value.endswith("]"):
                errors.append((i + 1, "front-matter list must close on its line: " + line.strip()))
                continue
            inner = value[1:-1].strip()
            fields[key] = [v.strip() for v in inner.split(",") if v.strip()] if inner else []
        else:
            fields[key] = value
    return None, 0, [(1, "front-matter is never closed with `---`")]


def prose(text: str, start: int = 0):
    """(1-based line number, line) outside code fences and HTML comments, inline code removed."""
    in_fence = in_comment = False
    for i, line in enumerate(text.split("\n")):
        if i < start:
            continue
        if FENCE.match(line):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        out, rest = "", line
        while rest:
            if in_comment:
                end = rest.find("-->")
                if end < 0:
                    rest = ""
                else:
                    in_comment, rest = False, rest[end + 3:]
            else:
                begin = rest.find("<!--")
                if begin < 0:
                    out, rest = out + rest, ""
                else:
                    out, rest, in_comment = out + rest[:begin], rest[begin + 4:], True
        yield i + 1, re.sub(r"`[^`]*`", "", out)


def sections(text: str):
    """[(level, title, first line index, end line index exclusive)], ignoring code fences."""
    heads, in_fence = [], False
    lines = text.split("\n")
    for i, line in enumerate(lines):
        if FENCE.match(line):
            in_fence = not in_fence
            continue
        m = None if in_fence else HEADING.match(line)
        if m:
            heads.append((len(m.group(1)), m.group(2).strip(), i))
    out = []
    for n, (level, title, at) in enumerate(heads):
        end = len(lines)
        for later in heads[n + 1:]:
            if later[0] <= level:
                end = later[2]
                break
        out.append((level, title, at, end))
    return out


def section_lines(text: str, title: str):
    """Lines (index, line) of the first section with this title, or None."""
    lines = text.split("\n")
    for _level, name, at, end in sections(text):
        if name.lower() == title.lower():
            return [(i, lines[i]) for i in range(at + 1, end)]
    return None


def table_rows(lines):
    """Cells of each markdown table row, skipping separator rows."""
    for i, line in lines:
        s = line.strip()
        if not s.startswith("|"):
            continue
        cells = [c.strip() for c in re.split(r"(?<!\\)\|", s.strip("|"))]
        if all(re.fullmatch(r":?-{2,}:?", c) for c in cells if c):
            continue
        yield i, cells


def glob_regex(pattern: str):
    out, i = "", 0
    while i < len(pattern):
        if pattern.startswith("**/", i):
            out, i = out + "(?:.*/)?", i + 3
        elif pattern.startswith("**", i):
            out, i = out + ".*", i + 2
        elif pattern[i] == "*":
            out, i = out + "[^/]*", i + 1
        elif pattern[i] == "?":
            out, i = out + "[^/]", i + 1
        else:
            out, i = out + re.escape(pattern[i]), i + 1
    return re.compile("^" + out + "$")


def replace_block(text: str, name: str, content: str):
    """Replace the body of `<!-- spry:name -->` … `<!-- /spry:name -->`. None if absent."""
    pattern = re.compile(r"(<!-- spry:" + re.escape(name) + r" -->\n)(.*?)(<!-- /spry:"
                         + re.escape(name) + r" -->)", re.S)
    if not pattern.search(text):
        return None
    return pattern.sub(lambda m: m.group(1) + content.rstrip("\n") + "\n" + m.group(3), text, count=1)


def string_spans(line: str, triple: str | None):
    """([(start, end)] of the string contents on one source line, the triple quote still open after it).

    `triple` is the `\"\"\"` or `'''` left open by an earlier line, as in a Python docstring. A trailing
    `#` or `//` comment ends the scan, so a quoted citation inside one is not a string."""
    spans, i = [], 0
    if triple:
        close = line.find(triple)
        if close < 0:
            return [(0, len(line))], triple
        spans.append((0, close))
        i = close + 3
    while i < len(line):
        c = line[i]
        if line.startswith('"""', i) or line.startswith("'''", i):
            delim = line[i:i + 3]
            close = line.find(delim, i + 3)
            if close < 0:
                spans.append((i + 3, len(line)))
                return spans, delim
            spans.append((i + 3, close))
            i = close + 3
            continue
        if c in "\"'`":
            j = i + 1
            while j < len(line) and line[j] != c:
                j += 2 if line[j] == "\\" else 1
            spans.append((i + 1, min(j, len(line))))
            i = j + 1
            continue
        if (c == "#" or line.startswith("//", i)) and (i == 0 or line[i - 1].isspace()):
            break
        i += 1
    return spans, None


def strip_blocks(text: str) -> str:
    """The text without generated blocks; each block's lines stay as blank lines, so line numbers hold."""
    return re.sub(r"<!-- spry:(\w+) -->\n.*?<!-- /spry:\1 -->", lambda m: "\n" * m.group(0).count("\n"),
                  text, flags=re.S)


def tokens(text: str):
    return [w for w in re.findall(r"[a-z][a-z'-]{3,}", text.lower()) if w not in STOPWORDS]


# ---------------------------------------------------------------- model

@dataclass
class Problem:
    path: str
    line: int
    message: str
    level: str = "error"

    def __str__(self):
        return f"{self.path}:{self.line}: {self.level}: {self.message}"


@dataclass(eq=False)
class Item:
    type: str
    id: str
    num: int
    doc: str                     # absolute path of README.md, or of the slice file
    folder: str | None           # absolute folder, None for a slice
    fm: dict
    text: str
    body_start: int
    parent: "Item | None" = None
    container: str | None = None
    children: list = field(default_factory=list)
    acs: dict = field(default_factory=dict)       # story: "AC-1" → {"dropped": bool, "line": int}

    @property
    def title(self) -> str:
        return self.fm.get("title", "")

    @property
    def state(self) -> str:
        return self.fm.get("state", "")

    @property
    def label(self) -> str:
        return f"{self.id} {self.title}".strip()

    def kids(self, kind: str):
        return [c for c in self.children if c.type == kind]

    def ancestors(self):
        node, out = self.parent, []
        while node:
            out.append(node)
            node = node.parent
        return out


class Project:
    def __init__(self, root: str, load: bool = True, config: dict | None = None):
        """`load=False` reads the config alone — or takes `config`, read from another commit — for
        `new`, `claim` and `release`, which open only the files they write (`Names`)."""
        self.root = os.path.abspath(root)
        self.spry = os.path.join(self.root, "spry")
        self.plan_dir = os.path.join(self.spry, "plan")
        self.problems: list[Problem] = []
        config_path = os.path.join(self.spry, "spry.config.json")
        try:
            self.config = config if config is not None else json.loads(read(config_path))
        except FileNotFoundError:
            raise SystemExit(f"no spry/spry.config.json under {self.root}")
        except json.JSONDecodeError as e:
            raise SystemExit(f"spry/spry.config.json is not valid JSON: {e}")
        self.ids = {**DEFAULT_IDS, **self.config.get("ids", {})}
        self.levels = self.config.get("levels") or DEFAULT_LEVELS
        self.type_of_prefix = {v: k for k, v in self.ids.items()}
        self.item_dir = re.compile(r"^([A-Z]+)-(\d+)(?:-[a-z0-9][a-z0-9-]*)?$")
        self.slice_file = re.compile(r"^" + re.escape(self.ids["slice"]) + r"-(\d+)(?:-[a-z0-9][a-z0-9-]*)?\.md$")
        self.items: dict[str, Item] = {}
        self.top: list[Item] = []
        self.decisions: dict[str, str] = {}
        self._memo: dict = {}
        if not load:
            self.tests, self.manual = {}, {}
            return
        self._load_plan()
        self._load_decisions()
        self.tests = self._scan_tests()
        self.manual = {s.id: self._manual_checks(s) for s in self.of_type("story")}

    # -- paths

    def rel(self, path: str) -> str:
        return os.path.relpath(path, self.root).replace(os.sep, "/")

    def problem(self, path: str, line: int, message: str, level: str = "error"):
        self.problems.append(Problem(self.rel(path), line, message, level))

    def readable(self, path: str) -> str | None:
        """The file's text, or None and a problem named once: one file the system refuses must not
        stop every command."""
        try:
            return read(path)
        except OSError as e:
            message = f"cannot be read: {e.strerror or e}"
            if Problem(self.rel(path), 0, message) not in self.problems:
                self.problem(path, 0, message)
            return None

    def of_type(self, kind: str):
        return [i for i in self.items.values() if i.type == kind]

    # -- loading

    def _load_plan(self):
        if not os.path.isdir(native(self.plan_dir)):
            self.problem(self.spry, 0, "no spry/plan/ folder")
            return
        self._walk(self.plan_dir, None)

    def _walk(self, folder: str, parent: Item | None):
        for name in sorted(os.listdir(native(folder)), key=natural_key):
            path = os.path.join(folder, name)
            if name.startswith(".") or name in ("__pycache__",):
                continue
            if os.path.isdir(native(path)):
                if name in CONTAINERS and parent is not None:
                    for sub in sorted(os.listdir(native(path)), key=natural_key):
                        sub_path = os.path.join(path, sub)
                        if sub.startswith("."):
                            continue
                        if os.path.isdir(native(sub_path)):
                            self._add_folder(sub_path, parent, name)
                        else:
                            self.problem(sub_path, 0, f"only {CONTAINERS[name]} folders belong in {name}/")
                    continue
                self._add_folder(path, parent, None)
            elif name == "README.md":
                continue
            elif name == "checks.md" and parent is not None and parent.type == "story":
                continue
            elif self.slice_file.match(name):
                self._add_slice(path, parent)
            else:
                self.problem(path, 0, "not part of the plan — expected an item folder, a slice, README.md or checks.md")

    def _make(self, kind: str, ident: str, num: int, doc: str, folder: str | None,
              parent: Item | None, container: str | None):
        text = self.readable(doc)
        if text is None:
            return None
        fm, body_start, errors = parse_front_matter(text)
        for line, message in errors:
            self.problem(doc, line, message)
        item = Item(kind, ident, num, doc, folder, fm or {}, text, body_start, parent, container)
        if ident in self.items:
            self.problem(doc, 1, f"{ident} is also {self.rel(self.items[ident].doc)} — rename the newer one (`next {kind}`)")
        else:
            self.items[ident] = item
        if fm is not None:
            if fm.get("id") != ident:
                self.problem(doc, 2, f"front-matter id `{fm.get('id', '')}` does not match the name `{ident}`")
            for key in ("title", "state"):
                if not fm.get(key):
                    self.problem(doc, 1, f"front-matter has no `{key}`")
            states = SLICE_STATES if kind == "slice" else PLAN_STATES
            if fm.get("state") and fm["state"] not in states:
                self.problem(doc, 1, f"state `{fm['state']}` is not one of {', '.join(sorted(states))}")
        if parent is None:
            self.top.append(item)
        else:
            parent.children.append(item)
        return item

    def _add_folder(self, path: str, parent: Item | None, container: str | None):
        m = self.item_dir.match(os.path.basename(path))
        kind = self.type_of_prefix.get(m.group(1)) if m else None
        if not m or kind in (None, "slice", "decision"):
            self.problem(path, 0, "folder name is not `<PREFIX>-<n>-<slug>` for a plan item")
            return
        readme = os.path.join(path, "README.md")
        if not os.path.isfile(native(readme)):
            self.problem(path, 0, f"{m.group(1)}-{m.group(2)} has no README.md")
            return
        if not self._placed_well(kind, parent, container):
            where = f"{parent.type} {parent.id}" if parent else "the top of the plan"
            self.problem(readme, 1, f"a {kind} cannot sit under {where}" + (f"/{container}" if container else ""))
        item = self._make(kind, f"{m.group(1)}-{m.group(2)}", int(m.group(2)), readme, path, parent, container)
        if item is None:
            return
        if kind == "story":
            item.acs = self._acceptance_criteria(item)
        self._walk(path, item)

    def _add_slice(self, path: str, parent: Item | None):
        m = self.slice_file.match(os.path.basename(path))
        if parent is None or parent.type not in ("story", "task", "bug"):
            self.problem(path, 1, "a slice must sit in a story, task or bug folder")
        item = self._make("slice", f"{self.ids['slice']}-{m.group(1)}", int(m.group(1)), path, None, parent, None)
        if item and "covers" in item.fm and not isinstance(item.fm["covers"], list):
            self.problem(path, 1, "`covers` must be a list: `covers: [AC-1]`")

    def _placed_well(self, kind: str, parent: Item | None, container: str | None) -> bool:
        if container:
            if CONTAINERS[container] != kind or parent is None:
                return False
            if kind == "task":
                return parent.type in self.levels[:-1]
            return parent.type in self.levels[-2:]
        if kind in ("task", "bug"):
            return False
        if parent is None:
            return kind == self.levels[0]
        if parent.type not in self.levels:
            return False
        at = self.levels.index(parent.type)
        return at + 1 < len(self.levels) and self.levels[at + 1] == kind

    def _acceptance_criteria(self, story: Item):
        found = {}
        lines = section_lines(story.text, "Acceptance criteria") or []
        for i, cells in table_rows(lines):
            m = re.fullmatch(r"(~~)?(AC-\d+)(~~)?", cells[0]) if cells else None
            if m:
                if m.group(2) in found:
                    self.problem(story.doc, i + 1, f"{m.group(2)} appears twice")
                found[m.group(2)] = {"dropped": bool(m.group(1)), "line": i + 1}
        return found

    def _load_decisions(self):
        folder = os.path.join(self.spry, "knowledge", "decisions")
        if not os.path.isdir(native(folder)):
            return
        prefix = self.ids["decision"]
        for name in sorted(os.listdir(native(folder)), key=natural_key):
            m = re.match(r"^(" + re.escape(prefix) + r"-\d+)\b", name)
            if m and name.endswith(".md"):
                if m.group(1) in self.decisions:
                    self.problem(os.path.join(folder, name), 1, f"{m.group(1)} is used twice")
                self.decisions[m.group(1)] = os.path.join(folder, name)

    def _test_globs(self):
        patterns = self.config.get("tests", {}).get("match") or DEFAULT_TEST_MATCH
        real = [g for g in patterns if not re.search(r"<[^>]*>", g)]
        if len(real) < len(patterns) and not getattr(self, "_warned_match", False):
            self._warned_match = True
            self.problem(os.path.join(self.spry, "spry.config.json"), 0,
                         "tests.match is still the template's placeholder — using the defaults until it is set")
        return [glob_regex(g) for g in (real or DEFAULT_TEST_MATCH)]

    def _scan_tests(self):
        """{"S-1/AC-1": [(rel path, line, test name)]} from every test file outside spry/.

        Only a citation inside a string — a test's title, a docstring, a parametrize id — counts.
        One in a comment or in code is listed in `self.unproving`, so `check` can say why.
        A bug's or a task's ID in a test's name (`B-4 …`, `T-7 …`) goes to `self.item_tests`, the same
        way: neither has criteria, so falsify of its slice expects the bug or the task itself."""
        story = re.escape(self.ids["story"])
        ref = re.compile(r"(?<![A-Za-z0-9])(" + story + r"-\d+)/(AC-\d+)(?!\d)")
        marks = tuple(self.ids[k] + "-" for k in ("bug", "task"))
        # not inside another word, a path or a file name: `SUB-2`, `fixtures/B-4.json`, `B-7.json`
        bug = re.compile(r"(?<![A-Za-z0-9_/-])((?:" + "|".join(re.escape(self.ids[k]) for k in ("bug", "task"))
                         + r")-\d+)(?!\d|\.\w|/\w+\.)")
        globs, found = self._test_globs(), {}
        self.unproving, self.item_tests, self.item_unproving = [], {}, []
        for dirpath, dirnames, filenames in walk_dir(self.root):
            dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS and not d.startswith(".")]
            if os.path.abspath(dirpath) == self.root and "spry" in dirnames:
                dirnames.remove("spry")
            for name in filenames:
                path = os.path.join(dirpath, name)
                rel = self.rel(path)
                if not any(g.match(rel) for g in globs):
                    continue
                try:
                    if os.path.getsize(native(path)) > 2_000_000:
                        continue
                    text = read(path)
                except (UnicodeDecodeError, OSError):
                    continue
                triple = None
                for n, line in enumerate(text.split("\n"), 1):
                    hits = list(ref.finditer(line)) if "/AC-" in line else []
                    bugs = list(bug.finditer(line)) if any(m in line for m in marks) else []
                    if not hits and not bugs and '""' not in line and "''" not in line:
                        continue  # no citation, and no triple quote to open or close: nothing to track
                    spans, triple_after = string_spans(line, triple)
                    if bugs and not NOT_RUN.search(line):
                        comment = COMMENT_LINE.match(line) and triple is None
                        for m in bugs:
                            span = None if comment else next((s for s in spans if s[0] <= m.start() < s[1]), None)
                            if span is None:
                                self.item_unproving.append((rel, n, m.group(1)))
                            else:
                                self.item_tests.setdefault(m.group(1), []).append(
                                    (rel, n, line[span[0]:span[1]].strip()))
                    if hits and not NOT_RUN.search(line):
                        comment = COMMENT_LINE.match(line) and triple is None
                        for m in hits:
                            span = None if comment else next(
                                (s for s in spans if s[0] <= m.start() < s[1]), None)
                            key = f"{m.group(1)}/{m.group(2)}"
                            if span is None:
                                self.unproving.append((rel, n, key))
                            else:
                                found.setdefault(key, []).append((rel, n, line[span[0]:span[1]].strip()))
                    triple = triple_after
        return found

    def _manual_checks(self, story: Item):
        """{"AC-1": (date, build, by, result, line)} — the latest row per criterion."""
        path = os.path.join(story.folder, "checks.md")
        if not os.path.isfile(native(path)):
            return {}
        text = read(path)
        for _level, title, at, _end in sections(text):
            m = SCENARIO_ACS.match(title)
            for ac in re.findall(r"AC-\d+", m.group(1)) if m else []:
                if ac not in story.acs:
                    self.problem(path, at + 1, f"scenario for {ac}, which {story.id} does not have")
        latest = {}
        for i, cells in table_rows(section_lines(text, "Check log") or []):
            if len(cells) < 5 or not DATE.match(cells[0]):
                continue
            ac = cells[1]
            if not re.fullmatch(r"AC-\d+", ac):
                self.problem(path, i + 1, f"check log row names `{ac}`, not an AC")
                continue
            if ac not in story.acs:
                self.problem(path, i + 1, f"{story.id} has no {ac}")
            result = cells[4].lower()
            if result not in ("pass", "fail"):
                self.problem(path, i + 1, f"result `{cells[4]}` is not pass or fail")
            if ac not in latest or cells[0] >= latest[ac][0]:
                latest[ac] = (cells[0], cells[2], cells[3], result, i + 1)
        return latest

    # -- derived status

    def proof(self, story: Item, ac: str):
        """(proven, description)."""
        ref = f"{story.id}/{ac}"
        tests = self.tests.get(ref, [])
        manual = self.manual.get(story.id, {}).get(ac)
        parts = [f"test `{path}`" + (f' — "{name}"' if name else "") for path, _, name in tests]
        if manual:
            date, _build, by, result, _line = manual
            parts.append(f"manual check {date} · {by} · {result} ([checks](checks.md))")
        if manual and manual[3] == "fail":
            return False, " · ".join(parts)
        return bool(tests or manual), " · ".join(parts) or "not yet"

    def done(self, item: Item) -> bool:
        if item.id in self._memo:
            return self._memo[item.id]
        self._memo[item.id] = False
        if item.state in ("dropped", "draft"):
            result = False
        elif item.type == "slice":
            result = item.state == "closed"
        elif item.type == "story":
            slices = self.counted(item, "slice")
            acs = [a for a, v in item.acs.items() if not v["dropped"]]
            result = bool(slices) and all(self.done(s) for s in slices) and bool(acs) \
                and all(self.proof(item, a)[0] for a in acs)
        elif item.type in ("task", "bug"):
            slices = self.counted(item, "slice")
            result = bool(slices) and all(self.done(s) for s in slices)
        else:
            kind = self.child_level(item.type)
            kids = self.counted(item, kind) if kind else []
            result = bool(kids) and all(self.done(k) for k in kids)
        self._memo[item.id] = result
        return result

    def child_level(self, kind: str):
        if kind in self.levels and self.levels.index(kind) + 1 < len(self.levels):
            return self.levels[self.levels.index(kind) + 1]
        return "slice" if kind in ("story", "task", "bug") else None

    def counted(self, item: Item, kind: str):
        return [c for c in item.kids(kind) if c.state != "dropped"]

    def descendants(self, item: Item, kind: str):
        out = []
        for c in item.children:
            if c.type == kind and c.state != "dropped":
                out.append(c)
            out += self.descendants(c, kind)
        return out

    def open_bugs(self, item: Item):
        return [b for b in self.descendants(item, "bug") if not self.done(b)]

    def slice_state(self, s: Item) -> str:
        pr = s.fm.get("pr", "")
        pr = f" · PR #{pr}" if isinstance(pr, str) and pr.isdigit() else ""
        return ("done" if self.done(s) else s.state) + (pr if s.state in ("open", "closed") else "")

    def progress(self, item: Item) -> str:
        if item.type == "slice":
            return self.slice_state(item)
        if item.state == "dropped":
            return "dropped"
        bugs = self.open_bugs(item)
        bug_note = f" · {len(bugs)} open bug{'s' if len(bugs) != 1 else ''}" if bugs else ""
        if item.type == "story":
            slices = self.counted(item, "slice")
            acs = [a for a, v in item.acs.items() if not v["dropped"]]
            proven = sum(1 for a in acs if self.proof(item, a)[0])
            if self.done(item):
                word = "done"
            elif item.state == "draft":
                word = "draft"
            elif slices and all(self.done(s) for s in slices):
                word = "not proven"
            elif any(s.state in ("open", "closed") for s in slices):
                word = "in progress"
            else:
                word = "not started"
            return (f"{word} · {sum(map(self.done, slices))} of {len(slices)} slices · "
                    f"{proven} of {len(acs)} criteria proven{bug_note}")
        kind = self.child_level(item.type)
        kids = self.counted(item, kind) if kind else []
        if not kids:
            return f"no {PLURAL[kind]} yet{bug_note}"
        if item.type in ("task", "bug") and self.done(item):
            return "done"
        return f"{sum(map(self.done, kids))} of {len(kids)} {PLURAL[kind]} done{bug_note}"


# ---------------------------------------------------------------- check

def history_files(project: Project) -> list:
    """Documents kept from an earlier process, as they were: `spry/history/<source>/**/*.md`."""
    out, top = [], os.path.join(project.spry, "history")
    for dirpath, dirnames, filenames in walk_dir(top):
        dirnames[:] = [d for d in dirnames if not d.startswith(".")]
        if os.path.abspath(dirpath) != os.path.abspath(top):
            out += [os.path.join(dirpath, f) for f in filenames if f.endswith(".md")]
    return sorted(out)


def markdown_files(project: Project):
    """Every .md under spry/ except the copied process/, tool/ and skills/, and history kept as it
    was (`history_files`), plus AGENTS.md."""
    out = []
    agents = os.path.join(project.root, "AGENTS.md")
    if os.path.isfile(native(agents)):
        out.append(agents)
    for dirpath, dirnames, filenames in walk_dir(project.spry):
        rel = project.rel(dirpath)
        if rel in ("spry/process", "spry/tool", "spry/skills") or rel.startswith(("spry/process/", "spry/tool/", "spry/skills/", "spry/history/")):
            dirnames[:] = []
            continue
        dirnames[:] = [d for d in dirnames if not d.startswith(".")]
        out += [os.path.join(dirpath, f) for f in filenames if f.endswith(".md")]
    return sorted(out)


def glossary(project: Project):
    """[(banned phrase, preferred term)]."""
    path = os.path.join(project.root, project.config.get("glossary", "spry/knowledge/glossary.md"))
    if not os.path.isfile(native(path)):
        return path, []
    return path, glossary_terms(read(path))


def glossary_terms(text: str) -> list:
    out = []
    for _i, cells in table_rows(enumerate(text.split("\n"))):
        if len(cells) >= 3 and cells[0].lower() != "term":
            out += [(b.strip(), cells[0]) for b in cells[2].split(",") if b.strip() and not b.strip().startswith("<")]
    return out


def banned_patterns(banned: list) -> list:
    return [(re.compile(r"(?<![\w-])" + re.escape(b) + r"(?![\w-])", re.I), b, t) for b, t in banned]


def budget_patterns(project: Project) -> list:
    return [(glob_regex(g), n, g) for g, n in project.config.get("budgets", {}).items()]


def check_text(project: Project, path: str, text: str, fm: dict, banned_res: list, budgets: list, gloss_path: str,
               exists=lambda path: os.path.exists(native(path))):
    """`check` of one document's text: budget, guides and placeholders, links, glossary words.
    `exists` says whether a link's target is there — on disk, or at a commit for `new` on the main branch."""
    rel = project.rel(path)
    lines = text.split("\n")

    for regex, limit, pattern in budgets:
        if regex.match(rel) and len(lines) > limit:
            project.problem(path, len(lines), f"{len(lines)} lines, budget {limit} ({pattern}) — /spry:compact moves sections to the files that own them")

    unfinished_ok = fm.get("state") in ("draft", "planned")
    if not unfinished_ok:
        in_fence = False
        for n, line in enumerate(lines, 1):
            if FENCE.match(line):
                in_fence = not in_fence
            if not in_fence and "<!-- guide:" in line:
                project.problem(path, n, "template guide left in a finished document")
        for n, line in prose(strip_blocks(text)):
            for m in PLACEHOLDER.finditer(line):
                word = m.group(1).split()[0].lower()
                if word not in HTML_TAGS and not m.group(1).startswith(("http", "/")):
                    project.problem(path, n, f"placeholder `<{m.group(1)}>` left in a finished document")

    visible = strip_blocks(text)
    skip = set()
    for _level, title, at, end in sections(visible):
        if title.lower() == "conflict check":
            skip.update(range(at + 1, end + 1))
    check_words = os.path.abspath(path) != os.path.abspath(gloss_path) and rel != "AGENTS.md"
    for n, line in prose(visible):
        for target in LINK.findall(line):
            if target.startswith(("http:", "https:", "mailto:", "#")):
                continue
            base = project.root if target.startswith("/") else os.path.dirname(path)
            resolved = os.path.normpath(os.path.join(base, target.split("#")[0].lstrip("/")))
            if not exists(resolved):
                project.problem(path, n, f"link to `{target}` does not resolve")
        if check_words and n not in skip:
            for regex, phrase, term in banned_res:
                if regex.search(line):
                    project.problem(path, n, f"`{phrase}` — the glossary says `{term}`")


def check(project: Project):
    gloss_path, banned = glossary(project)
    banned_res, budgets = banned_patterns(banned), budget_patterns(project)
    by_doc = {i.doc: i for i in project.items.values()}

    for path in markdown_files(project):
        rel = project.rel(path)
        if len(rel) > LONG_PATH:
            project.problem(path, 0, f"{len(rel)} characters from the repository root — Windows without long paths "
                                     f"stops at 260 in all: shorten a folder's slug (`git mv`)", "warning")
        text = project.readable(path)
        if text is None:
            continue
        item = by_doc.get(path)
        fm = item.fm if item else None
        start = item.body_start if item else 0
        if item is None and rel != "AGENTS.md":
            fm, start, errors = parse_front_matter(text)
            for line, message in errors:
                project.problem(path, line, message)
        check_text(project, path, text, fm or {}, banned_res, budgets, gloss_path)

    known = set(project.items) | set(project.decisions)
    for item in project.items.values():
        for key in ("blocked_by", "related"):
            value = item.fm.get(key, [])
            if not isinstance(value, list):
                project.problem(item.doc, 1, f"`{key}` must be a list")
                continue
            for ref in value:
                if ref not in known:
                    project.problem(item.doc, 1, f"`{key}` names {ref}, which does not exist")
        if item.type == "slice" and item.fm.get("closed") and not closed_on(item):
            project.problem(item.doc, 1, f"`closed: {item.fm['closed']}` is not a date — YYYY-MM-DD, the day the slice closed")
        if item.type == "slice" and item.state == "open" and not owner_of(item):
            project.problem(item.doc, 1, f"open without an `owner:` — who is building it: `link {item.id} --owner`", "warning")
        if item.type == "slice" and item.state == "open" and project.config.get("slices", {}).get("issue") \
                and not str(item.fm.get("issue", "")).isdigit():
            project.problem(item.doc, 1, "open without an `issue:` number — `slices.issue` is on: "
                                         "slicing.md *Open* creates the issue before the branch")
        needs_check = (item.type == "slice" and item.state in ("open", "closed")) or \
                      (item.type not in ("slice", "bug") and item.state == "ready")
        if needs_check:
            body = section_lines(item.text, "Conflict check")
            if body is None:
                project.problem(item.doc, 1, f"{item.state} without a `Conflict check` section — spry/process/conflicts.md")
            else:
                if not any(CHECKED_LINE.match(line) for _, line in body):
                    project.problem(item.doc, (body[0][0] if body else 0) + 1,
                                    "conflict check has no `- Checked <date> against: …` line")
                for i, line in body:
                    if OPEN_FINDING.search(line):
                        project.problem(item.doc, i + 1, "conflict finding still open: " + line.strip(" -"))
        if item.type == "slice" and item.parent is not None and isinstance(item.fm.get("covers"), list):
            if item.parent.type == "story":
                for ac in item.fm["covers"]:
                    if ac not in item.parent.acs:
                        project.problem(item.doc, 1, f"covers {ac}, which {item.parent.id} does not have")
            elif item.fm["covers"]:
                project.problem(item.doc, 1, f"`covers` lists acceptance criteria, but {item.parent.id} is a "
                                             f"{item.parent.type}, not a story — leave `covers: []`: the slice "
                                             f"fixes what its {item.parent.type} says, and a test that re-proves a "
                                             f"story's criterion still cites it in its name")
        if item.type == "bug":
            for ref in item.fm.get("breaks", []) if isinstance(item.fm.get("breaks"), list) else []:
                story_id, _, ac = ref.partition("/")
                story = project.items.get(story_id)
                if story is None or story.type != "story" or ac not in story.acs:
                    project.problem(item.doc, 1, f"`breaks` names {ref}, which does not exist")
        if not gone(item):
            for ref in item.fm.get("blocked_by") if isinstance(item.fm.get("blocked_by"), list) else []:
                if ref in project.items and gone(project.items[ref]):
                    project.problem(item.doc, 1, f"`blocked_by` names {ref}, which is dropped — it never finishes; remove it")
    for source, chain in blocked_cycles(project):
        project.problem(source.doc, 1, f"`blocked_by` goes in a circle, so none of it can start: {chain}")

    for ref, hits in sorted(project.tests.items()):
        story_id, ac = ref.split("/")
        story = project.items.get(story_id)
        for path, line, _ in hits:
            if story is None or story.type != "story":
                project.problem(os.path.join(project.root, path), line, f"test cites {ref}, but there is no story {story_id}")
            elif ac not in story.acs:
                project.problem(os.path.join(project.root, path), line, f"test cites {ref}, but {story_id} has no {ac}")
            elif story.acs[ac]["dropped"]:
                project.problem(os.path.join(project.root, path), line, f"test cites {ref}, which is dropped", "warning")
    for path, line, ref in project.unproving:
        if ref not in project.tests:
            project.problem(os.path.join(project.root, path), line,
                            f"{ref} is cited outside a test's name (a comment or code), which proves nothing — "
                            f"put it in the test's title string", "warning")
    return project.problems


# ---------------------------------------------------------------- index

def link(from_doc: str, item: Item) -> str:
    target = os.path.relpath(item.doc, os.path.dirname(from_doc)).replace(os.sep, "/")
    return f"[{item.label}]({target})"


def children_block(project: Project, item: Item) -> str:
    parts = []
    kind = project.child_level(item.type)
    if kind == "slice":
        rows = item.kids("slice")
        if not rows:
            parts.append("_No slices yet._")
        elif item.type == "story":
            parts.append("| Slice | State | Covers |\n|---|---|---|")
            parts[-1] += "".join(f"\n| {link(item.doc, s)} | {project.slice_state(s)} | {', '.join(s.fm.get('covers', []) or []) or '—'} |" for s in rows)
        else:
            parts.append("| Slice | State |\n|---|---|")
            parts[-1] += "".join(f"\n| {link(item.doc, s)} | {project.slice_state(s)} |" for s in rows)
    elif kind:
        rows = item.kids(kind)
        if rows:
            table = f"| {kind.capitalize()} | State | Progress |\n|---|---|---|"
            table += "".join(f"\n| {link(item.doc, c)} | {c.state} | {project.progress(c)} |" for c in rows)
            parts.append(table)
        else:
            parts.append(f"_No {PLURAL[kind]} yet._")
    tasks, bugs = item.kids("task"), item.kids("bug")
    if tasks:
        table = "| Task | State | Progress |\n|---|---|---|"
        table += "".join(f"\n| {link(item.doc, t)} | {t.state} | {project.progress(t)} |" for t in tasks)
        parts.append(table)
    if bugs:
        table = "| Bug | Severity | State | Progress |\n|---|---|---|---|"
        table += "".join(f"\n| {link(item.doc, b)} | {b.fm.get('severity', '—')} | {b.state} | {project.progress(b)} |" for b in bugs)
        parts.append(table)
    return "\n\n".join(parts)


def proof_block(project: Project, story: Item) -> str:
    rows = [(ac, project.proof(story, ac)[1]) for ac, v in story.acs.items() if not v["dropped"]]
    out = "| AC | Proven by |\n|---|---|" + "".join(f"\n| {ac} | {how} |" for ac, how in rows) if rows else "_No acceptance criteria yet._"
    bugs = [b for b in project.of_type("bug") if not project.done(b) and b.state != "dropped"
            and any(r.startswith(story.id + "/") for r in (b.fm.get("breaks") or []))]
    for b in bugs:
        acs = ", ".join(r.split("/")[1] for r in b.fm["breaks"] if r.startswith(story.id + "/"))
        out += f"\n\nOpen bug: {link(story.doc, b)} breaks {acs}."
    return out


def top_block(project: Project, doc: str, deep: bool) -> str:
    first = project.levels[0]
    rows = [i for i in project.top if i.type == first]
    if not rows:
        return f"_No {PLURAL[first]} yet._"
    if deep:
        out = f"| {first.capitalize()} | Progress |\n|---|---|"
        for m in rows:
            stories = project.descendants(m, "story")
            progress, _, bugs = project.progress(m).partition(" · ") if project.open_bugs(m) and m.type != "story" else (project.progress(m), "", "")
            extra = f" · {sum(map(project.done, stories))} of {len(stories)} stories done" if m.type != "story" else ""
            out += f"\n| {link(doc, m)} | {progress}{extra}{' · ' + bugs if bugs else ''} |"
        return out
    out = f"| {first.capitalize()} | State | Progress |\n|---|---|---|"
    return out + "".join(f"\n| {link(doc, m)} | {m.state} | {project.progress(m)} |" for m in rows)


def coverage_block(project: Project, doc: str) -> str:
    """Defined vs done for the whole plan, and the gaps a total would hide."""
    def pct(done, total):
        return f"{round(100 * done / total)}%" if total else "—"

    def live(kind):
        return [i for i in project.of_type(kind) if i.state != "dropped"
                and not any(a.state == "dropped" for a in i.ancestors())]

    def criteria(story):
        return [a for a, v in story.acs.items() if not v["dropped"]]

    def started(item):
        """Some slice under it — or it, if a slice — is open or closed."""
        slices = [item] if item.type == "slice" else project.descendants(item, "slice")
        return any(s.state in ("open", "closed") for s in slices)

    def tally(items):
        done = sum(map(project.done, items))
        return done, sum(1 for i in items if not project.done(i) and started(i)), len(items)

    def table(levels, under=None):
        """The totals table, for the whole plan or for what sits under one top-level item."""
        def of(kind):
            return [i for i in live(kind) if under is None or under in i.ancestors()]
        rows = [(PLURAL.get(kind, kind).capitalize(), *tally(of(kind))) for kind in levels]
        acs = [(s, a) for s in ([under] if under and under.type == "story" else of("story"))
               for a in criteria(s)]
        rows.append(("Acceptance criteria proven", sum(1 for s, a in acs if project.proof(s, a)[0]), None, len(acs)))
        for kind in ("slice", "task", "bug"):
            label = {"slice": "Slices closed", "task": "Tasks", "bug": "Bugs fixed"}[kind]
            rows.append((label, *tally(of(kind))))
        return ["| | Done | In progress | Defined | |", "|---|--:|--:|--:|--:|"] + [
            f"| {name} | {done} | {'—' if busy is None else busy} | {total} | {pct(done, total)} |"
            for name, done, busy, total in rows]

    stories = live("story")
    out = ["### Totals", "",
           "In progress: not done, and some slice under it is open or closed. A criterion is proven or not.", ""]
    out += table(project.levels)

    first = project.levels[0]
    tops = [i for i in project.top if i.type == first and i.state != "dropped"]
    out += ["", f"### By {first}", ""]
    if not tops:
        out.append(f"_No {PLURAL.get(first, first)} yet._")
    for m in tops:
        if project.done(m):
            out += [f"{link(doc, m)} — done.", ""]
        else:
            out += [f"#### {link(doc, m)} — {m.state}", ""] + table(project.levels[1:], m) + [""]
    if tops:
        out.pop()

    out += ["", "### Built, not proven", "",
            "Every slice is closed and these criteria still have no passing proof — no test names them "
            "in its title, and no manual check passed.", ""]
    gaps = []
    for s in stories:
        slices = project.counted(s, "slice")
        if s.state == "draft" or not slices or not all(map(project.done, slices)):
            continue
        missing = [a for a in criteria(s) if not project.proof(s, a)[0]]
        if missing:
            gaps.append(f"| {link(doc, s)} | {', '.join(missing)} |")
    out += ["| Story | Not proven |", "|---|---|"] + gaps if gaps else ["_None._"]

    out += ["", "### Cited outside a test's name", "",
            "Not proven, and cited only in a comment or in code. Moving the ID into the test's title "
            "string proves it.", ""]
    cited = {}
    for rel, line, key in project.unproving:
        cited.setdefault(key, []).append(f"{rel}:{line}")
    rows = []
    for key in sorted(cited, key=natural_key):
        sid, ac = key.split("/")
        s = project.items.get(sid)
        if not s or s.type != "story" or s not in stories or ac not in criteria(s) or project.proof(s, ac)[0]:
            continue
        where = cited[key]
        more = f" · {len(where) - 1} more" if len(where) > 1 else ""
        target = os.path.relpath(s.doc, os.path.dirname(doc)).replace(os.sep, "/")
        rows.append(f"| [{key}]({target}) {s.title} | `{where[0]}`{more} |")
    out += ["| Criterion | Cited at |", "|---|---|"] + rows if rows else ["_None._"]
    return "\n".join(out)


def slice_branches(project: Project) -> dict:
    """{"SL-2": "origin/sl-2-refuse-over-limit"} — local or remote-tracking branches named for a slice
    as `slice-open` names them: the slice's file name without `.md`, lower case."""
    done = git(project.root, "for-each-ref", "--format=%(refname:short)", "refs/heads", "refs/remotes")
    if done.returncode != 0:
        return {}
    refs = sorted(done.stdout.split())
    out = {}
    for s in project.of_type("slice"):
        stem = os.path.basename(s.doc)[:-3].lower()
        found = next((r for r in refs if r.lower() == stem or r.lower().endswith("/" + stem)), None)
        if found:
            out[s.id] = found
    return out


def gone(item: Item) -> bool:
    """Dropped, or under something dropped: it will never be done."""
    return item.state == "dropped" or any(a.state == "dropped" for a in item.ancestors())


def blocked_cycles(project: Project) -> list:
    """Waits that never end: [(the item whose `blocked_by` starts it, "SL-5 waits on SL-6, …")].
    An item is done only when what it counts is (`Project.done`), and waits on what it and anything
    above it names — so a slice that names its own story waits on itself."""
    live = {i.id: i for i in project.items.values() if not gone(i) and not project.done(i)}

    def edges(item):
        kind = project.child_level(item.type)
        out = [(c.id, None) for c in (project.counted(item, kind) if kind else []) if c.id in live]
        for node in [item] + item.ancestors():
            refs = node.fm.get("blocked_by") if isinstance(node.fm.get("blocked_by"), list) else []
            out += [(r, node) for r in refs if r in live]
        return out

    state, found, seen = {}, [], set()
    for start in sorted(live, key=natural_key):
        if start in state:
            continue
        state[start] = 1
        path, via, stack = [start], [], [iter(edges(live[start]))]
        while stack:
            step = next(stack[-1], None)
            if step is None:
                state[path.pop()] = 2
                stack.pop()
                if via:
                    via.pop()
            elif state.get(step[0]) == 1:
                at = path.index(step[0])
                ring, sources = path[at:] + [step[0]], via[at:] + [step[1]]
                named = frozenset((s.id, b) for b, s in zip(ring[1:], sources) if s is not None)
                if named not in seen:
                    seen.add(named)
                    chain = ", ".join(f"{a} needs {b}" if s is None else f"{a} waits on {b}" if s.id == a
                                      else f"{a} waits on {b}, as {s.id} does"
                                      for a, b, s in zip(ring, ring[1:], sources))
                    found.append((next(s for s in sources if s is not None), chain))
            elif step[0] not in state:
                state[step[0]] = 1
                path.append(step[0])
                via.append(step[1])
                stack.append(iter(edges(live[step[0]])))
    return found


def blockers(project: Project, item: Item) -> list:
    """Unfinished plan items named in `blocked_by` by the item or anything above it."""
    out = []
    for node in [item] + item.ancestors():
        refs = node.fm.get("blocked_by") if isinstance(node.fm.get("blocked_by"), list) else []
        out += [project.items[r] for r in refs if r in project.items and not project.done(project.items[r])
                and project.items[r] not in out]
    return out


def part_of(doc: str, item: Item) -> str:
    """Everything the item sits under, from the top: what it is part of, at a glance."""
    return " › ".join(link(doc, a) for a in reversed(item.ancestors())) or "—"


def work_type(item: Item) -> str:
    """What kind of work a row is: a slice's is what it builds — story, task or bug."""
    return item.parent.type if item.type == "slice" and item.parent is not None else item.type


DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def closed_on(item: Item) -> str:
    """A slice's `closed:` date, or "" when it has none yet."""
    value = str(item.fm.get("closed") or "")
    return value if DATE.match(value) else ""


def backlog(project: Project) -> dict:
    """What to pick up, in plan order: by top-level item; inside one, bugs, then tasks, then stories,
    each in tree order; slices by ID. Nothing here is typed — no priority field, no hand-kept queue."""
    branches = slice_branches(project)
    rank = {"bug": 0, "task": 1, "story": 2}
    out = {"progress": [], "ready": [], "slicing": [], "blocked": [], "planning": []}

    def live(item):
        return not gone(item)

    def walk(item):
        yield item
        for child in item.children:
            yield from walk(child)

    for top in project.top:
        nodes = [n for n in walk(top) if live(n)]
        for n in nodes:
            if n.type == "slice" or any(a.state == "draft" for a in n.ancestors()):
                continue
            kind = project.child_level(n.type) if n.type in project.levels else None
            if n.state == "draft":
                out["planning"].append((n, "finishing — it is a draft"))
            elif kind and kind != "slice" and n.state == "ready" and not project.counted(n, kind):
                out["planning"].append((n, PLURAL[kind]))
        units = sorted((n for n in nodes if n.type in rank), key=lambda n: rank[n.type])
        for unit in units:
            if unit.state != "ready" or any(a.state == "draft" for a in unit.ancestors()) or project.done(unit):
                continue
            waiting = blockers(project, unit)
            slices = sorted(project.counted(unit, "slice"), key=lambda s: s.num)
            for s in slices:
                if claimed(s) or (s.state == "planned" and s.id in branches):
                    where = branch_of(s) or branches.get(s.id, "")
                    pr = s.fm.get("pr", "")
                    out["progress"].append((s, f"`{where}`" + (f" · PR #{pr}" if str(pr).isdigit() else "")))
                elif s.state == "planned":
                    late = waiting + [b for b in blockers(project, s) if b not in waiting]
                    out["blocked" if late else "ready"].append((s, late))
            if unit.type == "story":
                covered = {ac for s in slices for ac in (s.fm.get("covers") or [])}
                missing = [a for a, v in unit.acs.items() if not v["dropped"] and a not in covered]
                need = "slices" if not slices else ", ".join(missing) if missing else None
            else:
                need = None if slices else "slices"
            if need:
                out["blocked" if waiting else "slicing"].append((unit, waiting if waiting else need))
    return out


def backlog_block(project: Project, doc: str) -> str:
    """The backlog page: what is being built, what to build next, and what stands in the way."""
    items = backlog(project)
    order = (("progress", "in progress"), ("ready", "ready to build"), ("slicing", "needs slicing"),
             ("blocked", "blocked"), ("planning", "needs planning"))
    where = {}
    for key, label in reversed(order):
        where.update({i.id: label for i, _ in items[key]})
    rank = [label for _, label in order]
    waiters = {}
    for i in project.items.values():
        if not gone(i) and not project.done(i):
            for ref in i.fm.get("blocked_by") if isinstance(i.fm.get("blocked_by"), list) else []:
                waiters.setdefault(ref, []).append(i)

    def owner(item):
        return item.fm.get("owner") or "—"

    def under(item):
        yield item
        for child in item.children:
            yield from under(child)

    def status(item):
        """Where a blocker stands, in this page's words, and who owns it."""
        if gone(item):
            label = "dropped"
        elif any(a.state == "draft" for a in [item] + item.ancestors()):
            label = "needs planning"
        else:
            labels = [where[n.id] for n in under(item) if n.id in where]
            label = min(labels, key=rank.index) if labels else "built, not yet proven"
        who = item.fm.get("owner")
        return f"{link(doc, item)} · {label}" + (f" ({who})" if who else "")

    def unblocks(item):
        """What waits on this slice, or on something it is part of."""
        out = []
        for node in [item] + [a for a in item.ancestors() if not project.done(a)]:
            out += [w for w in waiters.get(node.id, []) if w not in out]
        return ", ".join(link(doc, w) for w in sorted(out, key=lambda w: natural_key(w.id))) or "—"

    def trail(item):
        return part_of(doc, item)

    def section(title, intro, head, rows):
        """A table whose rows are numbered from 1, so "SL-4, row 2 of Blocked" is easy to say."""
        out = ["", f"### {title}", "", intro, ""]
        if not rows:
            return out + ["_None._"]
        cols = head.count("|") - 1
        return out + ["| # " + head, "|--:|" + "---|" * cols] + [f"| {n} {row}" for n, row in enumerate(rows, 1)]

    out = []
    out += section("In progress", "Being built now — open, or on a branch named for the slice. Leave these to their owner.",
                   "| Slice | Type | Part of | Owner | Where | Unblocks |",
                   [f"| {link(doc, s)} | {work_type(s)} | {trail(s)} | {owner(s)} | {branch} | {unblocks(s)} |"
                    for s, branch in items["progress"]])
    out += section("Ready to build", "Planned, and nothing they wait for is unfinished. The first row is next; "
                   "`/spry:slice-open` with no ID offers it. *Unblocks* is what waits on the slice, or on "
                   "something it is part of — between two rows, the one that frees more.",
                   "| Slice | Type | Part of | Covers | Owner | Unblocks |",
                   [f"| {link(doc, s)} | {work_type(s)} | {trail(s)} | {', '.join(s.fm.get('covers') or []) or '—'} | {owner(s)} "
                    f"| {unblocks(s)} |" for s, _ in items["ready"]])
    out += section("Needs slicing", "Ready, but no slice is planned for all of it yet — `/spry:slice <ID>` splits it.",
                   "| Item | Type | Part of | Missing | Owner |",
                   [f"| {link(doc, i)} | {work_type(i)} | {trail(i)} | {'slices' if need == 'slices' else 'a slice for ' + need} | {owner(i)} |"
                    for i, need in items["slicing"]])
    out += section("Blocked", "Waiting on unfinished work, named here with where it stands and who owns it.",
                   "| Item | Type | Part of | Waiting on | Owner |",
                   [f"| {link(doc, i)} | {work_type(i)} | {trail(i)} | {'; '.join(status(b) for b in waits)} | {owner(i)} |"
                    for i, waits in items["blocked"]])
    out += section("Needs planning", "Product's next step: finish a draft, or add what an item is still missing.",
                   "| Item | Type | Part of | Needs | Owner |",
                   [f"| {link(doc, i)} | {work_type(i)} | {trail(i)} | {need} | {owner(i)} |" for i, need in items["planning"]])
    return "\n".join(out[1:])


def finished(project: Project) -> list:
    """[(item, date)] — every finished story, task and bug, newest first; undated ones last, in plan
    order. The date is the day its last slice closed, or "" when a slice it counts has no `closed:`."""
    def walk(item):
        yield item
        for child in item.children:
            yield from walk(child)

    out = []
    for top in project.top:
        for n in walk(top):
            if n.type in ("story", "task", "bug") and not gone(n) and project.done(n):
                dates = [closed_on(s) for s in project.counted(n, "slice")]
                out.append((n, max(dates) if all(dates) else ""))
    return sorted(out, key=lambda row: row[1], reverse=True)


def done_block(project: Project, doc: str) -> str:
    """The done page: what is finished, newest first."""
    rows = finished(project)
    if not rows:
        return "_Nothing done yet._"
    out = ["| # | Item | Type | Part of | Closed |", "|--:|---|---|---|---|"]
    out += [f"| {n} | {link(doc, i)} | {i.type} | {part_of(doc, i)} | {date or '—'} |"
            for n, (i, date) in enumerate(rows, 1)]
    return "\n".join(out)


# ---------------------------------------------------------------- owners and work

def owner_of(item: Item) -> str:
    """An item's `owner:` — empty while it is still the template's `<name>`. A slice's is who built it."""
    owner = str(item.fm.get("owner") or "").strip()
    return "" if owner.startswith("<") else owner


def members(project: Project) -> list:
    return [m for m in project.config.get("team", {}).get("members", []) if isinstance(m, dict) and m.get("name")]


def member_named(project: Project, who: str) -> dict | None:
    """The team member a name or a GitHub login stands for, ignoring case."""
    who = who.strip().lower()
    return next((m for m in members(project) if who in (m["name"].lower(), str(m.get("github") or "").lower())), None)


def whoami(project: Project) -> str | None:
    """The person at this clone, as `owner:` names them: their `team.members` name, found by git's
    user.name or the start of user.email; solo, git's user.name. None when neither says."""
    said = [git(project.root, "config", key).stdout.strip() for key in ("user.name", "user.email")]
    if not members(project):
        return said[0] or None
    for word in (said[0], said[1].split("@")[0]):
        found = member_named(project, word) if word else None
        if found:
            return found["name"]
    return None


def resolve_owner(project: Project, given: str) -> str:
    """`--owner NAME` as `owner:` writes it — a member's name, given by name or login — or, bare, `whoami`."""
    names = ", ".join(m["name"] for m in members(project))
    if not given:
        me = whoami(project)
        if me is None:
            raise SystemExit("who is building this? git's user.name and user.email match no one in team.members "
                             f"— pass --owner <name>, one of: {names}" if names else
                             "who is building this? git has no user.name — pass --owner <name>")
        return me
    if not members(project):
        return given.strip()
    found = member_named(project, given)
    if found is None:
        raise SystemExit(f"{given} is not in team.members — one of: {names}")
    return found["name"]


def work(project: Project, who: str, since: str, until: str) -> dict:
    """What one person built between two days: their slices closed in the range, under the story, task
    or bug each builds — newest first, by the last of their slices to close — and their slices being
    built now. Read from the slice files alone (`owner:`, `closed:`), never from git."""
    for day in (since, until):
        try:
            date.fromisoformat(day if DATE.match(day) else "")
        except ValueError:
            raise SystemExit(f"{day!r} is not a date — YYYY-MM-DD")
    if since > until:
        raise SystemExit(f"--since {since} is after --until {until}")
    found = member_named(project, who)
    name = found["name"] if found else who.strip()
    aliases = {name.lower()} | ({str(found.get("github") or "").lower()} - {""} if found else set())

    def theirs(s):
        return owner_of(s).lower() in aliases

    def rel(item):
        return project.rel(item.doc)

    # A slice under something dropped later was still built, so only a dropped slice is left out.
    slices = sorted((s for s in project.of_type("slice") if s.state != "dropped"), key=lambda s: natural_key(s.id))
    closed = [s for s in slices if s.state == "closed"]
    in_range = [s for s in closed if since <= closed_on(s) <= until]
    groups = {}
    for s in in_range:
        if theirs(s) and s.parent is not None:
            groups.setdefault(s.parent.id, (s.parent, []))[1].append(s)
    items = []
    for parent, mine in groups.values():
        others = {}
        for s in project.counted(parent, "slice"):
            if s.state == "closed" and not theirs(s):
                found = member_named(project, owner_of(s)) if owner_of(s) else None
                key = found["name"] if found else owner_of(s)
                others[key] = others.get(key, 0) + 1
        items.append({"id": parent.id, "title": parent.title, "type": parent.type, "doc": rel(parent),
                      "part_of": [a.label for a in reversed(parent.ancestors())],
                      "progress": project.progress(parent),
                      "slices": [{"id": s.id, "title": s.title, "closed": closed_on(s), "doc": rel(s)} for s in mine],
                      "others": dict(sorted(others.items()))})
    items.sort(key=lambda i: max(s["closed"] for s in i["slices"]), reverse=True)
    return {
        "owner": name, "since": since, "until": until, "items": items,
        "in_progress": [{"id": s.id, "title": s.title, "state": s.state if s.state == "open" else "claimed",
                         "parent": s.parent.label if s.parent else "", "doc": rel(s)}
                        for s in slices if theirs(s) and claimed(s)],
        "unowned": [s.id for s in in_range if not owner_of(s)],
        "undated": [s.id for s in closed if theirs(s) and not closed_on(s)],
        "owners": sorted({owner_of(s) for s in slices if owner_of(s)}, key=str.lower),
    }


def work_text(report: dict) -> str:
    """`work` for a person to read: one heading per story, task or bug, its slices under it."""
    who = report["owner"]
    count = sum(len(i["slices"]) for i in report["items"])
    out = [f"# Work by {who} · {report['since']} to {report['until']}", ""]
    if not report["items"] and not report["in_progress"] and who.lower() not in (o.lower() for o in report["owners"]):
        out.append(f"No slice names {who} as its owner. Owners: {', '.join(report['owners']) or 'none yet'}.")
    else:
        out.append(f"{count} slice{'s' if count != 1 else ''} closed, under {len(report['items'])} "
                   f"item{'s' if len(report['items']) != 1 else ''}." if count else "Nothing closed in this range.")
    for i in report["items"]:
        out += ["", f"## {i['id']} {i['title']}", "", f"{i['type']} · {i['progress']} · {' › '.join(i['part_of']) or '—'}", ""]
        out += [f"- {s['id']} {s['title']} — closed {s['closed']}" for s in i["slices"]]
        if i["others"]:
            out.append("- also closed here: " + ", ".join(f"{n} by {o}" if o else f"{n} with no owner"
                                                          for o, n in i["others"].items()))
    if report["in_progress"]:
        out += ["", "## In progress now", ""]
        out += [f"- {s['id']} {s['title']} — {s['state']} · {s['parent']}" for s in report["in_progress"]]
    notes = []
    if report["unowned"]:
        notes.append(f"{len(report['unowned'])} slice{'s' if len(report['unowned']) != 1 else ''} closed in this range "
                     f"name{'s' if len(report['unowned']) == 1 else ''} no owner, so may be missing here: "
                     f"{', '.join(report['unowned'])} — `owners --from-prs` fills them from their pull requests")
    if report["undated"]:
        one = len(report["undated"]) == 1
        notes.append(f"{len(report['undated'])} of {who}'s closed slices {'has' if one else 'have'} no `closed:` date "
                     f"and {'is' if one else 'are'} left out: "
                     + ", ".join(report["undated"]))
    if notes:
        out += ["", "## Not counted", ""] + [f"- {n}" for n in notes]
    return "\n".join(out)


def fill_owners(project: Project, prs: list, replace: bool = False, dry: bool = False) -> dict:
    """Once, for slices opened before `slice-open` set `owner:`: each open or closed slice's owner from
    its pull request's author (`gh pr list --state all --json number,author`) — a member's name by
    their login, solo the author's name. With `replace`, an owner the author contradicts is changed too."""
    authors = {}
    for pr in prs if isinstance(prs, list) else []:
        author = pr.get("author") if isinstance(pr, dict) else None
        if isinstance(author, dict) and str(pr.get("number", "")).isdigit():
            authors[int(pr["number"])] = author
    out = {"filled": [], "replaced": [], "differs": [], "unknown": [], "no_pr": []}
    for s in sorted(project.of_type("slice"), key=lambda s: natural_key(s.id)):
        if s.state not in ("open", "closed"):
            continue
        pr = str(s.fm.get("pr", "")).lstrip("#")
        author = authors.get(int(pr)) if pr.isdigit() else None
        if author is None:
            if not owner_of(s):
                out["no_pr"].append(s.id if not pr.isdigit() else f"{s.id} (PR #{pr} not in the list)")
            continue
        login = str(author.get("login") or "")
        if members(project):
            found = member_named(project, login)
            name = found["name"] if found else ""
        else:
            name = str(author.get("name") or "").strip() or login
        if not name:
            if not owner_of(s):
                out["unknown"].append(f"{s.id} (PR #{pr} by {login})")
            continue
        now = owner_of(s)
        if now and now.lower() == name.lower():
            continue
        if now and not replace:
            out["differs"].append(f"{s.id}: {now}, PR #{pr} by {name}")
            continue
        out["replaced" if now else "filled"].append(f"{s.id}: {name}" + (f" (was {now})" if now else ""))
        if not dry:
            write(s.doc, set_fields(s.text, {"owner": name}))
    return out


def index_block(project: Project, index_path: str) -> str:
    folder = os.path.dirname(index_path)
    lines = []
    for name in sorted(os.listdir(native(folder)), key=natural_key):
        path = os.path.join(folder, name)
        target = None
        if name.endswith(".md") and name != "INDEX.md":
            target = path
        elif os.path.isdir(native(path)) and os.path.isfile(native(os.path.join(path, "INDEX.md"))):
            target = os.path.join(path, "INDEX.md")
        if not target:
            continue
        fm, _, _ = parse_front_matter(read(target))
        fm = fm or {}
        title = fm.get("title") or name
        if fm.get("id") and not title.startswith(fm["id"]):
            title = f"{fm['id']} {title}"
        summary = fm.get("summary", "")
        if not summary and target != path:
            # A folder's own index: its count says enough, and setup writes these by the dozen.
            count = sum(1 for n in os.listdir(native(path)) if n != "INDEX.md" and (n.endswith(".md") or os.path.isdir(native(os.path.join(path, n)))))
            summary = f"{count} entr{'y' if count == 1 else 'ies'}"
        if not summary:
            project.problem(target, 1, "no `summary` in front-matter — the index line needs one", "warning")
        rel = os.path.relpath(target, folder).replace(os.sep, "/")
        lines.append(f"- [{title}]({rel})" + (f" — {summary}" if summary else ""))
    return "\n".join(lines) or "_Nothing here yet._"


def block_makers(project: Project) -> dict:
    """{absolute path: [(block, make, required)]} — every generated block and what fills it.
    `make()` builds the content, so `serve` builds only the blocks of the page it shows."""
    out = {}

    def add(path: str, name: str, make, required: bool):
        out.setdefault(path, []).append((name, make, required))

    for item in project.items.values():
        if item.folder:
            add(item.doc, "children", lambda i=item: children_block(project, i), True)
        if item.type == "story":
            add(item.doc, "proof", lambda i=item: proof_block(project, i), True)
    roadmap = os.path.join(project.plan_dir, "README.md")
    add(roadmap, "children", lambda: top_block(project, roadmap, False), True)
    front = os.path.join(project.spry, "README.md")
    add(front, "children", lambda: top_block(project, front, True), False)
    cover = os.path.join(project.spry, "COVERAGE.md")
    add(cover, "coverage", lambda: coverage_block(project, cover), True)
    queue = os.path.join(project.spry, "BACKLOG.md")
    add(queue, "backlog", lambda: backlog_block(project, queue), True)
    finish = os.path.join(project.spry, "DONE.md")
    add(finish, "done", lambda: done_block(project, finish), True)
    for dirpath, dirnames, filenames in walk_dir(os.path.join(project.spry, "knowledge")):
        dirnames[:] = [d for d in dirnames if not d.startswith(".")]
        if "INDEX.md" in filenames:
            path = os.path.join(dirpath, "INDEX.md")
            add(path, "index", lambda p=path: index_block(project, p), True)
    return out


def index(project: Project, dry: bool):
    """Regenerate every marker block. Returns the files that changed (or would)."""
    changed = []
    for path, blocks in block_makers(project).items():
        for name, make, required in blocks:
            if not os.path.isfile(native(path)):
                continue
            text = read(path)
            new = replace_block(text, name, make())
            if new is None:
                if required:
                    project.problem(path, 1, f"no `<!-- spry:{name} -->` block to fill", "warning")
                continue
            if new != text:
                changed.append(project.rel(path))
                if not dry:
                    write(path, new)
    return sorted(changed)


# ---------------------------------------------------------------- status

STATUS_LINES = 100


def status(project: Project, level: str | None, item_id: str | None = None, everything: bool = False):
    """The tree with done/total. With no level, as deep as fits in STATUS_LINES — a big plan is read
    top down, one branch at a time — unless `everything`."""
    if level and level not in project.levels:
        raise SystemExit(f"unknown level `{level}` — one of {', '.join(project.levels)}")
    if item_id and item_id not in project.items:
        raise SystemExit(f"no item {item_id}")
    roots = [project.items[item_id]] if item_id else project.top
    if level or everything:
        return status_tree(project, roots, project.levels.index(level) if level else None)
    full = status_tree(project, roots, None)
    if full.count("\n") < STATUS_LINES:
        return full
    for stop in range(len(project.levels) - 1, -1, -1):
        cut = status_tree(project, roots, stop)
        if cut.count("\n") < STATUS_LINES or stop == 0:
            deeper = project.levels[stop + 1] if stop + 1 < len(project.levels) else "slices"
            return (cut + f"\n\n(down to {project.levels[stop]}s, to fit {STATUS_LINES} lines; deeper: "
                    f"`status <ID>` for one branch, `--level {deeper}`, or `--all` for all "
                    f"{full.count(chr(10)) + 1} lines)")
    return full


def status_tree(project: Project, roots: list, stop: int | None) -> str:
    out = []

    def show(item: Item, depth: int):
        if stop is not None and item.type in project.levels and project.levels.index(item.type) > stop:
            return
        if stop is not None and item.type == "slice":
            return
        name = item.label if item.type in project.levels else f"{item.type} {item.label}"
        out.append(f"{'  ' * depth}{name[:60]:<{max(8, 62 - 2 * depth)}}{project.progress(item)}")
        order = {"task": 1, "bug": 2}
        for child in sorted(item.children, key=lambda c: order.get(c.type, 0)):
            show(child, depth + 1)

    for item in roots:
        show(item, 0)
    return "\n".join(out) or "No plan yet — spry/plan/ is empty."


# ---------------------------------------------------------------- related

def plan_paths(text: str):
    body = section_lines(text, "Plan") or []
    return {p for _, line in body for p in re.findall(r"`([^`\s]+[/.][^`\s]*)`", line.split(" — ")[0])}


def related(project: Project, target_path: str, limit: int = 8):
    target_path = os.path.abspath(target_path)
    if not os.path.isfile(native(target_path)):
        raise SystemExit(f"no such file: {target_path}")
    item = next((i for i in project.items.values() if i.doc == target_path), None)
    text = read(target_path)
    out, listed = [], set()

    def section(title, rows):
        out.append(f"## {title}")
        out.extend(rows or ["- none"])
        out.append("")

    if item:
        chain = item.ancestors()
        section("Parents", [f"- {p.label} — {project.rel(p.doc)}" for p in chain])
        listed.update(p.id for p in chain)
        siblings = [c for c in (item.parent.children if item.parent else project.top)
                    if c is not item and c.type == item.type]
        section("Siblings", [f"- {s.label} ({s.state}) — {project.rel(s.doc)}" for s in siblings])
        listed.update(s.id for s in siblings)
        listed.add(item.id)

    docs = [i for i in project.items.values() if i.id not in listed]
    corpus = {i.id: tokens(strip_blocks(i.text)) for i in project.items.values()}
    df: dict[str, int] = {}
    for words in corpus.values():
        for w in set(words):
            df[w] = df.get(w, 0) + 1
    n = max(1, len(corpus))

    def vector(words):
        v: dict[str, float] = {}
        for w in words:
            v[w] = v.get(w, 0) + 1
        return {w: c * math.log(1 + n / df.get(w, 1)) for w, c in v.items()}

    mine = vector(tokens(strip_blocks(text)))
    norm = math.sqrt(sum(x * x for x in mine.values())) or 1
    scored = []
    for d in docs:
        theirs = vector(corpus[d.id])
        dot = sum(mine.get(w, 0) * x for w, x in theirs.items())
        score = dot / (norm * (math.sqrt(sum(x * x for x in theirs.values())) or 1))
        if score > 0.05:
            scored.append((score, d))
    scored.sort(key=lambda p: -p[0])
    section("Similar text", [f"- {d.label} ({d.state}) — {project.rel(d.doc)} · {s:.2f}" for s, d in scored[:limit]])

    _, banned = glossary(project)
    terms = sorted({t for _, t in banned})
    used = [t for t in terms if re.search(r"(?<!\w)" + re.escape(t) + r"(?!\w)", text, re.I)]
    section("Glossary terms used", [f"- {t}" for t in used])

    always = project.config.get("always_check", [])
    section("Always check", [f"- {p}" + ("" if os.path.exists(native(os.path.join(project.root, p))) else " (missing)") for p in always])

    ids = {item.id, *(p.id for p in item.ancestors())} if item else set()
    hits = []
    for d_id, path in project.decisions.items():
        fm, _, _ = parse_front_matter(read(path))
        affects = (fm or {}).get("affects") or []
        if ids & set(affects if isinstance(affects, list) else []):
            hits.append(f"- {d_id} {(fm or {}).get('title', '')} — {project.rel(path)}")
    section("Decisions affecting this", hits)

    if item and item.type == "slice":
        mine_paths = plan_paths(text)
        rows = []
        for s in project.of_type("slice"):
            if s is item or not claimed(s):
                continue
            shared = sorted(mine_paths & plan_paths(s.text))
            rows.append(f"- {s.label}" + ("" if s.state == "open" else " (claimed, no work order yet)")
                        + f" — {project.rel(s.doc)}" + (f" · same files: {', '.join(shared)}" if shared else ""))
        section("Open slices", rows)
    return "\n".join(out).rstrip() + "\n"


# ---------------------------------------------------------------- next

def next_id(project: Project, kind: str) -> str:
    if kind not in project.ids:
        raise SystemExit(f"unknown type `{kind}` — one of {', '.join(project.ids)}")
    prefix = project.ids[kind]
    if kind == "decision":
        nums = [int(d.split("-")[1]) for d in project.decisions]
    else:
        nums = [i.num for i in project.items.values() if i.type == kind]
        # Folders and files that failed to load still hold their number.
        taken = re.compile(r"^" + re.escape(prefix) + r"-(\d+)(?:-|\.md$|$)")
        for _dir, dirnames, filenames in walk_dir(project.plan_dir):
            nums += [int(m.group(1)) for n in dirnames + filenames if (m := taken.match(n))]
    return f"{prefix}-{max(nums, default=0) + 1}"


# ---------------------------------------------------------------- new

def link_slice(project: Project, slice_id: str, fields: dict) -> str:
    """Set front-matter fields on a slice — `branch`, `pr`, `issue`, `owner` — in place. Returns the file."""
    item = project.items.get(slice_id)
    if item is None or item.type != "slice":
        raise SystemExit(f"no slice {slice_id}")
    if not fields:
        raise SystemExit("nothing to set — give --branch, --pr, --issue or --owner")
    for key in ("pr", "issue"):
        if key in fields:
            fields[key] = str(fields[key]).lstrip("#")
            if not fields[key].isdigit():
                raise SystemExit(f"`{key}` is a number, not {fields[key]!r}")
    write(item.doc, set_fields(item.text, fields))
    return item.doc


def set_fields(text: str, fields: dict) -> str:
    """The document with these front-matter fields set — replaced where present, added at the end."""
    lines = text.split("\n")
    end = next(i for i in range(1, len(lines)) if lines[i].strip() == "---")
    for key, value in fields.items():
        at = next((i for i in range(1, end) if lines[i].split(":", 1)[0] == key), None)
        if at is None:
            lines.insert(end, f"{key}: {value}".rstrip())
            end += 1
        else:
            lines[at] = f"{key}: {value}".rstrip()
    return "\n".join(lines)


def slugify(title: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    if len(slug) > 20:  # a bug's slice six slugs deep, three-digit IDs, stays under `LONG_PATH`
        slug = slug[:20].rsplit("-", 1)[0]
    return slug or "untitled"


def fill_template(template: str, kind: str, ident: str, title: str, owner: str | None, today: str) -> str:
    lines = template.split("\n")
    if lines and lines[0].strip() == "---":
        for i in range(1, len(lines)):
            if lines[i].strip() == "---":
                break
            key = lines[i].split(":", 1)[0]
            value = {"id": ident, "title": title, "state": "planned" if kind == "slice" else "draft",
                     "covers": "[]", "breaks": "[]", "branch": "", "pr": "", "closed": "", "date": today}.get(key)
            if key == "owner" and owner:
                value = owner
            if value is not None:
                lines[i] = f"{key}: {value}".rstrip()
    for i, line in enumerate(lines):
        if line.startswith("# "):
            lines[i] = f"# {ident} · {title}"
            break
    return "\n".join(lines)


DOCUMENT_KINDS = ("checks", "convention", "external", "audit")


def ensure_index(project: Project, folder: str, name: str):
    """An INDEX.md for a knowledge folder, from the template, when there is none yet."""
    path = os.path.join(folder, "INDEX.md")
    if not os.path.exists(native(path)):
        template = read(os.path.join(project.spry, "process", "templates", "index.md"))
        write(path, template.replace("<folder> index", f"{name} index").replace("# <folder>", f"# {name}"))


def new_document(project: Project, kind: str, parent_id: str | None, title: str,
                 dependency: str | None, today: str) -> str:
    """Create a knowledge or QA document — no ID of its own — from its template."""
    template = read(os.path.join(project.spry, "process", "templates", f"{kind}.md"))
    knowledge = os.path.join(project.spry, "knowledge")
    if kind == "checks":
        story = project.items.get(parent_id or "")
        if story is None or story.type != "story":
            raise SystemExit("checks need --parent: a story")
        path = os.path.join(story.folder, "checks.md")
        text = template.replace("S-<n>", story.id).replace("<story title>", story.title)
    elif kind == "convention":
        folder = os.path.join(knowledge, "conventions")
        os.makedirs(native(folder), exist_ok=True)
        ensure_index(project, folder, "Conventions")
        path = os.path.join(folder, f"{slugify(title)}.md")
        text = template.replace("<area>", title)
    elif kind == "external":
        if not dependency:
            raise SystemExit("an external behaviour needs --dependency: the service it is about")
        folder = os.path.join(knowledge, "external", slugify(dependency))
        os.makedirs(native(folder), exist_ok=True)
        ensure_index(project, folder, dependency)
        path = os.path.join(folder, f"{slugify(title)}.md")
        text = (template.replace("<dependency>", dependency).replace("<behaviour, as a statement>", title)
                .replace("<behaviour>", title).replace("observed: <YYYY-MM-DD>", f"observed: {today}")
                .replace("dependency: <name>", f"dependency: {dependency}").replace("affects: [<item IDs>]", "affects: []"))
    else:
        folder = os.path.join(knowledge, "audits")
        os.makedirs(native(folder), exist_ok=True)
        ensure_index(project, folder, "Audits")
        path = os.path.join(folder, f"{today}-{slugify(title)}.md")
        text = re.sub(r"(?m)^title: .*$", f"title: {title}", template, count=1)
        text = text.replace("date: <YYYY-MM-DD>", f"date: {today}").replace("# <title>", f"# {title}")
    if os.path.exists(native(path)):
        raise SystemExit(f"{project.rel(path)} already exists — edit it instead")
    write(path, text)
    return path


def new_item(project: Project, kind: str, parent_id: str | None, title: str,
             owner: str | None = None, today: str | None = None, dependency: str | None = None) -> str:
    """Create an item from its template at the right place with the next ID. Returns the path."""
    if kind in DOCUMENT_KINDS:
        return new_document(project, kind, parent_id, title, dependency, today or date.today().isoformat())
    if kind not in project.ids:
        raise SystemExit(f"unknown type `{kind}` — one of {', '.join([*project.ids, *DOCUMENT_KINDS])}")
    template = os.path.join(project.spry, "process", "templates", f"{kind}.md")
    if not os.path.isfile(native(template)):
        raise SystemExit(f"no template {project.rel(template)} — bring the process in with `vendor`")
    ident, slug = next_id(project, kind), slugify(title)
    parent = None
    if parent_id:
        parent = project.items.get(parent_id)
        if parent is None:
            raise SystemExit(f"no item {parent_id} in the plan")
    if kind == "decision":
        folder = os.path.join(project.spry, "knowledge", "decisions")
        os.makedirs(native(folder), exist_ok=True)
        path = os.path.join(folder, f"{ident}-{slug}.md")
    elif kind == "slice":
        if parent is None or parent.type not in ("story", "task", "bug"):
            raise SystemExit("a slice needs --parent: a story, task or bug")
        path = os.path.join(parent.folder, f"{ident}-{slug}.md")
    else:
        container = {"task": "tasks", "bug": "bugs"}.get(kind)
        if not project._placed_well(kind, parent, container):
            where = f"{parent.type} {parent.id}" if parent else "the top of the plan (pass --parent)"
            raise SystemExit(f"a {kind} cannot sit under {where}")
        base = parent.folder if parent else project.plan_dir
        folder = os.path.join(base, container, f"{ident}-{slug}") if container else os.path.join(base, f"{ident}-{slug}")
        os.makedirs(native(folder))
        path = os.path.join(folder, "README.md")
    if os.path.exists(native(path)):
        raise SystemExit(f"{project.rel(path)} already exists")
    write(path, fill_template(read(template), kind, ident, title, owner, today or date.today().isoformat()))
    return path


# ---------------------------------------------------------------- mint and claim on the main branch

# With `"mint": "main"` the main branch on the remote is the counter and the push is the lock: an ID
# is taken, and a slice claimed, by a commit pushed straight to it. Two sessions racing both build on
# the same tip; one push is refused as behind, and that one fetches, recomputes and tries again.
# `"mint": "local"` (the default) takes the next number in this tree.
#
# Neither way loads the plan: the next number, the parent and the slice come from the plan's file
# names (`Names`), and only the files written are opened. On the main branch the commit is made with
# git's plumbing from the fetched tip — nothing is checked out — so where a virus scanner reads every
# file opened, `new` costs the network and little else (Pulse: a minute before, mostly file opens).

REMOTE = "origin"
MAIN_TRIES = 5


def mint_mode(project: Project) -> str:
    mode = project.config.get("mint", "local")
    if mode not in ("main", "local"):
        raise SystemExit(f"`mint` is `{mode}` in spry/spry.config.json — one of main, local")
    return mode


def main_branch(project: Project) -> str:
    return project.config.get("main_branch", "main")


def remote_tip(project: Project, main: str) -> str | None:
    """The main branch's commit on the remote now, or None when the remote cannot be read."""
    done = git(project.root, "ls-remote", REMOTE, f"refs/heads/{main}")
    return done.stdout.split()[0] if done.returncode == 0 and done.stdout.strip() else None


def last_line(done: subprocess.CompletedProcess) -> str:
    lines = [l.strip() for l in (done.stderr or done.stdout).splitlines() if l.strip()]
    return lines[-1] if lines else f"exit {done.returncode}"


class Names:
    """The plan and the decisions by file name alone — from `git ls-tree` at a commit, or from the
    folders of this tree — plus `read` for the few files `new`, `claim` and `release` open."""

    def __init__(self, project: Project, commit: str | None = None):
        self.project, self.commit = project, commit
        self.cache: dict = {}
        if commit:
            self.top = git(project.root, "rev-parse", "--show-toplevel").stdout.strip()
            self.prefix = git_prefix(project.root)
            done = git(self.top, "ls-tree", "-r", "-z", "--name-only", f"{commit}:{self.prefix}spry")
            self.files = {"spry/" + n for n in done.stdout.split("\0") if n}
            self.dirs = {d for f in self.files for d in parents(f)}
        else:
            self.files, self.dirs = set(), set()
            for top in (project.plan_dir, os.path.join(project.spry, "knowledge", "decisions")):
                for dirpath, dirnames, filenames in walk_dir(top):
                    self.files |= {project.rel(os.path.join(dirpath, f)) for f in filenames}
                    self.dirs |= {project.rel(os.path.join(dirpath, d)) for d in dirnames}
            self.dirs |= {d for f in self.files for d in parents(f)}

    def read(self, rel: str) -> str | None:
        if rel not in self.cache:
            if self.commit:
                done = git(self.top, "cat-file", "blob", f"{self.commit}:{self.prefix}{rel}")
                self.cache[rel] = done.stdout if done.returncode == 0 else None
            else:
                path = os.path.join(self.project.root, rel)
                self.cache[rel] = read(path) if os.path.isfile(native(path)) else None
        return self.cache[rel]

    def exists(self, rel: str) -> bool:
        if rel in self.files or rel in self.dirs:
            return True
        if rel.startswith(("spry/",) if self.commit else ("spry/plan/", "spry/knowledge/decisions/")):
            return False  # listed in full above
        if self.commit:
            return git(self.top, "cat-file", "-e", f"{self.commit}:{self.prefix}{rel}").returncode == 0
        return os.path.exists(native(os.path.join(self.project.root, rel)))

    def located(self) -> dict:
        """{ID: [(type, document, folder or None)]}, paths from the project root."""
        p, out = self.project, {}
        for rel in sorted(self.files):
            if not rel.startswith("spry/plan/") or any(n.startswith(".") for n in rel.split("/")):
                continue  # as the plan loads: hidden folders are not part of it
            head, name = rel.rsplit("/", 1)
            if name == "README.md":
                m = p.item_dir.match(head.rsplit("/", 1)[-1])
                kind = p.type_of_prefix.get(m.group(1)) if m else None
                if kind not in (None, "slice", "decision"):
                    out.setdefault(f"{m.group(1)}-{m.group(2)}", []).append((kind, rel, head))
            elif m := p.slice_file.match(name):
                out.setdefault(f"{p.ids['slice']}-{m.group(1)}", []).append(("slice", rel, None))
        return out

    def numbers(self, kind: str) -> set:
        """Every number of this type a name holds — an item that fails to load still holds its own."""
        prefix = re.escape(self.project.ids[kind])
        if kind == "decision":
            taken = re.compile(r"^" + prefix + r"-(\d+)\b.*\.md$")
            names = [f.rsplit("/", 1)[1] for f in self.files if f.startswith("spry/knowledge/decisions/")]
        else:
            taken = re.compile(r"^" + prefix + r"-(\d+)(?:-|\.md$|$)")
            names = {n for f in self.files | self.dirs if f.startswith("spry/plan/") for n in f.split("/")[2:]}
        return {int(m.group(1)) for n in names if (m := taken.match(n))}


def parents(rel: str):
    while "/" in rel:
        rel = rel.rsplit("/", 1)[0]
        yield rel


def batch_entries(raw) -> list:
    """`new --batch`: a JSON list of {type, title, parent?, owner?, key?}. `parent` names an item in
    the plan or the `key` of an earlier entry."""
    if not isinstance(raw, list) or not raw:
        raise SystemExit("--batch takes a JSON list of {type, title, parent, owner, key}")
    keys, out = set(), []
    for n, entry in enumerate(raw, 1):
        if not isinstance(entry, dict) or set(entry) - {"type", "title", "parent", "owner", "key"}:
            raise SystemExit(f"--batch entry {n}: an object with type, title and optionally parent, owner, key")
        if not all(isinstance(entry.get(k), str) and entry[k].strip() for k in ("type", "title")) \
                or not all(isinstance(entry.get(k), (str, type(None))) for k in ("parent", "owner")):
            raise SystemExit(f"--batch entry {n}: `type` and `title` are needed, and every value is a string")
        key = entry.get("key")
        if key is not None:
            if not isinstance(key, str) or re.fullmatch(r"[A-Z]+-\d+", key) or key in keys:
                raise SystemExit(f"--batch entry {n}: `key` {key!r} must be unique and not look like an ID")
            keys.add(key)
        out.append({k: entry.get(k) for k in ("type", "title", "parent", "owner", "key")})
    for n, entry in enumerate(out, 1):
        later = {e["key"] for e in out[n:]}
        if entry["parent"] and entry["parent"] in later and entry["parent"] not in {e["key"] for e in out[:n - 1]}:
            raise SystemExit(f"--batch entry {n}: its parent `{entry['parent']}` comes later — put parents first")
    return out


def plan_new(project: Project, names: Names, entries: list, missing) -> list:
    """[(ID, title, path from the root, text)] for each entry, numbered on from `names` in order —
    nothing written. `missing(parent)` is the refusal for a parent the plan does not have."""
    today, made, keyed, numbers, templates = date.today().isoformat(), [], {}, {}, {}
    located = names.located()
    for entry in entries:
        kind, title, parent_id, owner = entry["type"], entry["title"].strip(), entry["parent"], entry["owner"]
        if kind in DOCUMENT_KINDS:
            raise SystemExit(f"a {kind} has no ID of its own — `new {kind}` makes one at a time")
        if kind not in project.ids:
            raise SystemExit(f"unknown type `{kind}` — one of {', '.join([*project.ids, *DOCUMENT_KINDS])}")
        if kind not in templates:
            templates[kind] = names.read(f"spry/process/templates/{kind}.md")
            if templates[kind] is None:
                raise SystemExit(f"no template spry/process/templates/{kind}.md — bring the process in with `vendor`")
            numbers[kind] = names.numbers(kind)
        parent = None
        if parent_id:
            if parent_id in keyed:
                parent = keyed[parent_id]
            else:
                found = [Item(t, parent_id, 0, doc, folder, {}, "", 0) for t, doc, folder in located.get(parent_id, [])]
                if not found:
                    raise SystemExit(missing(parent_id))
                if len(found) > 1:
                    raise SystemExit(f"{parent_id} is {' and '.join(i.doc for i in found)} — `check` names the "
                                     f"one to rename; fix that first")
                parent = found[0]
        num = max(numbers[kind], default=0) + 1
        numbers[kind].add(num)
        ident, slug = f"{project.ids[kind]}-{num}", slugify(title)
        if kind == "decision":
            path = f"spry/knowledge/decisions/{ident}-{slug}.md"
        elif kind == "slice":
            if parent is None or parent.type not in ("story", "task", "bug"):
                raise SystemExit("a slice needs --parent: a story, task or bug")
            path = f"{parent.folder}/{ident}-{slug}.md"
        else:
            container = {"task": "tasks", "bug": "bugs"}.get(kind)
            if not project._placed_well(kind, parent, container):
                where = f"{parent.type} {parent.id}" if parent else "the top of the plan (pass --parent)"
                raise SystemExit(f"a {kind} cannot sit under {where}")
            folder = "/".join(filter(None, (parent.folder if parent else "spry/plan", container, f"{ident}-{slug}")))
            path = f"{folder}/README.md"
        folder = os.path.dirname(path) if path.endswith("/README.md") else None
        if names.exists(folder or path):
            raise SystemExit(f"{folder or path} already exists")
        if entry["key"]:
            keyed[entry["key"]] = Item(kind, ident, num, path, folder, {}, "", 0)
        made.append((ident, title, path, fill_template(templates[kind], kind, ident, title, owner, today)))
    return made


def check_new(project: Project, names: Names, files: dict):
    """`check` of the files about to be written, by their text, before anything is written: the rest
    of the plan is not loaded, and a template, title or glossary that fails stops here."""
    gloss = project.config.get("glossary", "spry/knowledge/glossary.md")
    text = names.read(gloss)
    banned_res = banned_patterns(glossary_terms(text) if text else [])
    budgets = budget_patterns(project)

    def exists(path: str) -> bool:
        rel = project.rel(path)
        return rel in files or any(f.startswith(rel + "/") for f in files) or names.exists(rel)

    project.problems = []
    for rel, text in files.items():
        path = os.path.join(project.root, rel)
        fm, _start, errors = parse_front_matter(text)
        for line, message in errors:
            project.problem(path, line, message)
        for key in ("id", "title", "state"):
            if not (fm or {}).get(key):
                project.problem(path, 1, f"front-matter has no `{key}`")
        check_text(project, path, text, fm or {}, banned_res, budgets, os.path.join(project.root, gloss), exists)
    mine = [p for p in project.problems if p.level == "error"]
    if mine:
        raise SystemExit("the new item fails `check` — nothing written:\n" + "\n".join(map(str, mine)))


def mid_operation(project: Project) -> str | None:
    """Why a merge into this tree would fail now — checked before anything is pushed."""
    for name, what in (("MERGE_HEAD", "a merge"), ("rebase-merge", "a rebase"), ("rebase-apply", "a rebase"),
                       ("CHERRY_PICK_HEAD", "a cherry-pick")):
        path = git(project.root, "rev-parse", "--git-path", name).stdout.strip()
        if path and os.path.exists(native(os.path.join(project.root, path))):
            return f"{what} is in progress — finish it first"
    if git(project.root, "diff", "--cached", "--quiet").returncode != 0:
        return "files are staged — commit or unstage them first"
    return None


NO_HOOKS = ("-c", f"core.hooksPath={os.devnull}")


def commit_on(names: Names, files: dict, message: str) -> subprocess.CompletedProcess:
    """A commit on `names.commit` with `files` (paths from the project root) written — by plumbing,
    in an index of its own: no worktree, no checkout, no hook, and nothing here changes."""
    folder = tempfile.mkdtemp(prefix="spry-index-")
    try:
        env = {**os.environ, "GIT_INDEX_FILE": os.path.join(folder, "index")}
        done = git(names.top, "read-tree", names.commit, env=env)
        entries = []
        for rel, text in files.items():
            if done.returncode != 0:
                return done
            done = git(names.top, "hash-object", "-w", "--stdin", input=text)
            entries.append(f"100644 {done.stdout.strip()}\t{names.prefix}{rel}")
        for args, given in ((("update-index", "--add", "--index-info"), "\n".join(entries) + "\n"),
                            (("write-tree",), None)):
            if done.returncode != 0:
                return done
            done = git(names.top, *args, input=given, env=env)
        if done.returncode != 0:
            return done
        subject, _, body = message.partition("\n\n")
        return git(names.top, "commit-tree", done.stdout.strip(), "-p", names.commit, "-m", subject,
                   *(("-m", body) if body else ()))
    finally:
        shutil.rmtree(folder, ignore_errors=True)


def pushed(done: subprocess.CompletedProcess, main: str) -> bool:
    """Did `push --porcelain` update the main branch? Its line starts with a flag: ` ` fast-forward,
    `*` new, `=` up to date; `!` is refused."""
    lines = [l.split("\t") for l in done.stdout.splitlines()]
    return done.returncode == 0 and any(len(l) >= 2 and l[0] in (" ", "*", "+", "=")
                                        and l[1].endswith(f":refs/heads/{main}") for l in lines)


def push_said(done: subprocess.CompletedProcess) -> str:
    refused = [l.split("\t")[2] for l in done.stdout.splitlines() if l.startswith("!\t") and l.count("\t") >= 2]
    return refused[0] if refused else last_line(done)


def on_main(project: Project, step, ready=None) -> tuple:
    """Run `step(names of the remote main branch)`, which returns (result, commit message, {path:
    text}), commit those files on that tip and push it to the main branch — again from a fresh fetch
    when the remote moved under the push. `ready(tip)` runs after each fetch and may refuse before
    anything is written. `names.project` carries the main branch's config. Returns (step's result,
    the pushed commit, tries). Nothing is written to this tree, and no shared ref is written: two
    worktrees of one clone can mint at once."""
    main = main_branch(project)
    if git(project.root, "rev-parse", "--show-toplevel").returncode != 0:
        raise SystemExit("`mint: main` needs a git repository — set `mint` to local in spry/spry.config.json")
    url = git(project.root, "remote", "get-url", REMOTE).stdout.strip()
    if not url:
        raise SystemExit(f"no remote `{REMOTE}` — nothing written. `mint: main` takes IDs from {REMOTE}/{main}")
    for attempt in range(1, MAIN_TRIES + 1):
        # By URL, into FETCH_HEAD alone: FETCH_HEAD is per worktree, while a fetch from the named remote
        # also updates refs/remotes/…, shared by every worktree, which fails to lock when two fetch at once.
        done = git(project.root, "fetch", "-q", url, f"refs/heads/{main}")
        tip = git(project.root, "rev-parse", "-q", "--verify", "FETCH_HEAD^{commit}").stdout.strip()
        if done.returncode != 0 or not tip:
            raise SystemExit(f"cannot fetch `{main}` from {REMOTE} ({last_line(done)}) — nothing written. "
                             f"The ID comes from {REMOTE}/{main}; never from this tree alone while `mint` is main")
        if ready:
            ready(tip)
        names = Names(project, tip)
        config = names.read("spry/spry.config.json")
        if config is None:
            raise SystemExit(f"spry is not on {REMOTE}/{main} yet — nothing written. Keep `mint` local "
                             f"until the setup is merged; IDs are taken on {main} after that")
        try:
            config = json.loads(config)
        except json.JSONDecodeError as e:
            raise SystemExit(f"spry/spry.config.json on {REMOTE}/{main} is not valid JSON: {e} — nothing written")
        if not isinstance(config, dict):
            raise SystemExit(f"spry/spry.config.json on {REMOTE}/{main} is not a JSON object — nothing written")
        names.project = Project(project.root, load=False, config=config)
        result, message, files = step(names)
        done = commit_on(names, files, message)
        if done.returncode != 0:
            raise SystemExit(f"cannot commit on {main}: {last_line(done)} — nothing written")
        commit = done.stdout.strip()
        done = git(project.root, *NO_HOOKS, "push", "--porcelain", "--no-verify", url, f"{commit}:refs/heads/{main}")
        if pushed(done, main):
            return result, commit, attempt
        # Judge a failure by where the remote stands, not by the message: a race reads "fetch first",
        # "non-fast-forward" or "cannot lock ref" depending on timing and host.
        now = remote_tip(project, main)
        if now == commit:
            return result, commit, attempt
        if now is None:
            raise SystemExit(f"cannot reach {REMOTE} to push `{main}` ({push_said(done)}) — nothing written")
        if now == tip:
            raise SystemExit(f"{REMOTE} refused the push to `{main}` ({push_said(done)}) — nothing written. "
                             f"A project that never commits to {main} directly sets `mint` to local")
        print(f"{main} moved while writing — fetching and trying again ({attempt}/{MAIN_TRIES})", file=sys.stderr)
    raise SystemExit(f"`{main}` moved under every one of {MAIN_TRIES} pushes — nothing written; try again")


def can_bring_in(project: Project):
    """A check for `on_main(ready=…)`: refuse before pushing when the pushed commit could not be merged here."""
    main = main_branch(project)

    def ready(tip: str):
        why = mid_operation(project)
        here = git(project.root, "symbolic-ref", "-q", "--short", "HEAD").stdout.strip()
        if not why and here == main and git(project.root, "merge-base", "--is-ancestor", "HEAD", tip).returncode != 0:
            why = f"your `{main}` has commits {REMOTE}/{main} does not — push them, or `git pull --rebase`, first"
        if why:
            raise SystemExit(f"nothing written: {why}. The new item is merged in here after it is pushed")
    return ready


def bring_in(project: Project, commit: str, what: str):
    """Merge the pushed commit into this branch, so the file is here to edit and a later edit of it
    never meets the main branch's copy as a second, different addition."""
    main = main_branch(project)
    here = git(project.root, "symbolic-ref", "-q", "--short", "HEAD").stdout.strip()
    args = ["merge", "-q", "--ff-only", commit] if here == main else ["merge", "-q", "--no-edit", "--no-verify", commit]
    done = git(project.root, *args)
    if done.returncode != 0:
        if git(project.root, "rev-parse", "-q", "--verify", "MERGE_HEAD").returncode == 0:
            git(project.root, "merge", "--abort")
        raise SystemExit(f"{what} is on {REMOTE}/{main} ({commit[:7]}) — do not create it again — but bringing it "
                         f"into `{here or 'HEAD'}` failed: {last_line(done)}. Commit or stash, then `git merge {commit[:12]}`")


def mint(project: Project, kind: str, parent_id: str | None, title: str, owner: str | None = None,
         dependency: str | None = None) -> str:
    """`new` of one item or document. Returns its path."""
    if kind in DOCUMENT_KINDS:
        return new_item(project, kind, parent_id, title, owner, dependency=dependency)
    return mint_batch(project, [{"type": kind, "title": title, "parent": parent_id, "owner": owner, "key": None}])[0]


def mint_batch(project: Project, entries: list) -> list:
    """`new`: items numbered on in order, checked, and written all together or not at all — with
    `mint: main` as one commit pushed to the remote main branch, then brought here. Returns the paths."""
    if mint_mode(project) == "local":
        names = Names(project)
        made = plan_new(project, names, entries, lambda parent: f"no item {parent} in the plan")
        check_new(project, names, {path: text for _, _, path, text in made})
        for _, _, path, text in made:
            os.makedirs(native(os.path.dirname(os.path.join(project.root, path))), exist_ok=True)
            write(os.path.join(project.root, path), text)
        return [os.path.join(project.root, path) for _, _, path, _ in made]
    main = main_branch(project)

    def step(names: Names):
        made = plan_new(names.project, names, entries,
                        lambda parent: f"{parent} is not on {REMOTE}/{main} yet — nothing written. Merge it first: "
                                       f"a new item takes its ID on {main}, so its parent must be there")
        files = {path: text for _, _, path, text in made}
        check_new(names.project, names, files)
        if len(made) == 1:
            message = f"docs(plan): new {made[0][0]} {made[0][1]}"
        else:
            message = (f"docs(plan): new {', '.join(i for i, _, _, _ in made)}\n\n"
                       + "\n".join(f"- {i} {t}" for i, t, _, _ in made))
        return made, message, files

    made, commit, _ = on_main(project, step, can_bring_in(project))
    bring_in(project, commit, ", ".join(i for i, _, _, _ in made))
    return [os.path.join(project.root, path) for _, _, path, _ in made]


def branch_of(item: Item) -> str:
    """A slice's `branch:` — empty while it is still the template's `<sl-n-slug>`."""
    branch = str(item.fm.get("branch") or "")
    return "" if branch.startswith("<") else branch


def holder(item: Item) -> str | None:
    """Who holds a slice, in words — None when it is free to open."""
    branch = branch_of(item)
    owner = f" by {item.fm['owner']}" if item.fm.get("owner") else ""
    if item.state == "open":
        return f"open on `{branch}`{owner}" if branch else "open"
    if item.state in ("closed", "dropped"):
        return item.state
    if branch:
        return f"claimed on `{branch}`{owner} — `release {item.id}` frees it"
    return None


def claimed(item: Item) -> bool:
    return item.type == "slice" and (item.state == "open" or (item.state == "planned" and bool(branch_of(item))))


def slice_branch(item: Item) -> str:
    return os.path.basename(item.doc)[:-3].lower()


def slice_named(names: Names, slice_id: str) -> Item | None:
    """The slice, read from its one file — None when the plan has no slice by that ID."""
    found = [doc for kind, doc, _ in names.located().get(slice_id, []) if kind == "slice"]
    if len(found) > 1:
        raise SystemExit(f"{slice_id} is {' and '.join(found)} — `check` names the one to rename; fix that first")
    text = names.read(found[0]) if found else None
    if text is None:
        return None
    fm, start, _ = parse_front_matter(text)
    return Item("slice", slice_id, int(slice_id.rsplit("-", 1)[1]), os.path.join(names.project.root, found[0]),
                None, fm or {}, text, start)


def claim(project: Project, slice_id: str, owner: str | None = None, switch: bool = True) -> str:
    """`slice-open`'s first step: with `mint: main`, set `branch:` on the slice on the remote main branch —
    refused when someone holds it — then cut the branch from that commit. Returns the branch."""
    main = main_branch(project)
    shared = mint_mode(project) == "main"

    def refuse(s: Item | None, where: str):
        if s is None:
            raise SystemExit(f"no slice {slice_id}{where}")
        taken = holder(s)
        if taken:
            raise SystemExit(f"{slice_id} is taken: {taken}")
        branch = slice_branch(s)
        if git(project.root, "rev-parse", "-q", "--verify", f"refs/heads/{branch}").returncode == 0:
            raise SystemExit(f"{slice_id} is taken: a branch `{branch}` exists here — someone opened it before "
                             f"claims, or a release left it. Delete it, or `link {slice_id} --branch {branch}`")
        if shared and git(project.root, "ls-remote", "--exit-code", "--heads", REMOTE, branch).returncode == 0:
            raise SystemExit(f"{slice_id} is taken: `{REMOTE}/{branch}` exists — someone is building it")
        return branch

    if shared and switch and git(project.root, "diff", "--quiet", "HEAD").returncode != 0:
        raise SystemExit("nothing written: this tree has uncommitted changes, and claim switches to a branch "
                         f"cut from {REMOTE}/{main} — commit or stash them, or pass --no-switch")
    if shared:
        def step(names: Names):
            s = slice_named(names, slice_id)
            branch = refuse(s, f" on {REMOTE}/{main} — merge the slices first")
            text = set_fields(s.text, {"branch": branch, **({"owner": owner} if owner else {})})
            return branch, f"docs(slice): claim {slice_id} for {branch}", {names.project.rel(s.doc): text}

        branch, start, _ = on_main(project, step)
    else:
        branch = refuse(slice_named(Names(project), slice_id), "")
        start = main if git(project.root, "rev-parse", "-q", "--verify", main).returncode == 0 else f"{REMOTE}/{main}"
    make = ["switch", "-q", "--no-track", "-c", branch, start] if switch else ["branch", "--no-track", branch, start]
    done = git(project.root, *make)
    if done.returncode != 0:
        raise SystemExit((f"{slice_id} is yours on {main} — do not claim it again — but " if shared else "")
                         + f"making `{branch}` failed: {last_line(done)}. Then: `git {' '.join(make[:1] + make[2:])}`")
    return branch


def release(project: Project, slice_id: str) -> str:
    """Give back a slice nobody is building: `planned` again, `branch:` empty — on the remote main
    branch with `mint: main`, in this tree otherwise. The branch itself is left for its owner."""
    main = main_branch(project)

    def free(names: Names):
        s = slice_named(names, slice_id)
        if s is None:
            raise SystemExit(f"no slice {slice_id}" + (f" on {REMOTE}/{main}" if names.commit else ""))
        if not claimed(s):
            raise SystemExit(f"{slice_id} is not held — " + (holder(s) or "planned, with no branch"))
        was = branch_of(s) or "no branch"
        text = set_fields(s.text, {"state": "planned", "branch": ""})
        return was, f"docs(slice): release {slice_id} from {was}", {names.project.rel(s.doc): text}

    if mint_mode(project) == "main":
        return on_main(project, free)[0]
    was, _, files = free(Names(project))
    for rel, text in files.items():
        write(os.path.join(project.root, rel), text)
    return was


# ---------------------------------------------------------------- pr-body

def pr_body(project: Project, slice_id: str, base: str | None = None) -> str:
    item = project.items.get(slice_id)
    if item is None or item.type != "slice":
        raise SystemExit(f"no slice {slice_id}")
    lines = item.text.split("\n")
    start = next((i for i in range(item.body_start, len(lines)) if lines[i].strip() == "## Work order"), None)
    if start is None:
        raise SystemExit(f"{project.rel(item.doc)} has no `## Work order` section")
    body = re.sub(r"<!-- guide:.*?-->\n?", "", "\n".join(lines[start:]), flags=re.S)
    body = re.sub(r"\n{3,}", "\n\n", body).strip()
    parent = f" · {item.parent.label}" if item.parent else ""
    issue = f" · issue #{item.fm['issue']}" if str(item.fm.get("issue", "")).isdigit() else ""
    review = reviewer_page(project, item, base)
    return f"**{item.label}**{parent} — `{project.rel(item.doc)}`{issue}\n\n{review}{body}\n"


def issue_body(project: Project, slice_id: str, close: bool = False) -> str:
    """The slice's issue: the work order as agreed, frozen and saying so — or, with `close`, the
    close summary, posted on the issue as a comment. The file stays the living version."""
    item = project.items.get(slice_id)
    if item is None or item.type != "slice":
        raise SystemExit(f"no slice {slice_id}")
    part = "Close summary" if close else "Work order"
    lines = item.text.split("\n")
    start = next((i for i in range(item.body_start, len(lines)) if lines[i].strip() == f"## {part}"), None)
    if start is None:
        raise SystemExit(f"{project.rel(item.doc)} has no `## {part}` section")
    end = next((i for i in range(start + 1, len(lines)) if lines[i].startswith("## ")), len(lines))
    body = re.sub(r"<!-- guide:.*?-->\n?", "", "\n".join(lines[start:end]), flags=re.S)
    body = re.sub(r"\n{3,}", "\n\n", body).strip()
    rel = project.rel(item.doc)
    if close:
        return f"**{item.label}** closed — `{rel}`\n\n{body}\n"
    return (f"> **This is `{rel}`'s work order as agreed on {time.strftime('%Y-%m-%d')}, and it is never "
            f"updated.** The file is the living version; where the two differ, the file is right.\n\n{body}\n")


def reviewer_page(project: Project, item: Item, base: str | None) -> str:
    """What a person must judge, on one screen: the criteria in words, what changed in them, what
    falsify could not show, and what QA checks by hand. Everything else is the work order below."""
    story = item.parent if item.parent and item.parent.type == "story" else None
    out = []
    if story:
        texts = ac_texts(story.text)
        for ac in item.fm.get("covers") or []:
            ref = f"{story.id}/{ac}"
            proven = len(project.tests.get(ref, []))
            state = f"{proven} test{'s' if proven != 1 else ''}" if proven else "**no test yet**"
            out.append(f"- `{ref}` — {texts.get(ac, '?').replace(' | ', ' · ')} — {state}")
    if base and git(project.root, "rev-parse", "--verify", "--quiet", f"{base}^{{commit}}").returncode == 0:
        for st, ac, old, new in criteria_edits(project, base):
            out.append(f"- **Changed:** `{st.id}/{ac}` \"{old}\" → " + (f"\"{new}\"" if new is not None else "removed"))
    rows = falsify_table(item)
    if rows:
        caught = sum(1 for r in rows if r[-1].strip().lower() == "caught")
        out.append(f"- **Falsify:** {caught} of {len(rows)} caught")
        out += [f"  - `{r[0]}` — {r[-1].strip()}" for r in rows if r[-1].strip().lower() != "caught"]
    if story:
        manual = [f"`{story.id}/{ac}`" for ac in item.fm.get("covers") or []
                  if not project.tests.get(f"{story.id}/{ac}")]
        if manual and rows:
            out.append("- **QA checks by hand:** " + ", ".join(manual))
    return "## For the reviewer\n\n" + "\n".join(out) + "\n\n" if out else ""


# ---------------------------------------------------------------- vendor

def vendor(root: str, force: bool = False) -> list:
    """Copy this plugin's process/ and this file into <root>/spry/. Returns what was written."""
    here = os.path.dirname(os.path.abspath(__file__))
    source = os.path.join(os.path.dirname(here), "process")
    target = os.path.join(os.path.abspath(root), "spry")
    if not os.path.isdir(native(source)) or os.path.abspath(os.path.dirname(here)) == target:
        raise SystemExit("run `vendor` with the plugin's spry.py, not a project's copy")
    process_target = os.path.join(target, "process")
    if os.path.exists(native(process_target)) and not force:
        raise SystemExit("spry/process/ already exists — it may hold local process changes; "
                         "use /spry:update to merge, or --force to overwrite")
    if os.path.exists(native(process_target)):
        shutil.rmtree(process_target)
    shutil.copytree(source, process_target, ignore=shutil.ignore_patterns("__pycache__", ".DS_Store"))
    os.makedirs(native(os.path.join(target, "tool")), exist_ok=True)
    shutil.copy2(os.path.abspath(__file__), os.path.join(target, "tool", "spry.py"))
    return ["spry/process/", "spry/tool/spry.py"]


def vendor_diff(root: str) -> list:
    """['changed: process/chat.md', 'new in spry: …', 'only in project: …'] — plugin vs project."""
    here = os.path.dirname(os.path.abspath(__file__))
    plugin = os.path.dirname(here)
    target = os.path.join(os.path.abspath(root), "spry")
    if not os.path.isdir(native(os.path.join(plugin, "process"))) or os.path.abspath(plugin) == target:
        raise SystemExit("run `vendor --diff` with the plugin's spry.py, not a project's copy")

    def files(base):
        out = set()
        for dirpath, dirnames, filenames in walk_dir(os.path.join(base, "process")):
            dirnames[:] = [d for d in dirnames if d != "__pycache__" and not d.startswith(".")]
            out |= {os.path.relpath(os.path.join(dirpath, f), base).replace(os.sep, "/")
                    for f in filenames if not f.startswith(".")}
        if os.path.isfile(native(os.path.join(base, "tool", "spry.py"))):
            out.add("tool/spry.py")
        return out

    ours, theirs = files(plugin), files(target)
    lines = [f"changed: {f}" for f in sorted(ours & theirs)
             if not filecmp.cmp(os.path.join(plugin, f), os.path.join(target, f), shallow=False)]
    lines += [f"new in spry: {f}" for f in sorted(ours - theirs)]
    lines += [f"only in project: {f}" for f in sorted(theirs - ours)]
    return lines


# ---------------------------------------------------------------- scrub

def scrub(project: Project, path: str) -> list:
    """[(line, word)] — words private to this project still in a text meant to leave it."""
    words = set()
    if project.config.get("product"):
        words.add(project.config["product"])
    for member in project.config.get("team", {}).get("members", []):
        words |= {member.get("name", ""), member.get("github", "")}
    gloss_path, banned = glossary(project)
    words |= {b for b, _ in banned} | {t for _, t in banned}
    if os.path.isfile(native(gloss_path)):
        for _i, cells in table_rows(enumerate(read(gloss_path).split("\n"))):
            if cells and cells[0].lower() != "term" and not cells[0].startswith("<"):
                words.add(cells[0])
    words = sorted((w for w in words if w and len(w) > 1), key=len, reverse=True)
    patterns = [(re.compile(r"(?<![\w-])" + re.escape(w) + r"(?![\w-])", re.I), w) for w in words]
    patterns += [(re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+"), "an email address"),
                 (re.compile(r"https?://\S+"), "a URL")]
    hits = []
    for n, line in enumerate(read(path).split("\n"), 1):
        for regex, word in patterns:
            for m in regex.finditer(line):
                hits.append((n, f"{m.group(0)} ({word})" if word.startswith("a") and " " in word else m.group(0)))
    return hits


# ---------------------------------------------------------------- falsify

PACKAGE_MARKERS = ("package.json", "pyproject.toml", "go.mod", "Cargo.toml", "pom.xml",
                   "build.gradle", "Gemfile", "setup.py")


class PlanError(Exception):
    pass


def git(root: str, *args: str, input: str | None = None, env: dict | None = None) -> subprocess.CompletedProcess:
    if input is not None:  # as bytes: a text pipe turns "\n" into "\r\n" on Windows, and the blob with it
        done = subprocess.run(["git", "-C", root, *args], capture_output=True, input=input.encode("utf-8"), env=env)
        return subprocess.CompletedProcess(done.args, done.returncode, done.stdout.decode("utf-8", "replace"),
                                           done.stderr.decode("utf-8", "replace"))
    return subprocess.run(["git", "-C", root, *args], capture_output=True, text=True, encoding="utf-8",
                          errors="replace", env=env)


def git_prefix(root: str) -> str:
    """Where `root` sits inside its git repository, as `a/b/` — empty at the top."""
    done = git(root, "rev-parse", "--show-prefix")
    return done.stdout.strip() if done.returncode == 0 else ""


def git_clean(root: str, rel: str) -> bool:
    done = git(root, "status", "--porcelain", "--", rel)
    return done.returncode == 0 and not done.stdout.strip()


def in_line_endings(data: bytes, snippet: str) -> str:
    return snippet.replace("\r\n", "\n").replace("\n", "\r\n") if b"\r\n" in data else snippet


def runners(project: Project) -> list:
    table = project.config.get("falsify", {}).get("runners") or []
    if not table:
        raise PlanError("spry.config.json has no falsify.runners — say how to run a list of test files")
    for runner in table:
        command = str(runner.get("command") or "")
        if "{files}" not in command:
            raise PlanError("a falsify runner's command needs `{files}`: " + json.dumps(runner))
        if re.search(r"<[a-z][a-z ,/-]*>", command):
            raise PlanError("a falsify runner is still the template's placeholder: " + command)
        try:
            re.compile(str(runner.get("failed") or ""))
        except re.error as e:
            raise PlanError(f"a falsify runner's `failed` is not a pattern ({e}): " + json.dumps(runner))
    return table


def runner_cwd(project: Project, runner: dict, rel: str) -> str:
    """The folder a runner runs in for this test file: the project root, or its nearest package."""
    if runner.get("cwd") != "package":
        return project.root
    folder = os.path.dirname(os.path.join(project.root, rel))
    while os.path.abspath(folder).startswith(project.root):
        if any(os.path.isfile(native(os.path.join(folder, m))) for m in PACKAGE_MARKERS):
            return folder
        if os.path.abspath(folder) == project.root:
            break
        folder = os.path.dirname(folder)
    return project.root


def group_files(project: Project, files) -> dict:
    """{(runner index, cwd): [rel paths]} — the first runner whose `match` takes each file."""
    table = runners(project)
    groups: dict = {}
    for rel in sorted(set(files)):
        index = next((i for i, r in enumerate(table) if any(glob_regex(g).match(rel) for g in r.get("match", ["**"]))), None)
        if index is None:
            raise PlanError(f"no falsify runner matches {rel}")
        groups.setdefault((index, runner_cwd(project, table[index], rel)), []).append(rel)
    return groups


def load_plan(project: Project, path: str) -> list:
    try:
        plan = json.loads(read(path))
    except (OSError, json.JSONDecodeError) as e:
        raise PlanError(f"cannot read the plan {path}: {e}")
    if not isinstance(plan, list) or not plan:
        raise PlanError("a plan is a non-empty JSON list of controls")
    for n, entry in enumerate(plan, 1):
        where = f"control {n} ({entry.get('control', '?')})" if isinstance(entry, dict) else f"control {n}"
        if not isinstance(entry, dict):
            raise PlanError(f"{where} is not an object")
        for key in ("control", "file", "find", "expect"):
            if not entry.get(key):
                raise PlanError(f"{where} has no `{key}`")
        entry.setdefault("with", "")
        if entry["find"] == entry["with"]:
            raise PlanError(f"{where}: `find` equals `with` — nothing would change")
        target = os.path.join(project.root, entry["file"])
        if not os.path.isfile(native(target)):
            raise PlanError(f"{where}: no file {entry['file']}")
        if not git_clean(project.root, entry["file"]):
            raise PlanError(f"{where}: {entry['file']} has uncommitted changes — commit first; restoring would lose them")
        with open(native(target), "rb") as handle:
            data = handle.read()
        count = data.decode("utf-8").count(in_line_endings(data, entry["find"]))
        if count != 1:
            raise PlanError(f"{where}: `find` occurs {count} times in {entry['file']} — it must occur exactly once")
        if not isinstance(entry["expect"], list):
            raise PlanError(f"{where}: `expect` must be a list such as [\"S-1/AC-2\"], [\"B-4\"] or [\"T-7\"]")
        cited = set()
        for ref in entry["expect"]:
            cited |= {path for path, _, _ in expected_tests(project, ref, where)}
        if entry.get("files"):
            entry["files"] = [posixpath.normpath(f.replace("\\", "/")) for f in entry["files"]]
        cited = sorted(cited)
        if not cited:
            loose = sorted({f"{path}:{line}" for path, line, ref in project.item_unproving if ref in entry["expect"]})
            hint = f" (cited only outside a test's name: {', '.join(loose[:3])})" if loose else ""
            raise PlanError(f"{where}: no test cites {', '.join(entry['expect'])} — nothing could notice{hint}; "
                            "put the ID in a test's name, or name the test file that guards it")
        chosen = entry.get("files") or cited
        stray = sorted(set(chosen) - set(cited))
        if stray:
            raise PlanError(f"{where}: {', '.join(stray)} cites none of {', '.join(entry['expect'])}")
        entry["_tests"] = chosen
    return plan


EXPECT_FILE_NAME = re.compile(r"^(test_.+\.py|.+_test\.[^./]+|.+\.(test|spec)\.[^./]+)$")  # a helper or fixture runs no test


def expected_tests(project: Project, ref: str, where: str) -> list:
    """The tests one `expect` names: a criterion's (`S-1/AC-2`), a bug's or a task's (`B-4`, `T-7`) —
    by the ID in a test's name — or one test file by its path, for a guard a test already covers."""
    if re.fullmatch(re.escape(project.ids["story"]) + r"-\d+/AC-\d+", ref):
        return project.tests.get(ref, [])
    item = project.items.get(ref)
    if item is not None and item.type in ("bug", "task"):
        return project.item_tests.get(ref, [])
    rel = posixpath.normpath(ref.replace("\\", "/"))
    if os.path.isfile(native(os.path.join(project.root, rel))):
        parts = rel.split("/")
        # Only where the test scan looks: a path outside the project, or in `spry/`, a dot-folder or
        # installed dependencies, would run code a worktree never mutated — a false `survived`.
        if (posixpath.isabs(rel) or ntpath.splitdrive(rel)[0] or parts[0] in ("..", "spry")
                or any(p.startswith(".") or p in SKIP_DIRS for p in parts[:-1])):
            raise PlanError(f"{where}: `expect` names {ref}, which is not a test file inside the project")
        if not (any(g.match(rel) for g in project._test_globs()) and EXPECT_FILE_NAME.match(parts[-1])):
            raise PlanError(f"{where}: `expect` names {ref}, which is not named as a test file "
                            "(tests.match, and test_*.py, *_test.*, *.test.* or *.spec.*)")
        return [(rel, 0, "")]
    raise PlanError(f"{where}: `expect` names {ref}, which is not a criterion, a bug, a task or a test file")


def runner_command(project: Project, runner: dict, cwd: str, files: list, root: str | None = None) -> str:
    """The runner's command for these test files, each relative to `cwd`."""
    base = root or project.root
    # `/` on every platform: test runners take it on Windows, and a `\` would need quoting
    rels = [os.path.relpath(os.path.join(base, f), cwd).replace(os.sep, "/") for f in files]
    return runner["command"].replace("{files}", " ".join(shell_quote(r) for r in rels))


# What a runner prints when a test failed — not when it broke before any test could (no database,
# a port in use, an import error, pnpm refusing to run). A runner's `failed` replaces these.
# A line may carry turbo's `api:test: ` or docker compose's `api-1  | ` in front.
LINE_PREFIX = r"^(?:[\w@./-]+:[\w:-]+: |[\w.-]+\s+\| )?"
FAILED_PATTERNS = tuple(LINE_PREFIX + p for p in (
    r"\s*Tests\s+\d+ failed",               # vitest
    r"Tests:\s+\d+ failed",                 # jest
    r"(=+ )?\d+ failed\b",                  # pytest
    r"\s*\d+ failing\b",                    # mocha
    r"\s*--- FAIL: ",                       # go test
    r"test result: FAILED\.",               # cargo test
    r"FAILED \((failures|errors)=",         # unittest: an exception other than an assert is an error
    r"\d+ examples?, [1-9]\d* failures?",   # rspec
    r"(# |ℹ )fail [1-9]",                   # node --test
))
# Output that says the run broke, whatever else it reports: a test module that would not import
# (unittest counts it as an error), a mocha hook that failed before its tests.
BROKEN_PATTERNS = (r"unittest\.loader\._FailedTest", r"Failed to import test module",
                   r'"before (all|each)" hook')
ANSI = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")


def test_failed(runner: dict, output: str) -> bool:
    """Did a test fail, by the runner's own report? A non-zero exit alone says only that something did."""
    text = ANSI.sub("", output)
    if runner.get("failed"):
        return bool(re.search(runner["failed"], text, re.MULTILINE))
    if any(re.search(p, text, re.MULTILINE) for p in BROKEN_PATTERNS):
        return False
    return any(re.search(p, text, re.MULTILINE) for p in FAILED_PATTERNS)


def run_command(command: str, cwd: str, timeout: int, env: dict | None = None):
    """(exit code, or None on a timeout; output). Its own process group, so a timeout or Ctrl-C
    stops the command's children too (pnpm → vitest workers) — none may keep running against a
    mutated file."""
    proc = subprocess.Popen(command, shell=True, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            text=True, encoding="utf-8", errors="replace", start_new_session=True,
                            env={**os.environ, **env} if env else None)
    try:
        output, _ = proc.communicate(timeout=timeout)
    except BaseException as e:
        stop_group(proc)
        if isinstance(e, subprocess.TimeoutExpired):
            return None, ""
        raise
    return proc.returncode, output or ""


def run_tests(project: Project, runner: dict, cwd: str, files: list, timeout: int, root: str | None = None,
              env: dict | None = None):
    """('pass' | 'fail' | 'broken' | 'timeout', last lines of output). `root` is the tree the files
    live in. `broken` is a non-zero exit with no failed test in the output."""
    code, output = run_command(runner_command(project, runner, cwd, files, root), cwd, timeout, env)
    if code is None:
        return "timeout", ""
    tail = "\n".join(ANSI.sub("", output).strip().split("\n")[-5:])
    if code == 0:
        return "pass", tail
    return ("fail" if test_failed(runner, output) else "broken"), tail


def stop_group(proc: subprocess.Popen):
    try:
        if WINDOWS:  # no process groups: stop the shell and everything under it
            subprocess.run(["taskkill", "/T", "/F", "/PID", str(proc.pid)], capture_output=True)
        else:
            os.killpg(proc.pid, signal.SIGKILL)
    except (ProcessLookupError, PermissionError, OSError):
        pass
    finally:
        try:
            proc.kill()
        except OSError:
            pass
    proc.wait()


def describe(entry: dict) -> str:
    if entry.get("mutation"):
        return entry["mutation"]
    find = " ".join(entry["find"].split())
    return f"delete `{find}`" if not entry["with"] else f"`{find}` → `{' '.join(entry['with'].split())}`"


class Writer:
    """Writes files so no build cache can mistake one version for another.

    Every write gets its own whole-second mtime, later than the last. Build caches that judge
    "unchanged" by size and mtime (Python's .pyc among them) would otherwise run the previous
    mutation's compiled code when two mutations have the same size — a false `caught`."""

    def __init__(self):
        self.clock = int(time.time())
        self.lock = threading.Lock()

    def put(self, path: str, data: bytes):
        with open(native(path), "wb") as handle:
            handle.write(data)
        with self.lock:
            self.clock = max(self.clock + 1, int(time.time()))
            stamp = self.clock
        os.utime(native(path), (stamp, stamp))


def mutate(entry: dict, original: bytes) -> bytes:
    text = original.decode("utf-8")
    return text.replace(in_line_endings(original, entry["find"]), in_line_endings(original, entry["with"]), 1).encode("utf-8")


def in_tree(project: Project, root: str, cwd: str) -> str:
    """The same folder as `cwd` (under the project root), inside another tree."""
    return os.path.join(root, os.path.relpath(cwd, project.root))


GENERIC_STEMS = ("index", "__init__", "mod", "main", "lib")


def likely_first(project: Project, entry: dict) -> list:
    """The control's tests in tiers: those that name its source file first, then the rest.
    One failure is enough, so a cheap tier that catches it saves running a criterion's every test."""
    tests = entry.get("_tests") or []
    path = entry.get("file") or ""
    stem = os.path.splitext(os.path.basename(path))[0]
    if stem in GENERIC_STEMS:
        stem = os.path.basename(os.path.dirname(path))
    if not stem:
        return [tests]
    word = re.compile(r"(?<![\w-])" + re.escape(stem) + r"(?![\w-])")
    first = []
    for rel in tests:
        try:
            if word.search(read(os.path.join(project.root, rel))):
                first.append(rel)
        except (OSError, UnicodeDecodeError):
            pass
    rest = [rel for rel in tests if rel not in first]
    return [tier for tier in (first, rest) if tier] or [tests]


def run_control(project: Project, entry: dict, table: list, timeout: int, red: dict, root: str,
                env: dict | None = None) -> tuple:
    """Run the tests one mutated control should fail, in the tree at `root`. Returns (result, note).
    `caught` only when a test failed: a run that broke before any test did proves nothing."""
    outcomes, notes = [], []
    for tier in likely_first(project, entry):
        for key, files in group_files(project, tier).items():
            if key in red:
                outcomes.append("unreliable")
                notes.append(red[key])
                continue
            outcome, tail = run_tests(project, table[key[0]], in_tree(project, root, key[1]), files, timeout, root, env)
            outcomes.append({"fail": "caught", "pass": "survived"}.get(outcome, "unreliable"))
            if outcome == "timeout":
                notes.append("timed out")
            if outcome == "broken":
                notes.append("failed, but no test did" + (f": {tail.splitlines()[-1]}" if tail else ""))
            if outcome == "fail":
                break
        if "caught" in outcomes:
            break
    if "caught" in outcomes:
        return "caught", "; ".join(notes)
    if "survived" in outcomes and "unreliable" not in outcomes:
        return "survived", "; ".join(notes)
    return "unreliable", "; ".join(notes)


def baseline(project: Project, groups: dict, table: list, timeout: int, root: str, say, env: dict | None = None) -> dict:
    """{group key: why it is red} for every group whose tests fail before anything is changed."""
    red = {}
    for key, files in groups.items():
        outcome, tail = run_tests(project, table[key[0]], in_tree(project, root, key[1]), files, timeout, root, env)
        if outcome != "pass":
            red[key] = f"baseline {outcome}" + (f": {tail.splitlines()[-1]}" if tail else "")
        say(f"baseline {'green' if outcome == 'pass' else outcome} · {len(files)} test files")
    return red


DEFAULT_SHARE = ("node_modules", ".venv", "venv")


def shared_paths(project: Project) -> list:
    """Untracked folders each worktree borrows from the main tree: installed dependencies."""
    names = set(DEFAULT_SHARE)
    found = list(project.config.get("falsify", {}).get("share", []))
    for dirpath, dirnames, _files in walk_dir(project.root):
        depth = os.path.relpath(dirpath, project.root).count(os.sep)
        keep = []
        for d in dirnames:
            if d in names:
                found.append(os.path.relpath(os.path.join(dirpath, d), project.root))
            elif not d.startswith(".") and d not in SKIP_DIRS and depth < 3:
                keep.append(d)
        dirnames[:] = keep
    return sorted(set(found))


def borrow(source: str, link: str, rel: str, pnpm: bool):
    """Give a worktree the main tree's installed dependencies.

    A pnpm package's own `node_modules` holds relative links to its workspace siblings
    (`../../packages/domain`). Linking the whole folder would resolve those in the main tree, so a
    test would run the unmutated sibling — a false `survived`. Copy its links instead: relative ones
    then resolve inside the worktree. The root `node_modules` (the store) is linked as usual."""
    nested = os.path.basename(source) == "node_modules" and os.path.dirname(rel.replace(os.sep, "/")) != ""
    if pnpm and nested:
        shutil.copytree(source, link, symlinks=True)
        return
    try:
        os.symlink(source, link, target_is_directory=os.path.isdir(native(source)))
    except OSError:
        if not WINDOWS:
            raise
        # A symlink needs Developer Mode or an administrator on Windows; a junction needs neither.
        done = subprocess.run(["cmd", "/c", "mklink", "/J", os.path.normpath(link),
                               os.path.normpath(os.path.abspath(source))], capture_output=True, text=True)
        if done.returncode != 0:
            raise PlanError(f"cannot link {rel} into a worktree ({done.stdout.strip() or done.stderr.strip()}) — "
                            "turn on Developer Mode, or set falsify.parallel to false")


def is_link(path: str) -> bool:
    """A symlink or a Windows junction — anything whose removal must not reach what it points at."""
    try:
        st = os.lstat(path)
    except OSError:
        return False
    return os.path.islink(path) or getattr(st, "st_reparse_tag", 0) == 0xA0000003  # a mount point


def unborrow(link: str) -> bool:
    """Remove a borrowed link itself, never its target. False when it could not be removed."""
    if not is_link(link):
        return not os.path.lexists(link) or not WINDOWS  # a pnpm copy holds only links on POSIX
    try:
        os.unlink(link)
    except OSError:
        try:
            os.rmdir(link)  # a junction or a directory symlink on Windows
        except OSError:
            return False
    return True


def parallel_blocker(project: Project, plan: list):
    """Why a worktree would not see what the main tree has — or None when parallel is safe."""
    status = git(project.root, "status", "--porcelain", "--untracked-files=no")
    if status.returncode != 0:
        return "not a git repository"
    if status.stdout.strip():
        return "tracked files have uncommitted changes, which a worktree would not see"
    for path in sorted({f for e in plan for f in e["_tests"]}):
        if git(project.root, "ls-files", "--error-unmatch", "--", path).returncode != 0:
            return f"{path} is not committed, so a worktree would not have it"
    if WINDOWS and os.path.isdir(native(os.path.join(project.root, "node_modules", ".pnpm"))) and any(
            os.path.basename(rel) == "node_modules" and os.path.dirname(rel.replace(os.sep, "/"))
            for rel in shared_paths(project)):
        # pnpm links packages with junctions there, which a copy follows: a worktree would test the
        # main tree's unmutated packages — a false `survived`
        return "Windows: pnpm's package links cannot be copied into a worktree safely"
    return None


def jobs_for(project: Project, wanted, controls: int) -> int:
    setting = wanted if wanted is not None else project.config.get("falsify", {}).get("parallel", False)
    if setting is True:
        setting = max(2, (os.cpu_count() or 2) // 2)
    try:
        jobs = int(setting or 1)
    except (TypeError, ValueError):
        raise PlanError(f"falsify.parallel must be true, false or a number, not {setting!r}")
    return max(1, min(jobs, controls))


WIDE_CONTROL = 20


def falsify_run(project: Project, plan_path: str, dry: bool = False, say=print, jobs=None) -> list:
    """Run a plan. Returns [(entry, result, note)], result caught | survived | unreliable."""
    plan = load_plan(project, plan_path)
    table = runners(project)
    timeout = int(project.config.get("falsify", {}).get("timeout", 600))
    groups = group_files(project, [f for e in plan for f in e["_tests"]])
    for entry in plan:
        if len(entry["_tests"]) > WIDE_CONTROL and not entry.get("files"):
            say(f"wide: `{entry['control']}` may run {len(entry['_tests'])} test files — the ones naming "
                f"{os.path.basename(entry['file'])} run first; list the ones that matter under `files` to cap it")
    jobs = jobs_for(project, jobs, len(plan))
    if jobs > 1:
        blocker = parallel_blocker(project, plan)
        if blocker:
            say(f"serial: {blocker}")
            jobs = 1
    if dry:
        say(f"{jobs} worktrees in parallel" if jobs > 1 else "serial, in this tree")
        for (index, cwd), files in groups.items():
            say(f"baseline · runner {index + 1} · {project.rel(cwd) if cwd != project.root else '.'} · {len(files)} test files")
        for entry in plan:
            say(f"would remove: {entry['control']} — {describe(entry)} — then run {', '.join(entry['_tests'])}")
        return []
    previous = signal.getsignal(signal.SIGTERM)

    def interrupt(*_):
        raise KeyboardInterrupt()

    signal.signal(signal.SIGTERM, interrupt)
    try:
        if jobs > 1:
            results = falsify_parallel(project, plan, table, timeout, groups, jobs, say)
        else:
            results = falsify_serial(project, plan, table, timeout, groups, say)
    finally:
        signal.signal(signal.SIGTERM, previous)
    dirty = [e["file"] for e in plan if not git_clean(project.root, e["file"])]
    if dirty:
        raise PlanError("after the run these files are not as committed — check them now: " + ", ".join(dirty))
    return results


def slot_env(slot: int, slots: int) -> dict:
    """What every command in a slot sees, so a project can give each slot its own database and port."""
    return {"SPRY_FALSIFY_SLOT": str(slot), "SPRY_FALSIFY_SLOTS": str(slots)}


def prepare_slot(project: Project, cwd: str, env: dict, timeout: int, say):
    """Run `falsify.setup` once in a slot, before its first test. A failure stops the run: a slot
    that is not ready would turn every control after it into a result."""
    command = str(project.config.get("falsify", {}).get("setup") or "")
    if not command:
        return
    code, output = run_command(command, cwd, timeout, env)
    slot = env["SPRY_FALSIFY_SLOT"]
    if code != 0:
        last = ANSI.sub("", output).strip().split("\n")[-1]
        why = "timed out" if code is None else f"exit {code}" + (f": {last}" if last else "")
        raise PlanError(f"falsify.setup failed in slot {slot} ({why}) — no control was run")
    say(f"setup · slot {slot}")


def falsify_serial(project: Project, plan: list, table: list, timeout: int, groups: dict, say) -> list:
    """One control at a time, in this tree; every file restored, whatever happens."""
    env = slot_env(1, 1)
    prepare_slot(project, project.root, env, timeout, say)
    red = baseline(project, groups, table, timeout, project.root, say, env)
    writer, results, touched = Writer(), [], {}

    def restore():
        for path, data in touched.items():
            writer.put(path, data)
        touched.clear()

    try:
        for entry in plan:
            target = os.path.join(project.root, entry["file"])
            with open(native(target), "rb") as handle:
                original = handle.read()
            touched[target] = original
            writer.put(target, mutate(entry, original))
            try:
                result, note = run_control(project, entry, table, timeout, red, project.root, env)
            finally:
                restore()
            results.append((entry, result, note))
            say(f"{result}: {entry['control']}")
    finally:
        restore()
    return results


# A worktree borrows the main tree's installed dependencies, which pnpm 11 judges stale and tries to
# reinstall before any script — a red baseline for every control. The main tree installed them.
WORKTREE_ENV = {"npm_config_verify_deps_before_run": "false", "pnpm_config_verify_deps_before_run": "false"}


def falsify_home(project: Project) -> str:
    """Where this checkout's worktrees are kept between runs: outside the repository, one per checkout."""
    key = hashlib.sha1(os.path.realpath(project.root).encode("utf-8")).hexdigest()[:8]
    return os.path.join(tempfile.gettempdir(), f"spry-falsify-{key}")


def take_home(home: str):
    """Claim the kept worktrees for this run: an open, locked file, or None while another run of this
    checkout holds them. The system lets go of the lock when the process ends, however it ends."""
    os.makedirs(native(home), exist_ok=True)
    handle = open(native(os.path.join(home, "lock")), "a+")
    try:
        if WINDOWS:
            import msvcrt
            handle.seek(0)
            msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        handle.close()
        return None
    return handle


def drop_links(tree: str):
    """Remove every link and junction in a tree without following one. Windows only needs it: git
    there walks into a junction as if it were a folder, and would clean the main tree through it."""
    for dirpath, dirnames, filenames in os.walk(tree):
        keep = []
        for name in dirnames:
            path = os.path.join(dirpath, name)
            if is_link(path):
                unborrow(path)
            elif name != ".git":
                keep.append(name)
        dirnames[:] = keep
        for name in filenames:
            if is_link(os.path.join(dirpath, name)):
                unborrow(os.path.join(dirpath, name))


def reset_tree(tree: str, commit: str) -> bool:
    """A kept worktree made exactly like a fresh one at `commit`: tracked files checked out, every
    untracked and ignored file gone — no build output from an older commit survives into this run.
    Files that did not change keep their identity, so a virus scanner does not read them again."""
    # Only a tree that is still its own worktree: without its `.git` file, git would look upward and
    # reset whatever repository holds the temporary folder.
    top = git(tree, "rev-parse", "--show-toplevel").stdout.strip()
    if not os.path.isfile(native(os.path.join(tree, ".git"))) or os.path.realpath(top) != os.path.realpath(tree):
        return False
    if WINDOWS:
        drop_links(tree)
    return (git(tree, "checkout", "-q", "-f", "--detach", commit).returncode == 0
            and git(tree, "clean", "-q", "-ffdx").returncode == 0)


def registered_worktrees(project: Project) -> set:
    done = git(project.root, "worktree", "list", "--porcelain")
    return {os.path.realpath(line[len("worktree "):]) for line in done.stdout.splitlines()
            if line.startswith("worktree ")}


def falsify_parallel(project: Project, plan: list, table: list, timeout: int, groups: dict, jobs: int, say) -> list:
    """Controls spread over `jobs` git worktrees of HEAD. This tree is never written to.

    The baseline runs inside a worktree, not here: a worktree missing something the tests need
    (a dependency not shared, a generated file) must show as a red baseline — `unreliable` —
    never as every control `caught`.

    The worktrees are kept between runs (`falsify.keep_worktrees`) and reset at the start of each:
    a fresh one is cold — a virus scanner reads every file it holds on the first run."""
    from concurrent.futures import ThreadPoolExecutor
    import queue

    commit = git(project.root, "rev-parse", "HEAD").stdout.strip()
    home = falsify_home(project) if project.config.get("falsify", {}).get("keep_worktrees", True) is not False else None
    held = take_home(home) if home else None
    if home and not held:
        say("another run holds the kept worktrees — fresh ones for this run")
        home = None
    if home:  # forget kept worktrees a temporary-folder cleaner deleted, or `worktree add` refuses them
        git(project.root, "worktree", "prune")
    parent = home or tempfile.mkdtemp(prefix="spry-falsify-")
    trees, made, writer, lock, envs = [], [], Writer(), threading.Lock(), {}
    share = shared_paths(project)
    prefix = git_prefix(project.root)
    pnpm = os.path.isdir(native(os.path.join(project.root, "node_modules", ".pnpm")))
    try:
        listed, reused = registered_worktrees(project) if home else set(), 0
        for n in range(jobs):
            tree = os.path.join(parent, f"w{n + 1}")
            if home and os.path.realpath(tree) in listed and reset_tree(tree, commit):
                reused += 1
            else:
                if os.path.lexists(native(tree)):  # not a worktree of this checkout, or would not reset
                    if WINDOWS:
                        drop_links(tree)
                    git(project.root, "worktree", "remove", "--force", tree)
                    shutil.rmtree(native(tree), ignore_errors=True)
                    git(project.root, "worktree", "prune")
                done = git(project.root, "worktree", "add", "--detach", "-q", tree, commit)
                if done.returncode != 0:
                    raise PlanError(f"git worktree add failed: {done.stderr.strip()}")
            made.append(tree)
            tree = os.path.join(tree, prefix)
            trees.append(tree)
            envs[tree] = {**slot_env(n + 1, jobs), **WORKTREE_ENV}
            for rel in share:
                link = os.path.join(tree, rel)
                if not os.path.exists(native(link)):
                    os.makedirs(native(os.path.dirname(link)), exist_ok=True)
                    borrow(os.path.join(project.root, rel), link, rel, pnpm)
        kept = f" · {reused} kept from the last run" if reused else ""
        say(f"{jobs} worktrees{kept} · sharing {', '.join(share) or 'nothing'}")
        for tree in trees:
            prepare_slot(project, tree, envs[tree], timeout, say)
        red = baseline(project, groups, table, timeout, trees[0], say, envs[trees[0]])

        def serial_only(entry):
            keys = group_files(project, entry["_tests"])
            return any(table[index].get("parallel") is False for index, _cwd in keys)

        free = queue.Queue()
        for tree in trees:
            free.put(tree)

        def one(entry):
            tree = free.get()
            target = os.path.join(tree, entry["file"])
            try:
                with open(native(target), "rb") as handle:
                    original = handle.read()
                writer.put(target, mutate(entry, original))
                try:
                    return run_control(project, entry, table, timeout, red, tree, envs[tree])
                finally:
                    writer.put(target, original)
            finally:
                free.put(tree)

        results: dict = {}
        pool_entries = [(i, e) for i, e in enumerate(plan) if not serial_only(e)]
        with ThreadPoolExecutor(max_workers=jobs) as pool:
            futures = {pool.submit(one, e): (i, e) for i, e in pool_entries}
            try:
                for future in futures:
                    i, entry = futures[future]
                    results[i] = (entry, *future.result())
                    with lock:
                        say(f"{results[i][1]}: {entry['control']}")
            except BaseException:
                pool.shutdown(wait=True, cancel_futures=True)
                raise
        for i, entry in enumerate(plan):
            if i not in results:
                results[i] = (entry, *one(entry))
                say(f"{results[i][1]}: {entry['control']} (serial runner)")
        return [results[i] for i in range(len(plan))]
    finally:
        # Take the borrowed links out first: git on Windows walks into a junction as if it were a
        # folder, and would delete the main tree's dependencies through it. A kept tree loses them
        # too, so nothing that deletes the temporary folder can reach the main tree's.
        for made_tree, tree in zip(made, trees):
            if all(unborrow(os.path.join(tree, rel)) for rel in share) and not home:
                git(project.root, "worktree", "remove", "--force", made_tree)
        if held:
            held.close()
        if not home:
            for made_tree in made[len(trees):]:
                git(project.root, "worktree", "remove", "--force", made_tree)
            shutil.rmtree(parent, ignore_errors=True)
        git(project.root, "worktree", "prune")


ROW_KEY = re.compile(r"\s*<!--\s*(f:[0-9a-f]{8})\s*-->")


def control_key(path: str, find: str) -> str:
    """Names a control by where it is, not by its label: a row renamed in plain words still matches."""
    return "f:" + hashlib.sha1(f"{path}\n{' '.join(find.split())}".encode()).hexdigest()[:8]


def falsify_rows(results) -> list:
    rows = []
    for entry, result, note in results:
        expect = ", ".join(entry["expect"])
        control = entry["control"]
        if entry.get("file") and entry.get("find"):
            control += f" <!-- {control_key(entry['file'], entry['find'])} -->"
        cells = [control, describe(entry), expect, result + (" — " + note if note else "")]
        rows.append("| " + " | ".join(c.replace("|", "\\|") for c in cells) + " |")
    return rows


def record_falsify(project: Project, slice_id: str, rows: list, replace: bool = False) -> tuple:
    """Write rows into the slice's Falsify table: a row for a control already there replaces it in place —
    matched by its `<!-- f:… -->` key, or by its control cell when the old row has none (written by hand) —
    and a new control is added at the end. Rows this run did not touch stay, so a run of only the survivors
    keeps the rest; `replace` drops them. Returns (the slice's file, how many rows were kept untouched)."""
    item = project.items.get(slice_id)
    if item is None or item.type != "slice":
        raise PlanError(f"no slice {slice_id}")
    lines = item.text.split("\n")
    head = next((i for i, l in enumerate(lines) if re.match(r"^\|\s*Control\s*\|", l)), None)
    if head is None:
        at = next((i for i, l in enumerate(lines) if l.strip() == "### Falsify"), None)
        if at is None:
            raise PlanError(f"{project.rel(item.doc)} has no `### Falsify` section")
        lines[at + 1:at + 1] = ["", "| Control | Mutation | Expect | Result |", "|---|---|---|---|"]
        head = at + 2
    end = head + 2
    while end < len(lines) and lines[end].startswith("|"):
        end += 1

    def control(row: str) -> str:
        return ROW_KEY.sub("", re.split(r"(?<!\\)\|", row.strip().strip("|"))[0]).strip()

    kept = [] if replace else lines[head + 2:end]
    by_key, by_control = {}, {}
    for i, row in enumerate(kept):
        found = ROW_KEY.search(row)
        if found:
            by_key.setdefault(found.group(1), i)
        else:
            by_control.setdefault(control(row), i)
    touched = set()
    for row in rows:
        found = ROW_KEY.search(row)
        at = by_key.get(found.group(1)) if found else None
        if at is None:
            at = by_control.pop(control(row), None)
        if at is None or at in touched:  # two mutations of one line in one run: both rows stay
            kept.append(row)
            at = len(kept) - 1
        kept[at] = row
        touched.add(at)
        if found:
            by_key.setdefault(found.group(1), at)
    lines[head + 2:end] = kept
    write(item.doc, "\n".join(lines))
    return item.doc, len(kept) - len(touched)


CONTROL_LINE = re.compile(r"^\s*(if\b|elif\b|else if\b|unless\b|guard\b|throw\b|raise\b|return\s+(err|Err|error|None|null|false|False)\b|assert\b|require\b)|(\|\||&&|>=|<=|===|!==|==|!=)")
# Boundaries only: `==` ↔ `!=` is negation (§16). A bare `>` / `<` needs spaces round it, so a
# generic (`Array<Item>`) is never taken for a comparison.
COMPARISON_FLIPS = [(">=", ">"), ("<=", "<"), (" > ", " >= "), (" < ", " <= ")]


def mutations_for(line: str) -> list:
    """Candidate (with, label) mutations for one added source line, most telling first."""
    stripped = line.strip()
    out = []
    # A guard is removed by making it never true. Negating it would also break the normal path,
    # so any test at all would "catch" it — a false catch, the one result falsify must not give.
    m = re.match(r"^(\s*(?:if|else if|while)\s*)\((.*)\)(\s*\{?\s*)$", line)
    if m:
        out.append((f"{m.group(1)}(false && ({m.group(2)})){m.group(3)}", "never true"))
    m = re.match(r"^(\s*(?:if|elif|while)\s+)(.*?)(:\s*)$", line)
    if m and not out:
        out.append((f"{m.group(1)}False and ({m.group(2)}){m.group(3)}", "never true"))
    for old, new in COMPARISON_FLIPS:
        at = re.search(r"(?<![=!<>])" + re.escape(old) + r"(?![=>])", line)
        if at and old.strip() in "<>" and re.search(r"\w<\w|<\w[\w.]*>", line):
            at = None
        if at:
            out.append((line[:at.start()] + new + line[at.end():], f"`{old}` → `{new}`"))
            break
    if re.match(r"^\s*(throw|raise|return\s+(err|Err|error|None|null|false|False)\b|assert\b|require\b)", line):
        out.append(("", "delete the line"))
    if not out and stripped:
        out.append(("", "delete the line"))
    return out


def added_source(project: Project, base: str) -> list:
    """[(path, line)] — every line this branch added outside tests, `spry/` and `checks.docs`."""
    diff = git(project.root, "diff", "--relative", "-U0", f"{base}...HEAD", "--", ".", ":(exclude)spry")
    if diff.returncode != 0:
        raise PlanError(f"git diff against {base} failed: {diff.stderr.strip()}")
    skip = project._test_globs() + [glob_regex(g) for g in project.config.get("checks", {}).get("docs") or DEFAULT_DOCS]
    out, current = [], None
    for line in diff.stdout.split("\n"):
        if line.startswith("+++ "):
            path = line[6:] if line.startswith("+++ b/") else None
            current = path if path and not any(g.match(path) for g in skip) else None
        elif current and line.startswith("+"):
            out.append((current, line[1:]))
    return out


# A line worth deleting when a slice adds no guard: it computes or stores something. Not an import,
# a declaration's head, a brace, a comment or a bare return.
STATEMENT_LINE = re.compile(r"^\s*(?!(import|from|export|def|class|function|interface|type|#|//|/\*|\*|return\s*;?$))"
                            r".*(\w\s*=[^=>]|\w\(|\.\w+\()")
FALLBACK_CONTROLS = 5


def falsify_suggest(project: Project, slice_id: str, base: str, fallback: bool = True) -> list:
    """A draft plan from the source lines this branch added, for a person to prune.
    With no guard among them, the lines that compute or store something are offered instead
    (`fallback`), so a slice that changes a value — a key, a digest — still has candidates."""
    item = project.items.get(slice_id)
    if item is None or item.type != "slice":
        raise PlanError(f"no slice {slice_id}")
    story = item.parent.id if item.parent and item.parent.type == "story" else None
    expect = [f"{story}/{ac}" for ac in item.fm.get("covers") or []] if story else []
    if item.parent and item.parent.type in ("bug", "task"):
        expect = [item.parent.id]  # no criteria: its tests cite the bug or the task
    added = added_source(project, base)
    texts: dict = {}

    def once(path, source):
        if path not in texts:
            try:
                texts[path] = read(os.path.join(project.root, path))
            except (OSError, UnicodeDecodeError):
                texts[path] = ""
        return texts[path].count(source) == 1

    plan = []
    for path, source in added:
        if CONTROL_LINE.search(source) and once(path, source):
            for with_, label in mutations_for(source)[:1]:
                plan.append({"control": " ".join(source.split())[:70], "file": path, "find": source,
                             "with": with_, "mutation": label, "expect": list(expect)})
    if plan or not fallback:
        return plan
    for path, source in added:
        if len(plan) == FALLBACK_CONTROLS:
            break
        if STATEMENT_LINE.match(source) and once(path, source):
            plan.append({"control": " ".join(source.split())[:70], "file": path, "find": source, "with": "",
                         "mutation": "delete the line — no guard was added; keep the lines a test must notice",
                         "expect": list(expect)})
    return plan


# ---------------------------------------------------------------- find

def searchable_files(project: Project) -> list:
    out = markdown_files(project) + history_files(project)
    process = os.path.join(project.spry, "process")
    if os.path.isdir(native(process)):
        for dirpath, _dirs, filenames in walk_dir(process):
            out += [os.path.join(dirpath, f) for f in filenames if f.endswith(".md")]
    return sorted(set(out))


def split_sections(path: str, text: str):
    """(document title, [(heading, first line, body)]) — one entry per heading, so a hit points at
    the part that matters. Link targets are dropped: a file name is not what a section is about."""
    fm, start, _ = parse_front_matter(text)
    title = (fm or {}).get("title") or os.path.basename(path)
    if (fm or {}).get("id") and not title.startswith(fm["id"]):
        title = f"{fm['id']} {title}"
    text = re.sub(r"\]\([^)]*\)", "]", strip_blocks(text))
    chunks, heading, first, body, in_fence = [], title, start + 1, [], False
    for n, line in enumerate(text.split("\n")[start:], start + 1):
        if FENCE.match(line):
            in_fence = not in_fence
        m = None if in_fence else HEADING.match(line)
        if m:
            if any(b.strip() for b in body):
                chunks.append((heading, first, "\n".join(body)))
            heading, first, body = m.group(2).strip(), n, []
        else:
            body.append(line)
    if any(b.strip() for b in body):
        chunks.append((heading, first, "\n".join(body)))
    return title, chunks


def search_terms(query: str) -> list:
    return [w for w in re.findall(r"[\w-]+", query.lower()) if w]


def find(project: Project, query: str, limit: int = 10, rebuild: bool = False, marks=("[", "]")) -> list:
    """[(rel path, line, heading, snippet)] best first, matches in the snippet between `marks`.
    SQLite FTS5 when the stdlib has it."""
    import sqlite3
    terms = search_terms(query)
    if not terms:
        return []
    files = searchable_files(project)
    db_path = os.path.join(project.root, ".spry", "index.db")
    os.makedirs(native(os.path.dirname(db_path)), exist_ok=True)
    if rebuild and os.path.exists(native(db_path)):
        os.remove(native(db_path))
    con = sqlite3.connect(db_path)
    columns = [r[1] for r in con.execute("PRAGMA table_info(sections)")]
    if columns and "title" not in columns:
        con.close()
        os.remove(native(db_path))
        con = sqlite3.connect(db_path)
    try:
        con.execute("CREATE VIRTUAL TABLE IF NOT EXISTS sections USING "
                    "fts5(path UNINDEXED, line UNINDEXED, title, heading, body, tokenize='porter unicode61')")
    except sqlite3.OperationalError:
        con.close()
        return find_plain(project, files, terms, limit)
    con.execute("CREATE TABLE IF NOT EXISTS files(path TEXT PRIMARY KEY, stamp TEXT)")
    known = dict(con.execute("SELECT path, stamp FROM files"))
    current = {}
    for path in files:
        st = os.stat(native(path))
        current[project.rel(path)] = (path, f"{st.st_mtime_ns}:{st.st_size}")
    for rel in set(known) - set(current):
        con.execute("DELETE FROM sections WHERE path = ?", (rel,))
        con.execute("DELETE FROM files WHERE path = ?", (rel,))
    for rel, (path, stamp) in current.items():
        if known.get(rel) == stamp:
            continue
        con.execute("DELETE FROM sections WHERE path = ?", (rel,))
        title, chunks = split_sections(path, read(path))
        con.executemany("INSERT INTO sections(path, line, title, heading, body) VALUES (?, ?, ?, ?, ?)",
                        [(rel, line, title, heading, body) for heading, line, body in chunks])
        con.execute("INSERT OR REPLACE INTO files(path, stamp) VALUES (?, ?)", (rel, stamp))
    con.commit()
    rows = []
    for joiner in (" ", " OR "):
        match = joiner.join('"' + t.replace('"', "") + '"*' for t in terms)
        rows = con.execute("SELECT path, line, title || ' › ' || heading, snippet(sections, 4, ?, ?, '…', 12) "
                           "FROM sections WHERE sections MATCH ? ORDER BY bm25(sections, 0, 0, 1.5, 2.0, 1.0) LIMIT ?",
                           (*marks, match, limit * 3)).fetchall()
        if rows:
            break
    con.close()
    return history_last([(path, int(line), heading, " ".join(snippet.split())) for path, line, heading, snippet in rows], limit)


def history_last(rows: list, limit: int) -> list:
    """Current documents first; what an earlier process left in spry/history/<source>/ after them, marked."""
    def old(row):
        return row[0].startswith("spry/history/") and row[0].count("/") > 2
    rows = [r for r in rows if not old(r)] + [(r[0], r[1], "history · " + r[2], r[3]) for r in rows if old(r)]
    return rows[:limit]


def find_plain(project: Project, files: list, terms: list, limit: int) -> list:
    scored = []
    for path in files:
        title, chunks = split_sections(path, read(path))
        for heading, line, body in chunks:
            text = (title + " " + heading + " " + body).lower()
            hits = sum(text.count(t) for t in terms)
            if hits and all(t in text for t in terms):
                at = text.find(terms[0])
                snippet = " ".join((heading + " " + body)[max(0, at - 40):at + 80].split())
                scored.append((hits, project.rel(path), line, f"{title} › {heading}", snippet))
    scored.sort(key=lambda s: -s[0])
    return history_last([s[1:] for s in scored], limit)


# ---------------------------------------------------------------- install

AGENTS = ("generic", "claude", "cursor", "gemini")


def install(root: str, agent: str) -> list:
    """Copy the plugin's skills where another agent finds them. Returns the paths written."""
    here = os.path.dirname(os.path.abspath(__file__))
    plugin = os.path.dirname(here)
    skills = os.path.join(plugin, "skills")
    if not os.path.isdir(native(skills)):
        raise SystemExit("run `install` with the plugin's spry.py, not a project's copy")
    if agent not in AGENTS:
        raise SystemExit(f"unknown agent `{agent}` — one of {', '.join(AGENTS)}")
    root = os.path.abspath(root)
    written, listing = [], []
    for name in sorted(os.listdir(native(skills)), key=natural_key):
        source = os.path.join(skills, name, "SKILL.md")
        if not os.path.isfile(native(source)):
            continue
        text = read(source).replace("two folders above this file's folder (`…/plugins/spry`)",
                                    f"`{plugin}` — a copy of spry's `plugins/spry`")
        fm, start, _ = parse_front_matter(text)
        fm = fm or {}
        body = "\n".join(text.split("\n")[start:]).strip() + "\n"
        description = fm.get("description", "")
        if agent == "generic":
            path = os.path.join(root, "spry", "skills", f"{name}.md")
            content = text
            short = re.split(r" — |\. |, ", description)[0].rstrip(".")
            if len(short) > 90:
                short = short[:90].rsplit(" ", 1)[0] + "…"
            listing.append(f"- `/spry:{name}` — {short} → `spry/skills/{name}.md`")
        elif agent == "claude":
            path = os.path.join(root, ".claude", "skills", f"spry-{name}", "SKILL.md")
            content = text.replace(f"name: {name}\n", f"name: spry-{name}\n", 1)
        elif agent == "cursor":
            path = os.path.join(root, ".cursor", "commands", f"spry-{name}.md")
            content = f"<!-- {description} -->\n\n{body}"
        else:
            if "'''" in body:
                raise SystemExit(f"skill {name} contains ''' and cannot be written as a TOML literal")
            path = os.path.join(root, ".gemini", "commands", "spry", f"{name}.toml")
            content = (f"description = {json.dumps(description, ensure_ascii=False)}\n"
                       f"prompt = '''\n{body.replace('$ARGUMENTS', '{{args}}')}'''\n")
        os.makedirs(native(os.path.dirname(path)), exist_ok=True)
        write(path, content)
        written.append(os.path.relpath(path, root).replace(os.sep, "/"))
    if agent == "generic":
        agents_md = os.path.join(root, "AGENTS.md")
        block = ("When the person types `/spry:<name>`, or asks for what a skill below does, read its file "
                 "and follow it. `$ARGUMENTS` in a skill means what they wrote after the command.\n\n"
                 + "\n".join(listing))
        text = read(agents_md) if os.path.isfile(native(agents_md)) else "# AGENTS.md\n"
        new = replace_block(text, "skills", block)
        if new is None:
            new = text.rstrip("\n") + "\n\n## spry skills\n\n<!-- spry:skills -->\n" + block + "\n<!-- /spry:skills -->\n"
        write(agents_md, new)
        written.append("AGENTS.md")
    return written


# ---------------------------------------------------------------- codeowners

def codeowners(project: Project) -> str:
    team = project.config.get("team", {})
    members, review = team.get("members", []), team.get("review", {})
    lines = ["# Generated by `spry.py codeowners` from team.review in spry/spry.config.json.",
             "# Change that, not this file. Later lines win, as GitHub reads them."]
    for pattern, roles in review.items():
        owners = sorted({"@" + m["github"] for m in members
                         if m.get("github") and set(m.get("roles", [])) & set(roles)})
        if not owners:
            project.problem(os.path.join(project.spry, "spry.config.json"), 1,
                            f"team.review `{pattern}` names roles nobody has: {', '.join(roles)}", "warning")
            continue
        anchored = pattern if pattern.startswith(("/", "*")) else "/" + pattern
        lines.append(f"{anchored} {' '.join(owners)}")
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------- draw

def _draw_hash(seed: str, counter: str, salt) -> int:
    import hashlib
    return int.from_bytes(hashlib.sha256(f"{seed}:{counter}:{salt}".encode()).digest()[:4], "big")


def draw(seed: str, counter: str, choices: list, mode: str, k: int = 1) -> list:
    """A choice that depends only on (seed, counter), so an exploratory walk can be replayed.

    A hash, not a random stream: no state to carry between shells, and the same pair gives the
    same answer on any machine, in any order."""
    if mode == "int":
        return [str(_draw_hash(seed, counter, "int") % k)]
    if not choices:
        raise SystemExit("nothing to draw from — pass one choice per line on stdin")
    order = list(choices)
    for i in range(len(order) - 1, 0, -1):
        j = _draw_hash(seed, counter, i) % (i + 1)
        order[i], order[j] = order[j], order[i]
    return {"pick": order[:1], "sample": order[:k], "shuffle": order}[mode]


def new_seed() -> str:
    import hashlib
    import random
    return hashlib.sha256(f"{time.time_ns()}:{random.random()}".encode()).hexdigest()[:12]


# ---------------------------------------------------------------- tests --slowest

def slowest(project: Project, junit: str | None = None, limit: int = 10) -> str:
    import glob as globber
    import xml.etree.ElementTree as ElementTree
    pattern = junit or project.config.get("tests", {}).get("junit", "")
    if not pattern or pattern.startswith("<"):
        raise SystemExit("no JUnit report — set tests.junit in spry.config.json, or pass --junit <path>")
    base = os.path.join(project.root, pattern)
    paths = sorted(globber.glob(os.path.join(base, "**", "*.xml"), recursive=True)) if os.path.isdir(native(base)) \
        else sorted(globber.glob(base, recursive=True))
    if not paths:
        raise SystemExit(f"no report at {pattern} — run the full test suite first")
    cases = []
    for path in paths:
        try:
            tree = ElementTree.parse(path)
        except ElementTree.ParseError as e:
            raise SystemExit(f"{project.rel(path)} is not JUnit XML: {e}")
        for case in tree.iter("testcase"):
            try:
                seconds = float(case.get("time") or 0)
            except ValueError:
                seconds = 0.0
            where = case.get("file") or case.get("classname") or "?"
            cases.append((seconds, where, case.get("name") or "?"))
    if not cases:
        return "no test cases in the report"
    total = sum(c[0] for c in cases)
    by_file: dict = {}
    for seconds, where, _ in cases:
        by_file[where] = by_file.get(where, 0) + seconds
    out = [f"{len(cases)} tests, {total:.1f}s in total", "", "Slowest tests:"]
    out += [f"  {s:7.2f}s  {w} — {n}" for s, w, n in sorted(cases, reverse=True)[:limit]]
    out += ["", "Slowest files:"]
    out += [f"  {s:7.2f}s  {w}" for w, s in sorted(by_file.items(), key=lambda p: -p[1])[:limit]]
    return "\n".join(out)


# ---------------------------------------------------------------- changed criteria

def ac_texts(text: str, struck: bool = False) -> dict:
    """{"AC-1": "given | when | then"}; with `struck`, a dropped (~~struck~~) criterion is marked."""
    out = {}
    for _i, cells in table_rows(section_lines(text, "Acceptance criteria") or []):
        m = re.fullmatch(r"(~~)?(AC-\d+)(~~)?", cells[0]) if cells else None
        if m:
            out[m.group(2)] = ("dropped: " if struck and m.group(1) else "") + " ".join(" | ".join(cells[1:]).split())
    return out


def fork_point(project: Project, base: str) -> str:
    """Where this branch left `base`: what the main branch did since is not the branch's."""
    return git(project.root, "merge-base", base, "HEAD").stdout.strip() or base


def criteria_edits(project: Project, base: str) -> list:
    """[(story, AC, text at the fork, text now or None)] for criteria that existed where the branch
    left `base` and changed."""
    out, fork = [], fork_point(project, base)
    for story in project.of_type("story"):
        before = git(project.root, "show", f"{fork}:./{project.rel(story.doc)}")
        if before.returncode != 0:
            continue
        old, new = ac_texts(before.stdout, struck=True), ac_texts(story.text, struck=True)
        out += [(story, ac, text, new.get(ac)) for ac, text in sorted(old.items()) if new.get(ac) != text]
    return out


def code_changed(project: Project, base: str) -> list:
    """Files outside spry/ that this branch changed since `base` — code, tests and configuration."""
    done = git(project.root, "diff", "--relative", "--name-only", f"{base}...HEAD", "--", ".", ":(exclude)spry")
    return [line for line in done.stdout.split("\n") if line.strip()] if done.returncode == 0 else []


def manual_reliance(text: str, ac: str) -> list:
    """[(line, what)] in a checks.md that rely on `ac`: each scenario under `## Scenarios` whose
    heading starts with it (`### AC-1 · …`, `### AC-1, AC-3 · …`), as its text with its
    sub-headings up to the next scenario, and each dated check-log row that names it."""
    lines, out = text.split("\n"), []
    heads = sections(text)
    scenarios = next(((at, end) for _l, title, at, end in heads if title.lower() == "scenarios"), None)
    for n, (_level, title, at, end) in enumerate(heads):
        m = SCENARIO_ACS.match(title)
        if scenarios and scenarios[0] < at < scenarios[1] and m and ac in re.findall(r"AC-\d+", m.group(1)):
            stop = next((h[2] for h in heads[n + 1:] if h[2] < end and SCENARIO_ACS.match(h[1])), end)
            out.append((at + 1, "\n".join(line.rstrip() for line in lines[at:stop]).strip()))
    for i, cells in table_rows(section_lines(text, "Check log") or []):
        if len(cells) >= 5 and DATE.match(cells[0]) and cells[1] == ac:
            out.append((i + 1, "log:" + lines[i].strip()))
    return out


def changed_criteria(project: Project, base: str):
    """Warn for each acceptance criterion whose text changed since `base` while a test cites it, or
    while its story's checks.md has scenarios or check-log rows for it that this branch left as they were.
    Both are read where the branch left `base`, so what the main branch did since is not the branch's."""
    if git(project.root, "rev-parse", "--verify", "--quiet", f"{base}^{{commit}}").returncode != 0:
        project.problem(project.spry, 0, f"--base {base} is not a commit here — fetch it (a shallow CI "
                                         f"clone needs `fetch-depth: 0`), or nothing was compared")
        return
    fork = fork_point(project, base)
    forked_on = git(project.root, "log", "-1", "--format=%cs", fork).stdout.strip()
    for story in project.of_type("story"):
        rel = project.rel(story.doc)
        before = git(project.root, "show", f"{fork}:./{rel}")
        if before.returncode != 0:
            continue
        old, new = ac_texts(before.stdout), ac_texts(story.text)
        checks, checks_then = os.path.join(story.folder, "checks.md"), None
        for ac, text in new.items():
            ref = f"{story.id}/{ac}"
            if ac not in old or old[ac] == text:
                continue
            if project.tests.get(ref):
                tests = ", ".join(sorted({p for p, _, _ in project.tests[ref]}))
                project.problem(story.doc, story.acs[ac]["line"],
                                f"{ref} changed since {base}, and {tests} cite it — check they still prove it",
                                "warning")
            if story.acs[ac]["dropped"] or not os.path.isfile(native(checks)):
                continue
            if checks_then is None:
                checks_then = git(project.root, "show", f"{fork}:./{project.rel(checks)}").stdout
            then, now = {w for _, w in manual_reliance(checks_then, ac)}, manual_reliance(read(checks), ac)
            rerun = any(w.startswith("log:") and w not in then and w[4:].strip("| ")[:10] >= forked_on
                        for _, w in now)
            stale = [(n, w) for n, w in now if w in then]
            if stale and not rerun:
                at = ", ".join(str(n) for n, _ in stale)
                todo = "log a new run" if all(w.startswith("log:") for _, w in stale) else \
                    "re-read those scenarios and change them, or log a new run"
                project.problem(story.doc, story.acs[ac]["line"],
                                f"{ref} changed since {base}, and checks.md:{at} still check the old wording — "
                                f"{todo}", "warning")


# ---------------------------------------------------------------- generated blocks on a branch

BLOCK = re.compile(r"<!-- spry:(\w+) -->\n(.*?)<!-- /spry:\1 -->", re.S)


def block_drift(project: Project, base: str) -> list:
    """[(path, block name, line, the base's content)] for generated blocks this branch changed.

    Only CI on the main branch writes them, so a branch that commits its own copy conflicts with the
    next one CI writes. A block may match `base` as it is now or as it was where the branch forked —
    merging the main branch in brings CI's newer copy, and that is not drift."""
    if git(project.root, "rev-parse", "--verify", "--quiet", f"{base}^{{commit}}").returncode != 0:
        return []
    fork = git(project.root, "merge-base", base, "HEAD").stdout.strip()
    refs = [base] + ([fork] if fork else [])
    touched = git(project.root, "diff", "--relative", "--name-only", fork or base, "--", "spry")
    out = []
    for rel in sorted(line for line in touched.stdout.split("\n") if line.endswith(".md")):
        path = os.path.join(project.root, rel)
        if not os.path.isfile(native(path)) or rel.startswith(("spry/process/", "spry/history/")):
            continue
        olds = [dict(BLOCK.findall(shown.stdout)) for shown in
                (git(project.root, "show", f"{ref}:./{rel}") for ref in refs) if shown.returncode == 0]
        if not olds:
            continue  # new on this branch: nothing on the main branch to conflict with
        text = read(path)
        for m in BLOCK.finditer(text):
            name, content = m.group(1), m.group(2)
            known = [old[name] for old in olds if name in old]
            if known and content not in known:
                out.append((path, name, text[:m.start()].count("\n") + 1, known[0]))
    return out


def changed_blocks(project: Project, base: str):
    for path, name, line, _ in block_drift(project, base):
        project.problem(path, line, f"`spry:{name}` block differs from {base} — it is written only on the main "
                                    f"branch; `spry index --restore {base}` puts it back, "
                                    f"`spry view` shows a fresh copy")


def ids_at(project: Project, ref: str) -> dict:
    """{"T-5": "spry/plan/…/T-5-x/README.md"} — every plan item and decision as committed at `ref`."""
    plan, decisions = project.rel(project.plan_dir), project.rel(os.path.join(project.spry, "knowledge", "decisions"))
    done = git(project.root, "ls-tree", "-r", "--name-only", ref, "--", plan, decisions)
    out = {}
    for path in done.stdout.splitlines() if done.returncode == 0 else []:
        name, folder = os.path.basename(path), os.path.basename(os.path.dirname(path))
        if path.startswith(decisions + "/"):
            m = re.match(r"^(" + re.escape(project.ids["decision"]) + r"-\d+)\b.*\.md$", name)
            ident = m.group(1) if m else None
        elif name == "README.md" and (m := project.item_dir.match(folder)) \
                and project.type_of_prefix.get(m.group(1)) not in (None, "slice", "decision"):
            ident = f"{m.group(1)}-{m.group(2)}"
        else:
            m = project.slice_file.match(name)
            ident = f"{project.ids['slice']}-{m.group(1)}" if m else None
        if ident:
            out.setdefault(ident, path)
    return out


def id_collisions(project: Project, base: str):
    """An ID this branch added that `base` also added since they forked, for something else — the
    duplicate `check` would only see after the merge, when the number is in branch names and trailers."""
    if git(project.root, "rev-parse", "--verify", "--quiet", f"{base}^{{commit}}").returncode != 0:
        return
    fork = git(project.root, "merge-base", base, "HEAD").stdout.strip()
    if not fork:
        return  # a shallow clone or unrelated histories: every moved item would look new
    theirs, before = ids_at(project, base), ids_at(project, fork)
    here = {i.id: i.doc for i in project.items.values()} | dict(project.decisions)
    for ident, doc in sorted(here.items(), key=lambda kv: natural_key(kv[0])):
        there = theirs.get(ident)
        if there is None or ident in before:
            continue
        mine = project.rel(doc)
        if there == mine and git(project.root, "rev-parse", f"{base}:./{there}").stdout.strip() == \
                git(project.root, "hash-object", doc).stdout.strip():
            continue
        kind = project.type_of_prefix.get(ident.rsplit("-", 1)[0], "item")
        project.problem(doc, 1, f"{ident} is also {there} on {base} — both took the number. Merge {base} in, "
                                f"rename this one to `next {kind}`, and every place it is cited "
                                f"(`mint: main` takes numbers on the main branch, so this cannot happen)")


def restore_blocks(project: Project, base: str) -> list:
    """Put back the base's content in every generated block this branch changed. Returns the files."""
    changed = {}
    for path, name, _, content in block_drift(project, base):
        changed[path] = replace_block(changed.get(path) or read(path), name, content)
    for path, text in changed.items():
        write(path, text)
    return sorted(project.rel(p) for p in changed)


# ---------------------------------------------------------------- view / hooks

VIEWS = (("BACKLOG.md", "backlog", backlog_block), ("COVERAGE.md", "coverage", coverage_block),
         ("DONE.md", "done", done_block))
HOOK_MARK = "# spry: refresh .spry/view/"


def view(project: Project, since: str | None = None) -> list:
    """Write the backlog, coverage and done pages for this working tree to `.spry/view/`, never committed.

    With `since` (a git hook passes the commit it came from), only when the plan or a test file
    changed since then, or no view exists yet. Returns the files written."""
    folder = os.path.join(project.root, ".spry", "view")
    if since and all(os.path.isfile(native(os.path.join(folder, name))) for name, _, _ in VIEWS):
        diff = git(project.root, "diff", "--relative", "--name-only", since, "HEAD", "--", ".")
        globs = project._test_globs()
        paths = [p for p in diff.stdout.split("\n") if p]
        if diff.returncode == 0 and not any(p.startswith("spry/") or any(g.match(p) for g in globs) for p in paths):
            return []
    os.makedirs(native(folder), exist_ok=True)
    stamp = f"> Local view of this working tree, written {time.strftime('%Y-%m-%d %H:%M')} by `spry view`. Not committed."
    written = []
    for name, block, make in VIEWS:
        target = os.path.join(folder, name)
        content = make(project, target)
        source = os.path.join(project.spry, name)
        frame = read(source) if os.path.isfile(native(source)) else f"# {name[:-3].title()}\n\n<!-- spry:{block} -->\n<!-- /spry:{block} -->\n"
        text = replace_block(frame, block, content) or frame
        text = re.sub(r"^(# .*)$", lambda m: m.group(1) + "\n\n" + stamp, text, count=1, flags=re.M)
        write(target, text)
        written.append(project.rel(target))
    return written


def hooks(project: Project, remove: bool = False) -> list:
    """Install (or remove) git hooks that run `spry view --since` after a checkout or a pull.
    A hook spry did not write is never touched: the line to add is reported instead."""
    found = git(project.root, "rev-parse", "--git-path", "hooks")
    prefix = git(project.root, "rev-parse", "--show-prefix")
    if found.returncode != 0:
        raise SystemExit("not a git repository — hooks need one")
    folder = os.path.join(project.root, found.stdout.strip())
    prefix = prefix.stdout.strip()
    tool, config = shlex.quote(prefix + "spry/tool/spry.py"), shlex.quote(prefix + "spry/spry.config.json")
    run = (f"[ -f {config} ] && [ -f {tool} ] && command -v python3 >/dev/null 2>&1 || exit 0\n"
           f"python3 {tool} --root {shlex.quote(prefix or '.')} view --since \"$since\" || true\n")
    scripts = {"post-checkout": '[ "$3" = 1 ] || exit 0\nsince="$1"\n', "post-merge": "since=ORIG_HEAD\n"}
    out = []
    for name, head in scripts.items():
        path = os.path.join(folder, name)
        ours = os.path.isfile(native(path)) and HOOK_MARK in read(path)
        if remove:
            if ours:
                os.remove(native(path))
                out.append(f"removed: {name}")
            continue
        if os.path.isfile(native(path)) and not ours:
            out.append(f"kept: {name} is not spry's — add to it: python3 {tool} view --since <previous commit>")
            continue
        os.makedirs(native(folder), exist_ok=True)
        write(path, f"#!/bin/sh\n{HOOK_MARK} when the plan or a test changed. "
                    f"Remove: python3 {tool} hooks --remove\n{head}{run}")
        os.chmod(path, 0o755)
        out.append(f"wrote: {name}")
    return out


# ---------------------------------------------------------------- serve

SERVE_PORT = 8765
SERVE_STALE = 1.0  # seconds a read of the plan answers pages before the next request reads it again
SERVE_RAW = {"image/png", "image/jpeg", "image/gif", "image/webp", "image/svg+xml"}
SAFE_ATTRS = {"href", "src", "alt", "title", "open", "colspan", "rowspan", "align", "width", "height"}
LIST_ITEM = re.compile(r"^( *)([-*+]|\d{1,9}[.)])( +|$)(.*)$")
TABLE_SEP = re.compile(r"^\s*\|?\s*:?-+:?\s*(\|\s*:?-+:?\s*)*\|?\s*$")
RULE = re.compile(r"^ {0,3}([-*_])( *\1){2,} *$")


def safe_url(url: str) -> str:
    """A link target, or `#` for a scheme a page should never follow (`javascript:` …)."""
    url = url.strip()
    probe = re.sub(r"[\x00-\x20\x7f]", "", url)  # browsers drop these inside a URL: `java\tscript:` runs
    if re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*:", probe) and not re.match(r"^(https?|mailto):", probe, re.I):
        return "#"
    return url if probe == url else re.sub(r"[\x00-\x1f\x7f]", "", url)


def serve_href(project: Project, path: str) -> str:
    """The URL of a file under the project, quoted: a `#`, `?` or `%` in a name stays part of it."""
    import html
    from urllib.parse import quote
    return html.escape("/" + quote(project.rel(path)))


def heading_slug(text: str) -> str:
    """GitHub's anchor for a heading: lower case, punctuation dropped, spaces to `-`."""
    text = re.sub(r"<[^>]*>|[`*_~]|\[([^\]]*)\]\([^)]*\)", r"\1", text).strip().lower()
    return re.sub(r"\s", "-", re.sub(r"[^\w\s-]", "", text))


def md_inline(text: str, keep: list | None = None) -> str:
    """One paragraph's Markdown to HTML: code, links, images, emphasis, and the raw tags GitHub
    allows (HTML_TAGS, safe attributes only). Everything else is escaped — `<n>` stays text."""
    import html
    nested = keep is not None
    keep = [] if keep is None else keep  # shared with the call for a link's text, which holds its placeholders
    if not nested:
        text = text.replace("\x00", "\ufffd")  # \x00 marks a placeholder below

    def stash(s: str) -> str:
        keep.append(s)
        return f"\x00{len(keep) - 1}\x00"

    def tag(m):
        name = m.group(2).lower()
        if name not in HTML_TAGS:
            return m.group(0)
        if m.group(1):
            return stash(f"</{name}>")
        attrs = ""
        for key, value in re.findall(r"([a-zA-Z-]+)\s*=\s*(\"[^\"]*\"|'[^']*'|[^\s>]+)", m.group(3)):
            key, value = key.lower(), value.strip("\"'")
            if key in SAFE_ATTRS:
                value = safe_url(value) if key in ("href", "src") else value
                attrs += f' {key}="{html.escape(value)}"'
        if re.search(r"\bopen\b(?!\s*=)", m.group(3)) and name == "details":
            attrs += " open"
        return stash(f"<{name}{attrs}>")

    def link(m):
        return stash(f'<a href="{html.escape(safe_url(m.group(2)))}">{md_inline(m.group(1), keep)}</a>')

    def image(m):
        return stash(f'<img src="{html.escape(safe_url(m.group(2)))}" alt="{html.escape(m.group(1))}">')

    def bare(m):
        return stash(f'<a href="{html.escape(m.group(1))}">{html.escape(m.group(1))}</a>')

    text = re.sub(r"<!--.*?-->", "", text, flags=re.S)
    text = re.sub(r"(`+)(.+?)\1", lambda m: stash("<code>" + html.escape(m.group(2).strip()) + "</code>"), text)
    text = re.sub(r"\\([\\`*_{}\[\]()#+\-.!|~<>])", lambda m: stash(html.escape(m.group(1))), text)
    text = re.sub(r"<(https?://[^\s>]+)>", lambda m: bare(m), text)
    text = re.sub(r"<(/?)([a-zA-Z][a-zA-Z0-9]*)((?:\s[^<>]*)?)/?>", tag, text)
    text = re.sub(r"!\[([^\]]*)\]\(<?([^)\s>]+)>?(?:\s+\"[^\"]*\")?\)", image, text)
    text = re.sub(r"\[([^\]]+)\]\(<?([^)\s>]*)>?(?:\s+\"[^\"]*\")?\)", link, text)
    text = re.sub(r"(?<![\w/\"'=])(https?://[^\s<>\x00]*[^\s<>\x00.,;:!?)\]'\"])", bare, text)
    text = html.escape(text, quote=False)
    if len(text) < 20_000:  # the emphasis patterns are quadratic: a pathological paragraph stays plain
        text = re.sub(r"\*\*(?!\s)(.+?)(?<!\s)\*\*|(?<!\w)__(?!\s)(.+?)(?<!\s)__(?!\w)",
                      lambda m: f"<strong>{m.group(1) or m.group(2)}</strong>", text)
        text = re.sub(r"(?<![\w*])\*(?![\s*])(.+?)(?<![\s*])\*(?![\w*])|(?<!\w)_(?![\s_])(.+?)(?<![\s_])_(?!\w)",
                      lambda m: f"<em>{m.group(1) or m.group(2)}</em>", text)
        text = re.sub(r"~~(?!\s)(.+?)(?<!\s)~~", r"<del>\1</del>", text)
    text = re.sub(r"(?: {2,}|\\)\n", "<br>\n", text)
    if nested:
        return text
    restore = re.compile(r"\x00(\d+)\x00")
    for _ in range(3):  # a link's text holds placeholders of its own: two rounds, and one to spare
        text = restore.sub(lambda m: keep[int(m.group(1))], text)
    return text


def table_cells(line: str) -> list:
    """A table row's cells: split on `|`, but not on `\\|` or inside `code`."""
    cells, cell, code = [], "", False
    s = line.strip()
    s = s[1:] if s.startswith("|") else s
    s = s[:-1] if s.endswith("|") and not s.endswith("\\|") else s
    i = 0
    while i < len(s):
        c = s[i]
        if c == "\\" and s[i + 1:i + 2] == "|":
            cell, i = cell + "|", i + 2
            continue
        if c == "`":
            code = not code
        if c == "|" and not code:
            cells.append(cell.strip())
            cell = ""
        else:
            cell += c
        i += 1
    return cells + [cell.strip()]


def starts_block(lines: list, i: int) -> bool:
    """Does line `i` begin a block other than a paragraph or a list?"""
    s = lines[i].strip()
    return bool(FENCE.match(lines[i]) or HEADING.match(s) or RULE.match(lines[i]) or s.startswith((">", "<!--"))
                or ("|" in s and i + 1 < len(lines) and "-" in lines[i + 1] and TABLE_SEP.match(lines[i + 1])))


def md_html(text: str, slugs: dict | None = None, tight: bool = False) -> str:
    """Markdown to HTML, standard library only: what spry's documents use — headings, paragraphs,
    lists (nested, tasks), tables, quotes, code fences, rules, and the raw tags GitHub allows.
    HTML comments, spry's markers among them, are dropped."""
    import html
    slugs = {} if slugs is None else slugs
    lines = [re.sub(r"^\s+", lambda m: m.group(0).expandtabs(4), line) for line in text.split("\n")]
    out, i, n = [], 0, len(lines)
    while i < n:
        line, s = lines[i], lines[i].strip()
        if not s:
            i += 1
            continue
        fence = re.match(r"^\s*(`{3,}|~{3,})", line)
        if fence:
            mark, indent = fence.group(1), len(line) - len(line.lstrip())
            lang = s[len(mark):].strip().split()[0] if s[len(mark):].strip() else ""
            close = re.compile(r"^\s*" + re.escape(mark[0]) + "{" + str(len(mark)) + r",}\s*$")
            body, i = [], i + 1
            while i < n and not close.match(lines[i]):
                body.append(lines[i][indent:] if not lines[i][:indent].strip() else lines[i])
                i += 1
            i += 1
            cls = f' class="language-{html.escape(lang)}"' if lang else ""
            out.append(f"<pre><code{cls}>{html.escape(chr(10).join(body))}</code></pre>")
            continue
        if s.startswith("<!--"):
            while i < n and "-->" not in lines[i]:
                i += 1
            rest = lines[i].split("-->", 1)[1].strip() if i < n else ""
            if rest:
                out.append(md_inline(rest))
            i += 1
            continue
        heading = HEADING.match(s)
        if heading:
            level, title = len(heading.group(1)), heading.group(2)
            slug = base = heading_slug(title)
            if base in slugs:
                slugs[base] += 1
                slug = f"{base}-{slugs[base]}"
            else:
                slugs[base] = 0
            out.append(f'<h{level} id="{html.escape(slug)}">{md_inline(title)}</h{level}>')
            i += 1
            continue
        if RULE.match(line):
            out.append("<hr>")
            i += 1
            continue
        if "|" in s and i + 1 < n and "-" in lines[i + 1] and TABLE_SEP.match(lines[i + 1]):
            aligns = []
            for cell in table_cells(lines[i + 1]):
                left, right = cell.startswith(":"), cell.endswith(":")
                aligns.append("center" if left and right else "right" if right else "left" if left else "")
            head = table_cells(line)
            rows, i = [], i + 2
            while i < n and lines[i].strip() and "|" in lines[i]:
                rows.append(table_cells(lines[i]))
                i += 1

            def cells(row, tag):
                row = (row + [""] * len(head))[:len(head)]
                return "".join(f"<{tag}" + (f' style="text-align:{aligns[k]}"' if k < len(aligns) and aligns[k] else "")
                               + f">{md_inline(c)}</{tag}>" for k, c in enumerate(row))
            body = "".join(f"<tr>{cells(r, 'td')}</tr>" for r in rows)
            out.append(f"<div class=\"table\"><table><thead><tr>{cells(head, 'th')}</tr></thead><tbody>{body}</tbody></table></div>")
            continue
        if s.startswith(">"):
            quote = []
            while i < n and lines[i].strip().startswith(">"):
                quote.append(re.sub(r"^\s*> ?", "", lines[i]))
                i += 1
            out.append(f"<blockquote>{md_html(chr(10).join(quote), slugs)}</blockquote>")
            continue
        item = LIST_ITEM.match(line)
        if item:
            depth, ordered = len(item.group(1)), item.group(2)[0].isdigit()
            start = int(item.group(2)[:-1]) if ordered else 1
            entries, loose = [], False
            while i < n:
                item = LIST_ITEM.match(lines[i])
                if not item or len(item.group(1)) != depth or item.group(2)[0].isdigit() != ordered or RULE.match(lines[i]):
                    break
                inner = depth + len(item.group(2)) + (len(item.group(3)) if item.group(4) else 1)
                body, i = [item.group(4)], i + 1
                while i < n:
                    if not lines[i].strip():
                        j = i
                        while j < n and not lines[j].strip():
                            j += 1
                        if j < n and len(lines[j]) - len(lines[j].lstrip()) > depth:
                            if not LIST_ITEM.match(lines[j]):
                                loose = True
                            body += [""] * (j - i)
                            i = j
                            continue
                        break
                    indent = len(lines[i]) - len(lines[i].lstrip())
                    if indent > depth:
                        body.append(lines[i][min(indent, inner):])
                    elif LIST_ITEM.match(lines[i]) or starts_block(lines, i):
                        break
                    else:
                        body.append(lines[i].strip())
                    i += 1
                entries.append(body)
                j = i
                while j < n and not lines[j].strip():
                    j += 1
                after = LIST_ITEM.match(lines[j]) if j < n else None
                if j > i and after and len(after.group(1)) == depth and after.group(2)[0].isdigit() == ordered:
                    loose, i = True, j
            parts = []
            for body in entries:
                box = re.match(r"^\[([ xX])\] ", body[0])
                if box:
                    body = [body[0][4:]] + body[1:]
                content = md_html("\n".join(body), slugs, tight=not loose)
                if box:
                    checked = " checked" if box.group(1) != " " else ""
                    parts.append(f'<li class="task"><input type="checkbox" disabled{checked}> {content}</li>')
                else:
                    parts.append(f"<li>{content}</li>")
            tag = "ol" if ordered else "ul"
            first = f' start="{start}"' if ordered and start != 1 else ""
            out.append(f"<{tag}{first}>{''.join(parts)}</{tag}>")
            continue
        if re.match(r"^</?([a-zA-Z][a-zA-Z0-9]*)", s) and re.match(r"^</?([a-zA-Z][a-zA-Z0-9]*)", s).group(1).lower() in HTML_TAGS:
            out.append(md_inline(s))
            i += 1
            continue
        para = []
        while i < n and lines[i].strip() and not starts_block(lines, i) and not (para and LIST_ITEM.match(lines[i])):
            para.append(lines[i].strip() if not lines[i].endswith("  ") else lines[i].lstrip())
            i += 1
        text_html = md_inline("\n".join(para))
        out.append(text_html if tight else f"<p>{text_html}</p>")
    return "\n".join(out)


def github_url(root: str) -> str | None:
    """https://github.com/<owner>/<repo> from the `origin` remote, for PR, issue and branch links."""
    done = git(root, "remote", "get-url", REMOTE)
    m = re.search(r"github\.com[:/]([^/\s]+)/([^/\s]+?)(?:\.git)?/?$", done.stdout.strip()) if done.returncode == 0 else None
    return f"https://github.com/{m.group(1)}/{m.group(2)}" if m else None


def serve_short(project: Project, item: Item) -> str:
    """A tree row's count: a slice's state, or done/total of what the item counts."""
    if item.type == "slice":
        return "done" if project.done(item) else item.state
    kind = project.child_level(item.type)
    kids = project.counted(item, kind) if kind else []
    return f"{sum(map(project.done, kids))}/{len(kids)}" if kids else ""


def serve_mark(project: Project, item: Item) -> str:
    if project.done(item):
        return "done"
    if item.state in ("dropped", "draft", "open", "closed"):
        return item.state
    if item.type == "slice" and claimed(item):
        return "open"
    return "todo"


def serve_tree(project: Project, current: Item | None) -> str:
    import html
    chain = {current.id} | {a.id for a in current.ancestors()} if current else set()
    order = {"task": 1, "bug": 2, "slice": 3}

    def node(item: Item) -> str:
        here = ' aria-current="page"' if current is item else ""
        row = (f'<a href="{serve_href(project, item.doc)}"{here} title="{html.escape(project.progress(item))}">'
               f'<i class="mark {serve_mark(project, item)}"></i><b>{html.escape(item.id)}</b> '
               f'<span>{html.escape(item.title)}</span><small>{html.escape(serve_short(project, item))}</small></a>')
        kids = sorted(item.children, key=lambda c: order.get(c.type, 0))
        if not kids:
            return f"<li>{row}</li>"
        open_ = " open" if item.id in chain or (not current and item in project.top) else ""
        return f"<li><details{open_}><summary>{row}</summary><ul>{''.join(map(node, kids))}</ul></details></li>"

    return f"<ul>{''.join(map(node, project.top))}</ul>" if project.top else "<p>No plan yet.</p>"


def serve_meta(project: Project, item: Item, repo: str | None) -> str:
    """Breadcrumbs and front-matter as badges; IDs link to their items."""
    import html

    def ref(ident: str) -> str:
        target = project.items.get(ident.split("/")[0])
        if not target:
            return html.escape(ident)
        return f'<a href="{serve_href(project, target.doc)}" title="{html.escape(target.title)}">{html.escape(ident)}</a>'

    crumbs = " › ".join(f'<a href="{serve_href(project, a.doc)}">{html.escape(a.label)}</a>'
                        for a in reversed(item.ancestors()))
    badges = [f'<span class="badge type">{html.escape(item.type)}</span>',
              f'<span class="badge {serve_mark(project, item)}">{html.escape(project.progress(item))}</span>']
    fm = item.fm
    for key in ("owner", "audience", "severity", "closed"):
        if fm.get(key):
            badges.append(f'<span class="badge">{key} {html.escape(str(fm[key]))}</span>')
    pr, issue, branch = fm.get("pr", ""), fm.get("issue", ""), fm.get("branch", "")
    for key, value, path in (("PR", pr, "pull"), ("issue", issue, "issues")):
        if isinstance(value, str) and value.isdigit():
            label = f"{key} #{value}"
            badges.append(f'<a class="badge" href="{repo}/{path}/{value}">{label}</a>' if repo
                          else f'<span class="badge">{label}</span>')
    if branch:
        badges.append(f'<span class="badge"><code>{html.escape(branch)}</code></span>')
    rows = []
    for key, label in (("covers", "Covers"), ("blocked_by", "Blocked by"), ("breaks", "Breaks"), ("related", "Related")):
        values = fm.get(key) or []
        if isinstance(values, list) and values:
            if key == "covers" and item.parent:
                values = [f"{item.parent.id}/{v}" if "/" not in v else v for v in values]
            rows.append(f"<dt>{label}</dt><dd>{', '.join(ref(v) for v in values)}</dd>")
    links = f"<dl>{''.join(rows)}</dl>" if rows else ""
    return (f'<nav class="crumbs">{crumbs}</nav>' if crumbs else "") + f'<div class="badges">{"".join(badges)}</div>{links}'


SERVE_CSS = """
:root{--bg:#fff;--soft:#f7f8f5;--muted:#eef1ea;--code:#f4f6f1;--text:#171a16;--dim:#5c6458;--line:#e2e6dd;
--accent:#2f7d32;--accent-soft:#e9f4e6;--warn:#9a5b00;--warn-soft:#fdf3e2;--note:#2563a8;--note-soft:#eaf2fb;
--mono:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;color-scheme:light}
@media (prefers-color-scheme:dark){:root{--bg:#0e110e;--soft:#141814;--muted:#1b201b;--code:#161b16;--text:#e6ebe3;
--dim:#9aa496;--line:#252b24;--accent:#7cd67f;--accent-soft:rgb(124 214 127/10%);--warn:#f0b962;
--warn-soft:rgb(240 185 98/10%);--note:#7db3f0;--note-soft:rgb(125 179 240/10%);color-scheme:dark}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--text);
font:15px/1.6 ui-sans-serif,system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}
a{color:var(--accent)}header{position:sticky;top:0;z-index:2;display:flex;gap:16px;align-items:center;
padding:10px 20px;background:var(--bg);border-bottom:1px solid var(--line);flex-wrap:wrap}
header .brand{font-weight:700;color:var(--text);text-decoration:none}header nav{display:flex;gap:14px;flex-wrap:wrap}
header nav a{color:var(--dim);text-decoration:none}header nav a:hover{color:var(--accent)}
header form{margin-left:auto}header input{font:inherit;padding:5px 10px;border:1px solid var(--line);
border-radius:8px;background:var(--soft);color:var(--text);width:220px}
.wrap{display:grid;grid-template-columns:320px minmax(0,1fr)}
aside{position:sticky;top:53px;height:calc(100vh - 53px);overflow:auto;padding:12px 8px 40px;
border-right:1px solid var(--line);background:var(--soft);font-size:13.5px}
aside ul{list-style:none;margin:0;padding-left:12px}aside>ul{padding-left:0}
aside a{display:flex;gap:6px;align-items:baseline;padding:2px 6px;border-radius:6px;color:var(--text);text-decoration:none}
aside a:hover{background:var(--muted)}aside a[aria-current]{background:var(--accent-soft);color:var(--accent)}
aside a span{flex:1;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
aside small{color:var(--dim);font-family:var(--mono);font-size:11px}aside summary{list-style:none;cursor:pointer}
aside summary::-webkit-details-marker{display:none}aside summary>a::before{content:"▸";color:var(--dim);width:8px}
aside details[open]>summary>a::before{content:"▾"}aside li>a{padding-left:20px}
.mark{flex:none;width:8px;height:8px;border-radius:50%;border:1.5px solid var(--dim);align-self:center}
.mark.done{background:var(--accent);border-color:var(--accent)}.mark.open,.mark.closed{background:var(--warn);border-color:var(--warn)}
.mark.draft{border-style:dashed}.mark.dropped{opacity:.35}
main{padding:24px 40px 80px;max-width:1200px}.path{font-family:var(--mono);font-size:12px;color:var(--dim)}
.crumbs{font-size:13px;color:var(--dim)}.crumbs a{color:var(--dim)}.badges{display:flex;gap:6px;flex-wrap:wrap;margin:8px 0}
.badge{font-size:12px;padding:2px 8px;border-radius:999px;background:var(--muted);color:var(--text);text-decoration:none}
.badge.type{text-transform:uppercase;letter-spacing:.04em;font-weight:600}.badge.done{background:var(--accent-soft);color:var(--accent)}
.badge.open,.badge.closed{background:var(--warn-soft);color:var(--warn)}dl{display:grid;grid-template-columns:auto 1fr;gap:2px 12px;font-size:13px;margin:6px 0}
dt{color:var(--dim)}dd{margin:0}h1,h2,h3{line-height:1.25}h1{font-size:28px;margin:12px 0 8px}h2{margin-top:32px;
padding-bottom:4px;border-bottom:1px solid var(--line)}code{font-family:var(--mono);font-size:.9em;background:var(--code);
padding:1px 4px;border-radius:4px}pre{background:var(--code);padding:12px 14px;border-radius:8px;overflow:auto}
pre code{padding:0;background:none}.table{overflow:auto;margin:12px 0}table{border-collapse:collapse;width:100%}
th,td{border:1px solid var(--line);padding:5px 10px;text-align:left;vertical-align:top}th{background:var(--soft)}td:first-child{white-space:nowrap}
blockquote{margin:12px 0;padding:4px 14px;border-left:3px solid var(--note);background:var(--note-soft)}
li.task{list-style:none}li.task input{margin-left:-20px}mark{background:var(--warn-soft);color:inherit}
.hits li{margin:10px 0}.hits small{display:block;color:var(--dim)}
@media (max-width:800px){.wrap{display:block}aside{position:static;height:auto;max-height:40vh;border-right:0;
border-bottom:1px solid var(--line)}main{padding:16px}header input{width:100%}header form{margin-left:0;width:100%}}
"""


def serve_page(project: Project, title: str, main: str, current: Item | None = None) -> bytes:
    import html
    s = project.spry
    nav = [("Home", os.path.join(s, "README.md")), ("Roadmap", os.path.join(project.plan_dir, "README.md")),
           ("Backlog", os.path.join(s, "BACKLOG.md")), ("Coverage", os.path.join(s, "COVERAGE.md")),
           ("Done", os.path.join(s, "DONE.md")), ("Knowledge", os.path.join(s, "knowledge")),
           ("Glossary", os.path.join(project.root, project.config.get("glossary", "spry/knowledge/glossary.md"))),
           ("AGENTS.md", os.path.join(project.root, "AGENTS.md"))]
    links = "".join(f'<a href="{serve_href(project, p)}{"/" if os.path.isdir(native(p)) else ""}">{label}</a>'
                    for label, p in nav if os.path.exists(native(p)))
    if os.path.isfile(native(os.path.join(project.root, ".spry", "view", "pace.md"))):
        links += '<a href="/-/pace">Pace</a>'
    product = html.escape(project.config.get("product") or "spry")
    page = (f'<!doctype html><html lang="en"><head><meta charset="utf-8">'
            f'<meta name="viewport" content="width=device-width,initial-scale=1">'
            f"<title>{html.escape(title)} · {product}</title><style>{SERVE_CSS}</style></head><body>"
            f'<header><a class="brand" href="/">{product}</a><nav>{links}</nav>'
            f'<form action="/-/search"><input name="q" type="search" placeholder="Search the plan and knowledge"></form></header>'
            f'<div class="wrap"><aside>{serve_tree(project, current)}</aside><main>{main}</main></div></body></html>')
    return page.encode("utf-8")


class Snapshot:
    """The plan as last read, for `serve`. A page asked for more than SERVE_STALE seconds after the
    last read is answered from it while a fresh read runs in the background, so pages come at once
    even where reading the plan takes seconds, and a change shows by the next click. The page's own
    document is always read fresh."""

    def __init__(self, root: str):
        self.root, self.lock, self.busy = root, threading.Lock(), False
        self.project = Project(root)
        self.makers, self.at = block_makers(self.project), time.time()

    def get(self) -> tuple:
        with self.lock:
            if not self.busy and time.time() - self.at > SERVE_STALE:
                self.busy = True
                threading.Thread(target=self._read, daemon=True).start()
            return self.project, self.makers

    def _read(self):
        try:
            project = Project(self.root)
            makers = block_makers(project)
            with self.lock:
                self.project, self.makers = project, makers
        except BaseException:  # a config broken mid-edit: keep showing the last good read
            pass
        finally:
            with self.lock:
                self.at, self.busy = time.time(), False


def serve_response(project: Project, path: str, repo: str | None = None, makers: dict | None = None) -> tuple:
    """(status, content type, body, headers) for one GET. Read-only: nothing here writes a document."""
    import html
    import mimetypes
    from urllib.parse import parse_qs, quote, unquote, urlsplit
    url = urlsplit(path)
    redirect = lambda to: (302, "text/plain", b"", {"Location": quote(to)})  # noqa: E731
    if url.path == "/":
        home = os.path.join(project.spry, "README.md")
        return redirect("/" + project.rel(home if os.path.isfile(native(home)) else os.path.join(project.plan_dir, "README.md")))
    if url.path == "/-/search":
        query = (parse_qs(url.query).get("q") or [""])[0]
        hits = find(project, query, limit=30, marks=("\x01", "\x02")) if query.strip() else []
        rows = []
        for rel, _line, heading, snippet in hits:
            anchor = heading_slug(heading.split(" › ", 1)[1]) if " › " in heading else ""
            snippet = html.escape(snippet).replace("\x01", "<mark>").replace("\x02", "</mark>")
            rows.append(f'<li><a href="/{html.escape(quote(rel))}{"#" + html.escape(anchor) if anchor else ""}">{html.escape(heading)}</a>'
                        f'<small>{html.escape(rel)}</small>{snippet}</li>')
        found = f'<ol class="hits">{"".join(rows)}</ol>' if rows else ("<p>Nothing found.</p>" if query.strip() else "")
        return 200, "text/html; charset=utf-8", serve_page(project, f"Search {query}", f"<h1>Search: {html.escape(query)}</h1>{found}"), {}
    if url.path == "/-/pace":
        page = os.path.join(project.root, ".spry", "view", "pace.md")
        text = read(page) if os.path.isfile(native(page)) else "# Pace\n\nNo page yet: run `spry pace` to write it.\n"
        return 200, "text/html; charset=utf-8", serve_page(project, "Pace", md_html(text)), {}
    if url.path.startswith("/-/item/"):
        item = project.items.get(url.path[len("/-/item/"):])
        return redirect("/" + project.rel(item.doc)) if item else (404, "text/plain", b"no such item", {})
    rel = unquote(url.path).lstrip("/")
    parts = [p for p in rel.split("/") if p]
    doc = os.path.join(project.root, *parts)
    target = os.path.realpath(native(doc))
    real_root = os.path.realpath(native(project.root))
    inside = target == real_root or target.startswith(real_root + os.sep)
    real_parts = os.path.relpath(target, real_root).split(os.sep) if inside else []
    hidden = any(p.startswith(".") or p in SKIP_DIRS for p in parts + [p for p in real_parts if p != "."])
    if not inside or hidden or not os.path.exists(native(target)):  # a link to `.git` or `.env` is hidden too
        return 404, "text/html; charset=utf-8", serve_page(project, "Not found", f"<h1>Not found</h1><p><code>{html.escape(rel)}</code></p>"), {}
    if os.path.isdir(native(target)):
        for name in ("README.md", "INDEX.md"):
            if os.path.isfile(native(os.path.join(target, name))):
                return redirect("/" + "/".join(parts + [name]))
        if not url.path.endswith("/"):
            return redirect("/" + "/".join(parts) + "/")
        names = [n for n in sorted(os.listdir(native(target)), key=natural_key) if not n.startswith(".") and n not in SKIP_DIRS]
        items = "".join(f'<li><a href="./{html.escape(quote(n))}{"/" if os.path.isdir(native(os.path.join(target, n))) else ""}">'
                        f'{html.escape(n)}</a></li>' for n in names)
        return 200, "text/html; charset=utf-8", serve_page(project, rel or "/", f'<p class="path">{html.escape(rel)}</p><ul>{items}</ul>'), {}
    with open(native(target), "rb") as handle:
        data = handle.read()
    kind = mimetypes.guess_type(target)[0] or ""
    if kind in SERVE_RAW:  # an image a document shows; never a page that could run script
        return 200, kind, data, {"Content-Security-Policy": "sandbox; script-src 'none'"}
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        return 200, "application/octet-stream", data, {"Content-Security-Policy": "sandbox; script-src 'none'"}
    head = f'<p class="path">{html.escape(project.rel(doc))}</p>'
    if not target.endswith(".md"):
        return 200, "text/html; charset=utf-8", serve_page(project, os.path.basename(target),
                                                           f"{head}<pre><code>{html.escape(text)}</code></pre>"), {}
    for name, make, _required in (block_makers(project) if makers is None else makers).get(doc, []):
        text = replace_block(text, name, make()) or text
    item = next((i for i in project.items.values() if i.doc == doc), None)
    fm, start, _ = parse_front_matter(text)
    body = "\n".join(text.split("\n")[start:]) if fm is not None else text
    meta = serve_meta(project, item, repo) if item else ""
    title = item.label if item else (fm or {}).get("title") or os.path.basename(target)
    return 200, "text/html; charset=utf-8", serve_page(project, title, head + meta + md_html(body), item), {}


def serve(root: str, port: int | None = None, open_browser: bool = True, say=print) -> None:
    """Browse the plan and knowledge at http://127.0.0.1:<port>/ until Ctrl-C. Local only."""
    import http.server
    import webbrowser
    say("spry: reading the plan …")
    snapshot, repo = Snapshot(root), github_url(root)
    lock = threading.Lock()

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            host = (self.headers.get("Host") or "").rsplit(":", 1)[0]
            if host not in ("127.0.0.1", "localhost"):
                self.send_error(403, "spry serve answers only on 127.0.0.1 and localhost")
                return
            try:
                with lock:  # one page at a time: `find` writes the search index
                    project, makers = snapshot.get()
                    code, ctype, body, headers = serve_response(project, self.path, repo, makers)
            except Exception as e:  # a broken document shows as an error page, not a dead server
                code, ctype, headers = 500, "text/plain; charset=utf-8", {}
                body = f"spry serve: {type(e).__name__}: {e}".encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            for key, value in headers.items():
                self.send_header(key, value)
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *args):
            pass

    server = None
    for candidate in [port] if port else range(SERVE_PORT, SERVE_PORT + 10):
        try:
            server = http.server.ThreadingHTTPServer(("127.0.0.1", candidate), Handler)
            break
        except OSError as e:
            if port:
                raise SystemExit(f"cannot listen on port {candidate}: {e}")
    if server is None:
        raise SystemExit(f"ports {SERVE_PORT}–{SERVE_PORT + 9} are all taken — pass --port")
    server.daemon_threads = True

    def warm():
        with lock:
            find(snapshot.project, "spry")  # builds the search index once, so the first search is quick
    threading.Thread(target=warm, daemon=True).start()
    address = f"http://127.0.0.1:{server.server_address[1]}/"
    say(f"spry: serving {address} — read-only, this machine only. Ctrl-C stops it.")
    sys.stdout.flush()
    if open_browser:
        webbrowser.open(address)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


# ---------------------------------------------------------------- merge-check / merge-message

def falsify_table(item: Item) -> list:
    """Cells of each result row in the slice's Falsify table, row keys left out."""
    lines = section_lines(item.text, "Falsify") or []
    rows = [[ROW_KEY.sub("", c) for c in cells] for _i, cells in table_rows(lines)]
    return [r for r in rows if r and r[0].lower() != "control"]


def falsify_keys(item: Item) -> set:
    return {m.group(1) for _i, line in section_lines(item.text, "Falsify") or [] for m in ROW_KEY.finditer(line)}


def merge_check(project: Project, slice_id: str, base: str | None = None) -> list:
    """[(status, line)] — status `ok`, `warn` (merge may go ahead, someone must act) or `block`."""
    item = project.items.get(slice_id)
    if item is None or item.type != "slice":
        raise SystemExit(f"no slice {slice_id}")
    out = []
    out.append(("ok", "state is closed") if item.state == "closed"
               else ("block", f"state is `{item.state}` — run /spry:slice-close first"))
    out.append(("ok", f"closed {closed_on(item)}") if closed_on(item)
               else ("block", "no `closed:` date — set it to the day the slice closed (YYYY-MM-DD)"))
    out.append(("ok", f"built by {owner_of(item)}") if owner_of(item)
               else ("block", f"no `owner:` — who built it: `link {item.id} --owner`"))
    out.append(("ok", f"PR #{item.fm['pr']}") if str(item.fm.get("pr", "")).isdigit()
               else ("block", "no `pr:` number in the slice"))
    rows = falsify_table(item)
    if not rows and base and not added_or_none(project, base):
        out.append(("ok", "falsify: the branch adds no source lines — nothing to falsify"))
    elif not rows:
        out.append(("block", "no falsify results — run `falsify run … --record` at close"))
    for cells in rows:
        result = cells[-1].strip()
        control = cells[0].replace("\\|", "|")
        reason = re.sub(r"^\w+\s*(—|--|-|:)?\s*", "", result)
        if result.lower() == "survived":
            out.append(("block", f"falsify: `{control}` survived — add a test and re-run, or write the reason after `survived`"))
        elif result.lower().startswith("survived"):
            out.append(("warn", f"falsify: `{control}` survived, because \"{reason}\" — a person accepts this at the merge, or it gets a test"))
        elif result.lower().startswith("skipped"):
            out.append(("warn", f"falsify: `{control}` was not run, because \"{reason}\" — a person accepts this at the merge, or it is run"))
        elif result.lower().startswith("unreliable"):
            out.append(("warn", f"falsify: `{control}` unreliable — its tests never ran green; say why or re-run"))
    if base:
        out += required_controls(project, item, rows, base)
        out += criteria_and_code(project, item, base)
    else:
        out.append(("warn", "no --base: the controls the diff requires and any criteria it changes were not checked"))
    story = item.parent if item.parent and item.parent.type == "story" else None
    for ac in (item.fm.get("covers") or []) if story else []:
        ref = f"{story.id}/{ac}"
        tests = len(project.tests.get(ref, []))
        manual = project.manual.get(story.id, {}).get(ac)
        said = [f"{tests} test{'s' if tests != 1 else ''}"] if tests else []
        if manual:
            said.append(f"manual {manual[3]} {manual[0]}")
        if project.proof(story, ac)[0]:
            out.append(("ok", f"{ref} proven — {', '.join(said)}"))
        elif manual and manual[3] == "fail":
            out.append(("warn", f"{ref} — the latest manual check failed ({manual[0]}, {manual[2]}); is there a bug for it?"))
        else:
            out.append(("warn", f"{ref} — no test cites it; QA must check it by hand after the merge"))
    if base:
        changed_criteria(project, base)
        id_collisions(project, base)
    errors = [p for p in check(project) if p.level == "error"]
    out.append(("ok", "spry check clean") if not errors
               else ("block", f"spry check: {len(errors)} error{'s' if len(errors) != 1 else ''} — first: {errors[0]}"))
    for p in project.problems:
        if p.level == "warning" and "changed since" in p.message:
            out.append(("warn", p.message))
    return out


def added_or_none(project: Project, base: str) -> bool:
    """Did the branch add any source line? True when unsure, so an unreadable base never waives falsify."""
    try:
        return any(line.strip() for _path, line in added_source(project, base))
    except PlanError:
        return True


def required_controls(project: Project, item: Item, rows: list, base: str) -> list:
    """Every control `falsify suggest` finds in the diff must have a row: the agent adds, never drops."""
    try:
        wanted = falsify_suggest(project, item.id, base, fallback=False)
    except PlanError as e:
        return [("block", f"falsify: cannot list the controls the diff requires — {e}")]
    have = {" ".join(cells[0].replace("\\|", "|").split()) for cells in rows}
    keys = falsify_keys(item)
    missing = [e for e in wanted if control_key(e["file"], e["find"]) not in keys
               and " ".join(e["control"].split()) not in have]
    if not missing:
        return [("ok", f"falsify: all {len(wanted)} control{'s' if len(wanted) != 1 else ''} the diff adds were run")] if wanted else []
    return [("block", f"falsify: `{e['control']}` ({e['file']}) was not run — run it, or record it as "
                      f"`skipped — <reason>` for a person to accept") for e in missing]


def criteria_and_code(project: Project, item: Item, base: str) -> list:
    """Criteria changed in a branch that also changes code need the story owner's approval in the slice."""
    edits = criteria_edits(project, base)
    if not edits or not code_changed(project, base):
        return []
    approved = str(item.fm.get("criteria_approved_by") or "").strip()
    owners = {str(story.fm.get("owner") or "").strip() for story, *_ in edits} - {""}
    said = "; ".join(f"{story.id}/{ac}: \"{old}\" → " + (f"\"{new}\"" if new is not None else "removed")
                     for story, ac, old, new in edits)
    if approved and (not owners or approved in owners):
        return [("ok", f"criteria changed with the code, approved by {approved}: {said}")]
    who = " or ".join(sorted(owners)) or "the story's owner"
    return [("block", f"criteria changed in the same branch as the code — {said}. Only {who} approves this: "
                      f"after reading it, they add `criteria_approved_by: <name>` to {item.id}")]


def merge_message(project: Project, slice_id: str, ci_local: str | None = None) -> str:
    """Subject, blank line, body: the slice summary, then the trailers. For `gh pr merge --squash`.
    `ci_local`: why CI never ran — the trailer says the gate stood in for it, at which commit."""
    item = project.items.get(slice_id)
    if item is None or item.type != "slice":
        raise SystemExit(f"no slice {slice_id}")
    pr = f" (#{item.fm['pr']})" if str(item.fm.get("pr", "")).isdigit() else ""
    summary = [line.rstrip() for _i, line in (section_lines(item.text, "Summary") or [])
               if line.strip() and not line.strip().startswith("<!--")]
    trailers = [f"Slice: {item.id}"]
    if item.parent:
        trailers.append(f"Parent: {item.parent.id}")
    if item.parent and item.parent.type == "story" and item.fm.get("covers"):
        trailers.append("Covers: " + ", ".join(f"{item.parent.id}/{ac}" for ac in item.fm["covers"]))
    if str(item.fm.get("issue", "")).isdigit():
        trailers.append(f"Closes #{item.fm['issue']}")
    if ci_local:
        head = git(project.root, "rev-parse", "--short", "HEAD").stdout.strip() or "?"
        trailers.append(f"CI: did not run ({' '.join(ci_local.split())}); gate green locally at {head}")
    return f"{item.id} {item.title}{pr}\n\n" + ("\n".join(summary) + "\n\n" if summary else "") + "\n".join(trailers) + "\n"


# ---------------------------------------------------------------- gate

def code_fingerprint(project: Project, base: str | None = None):
    """A hash of every file a test result can depend on — tracked and untracked, minus `checks.docs`.
    None outside git, so the gate always runs there."""
    docs = [glob_regex(g) for g in project.config.get("checks", {}).get("docs") or DEFAULT_DOCS]
    staged = git(project.root, "ls-files", "-s", "--", ".")
    dirty = git(project.root, "ls-files", "-m", "-o", "--exclude-standard", "--", ".")
    if staged.returncode != 0 or dirty.returncode != 0:
        return None
    changed = {line for line in dirty.stdout.split("\n") if line}
    entries = {}
    for line in staged.stdout.split("\n"):
        meta, _, path = line.partition("\t")
        if path and path not in changed:
            entries[path] = meta.split()[1]
    for path in changed:
        full = os.path.join(project.root, path)
        try:
            with open(native(full), "rb") as handle:
                entries[path] = hashlib.sha1(handle.read()).hexdigest()
        except OSError:
            entries[path] = "deleted"
    digest = hashlib.sha256()
    for path in sorted(entries):
        # Untracked output a run leaves behind (`__pycache__`, `coverage`, `.spry/green` itself) is not code.
        if path in changed and SKIP_DIRS.intersection(path.split("/")[:-1]):
            continue
        if not any(g.match(path) for g in docs):
            digest.update(f"{path} {entries[path]}\n".encode())
    return digest.hexdigest()


def named_commands(entries, key: str, prefix: str = "") -> list:
    """[(name, command, key)] from a config list of commands, each a string or {"name", "run"}."""
    out = []
    for n, entry in enumerate(entries or [], 1):
        name, command = (entry.get("name"), entry.get("run")) if isinstance(entry, dict) else (None, entry)
        command = str(command or "")
        out.append((prefix + (name or (command.split()[0] if command.split() else f"check {n}")), command, key))
    return out


def gate_steps(project: Project, fast: bool = False, changed_tests: list | None = None) -> list:
    """[(name, command, cwd)] — fast checks cheapest first, then, unless `fast`, the affected tests —
    or, given `changed_tests`, those files through their falsify runners — then `tests.always`."""
    tests = project.config.get("tests", {})
    steps = named_commands(project.config.get("checks", {}).get("fast"), "checks.fast")
    if not fast and changed_tests is None:
        steps.append(("affected tests", str(tests.get("affected") or ""), "tests.affected"))
    if not fast:
        steps += named_commands(tests.get("always"), "tests.always", "always: ")
    for name, command, key in steps:
        if not command.strip() or re.search(r"<[a-z][a-z ,/-]*>", command):
            raise SystemExit(f"spry.config.json: `{name}` has no command yet — set {key}")
    steps = [(name, command, project.root) for name, command, _key in steps]
    if not fast and changed_tests:
        at = len(steps) - len(tests.get("always") or [])
        table = runners(project)
        steps[at:at] = [(f"changed tests{'' if cwd == project.root else ' in ' + os.path.relpath(cwd, project.root).replace(os.sep, '/')}",
                         runner_command(project, table[index], cwd, files), cwd)
                        for (index, cwd), files in group_files(project, changed_tests).items()]
    return steps


DEFAULT_RETRY_WHEN = r"timed? ?out|timeout|ETIMEDOUT"


def gate(project: Project, force: bool = False, say=print, fast: bool = False, full: bool = False) -> int:
    """The gate, timed into the step log (§17)."""
    started, seen = time.time(), {"steps": []}
    code = run_gate(project, force, say, fast, full, seen)
    pace_log(project, "gate", time.time() - started, ok=code == 0, fast=fast, full=full, force=force, **seen)
    return code


def run_gate(project: Project, force: bool, say, fast: bool, full: bool, seen: dict) -> int:
    """`spry check`, then the fast checks, then the affected tests, then `tests.always` — stopping at
    the first failure. A branch that changed only test files runs those files instead of the affected
    tests, unless `full`: a test file breaks no other package's tests. A pass is stamped with the
    code's fingerprint; while the code is unchanged, only `check` runs again.
    `fast` leaves out the tests, for each change while building, and stamps nothing."""
    started = time.time()
    errors = [p for p in check(project) if p.level == "error"]
    say(f"{'✗' if errors else '✓'} spry check · {time.time() - started:.1f}s")
    seen["steps"].append(["spry check", round(time.time() - started, 1), not errors])
    if errors:
        for p in errors[:10]:
            say(f"  {p}")
        return 1
    steps = gate_steps(project, fast)
    stamp_path = os.path.join(project.root, ".spry", "green")
    fingerprint = code_fingerprint(project)
    try:
        stamp = json.loads(read(stamp_path))
    except (OSError, ValueError):
        stamp = {}
    # A tests-only pass does not vouch for the affected tests `--full` asks for.
    if fingerprint and stamp.get("code") == fingerprint and not force and not (full and stamp.get("mode")):
        done = f"the {stamp['mode']} gate" if stamp.get("mode") else ", ".join(n for n, *_ in steps)
        say(f"– {done} skipped: no code changed since it passed at {stamp.get('at', '?')}")
        seen["skipped"] = "stamp"
        return 0
    changes = branch_changes(project)
    if changes and documents_only(project, changes[1]) and not force:
        say(f"– {', '.join(n for n, *_ in steps)} skipped: only documents changed since {changes[0]}")
        seen["skipped"] = "documents"
        return 0
    mode = None
    if changes and not fast and not full:
        files, why_not = tests_only(project, changes[1])
        if files is not None and why_not:
            say(f"– the branch changes only test files, but {why_not} — running the affected tests")
        elif files is not None:
            mode = "tests-only"
            steps = gate_steps(project, fast, changed_tests=files)
            say(f"– tests-only: the branch changes only test files since {changes[0]} — "
                + (f"running {len(files)} of them" if files else "it only removed them, so none to run")
                + ", not the affected tests (`gate --full` runs those)")
    tests = project.config.get("tests", {})
    retry = str(tests.get("retry") or "").strip()
    retry_when = re.compile(tests.get("retry_when") or DEFAULT_RETRY_WHEN, re.I)
    seen.update({"code": fingerprint, "tests": False, **({"mode": mode} if mode else {})})
    for name, command, cwd in steps:
        seen["tests"] = seen["tests"] or "test" in name
        started = time.time()
        done = subprocess.run(command, shell=True, cwd=cwd, capture_output=True, text=True)
        say(f"{'✓' if done.returncode == 0 else '✗'} {name} · {time.time() - started:.1f}s")
        if done.returncode != 0 and name == "affected tests" and retry and retry_when.search(done.stdout + done.stderr):
            # A test that times out under load and passes on a quiet machine is load, not code.
            # A real failure fails both runs, so the retry never turns red into green.
            say(f"  timed out under load — once more, quietly: {retry}")
            started = time.time()
            done = subprocess.run(retry, shell=True, cwd=project.root, capture_output=True, text=True)
            say(f"{'✓' if done.returncode == 0 else '✗'} {name}, quiet retry · {time.time() - started:.1f}s")
            seen["retried"] = True
        seen["steps"].append([name, round(time.time() - started, 1), done.returncode == 0])
        if done.returncode != 0:
            tail = (done.stdout + done.stderr).rstrip().split("\n")[-40:]
            say("\n".join("  " + line for line in tail))
            return 1
    if fast:
        say("fast checks green — tests not run; `spry.py gate` runs them")
        return 0
    if fingerprint:
        os.makedirs(native(os.path.dirname(stamp_path)), exist_ok=True)
        write(stamp_path, json.dumps({"code": fingerprint, "at": time.strftime("%Y-%m-%d %H:%M"),
                                      **({"mode": mode} if mode else {})}) + "\n")
        say(f"green{' (' + mode + ')' if mode else ''} — stamped; until the code changes, the gate runs only `spry check`")
    return 0


def code_changed_since(project: Project, base: str) -> bool:
    """Did anything outside `checks.docs` change between `base` and the working tree? True when unsure."""
    if git(project.root, "rev-parse", "--verify", "--quiet", f"{base}^{{commit}}").returncode != 0:
        return True
    done = git(project.root, "diff", "--relative", "--name-only", "--no-renames", base, "--", ".")
    if done.returncode != 0:
        return True
    docs = [glob_regex(g) for g in project.config.get("checks", {}).get("docs") or DEFAULT_DOCS]
    return any(not any(g.match(path) for g in docs) for path in done.stdout.split("\n") if path)


def branch_changes(project: Project):
    """(`origin/<main>`, [paths]) — every file the branch changed since it left the main branch, working
    tree, deletions and untracked files included; None when unsure. From the fork point, so what a
    rebase brought in, or what the main branch did since, is not the branch's."""
    main = f"{REMOTE}/{main_branch(project)}"
    fork = git(project.root, "merge-base", main, "HEAD")
    if fork.returncode != 0 or not fork.stdout.strip():
        return None
    done = git(project.root, "diff", "--relative", "--name-only", "--no-renames", fork.stdout.strip(), "--", ".")
    new = git(project.root, "ls-files", "-o", "--exclude-standard", "--", ".")
    if done.returncode != 0 or new.returncode != 0:
        return None
    paths = set(filter(None, done.stdout.split("\n")))
    paths |= {p for p in filter(None, new.stdout.split("\n")) if not SKIP_DIRS.intersection(p.split("/")[:-1])}
    return main, sorted(paths)


def documents_only(project: Project, paths: list) -> bool:
    docs = [glob_regex(g) for g in project.config.get("checks", {}).get("docs") or DEFAULT_DOCS]
    return all(any(g.match(path) for g in docs) for path in paths)


def tests_only(project: Project, paths: list):
    """([test files to run], why not) — the branch changed test files and nothing else outside
    `checks.docs`. `why not` names what sends it to the affected tests after all: a test file another
    file mentions (a shared helper its importers would need), or one no falsify runner takes.
    (None, None) when the branch changed anything else."""
    docs = [glob_regex(g) for g in project.config.get("checks", {}).get("docs") or DEFAULT_DOCS]
    code = [p for p in paths if not any(g.match(p) for g in docs)]
    tests = project._test_globs()
    if not code or not all(any(g.match(p) for g in tests) for p in code):
        return None, None
    for path in code:
        if not TEST_FILE_NAME.match(os.path.basename(path)):
            return code, f"{path} is not named as a test file, so tests that never name it may use it"
        # A mention is enough: it may be an import. Wrong only in sending the gate the long way.
        stem = os.path.splitext(os.path.basename(path))[0]
        done = git(project.root, "grep", "-l", "-F", "--untracked", "-e", stem, "--", ".")
        if done.returncode not in (0, 1):
            return code, f"`git grep` failed on {path}"
        for other in filter(None, done.stdout.split("\n")):
            if other not in code and not any(g.match(other) for g in docs):
                return code, f"{other} mentions {path}"
    present = [p for p in code if os.path.isfile(native(os.path.join(project.root, p)))]
    try:
        group_files(project, present)
    except PlanError as e:
        return code, str(e)
    return present, None


# ---------------------------------------------------------------- review-check

REVIEW_EVENTS = ("COMMENT", "REQUEST_CHANGES", "APPROVE")
SUGGESTION = re.compile(r"^(`{3,})suggestion[ \t]*\n(.*?)^\1[ \t]*$", re.S | re.M)


def diff_lines(diff: str) -> dict:
    """{path: {side: {line: (hunk, text)}}} — the lines of a unified diff GitHub lets a comment sit on."""
    files, old_path, current, hunk, left, right = {}, None, None, 0, 0, 0
    for raw in diff.split("\n"):
        if raw.startswith("diff --git "):
            current = None
        elif raw.startswith("--- "):
            old_path = raw[6:] if raw.startswith("--- a/") else None
        elif raw.startswith("+++ "):
            path = raw[6:] if raw.startswith("+++ b/") else old_path
            current = files.setdefault(path, {"LEFT": {}, "RIGHT": {}}) if path else None
        elif raw.startswith("@@ ") and current is not None:
            m = re.match(r"@@ -(\d+)(?:,\d+)? \+(\d+)(?:,\d+)? @@", raw)
            if m:
                hunk, left, right = hunk + 1, int(m.group(1)), int(m.group(2))
        elif current is not None and hunk and raw[:1] in (" ", "+", "-"):
            if raw[0] in " -":
                current["LEFT"][left] = (hunk, raw[1:])
                left += 1
            if raw[0] in " +":
                current["RIGHT"][right] = (hunk, raw[1:])
                right += 1
    return files


def review_check(payload, diff: str, own: bool = False) -> list:
    """What GitHub would refuse, or a reader would trip on, in a review payload — before it is posted."""
    if not isinstance(payload, dict):
        return ["the payload is not a JSON object"]
    problems = []
    if not isinstance(payload.get("commit_id"), str) or not payload["commit_id"].strip():
        problems.append("commit_id: missing — use the pull request's headRefOid")
    event = payload.get("event")
    if event not in REVIEW_EVENTS:
        problems.append(f"event: {event!r} is not one of {', '.join(REVIEW_EVENTS)}")
    elif own and event != "COMMENT":
        problems.append(f"event: GitHub refuses {event} on your own pull request — use COMMENT")
    if not isinstance(payload.get("body"), str) or not payload["body"].strip():
        problems.append("body: empty — one line saying what the review found")
    comments = payload.get("comments", [])
    if not isinstance(comments, list):
        return problems + ["comments: not a list"]
    files, spans = diff_lines(diff), []
    for n, c in enumerate(comments, 1):
        if not isinstance(c, dict):
            problems.append(f"comment {n}: not a JSON object")
            continue
        path, line, start = c.get("path"), c.get("line"), c.get("start_line", c.get("line"))
        where = f"comment {n} ({path}:{line})"
        if not isinstance(c.get("body"), str) or not c["body"].strip():
            problems.append(f"{where}: empty body")
        if not isinstance(path, str) or type(line) is not int or type(start) is not int:
            problems.append(f"{where}: needs path, and line (and start_line) as numbers")
            continue
        side = c.get("side", "RIGHT")
        if side not in ("LEFT", "RIGHT") or c.get("start_side", side) != side:
            problems.append(f"{where}: side and start_side must both be RIGHT, or both LEFT")
            continue
        if start >= line and "start_line" in c:
            problems.append(f"{where}: start_line {start} must be above line {line} — leave it out for one line")
            continue
        if path not in files:
            problems.append(f"{where}: {path} is not in the pull request's diff")
            continue
        lines = files[path][side]
        outside = [k for k in range(start, line + 1) if k not in lines]
        if outside:
            problems.append(f"{where}: line {outside[0]} is outside the diff — a comment sits only on lines the diff shows")
            continue
        if len({lines[k][0] for k in range(start, line + 1)}) > 1:
            problems.append(f"{where}: lines {start}–{line} span two parts of the diff — split the comment")
            continue
        body = c.get("body") or ""
        found = SUGGESTION.findall(body)
        if len(found) != len(re.findall(r"^`{3,}suggestion", body, re.M)):
            problems.append(f"{where}: a suggestion block is not closed")
            continue
        if not found:
            continue
        if side == "LEFT":
            problems.append(f"{where}: a suggestion replaces new lines — anchor it on the RIGHT side")
        elif len(found) > 1:
            problems.append(f"{where}: {len(found)} suggestions in one comment — one per comment, on exactly the lines it replaces")
        elif found[0][1].rstrip("\n") == "\n".join(lines[k][1] for k in range(start, line + 1)) and found[0][1]:
            problems.append(f"{where}: the suggestion is the same as the lines it replaces")
        for other, (p, a, b) in spans:
            if p == path and a <= line and start <= b:
                problems.append(f"{where}: its suggestion overlaps comment {other}'s — fold one into the other")
        spans.append((n, (path, start, line)))
    return problems


# ---------------------------------------------------------------- main

# ---------------------------------------------------------------- pace (§17)

PACE_VERSION = 1
# Every second of active time gets one of these; `away` is left out of every total.
PACE_KINDS = (("agent", "the agent, thinking and writing"), ("gate", "gate"), ("falsify", "falsify"),
              ("tests", "tests outside the gate"), ("fast", "fast checks outside the gate"),
              ("spry", "other spry commands"), ("git", "git"), ("gh", "gh"), ("stack", "local services"),
              ("polling", "polling loops"), ("files", "file tools"), ("subagent", "subagents waited on"),
              ("tool", "other tools"), ("you", "waiting on you"), ("question", "a question to you"),
              ("elsewhere", "you, busy in another session"), ("background", "waiting on a background task"),
              ("session", "waiting on another session"), ("wake", "waiting on a scheduled wake-up"))
PACE_LABEL = dict(PACE_KINDS)
PACE_GROUPS = (("agent", ("agent",)), ("checks", ("gate", "falsify", "tests", "fast")),
               ("other tools", ("spry", "git", "gh", "stack", "polling", "files", "subagent", "tool")),
               ("you", ("you", "question")), ("you elsewhere", ("elsewhere",)),
               ("waits", ("background", "session", "wake")))
PACE_PHASES = ("open", "build", "close", "review", "fixes", "merge", "other")
PACE_FLAGS = {"falsify_share": 0.2, "session_share": 0.2, "merge_wait_share": 0.5, "review_agents": 3}
PACE_LIMIT = 590       # a tool call this long ran into the agent's 10-minute limit
PACE_OTHER = re.compile(r'^\{"type":\s*"(?!(?:user|assistant|system)")')  # a record pace never reads, by its first key
PACE_GATE_STEP = re.compile(r"^([✓✗]) (.+?) · ([\d.]+)s", re.M)
PACE_RUNNERS = {"pytest", "vitest", "jest", "playwright", "mocha", "ava"}
PACE_ORDER = ("gate", "falsify", "tests", "fast", "polling", "spry", "stack", "gh", "git")


def pace_config(project: Project) -> dict:
    conf = project.config.get("pace") or {}
    flags = {**PACE_FLAGS, **(conf.get("flags") or {})}
    return {"away": float(conf.get("away", 30)) * 60, "logs": list(conf.get("logs") or []), "flags": flags}


def pace_root(project: Project) -> str:
    """The project's folder in the main checkout, so every worktree of one clone shares one step log."""
    done = git(project.root, "rev-parse", "--path-format=absolute", "--git-common-dir")
    common = done.stdout.strip() if done.returncode == 0 else ""
    if os.path.basename(common) != ".git":
        return project.root
    return os.path.join(os.path.dirname(common), git_prefix(project.root))


def pace_home(project: Project) -> str:
    return os.path.join(pace_root(project), ".spry", "pace")


def pace_log(project: Project, command: str, seconds: float, **fields) -> None:
    """One line in `.spry/pace/steps.jsonl` for a step spry ran. Never fails the command it times."""
    try:
        branch = git(project.root, "rev-parse", "--abbrev-ref", "HEAD").stdout.strip()
        home = pace_home(project)
        os.makedirs(native(home), exist_ok=True)
        line = json.dumps({"at": round(time.time(), 1), "branch": branch, "command": command,
                           "seconds": round(seconds, 1), **fields})
        with open(native(os.path.join(home, "steps.jsonl")), "a", encoding="utf-8", newline="\n") as handle:
            handle.write(line + "\n")
    except (OSError, ValueError, subprocess.SubprocessError):
        pass


def pace_segments(command: str):
    """The simple commands in a shell line, each as its words, heredoc bodies and env prefixes dropped."""
    command = re.sub(r"<<-?\s*['\"]?(\w+)['\"]?.*?\n.*?\n\1\b", " ", command, flags=re.S)
    for part in re.split(r"&&|\|\||;|\||\n|\(|\)|\bdo\b|\bthen\b", command):
        words = part.split()
        while words and (re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", words[0]) or words[0] in ("export", "env", "time", "exec", "sudo", "{")):
            words = words[1:]
        if words:
            yield words


def pace_word_kind(words: list) -> str | None:
    head = words[0].split("/")[-1]
    rest = " ".join(words[1:6])
    spry_tool = re.compile(r"(spry|writ)(\.py)?$")
    if spry_tool.search(head) or (head.startswith("python") and len(words) > 1 and spry_tool.search(words[1])):
        sub = next((w for w in words[1:] if not w.startswith("-") and not spry_tool.search(w) and "/" not in w), "")
        return {"gate": "gate", "falsify": "falsify"}.get(sub, "spry")
    if head in ("until", "while", "sleep") or (head == "for" and "sleep" in words):
        return "polling"
    package = head in ("npx", "pnpm", "npm", "yarn", "bunx")
    if head in PACE_RUNNERS or (package and re.search(r"(^|\s)(vitest|jest|playwright|test|test:\S+|e2e|falsify)\b", rest)):
        return "falsify" if "falsify" in rest else "tests"
    if head in ("go", "cargo") and rest.startswith("test"):
        return "tests"
    if head in ("tsc", "eslint", "ruff", "mypy", "prettier", "biome") or (package and re.search(r"\b(lint|typecheck|tsc|eslint|prettier|format|check-types)\b", rest)):
        return "fast"
    if head in ("docker", "docker-compose"):
        return "stack"
    if head in ("gh", "git"):
        return head
    return None


def pace_bash_kind(command: str) -> str:
    """A shell line's kind: the costliest kind of any command in it."""
    kinds = {pace_word_kind(w) for w in pace_segments(command)} - {None}
    return next((k for k in PACE_ORDER if k in kinds), "tool")


def pace_runs_suite(command: str, suite: list) -> bool:
    """A simple command in `command` is one of `suite` exactly, give or take a redirection: a run
    filtered to a package or a file is not the whole suite."""
    for words in pace_segments(command):
        words = [w for w in words if not re.match(r"^\d?>", w)]
        if words[:1] == ["npx"]:
            words = words[1:]
        if " ".join(words) in suite:
            return True
    return False


def pace_head(command: str) -> str:
    """A command's first line, short, without `NAME=value` words or a bearer token — what is kept."""
    line = command.strip().split("\n")[0] if command.strip() else ""
    line = " ".join(w for w in line.split() if not re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", w))
    return re.sub(r"(?i)(bearer|token)\s+\S+", r"\1 …", line)[:100]


def pace_tool_kind(block: dict) -> str:
    name, given = block.get("name", ""), block.get("input") or {}
    if name == "Bash":
        return pace_bash_kind(str(given.get("command", "")))
    if name in ("Agent", "Task"):
        return "subagent"
    if name in ("Edit", "Write", "Read", "Grep", "Glob", "NotebookEdit", "MultiEdit"):
        return "files"
    if name == "AskUserQuestion":
        return "question"
    if name in ("Monitor", "TaskOutput", "BashOutput"):
        return "background"
    return "tool"


def pace_is_review(block: dict) -> bool:
    given = block.get("input") or {}
    text = f"{given.get('description', '')} {given.get('subagent_type', '')} {str(given.get('prompt', ''))[:400]}"
    return block.get("name") in ("Agent", "Task") and bool(re.search(r"\breview", text, re.I))


def pace_phase_of(skill: str) -> str | None:
    name = skill.split(":")[-1].lstrip("/").strip()
    return {"slice-open": "open", "slice-close": "close", "merge": "merge"}.get(name)


def pace_text(content) -> str:
    if isinstance(content, str):
        return content
    return " ".join(str(c.get("text", "")) for c in content or [] if isinstance(c, dict))


def pace_stamp(text: str) -> float:
    from datetime import datetime
    return datetime.fromisoformat(text.replace("Z", "+00:00")).timestamp()


def pace_records(path: str):
    """The user, assistant and system records of a session log, oldest first; others skipped unread."""
    with open(native(path), encoding="utf-8", errors="replace") as handle:
        for line in handle:
            if PACE_OTHER.match(line):
                continue
            try:
                record = json.loads(line)
            except ValueError:
                continue
            if not isinstance(record, dict) or record.get("type") not in ("user", "assistant", "system"):
                continue
            try:
                record["_t"] = pace_stamp(str(record.get("timestamp")))
            except ValueError:
                continue
            message = record.get("message") if isinstance(record.get("message"), dict) else {}
            content = message.get("content")
            if not isinstance(content, str):  # a record of an unexpected shape loses its content, not the log
                message["content"] = [c for c in content if isinstance(c, dict)] if isinstance(content, list) else []
            record["message"] = message
            if not isinstance(record.get("origin"), dict):
                record["origin"] = {}
            yield record


def pace_branch_entry() -> dict:
    return {"kinds": {}, "phases": {}, "first": None, "last": None, "prompts": 0, "questions": 0,
            "compactions": 0, "gates": [], "limit": 0, "slowest": [], "suite": 0}


def pace_read_log(path: str, away: float, suite: list) -> dict:
    """What one Claude Code session log says, per git branch: seconds by kind and by phase, and the
    events pace counts. A gap between two records takes the kind of what filled it: a tool still
    running, the agent writing, or a wait — on you only once the agent's turn has ended."""
    branches, prompts, you_gaps = {}, [], []
    pending = {}    # tool_use id → (start, kind, head, gate fast flag or None, review)
    background = set()  # background tasks started and not yet reported finished, by tool_use id
    prev, branch, ended, phase = None, "", True, "other"
    turn = phase_turn = 0   # a phase set in this turn follows the agent to a new branch; an older one does not

    def entry(name):
        return branches.setdefault(name or "", pace_branch_entry())

    for record in pace_records(path):
        t = record["_t"]
        kind_of_record = record["type"]
        origin = record["origin"].get("kind")
        message = record["message"]
        content = message.get("content")
        if prev is not None and t > prev:
            gap = t - prev
            if pending:
                kind = min(pending.values(), key=lambda v: v[0])[1]
                kind = "away" if kind == "question" and gap > away else kind
            elif kind_of_record == "assistant":
                kind = "agent"
            elif gap > away:
                kind = "away"
            elif record.get("subtype") == "scheduled_task_fire":
                kind = "wake"
            elif origin == "peer":
                kind = "session"
            elif origin == "task-notification" or (ended and background):
                kind = "background"
            elif not ended:
                kind = "agent"
            else:
                kind = "you"
            spot = entry(branch)
            spot["kinds"][kind] = spot["kinds"].get(kind, 0) + gap
            if kind != "away":
                cell = spot["phases"].setdefault(phase, {})
                cell[kind] = cell.get(kind, 0) + gap
                spot["first"] = prev if spot["first"] is None else min(spot["first"], prev)
                spot["last"] = t if spot["last"] is None else max(spot["last"], t)
            if kind == "you":
                you_gaps.append([prev, t, branch, phase])
        if record.get("gitBranch") and record["gitBranch"] != branch:
            branch = record["gitBranch"]
            phase = phase if phase_turn == turn else "other"
        spot = entry(branch)
        if kind_of_record == "assistant":
            for block in content if isinstance(content, list) else []:
                if block.get("type") != "tool_use":
                    continue
                given = block.get("input") or {}
                kind = pace_tool_kind(block)
                command = str(given.get("command", ""))
                if block.get("name") == "Skill" and pace_phase_of(str(given.get("skill", ""))):
                    phase, phase_turn = pace_phase_of(str(given.get("skill", ""))), turn
                elif kind == "question":
                    spot["questions"] += 1
                elif block.get("name") == "Bash":
                    if re.search(r"\blink\b.*--pr\b", command):
                        phase, phase_turn = "build", turn
                    elif re.search(r"\bmerge-check\b", command):
                        phase, phase_turn = "merge", turn
                    if pace_runs_suite(command, suite):
                        spot["suite"] += 1
                review = pace_is_review(block)
                if review:
                    phase, phase_turn = "review", turn
                if given.get("run_in_background"):
                    background.add(block.get("id"))
                    kind = "tool"
                head = pace_head(command) or block.get("name", "")
                gate_fast = ("--fast" in command) if kind == "gate" else None
                pending[block.get("id")] = (t, kind, head, gate_fast, review and not given.get("run_in_background"))
            ended = message.get("stop_reason") == "end_turn" and not pending
        elif kind_of_record == "user" and isinstance(content, list) and any(c.get("type") == "tool_result" for c in content if isinstance(c, dict)):
            for c in content:
                if not isinstance(c, dict) or c.get("type") != "tool_result" or c.get("tool_use_id") not in pending:
                    continue
                start, kind, head, gate_fast, review = pending.pop(c["tool_use_id"])
                seconds = t - start
                if seconds >= PACE_LIMIT and kind not in ("question", "you"):
                    spot["limit"] += 1
                if kind not in ("question",):
                    spot["slowest"] = sorted(spot["slowest"] + [[round(seconds, 1), kind, head]], reverse=True)[:5]
                if gate_fast is not None:
                    out = pace_text(c.get("content"))
                    steps = {m.group(2): float(m.group(3)) for m in PACE_GATE_STEP.finditer(out)}
                    if steps:
                        spot["gates"].append({"at": start, "fast": gate_fast, "ok": "✗" not in out,
                                              "tests": any("test" in s for s in steps) or "tests-only" in out,
                                              "retried": "quiet retry" in out, "steps": steps})
                if review:
                    phase = "fixes"
        elif kind_of_record == "user":
            text = pace_text(content)
            named = re.search(r"<command-name>(.*?)</command-name>", text)
            if origin == "human":
                turn += 1
            if named and pace_phase_of(named.group(1)):
                phase, phase_turn = pace_phase_of(named.group(1)), turn
            if named:
                if named.group(1).strip() == "/compact":
                    spot["compactions"] += 1
            if origin == "human":
                spot["prompts"] += 1
                prompts.append(t)
                pending.clear()
                ended = False
            elif origin == "task-notification":
                finished = re.search(r"<tool-use-id>(.*?)</tool-use-id>", text)
                if finished:
                    background.discard(finished.group(1))
                elif background:
                    background.pop()
                if phase == "review":
                    phase = "fixes"
            if "[Request interrupted" in text:
                pending.clear()
                ended = True
        elif kind_of_record == "system":
            subtype = record.get("subtype")
            if subtype == "local_command":
                ended = True
                background.clear()  # `/clear` stops what the session had running
            elif subtype == "turn_duration":
                ended = ended or not pending
            elif subtype == "compact_boundary":
                spot["compactions"] += 1
        prev = t if prev is None else max(prev, t)  # a record a few ms out of order is not counted twice
    return {"branches": branches, "prompts": prompts, "you": you_gaps, "agents": pace_subagents(path)}


def pace_subagents(path: str) -> list:
    """[branch, seconds, review] for each subagent this session started; a review agent is one whose
    first prompt says review."""
    found = []
    for sub in sorted(glob.glob(os.path.join(glob.escape(path[:-6]), "subagents", "*.jsonl"))):
        first = last = None
        branch, review = "", False
        for record in pace_records(sub):
            t = record["_t"]
            if first is None:
                first = t
                review = bool(re.search(r"\breview", pace_text(record["message"]["content"])[:3000], re.I))
            last = t
            branch = branch or record.get("gitBranch") or ""
        if first is not None:
            found.append([branch, round(last - first, 1), review])
    return found


def pace_log_dirs(project: Project) -> list:
    """Claude Code's session-log folders for this clone and its worktrees, plus `pace.logs`."""
    home = os.environ.get("CLAUDE_CONFIG_DIR") or os.path.join(os.path.expanduser("~"), ".claude")
    folder = os.path.join(home, "projects")
    names = {re.sub(r"[^A-Za-z0-9]", "-", os.path.realpath(r).rstrip(os.sep)) for r in (project.root, pace_root(project))}
    dirs = []
    if os.path.isdir(folder):
        for name in sorted(os.listdir(folder)):
            if any(name == n or name.startswith(n + "--claude-worktrees-") for n in names):
                dirs.append(os.path.join(folder, name))
    for pattern in pace_config(project)["logs"]:
        dirs += [d for d in sorted(glob.glob(os.path.expanduser(pattern))) if os.path.isdir(d) and d not in dirs]
    return dirs


def pace_suite(project: Project) -> list:
    """The commands that run the whole suite — an agent running one breaks §15."""
    tests = project.config.get("tests") or {}
    found = [tests.get("all")] + [p.get("run") for p in tests.get("parts") or [] if isinstance(p, dict)]
    return [str(c).strip() for c in found if c and not PLACEHOLDER.search(str(c)) and str(c).strip()]


def pace_logs(project: Project, newer_than: float | None = None, say=None) -> dict:
    """{log path: what it says}, read once per size and mtime and kept in `.spry/pace/logs.json`."""
    conf = pace_config(project)
    suite = pace_suite(project)
    key = hashlib.sha256(json.dumps([PACE_VERSION, conf["away"], suite]).encode()).hexdigest()[:12]
    cache_path = os.path.join(pace_home(project), "logs.json")
    try:
        cache = json.loads(read(cache_path))
    except (OSError, ValueError):
        cache = {}
    known = cache.get("logs", {}) if cache.get("key") == key else {}
    found, fresh = {}, 0
    for folder in pace_log_dirs(project):
        for path in sorted(glob.glob(os.path.join(glob.escape(folder), "*.jsonl"))):
            try:  # a log deleted or rotated under us is simply not there
                stat = os.stat(native(path))
                subs = glob.glob(os.path.join(glob.escape(path[:-6]), "subagents", "*.jsonl"))
                sign = [stat.st_size, int(stat.st_mtime), sum(os.path.getsize(native(s)) for s in subs)]
            except OSError:
                continue
            old = known.get(path)
            if old and old.get("sign") == sign:
                found[path] = old
                continue
            if newer_than is not None and stat.st_mtime < newer_than:
                if old:
                    found[path] = old
                continue
            try:
                found[path] = {"sign": sign, **pace_read_log(path, conf["away"], suite)}
                fresh += 1
            except (OSError, ValueError, KeyError, TypeError, AttributeError) as error:
                if say:
                    say(f"  skipped {os.path.basename(path)}: {error}")
    if fresh:
        keep = {**known, **found} if newer_than is not None else found
        try:
            os.makedirs(native(os.path.dirname(cache_path)), exist_ok=True)
            write(cache_path, json.dumps({"key": key, "logs": keep}) + "\n")
        except OSError:
            pass
    return found


def pace_steps(project: Project) -> list:
    try:
        lines = read(os.path.join(pace_home(project), "steps.jsonl")).split("\n")
    except OSError:
        return []
    out = []
    for line in lines:
        try:
            out.append(json.loads(line)) if line.strip() else None
        except ValueError:
            continue
    return out


def pace_branch_map(project: Project) -> dict:
    """{branch: slice ID} — a slice's `branch:`, else the branch named after its file."""
    out = {}
    for item in project.items.values():
        if item.type != "slice":
            continue
        out.setdefault(slice_branch(item), item.id)
        if branch_of(item):
            out[branch_of(item)] = item.id
    return out


def pace_lines(project: Project) -> dict:
    """{slice ID: lines changed}, from the `Slice:` trailer of each squash commit on the main branch."""
    done = git(project.root, "log", main_branch(project), "--format=%x1e%B", "--shortstat")
    out = {}
    for chunk in done.stdout.split("\x1e") if done.returncode == 0 else []:
        named = re.search(r"^Slice:\s*(\S+)\s*$", chunk, re.M)
        stat = re.search(r"(\d+) insertions?\(\+\)", chunk), re.search(r"(\d+) deletions?\(-\)", chunk)
        if named and (stat[0] or stat[1]):
            out[named.group(1)] = sum(int(s.group(1)) for s in stat if s)
    return out


def pace_add(into: dict, more: dict) -> None:
    for key, value in more.items():
        into[key] = into.get(key, 0) + value


def pace_slices(project: Project, logs: dict, only: str | None = None) -> dict:
    """{slice ID: its numbers} from the session logs, the step log and the summaries kept in
    `.spry/pace/slices/` — a summary outlives the logs it came from."""
    by_branch = pace_branch_map(project)
    slices = {}

    def spot(slice_id):
        return slices.setdefault(slice_id, {"id": slice_id, "kinds": {}, "phases": {}, "first": None, "last": None,
                                            "sessions": 0, "prompts": 0, "questions": 0, "compactions": 0,
                                            "reviews": [], "limit": 0, "slowest": [], "suite": 0, "gates": [],
                                            "log_gates": []})
    prompts = sorted((t, path) for path, data in logs.items() for t in data.get("prompts", []))
    times = [p[0] for p in prompts]
    import bisect
    for path, data in logs.items():
        for branch, d in data["branches"].items():
            slice_id = by_branch.get(branch)
            if not slice_id or (only and slice_id != only) or d["first"] is None:
                continue
            s = spot(slice_id)
            pace_add(s["kinds"], d["kinds"])
            for phase, kinds in d["phases"].items():
                pace_add(s["phases"].setdefault(phase, {}), kinds)
            s["first"] = d["first"] if s["first"] is None else min(s["first"], d["first"])
            s["last"] = d["last"] if s["last"] is None else max(s["last"], d["last"])
            s["sessions"] += 1
            for key in ("prompts", "questions", "compactions", "limit", "suite"):
                s[key] += d[key]
            s["slowest"] = sorted(s["slowest"] + d["slowest"], reverse=True)[:5]
            s["log_gates"] += d["gates"]
        for start, end, branch, phase in data.get("you", []):
            slice_id = by_branch.get(branch)
            if slice_id not in slices:
                continue
            i, j = bisect.bisect_right(times, start), bisect.bisect_left(times, end)
            if any(prompts[x][1] != path for x in range(i, j)):
                s, gap = slices[slice_id], end - start
                for kinds in (s["kinds"], s["phases"].setdefault(phase, {})):
                    kinds["you"] = kinds.get("you", 0) - gap
                    kinds["elsewhere"] = kinds.get("elsewhere", 0) + gap
        for branch, seconds, review in data.get("agents", []):
            if review and by_branch.get(branch) in slices:
                slices[by_branch[branch]]["reviews"].append(seconds)
    for step in pace_steps(project):
        slice_id = by_branch.get(step.get("branch", ""))
        if step.get("command") == "gate" and slice_id and (not only or slice_id == only):
            spot(slice_id)["gates"].append(step)
    lines = {} if only else pace_lines(project)  # a slice at merge-check has no squash commit yet
    folder = os.path.join(pace_home(project), "slices")
    for slice_id, s in slices.items():
        if not s["gates"]:  # no step log (before CH-44, or another clone): the gate's own output
            s["gates"] = [{"fast": g["fast"], "ok": g["ok"], "tests": g["tests"], "retried": g["retried"],
                           "steps": [[n, v, True] for n, v in g["steps"].items()], "at": g["at"]} for g in s["log_gates"]]
        del s["log_gates"]
        s["lines"] = lines.get(slice_id)
    kept = glob.glob(os.path.join(glob.escape(folder), "*.json"))
    for path in kept:
        slice_id = os.path.basename(path)[:-5]
        if only and slice_id != only:
            continue
        try:
            stored = json.loads(read(path))
        except (OSError, ValueError):
            continue
        if slice_id not in slices or pace_active(stored) > pace_active(slices[slice_id]):
            stored["lines"] = stored.get("lines") or lines.get(slice_id)
            slices[slice_id] = stored
    for slice_id, s in slices.items():
        item = project.items.get(slice_id)
        if item is not None and item.state == "closed" and s["first"] is not None:
            try:
                os.makedirs(native(folder), exist_ok=True)
                write(os.path.join(folder, f"{slice_id}.json"), json.dumps(s) + "\n")
            except OSError:
                pass
    return slices


def pace_active(s: dict) -> float:
    return sum(v for k, v in s["kinds"].items() if k != "away")


def pace_group(s: dict, kinds) -> float:
    return sum(s["kinds"].get(k, 0) for k in kinds)


def pace_time(seconds: float) -> str:
    seconds = int(round(seconds))
    if seconds >= 3600:
        return f"{seconds // 3600}h{seconds % 3600 // 60:02d}"
    return f"{seconds // 60}m{seconds % 60:02d}"


def pace_share(part: float, whole: float) -> str:
    return f"{100 * part / whole:.0f}%" if whole else "–"


def pace_median(values: list):
    values = sorted(v for v in values if v is not None)
    if not values:
        return None
    middle = len(values) // 2
    return values[middle] if len(values) % 2 else (values[middle - 1] + values[middle]) / 2


def pace_full_gates(s: dict) -> list:
    return [g for g in s["gates"] if not g.get("fast")]


def pace_flags(project: Project, s: dict) -> list:
    """What stands out in one slice, each with its number. Flags describe; they never judge."""
    conf = pace_config(project)["flags"]
    active = pace_active(s) or 1
    full = pace_full_gates(s)
    out = []
    failed = [g for g in full if not g.get("ok", True)]
    if failed:
        out.append(f"the full gate failed {len(failed)}× — fast checks while building catch most of that earlier")
    tested = [g for g in full if g.get("tests")]
    if len(tested) > 1:
        out.append(f"tests ran through the full gate {len(tested)}× — §15 expects one full gate")
    passed, again = set(), 0
    for g in sorted(full, key=lambda g: g.get("at", 0)):
        code = g.get("code")
        if code and g.get("tests") and code in passed and not (g.get("force") or g.get("full")):
            again += 1
        if code and g.get("ok", True):
            passed.add(code)
    if again:
        out.append(f"tests ran again {again}× on code that had passed — the stamp missed: a spry bug, worth /spry:contribute")
    retried = sum(1 for g in s["gates"] if g.get("retried"))
    if retried:
        out.append(f"{retried} quiet retr{'y' if retried == 1 else 'ies'} — the machine was loaded, or a test is flaky")
    if s.get("limit"):
        out.append(f"{s['limit']} call{'s' if s['limit'] != 1 else ''} ran to the agent's 10-minute limit — a wait that belonged in the background, or a hung test")
    session = s["kinds"].get("session", 0)
    if session / active > conf["session_share"]:
        out.append(f"waiting on another session took {pace_share(session, active)} ({pace_time(session)})")
    merge = s["phases"].get("merge", {})
    merge_all = sum(merge.values())
    merge_you = merge.get("you", 0) + merge.get("question", 0)
    if merge_all >= 600 and merge_you / merge_all > conf["merge_wait_share"]:
        out.append(f"the merge waited on you for {pace_share(merge_you, merge_all)} of its {pace_time(merge_all)}")
    if len(s.get("reviews", [])) > conf["review_agents"]:
        out.append(f"{len(s['reviews'])} review agents — the slice may be too big, or its work order unclear")
    if s.get("compactions"):
        out.append(f"{s['compactions']} compaction{'s' if s['compactions'] != 1 else ''} — the slice outgrew one context")
    falsify = s["kinds"].get("falsify", 0)
    if falsify / active > conf["falsify_share"]:
        out.append(f"falsify took {pace_share(falsify, active)} ({pace_time(falsify)}) — `falsify.parallel` or `falsify.setup`")
    if s.get("suite"):
        out.append(f"the agent ran the whole suite {s['suite']}× — §15 leaves that to CI and /spry:test-all")
    return out


def pace_changes(project: Project) -> list:
    """[(time, what)] — each dated change to how the project runs spry: a process-changes row, a
    commit that changed the config (a new `spry_baseline` among them)."""
    from datetime import datetime
    out = []
    log = os.path.join(project.spry, "knowledge", "process-changes.md")
    try:
        text = read(log)
    except OSError:
        text = ""
    for line in text.split("\n"):
        cells = table_cells(line) if line.lstrip().startswith("|") else []
        if len(cells) > 1 and DATE.match(cells[0].strip()):
            out.append((datetime.strptime(cells[0].strip(), "%Y-%m-%d").timestamp(), f"process change: {cells[1].strip()}"))
    config = os.path.relpath(os.path.join(project.spry, "spry.config.json"), project.root)
    done = git(project.root, "log", "--format=%ct%x09%h %s", "--", config)
    for line in done.stdout.split("\n") if done.returncode == 0 else []:
        if "\t" in line:
            stamp, what = line.split("\t", 1)
            out.append((float(stamp), f"config: {what}"))
    return sorted(out)


def pace_point(project: Project, point: str) -> tuple:
    """(time, label) for `--compare`: a date, a CH-n taken (its process-changes row) or a commit."""
    from datetime import datetime
    if DATE.match(point):
        return datetime.strptime(point, "%Y-%m-%d").timestamp(), "the day you named"
    if re.match(r"^CH-\d+$", point):
        for t, what in pace_changes(project):
            if re.search(rf"\b{point}\b", what):
                return t, what
        raise PlanError(f"no process-changes row or config commit names {point}")
    done = git(project.root, "show", "-s", "--format=%ct%x09%h %s", point)
    if done.returncode != 0 or "\t" not in done.stdout:
        raise PlanError(f"{point} is not a date (YYYY-MM-DD), a CH-n or a commit")
    stamp, what = done.stdout.strip().split("\t", 1)
    return float(stamp), what


def pace_merged(slices: list, changes: list) -> list:
    """Changes with no slice ending between them become one: their before and after are the same."""
    out = []
    for at, label in changes:
        label = label if len(label) <= 100 else label[:99] + "…"
        if out and not any(out[-1][0] < s["last"] <= at for s in slices):
            out[-1] = (at, out[-1][1] + "; " + label)
        else:
            out.append((at, label))
    return out


def pace_measures(s: dict) -> dict:
    active = pace_active(s)
    full = pace_full_gates(s)
    out = {"active time": active}
    for name, kinds in PACE_GROUPS:
        out[f"{name} share"] = pace_group(s, kinds) / active if active else None
    out["full gates failed"] = sum(1 for g in full if not g.get("ok", True))
    out["quiet retries"] = sum(1 for g in s["gates"] if g.get("retried"))
    out["active time per 100 lines"] = active / s["lines"] * 100 if s.get("lines") else None
    return out


def pace_compare(slices: list, at: float, label: str) -> list:
    """Markdown: the slices ended after `at` against as many ended before it, by median."""
    after = sorted((s for s in slices if s["last"] > at), key=lambda s: s["last"])[:20]
    before = sorted((s for s in slices if s["last"] <= at), key=lambda s: s["last"])[-max(len(after), 1):]
    head = f"### {time.strftime('%Y-%m-%d', time.localtime(at))} — {label}"
    if len(after) < 10 or len(before) < 10:
        return [head, "", f"- too few slices to tell: {len(before)} before, {len(after)} after (10 a side needed)", ""]
    rows = [head, "", f"| {len(before)} slices a side | before | after |", "|---|---:|---:|"]
    measured = [pace_measures(s) for s in before], [pace_measures(s) for s in after]
    for key in measured[0][0]:
        counted = key in ("full gates failed", "quiet retries")
        values = [(sum(m[key] for m in side) / len(side)) if counted else pace_median([m[key] for m in side]) for side in measured]
        if key.endswith("share"):
            shown = [f"{100 * v:.0f}%" if v is not None else "–" for v in values]
        elif key.startswith("active"):
            shown = [pace_time(v) if v is not None else "–" for v in values]
        else:
            shown = [f"{v:.2f}" if v is not None else "–" for v in values]
        rows.append(f"| {key + ', per slice' if counted else 'median ' + key} | {shown[0]} | {shown[1]} |")
    return rows + [""]


def pace_slice_lines(s: dict, flags: list) -> list:
    """Markdown for one slice."""
    active = pace_active(s)
    rows = [f"## {s['id']}", "",
            f"- {pace_time(active)} active over {s['sessions']} session{'s' if s['sessions'] != 1 else ''}, "
            f"{s['prompts']} prompt{'s' if s['prompts'] != 1 else ''}, {s['questions']} question{'s' if s['questions'] != 1 else ''}"
            + (f", {s['lines']} lines changed" if s.get("lines") else ""), ""]
    rows += ["| | time | share |", "|---|---:|---:|"]
    for kind, label in PACE_KINDS:
        if s["kinds"].get(kind, 0) >= 1:
            rows.append(f"| {label} | {pace_time(s['kinds'][kind])} | {pace_share(s['kinds'][kind], active)} |")
    rows += ["", "| phase | time | most of it |", "|---|---:|---|"]
    for phase in PACE_PHASES:
        cell = s["phases"].get(phase) or {}
        total = sum(cell.values())
        if total >= 1:
            top = sorted(((v, k) for k, v in cell.items() if v > 0), reverse=True)[:3]
            rows.append(f"| {phase} | {pace_time(total)} | " + ", ".join(f"{PACE_LABEL.get(k, k)} {pace_share(v, total)}" for v, k in top) + " |")
    full = pace_full_gates(s)
    rows += ["", f"- gate: {len(full)} full ({sum(1 for g in full if not g.get('ok', True))} failed, "
             f"{sum(1 for g in full if g.get('tests'))} ran tests), {len(s['gates']) - len(full)} fast"
             + (f"; {len(s['reviews'])} review agent{'s' if len(s['reviews']) != 1 else ''}, {pace_time(sum(s['reviews']))}" if s.get("reviews") else "")]
    if s.get("slowest"):
        rows.append("- slowest calls: " + "; ".join(f"{pace_time(v)} {PACE_LABEL.get(k, k)} `{h[:60]}`" for v, k, h in s["slowest"][:3]))
    rows += [f"- flag: {f}" for f in flags]
    return rows + [""]


def pace_page(project: Project, slices: dict, since: str | None = None, last: int | None = None,
              compare: tuple | None = None) -> str:
    """The page, `.spry/view/pace.md`: where the slices' time went, before and after each change."""
    from datetime import datetime
    chosen = sorted((s for s in slices.values() if s["first"] is not None), key=lambda s: s["last"])
    if since:
        if not DATE.match(since):
            raise PlanError(f"--since takes a day, YYYY-MM-DD, not {since}")
        cut = datetime.strptime(since, "%Y-%m-%d").timestamp()
        chosen = [s for s in chosen if s["last"] >= cut]
    if last:
        chosen = chosen[-last:]
    rows = ["# Pace", "",
            f"> Local to this clone, written {time.strftime('%Y-%m-%d %H:%M')} by `spry pace`. Not committed. "
            "Away time (a gap over `pace.away`) is left out of every number.", ""]
    if not chosen:
        return "\n".join(rows + ["No slice time found yet: none of this clone's session logs or step logs name a slice's branch.", ""])
    actives = sorted(pace_active(s) for s in chosen)
    total = sum(actives)
    kinds = {}
    for s in chosen:
        pace_add(kinds, {k: v for k, v in s["kinds"].items() if k != "away"})
    rows += [f"- {len(chosen)} slices, {time.strftime('%Y-%m-%d', time.localtime(chosen[0]['first']))} to "
             f"{time.strftime('%Y-%m-%d', time.localtime(chosen[-1]['last']))}; median {pace_time(pace_median(actives))} "
             f"active, the slowest quarter from {pace_time(actives[3 * len(actives) // 4])}", ""]
    rows += ["## Where the time went", "", "| | time | share |", "|---|---:|---:|"]
    for name, group in PACE_GROUPS:
        part = sum(kinds.get(k, 0) for k in group)
        if part >= 1:
            rows.append(f"| **{name}** | {pace_time(part)} | {pace_share(part, total)} |")
            if len(group) > 1:
                for k in group:
                    if kinds.get(k, 0) >= 1:
                        rows.append(f"| {PACE_LABEL[k]} | {pace_time(kinds[k])} | {pace_share(kinds[k], total)} |")
    changes = [compare] if compare else pace_merged(chosen, [c for c in pace_changes(project) if chosen[0]["first"] < c[0] < chosen[-1]["last"]])[-5:]
    rows += ["", "## Before and after each change", ""]
    if not changes:
        rows += ["- no dated change in this range: a process-changes row or a config commit marks one", ""]
    for at, label in reversed(changes):
        rows += pace_compare(chosen, at, label)
    flagged = [(s, pace_flags(project, s)) for s in reversed(chosen)]
    rows += ["## Flags", ""]
    listed = [f"- {s['id']}: {f}" for s, flags in flagged for f in flags]
    rows += (listed[:40] or ["- none"]) + [""]
    rows += ["## Slices, newest first", "",
             "| slice | active | agent | checks | other tools | you | you elsewhere | waits | full gates (failed) | review agents | sessions |",
             "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for s, _ in flagged[:60]:
        active = pace_active(s)
        shares = [pace_share(pace_group(s, group), active) for _, group in PACE_GROUPS]
        full = pace_full_gates(s)
        rows.append(f"| {s['id']} | {pace_time(active)} | " + " | ".join(shares)
                    + f" | {len(full)} ({sum(1 for g in full if not g.get('ok', True))}) | {len(s.get('reviews', []))} | {s['sessions']} |")
    steps = {}
    for s in chosen:
        for g in s["gates"]:
            for name, seconds, *_ in g.get("steps", []):
                steps.setdefault(name, []).append(seconds)
    if steps:
        rows += ["", "## Gate steps", "", "| step | runs | total | median | longest |", "|---|---:|---:|---:|---:|"]
        for name, values in sorted(steps.items(), key=lambda kv: -sum(kv[1])):
            rows.append(f"| {name} | {len(values)} | {pace_time(sum(values))} | {pace_median(values):.1f}s | {max(values):.1f}s |")
    calls = sorted(([v, k, h, s["id"]] for s in chosen for v, k, h in s.get("slowest", [])), reverse=True)[:15]
    if calls:
        rows += ["", "## Slowest single calls", "", "| time | slice | kind | command |", "|---:|---|---|---|"]
        for v, k, h, slice_id in calls:
            rows.append(f"| {pace_time(v)} | {slice_id} | {PACE_LABEL.get(k, k)} | `{h[:80].replace('|', '¦').replace('`', '')}` |")
    return "\n".join(rows) + "\n"


def pace(project: Project, slice_id: str | None = None, since: str | None = None, last: int | None = None,
         compare: str | None = None, say=print) -> int:
    """`spry pace`: read what changed, keep each closed slice's numbers, write the page."""
    if slice_id and slice_id not in project.items:
        raise PlanError(f"no slice {slice_id}")
    if since and not DATE.match(since):
        raise PlanError(f"--since takes a day, YYYY-MM-DD, not {since}")
    point = pace_point(project, compare) if compare else None
    logs = pace_logs(project, say=say)
    slices = pace_slices(project, logs)
    if slice_id:
        s = slices.get(slice_id)
        if not s:
            say(f"no time found for {slice_id}: no session or step log names its branch")
            return 1
        say("\n".join(pace_slice_lines(s, pace_flags(project, s))).rstrip())
        return 0
    page = pace_page(project, slices, since, last, point)
    target = os.path.join(project.root, ".spry", "view", "pace.md")
    os.makedirs(native(os.path.dirname(target)), exist_ok=True)
    write(target, page)
    head = page.split("## Flags")[0].split("\n")
    say("\n".join(line for line in head if line.startswith("- ")))
    say(f"page: {project.rel(target)} — `spry serve` shows it at /-/pace")
    return 0


def pace_on_merge_check(project: Project, slice_id: str) -> None:
    """Keep a passing slice's numbers, reading only logs touched since its file was made."""
    try:
        item = project.items[slice_id]
        made = git(project.root, "log", "-1", "--diff-filter=A", "--format=%ct", "--", project.rel(item.doc)).stdout.strip()
        newer = float(made) - 86400 if made else time.time() - 30 * 86400
        pace_slices(project, pace_logs(project, newer_than=newer), only=slice_id)
    except Exception:  # noqa: BLE001 — pace never stands between a slice and its merge
        pass


# ---------------------------------------------------------------- memory-check

# Claude Code's auto-memory lives outside the repository, one folder per checkout that all its
# worktrees share: `~/.claude/projects/<the checkout's path, each other character a dash>/memory/`,
# an index (MEMORY.md, loaded into every session) and one file per fact. `memory-check` finds what
# can be told for certain — the index against the files, dates gone by, and the IDs, pull requests,
# commits and paths the memories name — and leaves what a claim means to `/spry:memory-check`.
MEMORY_DEFAULTS = {"index_lines": 60, "index_bytes": 8000, "line_chars": 200, "stale_days": 30}
# Claude Code loads the index's first 200 lines or 25 KB, whichever comes first; a session never sees the rest.
MEMORY_LOADED, MEMORY_LOADED_BYTES = 200, 25_000
MEMORY_TYPES = ("user", "feedback", "project", "reference")
MEMORY_LINE = re.compile(r"^\s*[-*]\s+\[([^\]]+)\]\(([^)\s]+)\)\s*(?:[—–-]\s*)?(.*)$")
MEMORY_WIKI = re.compile(r"\[\[([^\]|#]+)(?:[|#][^\]]*)?\]\]")
MEMORY_PENDING = re.compile(r"\b(?:pending|queued|due(?!\s+to\b)|overdue|owed|decides|deciding|waiting (?:on|for)|awaiting|"
                            r"remind(?:er)?|revisit|scheduled|follow[- ]?up|todo|tbd|deadline|not yet|to be decided)\b", re.I)
MEMORY_RELATIVE = re.compile(r"\b(?:tomorrow|yesterday|today|tonight|(?:next|this|last) (?:week|month|sprint))\b", re.I)
MEMORY_DATE = re.compile(r"\b(\d{4})-(\d{2})-(\d{2})\b")
# `by` and `on` read too many ranges ("on 2-3 worktrees") to take a day without two digits each.
MEMORY_SHORT_DATE = re.compile(r"\b(?:(?:decides?|due|revisit)\s+(\d{1,2})-(\d{1,2})|(?:by|on)\s+(\d{2})-(\d{2}))\b(?!-)", re.I)
MEMORY_REF = re.compile(r"(?:(?<![\w/&])#|\b(?:PR|pull request|issue)\s+#?)(\d{1,6})\b", re.I)
MEMORY_COMMIT = re.compile(r"\b(?=[0-9a-f]*[a-f])(?=[0-9a-f]*\d)[0-9a-f]{7,40}\b")
MEMORY_VERSION = re.compile(r"\b(\d+\.\d+\.\d+)\b")
MEMORY_PATH = re.compile(r"`([^`\s]+)`")
MEMORY_URL = re.compile(r"\bhttps?://\S+")
MEMORY_EXTENSIONS = (".md", ".py", ".json", ".ts", ".tsx", ".js", ".mjs", ".yml", ".yaml", ".toml", ".html",
                     ".css", ".sh", ".sql", ".go", ".rs", ".java", ".kt", ".swift", ".rb", ".txt")


def memory_config(project: Project) -> dict:
    conf = project.config.get("memory") or {}
    return {k: type(v)(conf.get(k, v)) for k, v in MEMORY_DEFAULTS.items()}


def memory_dir(project: Project, given: str | None = None) -> str:
    """This checkout's memory folder: the main checkout's, which its worktrees share."""
    if given:
        return os.path.abspath(os.path.expanduser(given))
    home = os.environ.get("CLAUDE_CONFIG_DIR") or os.path.join(os.path.expanduser("~"), ".claude")
    # `autoMemoryDirectory` moves it: the local settings win over the project's, the project's over the user's.
    for settings in (os.path.join(project.root, ".claude", "settings.local.json"),
                     os.path.join(project.root, ".claude", "settings.json"), os.path.join(home, "settings.json")):
        try:
            moved = json.loads(read(settings)).get("autoMemoryDirectory")
        except (OSError, ValueError, AttributeError):
            continue
        if isinstance(moved, str) and moved.strip():
            return os.path.abspath(os.path.join(project.root, os.path.expanduser(moved.strip())))
    roots = []
    done = git(project.root, "rev-parse", "--path-format=absolute", "--git-common-dir")
    common = done.stdout.strip() if done.returncode == 0 else ""
    if os.path.basename(common) == ".git":
        roots.append(os.path.dirname(common))
    done = git(project.root, "rev-parse", "--show-toplevel")
    if done.returncode == 0 and done.stdout.strip():
        roots.append(done.stdout.strip())
    roots.append(project.root)
    dirs = []
    for root in roots:
        for path in (os.path.abspath(root), os.path.realpath(root)):
            d = os.path.join(home, "projects", re.sub(r"[^A-Za-z0-9]", "-", path.rstrip("/\\")), "memory")
            if d not in dirs:
                dirs.append(d)
    return next((d for d in dirs if os.path.isdir(native(d))), dirs[0])


def memory_front_matter(text: str):
    """({key: value}, first body line). Claude Code's memories nest `type` under `metadata:`."""
    lines = text.split("\n")
    if not lines or lines[0].lstrip("﻿").strip() != "---":
        return None, 0
    fields, parent = {}, None
    for i in range(1, len(lines)):
        line = lines[i]
        if line.strip() == "---":
            return fields, i + 1
        m = re.match(r"^(\s*)([A-Za-z_][\w-]*):\s*(.*)$", line)
        if not m:
            continue
        key, value = m.group(2), m.group(3).strip()
        if len(value) > 1 and value[0] == value[-1] == '"':
            try:
                value = json.loads(value)
            except ValueError:
                value = value[1:-1]
        elif len(value) > 1 and value[0] == value[-1] == "'":
            value = value[1:-1].replace("''", "'")
        if m.group(1) and parent:
            fields[f"{parent}.{key}"] = value
        else:
            fields[key], parent = value, key if not value else None
    return None, 0


def memory_day(year: int, month: int, day: int) -> date | None:
    """The day, or None for one that does not exist (2026-02-31): a typo must not stop the report."""
    try:
        return date(year, month, day)
    except ValueError:
        return None


def memory_clauses(line: str) -> list:
    """A line in the parts a date or an ID belongs to, so one `pending` reaches only its own clause."""
    return [c for c in re.split(r"(?<=[.;])\s+|\s+[—–]\s+|\s+-\s+|;\s*", line) if c.strip()]


def memory_words(text: str) -> list:
    return re.findall(r"[a-z0-9]+", text.lower())


def memory_shingles(text: str, size: int = 5) -> set:
    words = memory_words(text)
    return {" ".join(words[i:i + size]) for i in range(len(words) - size + 1)}


def memory_refs(project: Project, numbers: list) -> dict | None:
    """{number: {kind, state, title, date}} from one `gh api graphql` call per hundred numbers, or None
    when gh cannot answer. A number the repository does not have maps to None."""
    if not numbers:
        return {}
    if not shutil.which("gh"):
        return None
    found = {}
    for i in range(0, len(numbers), 100):
        fields = " ".join(f"n{n}: issueOrPullRequest(number: {n}) {{ __typename ... on PullRequest "
                          "{ state title mergedAt closedAt } ... on Issue { state title closedAt } }"
                          for n in numbers[i:i + 100])
        query = f"query($owner: String!, $name: String!) {{ repository(owner: $owner, name: $name) {{ {fields} }} }}"
        try:
            # A number it cannot find fails the call, with the rest of the answer still on stdout.
            done = subprocess.run(["gh", "api", "graphql", "-F", "owner={owner}", "-F", "name={repo}", "-f",
                                   f"query={query}"], cwd=project.root, capture_output=True, text=True, timeout=60)
            repo = (json.loads(done.stdout or "null") or {}).get("data", {}).get("repository")
        except (OSError, ValueError, AttributeError, subprocess.TimeoutExpired):
            repo = None
        if repo is None:
            return None
        for n in numbers[i:i + 100]:
            said = repo.get(f"n{n}")
            found[n] = said and {"kind": "pr" if said.get("__typename") == "PullRequest" else "issue",
                                 "state": str(said.get("state", "")).lower(), "title": said.get("title", ""),
                                 "date": (said.get("mergedAt") or said.get("closedAt") or "")[:10]}
    return found


def memory_commit(project: Project, sha: str, main: str) -> str:
    """`main`, `elsewhere` (in this clone, not on the main branch) or `missing`."""
    if git(project.root, "cat-file", "-e", f"{sha}^{{commit}}").returncode != 0:
        return "missing"
    for ref in (f"origin/{main}", main):
        if git(project.root, "rev-parse", "--verify", "--quiet", ref).returncode == 0:
            return "main" if git(project.root, "merge-base", "--is-ancestor", sha, ref).returncode == 0 else "elsewhere"
    return "elsewhere"


def memory_path_exists(tracked: set, token: str) -> bool | None:
    """Whether a backticked path a memory names is tracked — as given, or as the end of a longer
    path, since a memory often names a file by its last parts. None when the token is not a path."""
    path = re.sub(r":\d+(?:-\d+)?$", "", token)
    folder = path.endswith("/")
    path = path.rstrip("/")
    if path.startswith("/") or (folder and "/" not in path):
        return None  # a URL's path, or a branch prefix like `fix/`
    name = path.rsplit("/", 1)[-1]
    if (not path or not re.match(r"^[\w./@+-]+$", path) or ".." in path.split("/") or path.startswith(("~", "-"))
            or not (folder or (name.endswith(MEMORY_EXTENSIONS) and not name.startswith(".") and "." in name[1:]))):
        return None
    return any(f == path or f.endswith("/" + path) or (folder and (f.startswith(path + "/") or f"/{path}/" in f))
               for f in tracked)


def memory_items(project: Project) -> tuple:
    """({ID: state}, ID pattern) from file names, opening only the files a memory names."""
    names = Names(project)
    located = names.located()
    for n in names.numbers("decision"):
        located.setdefault(f"{project.ids['decision']}-{n}", []).append(("decision", None, None))
    prefixes = sorted(set(project.ids.values()), key=len, reverse=True)
    pattern = re.compile(r"(?<![\w/-])(" + "|".join(map(re.escape, prefixes)) + r")-(\d+)\b")

    def state(ident):
        if ident not in located:
            return None
        kind, rel, _ = located[ident][0]
        if not rel:
            return "recorded"
        fm, _, _ = parse_front_matter(names.read(rel) or "")
        return (fm or {}).get("state") or "unknown"

    return state, pattern


def memory_check(project: Project, folder: str | None = None, offline: bool = False, today: str | None = None) -> dict:
    """The memory folder's index and files, each with what can be told for certain about it."""
    conf, folder = memory_config(project), memory_dir(project, folder)
    now = date.fromisoformat(today) if today else date.today()
    report = {"dir": folder, "exists": os.path.isdir(native(folder)), "today": now.isoformat(),
              "index": {}, "problems": [], "memories": [], "gh": "offline" if offline else "unused"}
    if not report["exists"]:
        return report

    def finding(level, kind, text, line=0, where="file"):
        return {"level": level, "kind": kind, "text": text, "line": line, "where": where}

    index_path = os.path.join(folder, "MEMORY.md")
    index_text = read(index_path) if os.path.isfile(native(index_path)) else None
    files = sorted((f for f in os.listdir(native(folder)) if f.endswith(".md") and f != "MEMORY.md"), key=natural_key)
    problems, listed, long_lines = report["problems"], {}, []
    if index_text is None:
        problems.append(finding("error", "no_index", "there is no MEMORY.md, so no memory reaches a session", where="index"))
        index_lines = []
    else:
        index_lines = index_text.split("\n")
        while index_lines and not index_lines[-1].strip():
            index_lines.pop()
        size = len(index_text.encode("utf-8"))
        report["index"] = {"lines": len(index_lines), "bytes": size, "budget_lines": conf["index_lines"],
                           "budget_bytes": conf["index_bytes"]}
        if len(index_lines) > MEMORY_LOADED or size > MEMORY_LOADED_BYTES:
            problems.append(finding("error", "cut_off", f"{len(index_lines)} lines, {size / 1000:.1f} KB — Claude Code "
                                    f"loads the first {MEMORY_LOADED} lines or {MEMORY_LOADED_BYTES // 1000} KB, so the "
                                    "rest never reaches a session", where="index"))
        if len(index_lines) > conf["index_lines"] or size > conf["index_bytes"]:
            problems.append(finding("warning", "over_budget", f"{len(index_lines)} lines, {size / 1000:.1f} KB — over the "
                                    f"budget of {conf['index_lines']} lines, {conf['index_bytes'] / 1000:.1f} KB "
                                    "(`memory` in the config); every session pays for it", where="index"))
    for number, line in enumerate(index_lines, 1):
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        m = MEMORY_LINE.match(line)
        if not m:
            problems.append(finding("warning", "not_a_line", "not an index line `- [Title](file.md) — hook`: "
                                    + line.strip()[:80], number, "index"))
            continue
        target = posixpath.normpath(urllib.parse.unquote(m.group(2).split("#")[0]))
        if target in listed:
            problems.append(finding("warning", "twice", f"{target} is listed again (first on line {listed[target][0]})",
                                    number, "index"))
            continue
        listed[target] = (number, m.group(1), m.group(3), line)
        if not os.path.isfile(native(os.path.join(folder, target))):
            problems.append(finding("error", "dead_line", f"points at {target}, which does not exist", number, "index"))
        if len(line) > conf["line_chars"]:
            long_lines.append(f"{target} ({len(line)})")

    if long_lines:
        problems.append(finding("warning", "long_line", f"{len(long_lines)} line{'s' if len(long_lines) != 1 else ''} "
                                f"over {conf['line_chars']} characters — the detail belongs in the file: "
                                + ", ".join(long_lines), where="index"))
    state_of, id_pattern = memory_items(project)
    done = git(project.root, "ls-files", "-z")
    tracked = set(done.stdout.split("\0")) - {""} if done.returncode == 0 else set()
    main = main_branch(project)
    current = version_tuple(str(project.config.get("spry", "")))
    corpus = {}
    for rel in ("AGENTS.md", "CLAUDE.md"):
        if os.path.isfile(native(os.path.join(project.root, rel))):
            corpus[rel] = memory_shingles(read(os.path.join(project.root, rel)))
    for dirpath, _, filenames in walk_dir(os.path.join(project.spry, "knowledge")):
        for f in filenames:
            if f.endswith(".md"):
                path = os.path.join(dirpath, f)
                corpus[project.rel(path)] = memory_shingles(read(path))

    memories, names, refs_wanted = [], {}, set()
    for f in files:
        path = os.path.join(folder, f)
        text = read(path)
        fm, start = memory_front_matter(text)
        fm = fm or {}
        kind = fm.get("metadata.type") or fm.get("type") or ""
        body_lines = text.split("\n")[start:]
        days = int((time.time() - os.path.getmtime(native(path))) // 86400)
        m = {"file": f, "name": fm.get("name", ""), "type": kind, "description": fm.get("description", ""),
             "days": days, "findings": [], "ids": {}, "refs": {}, "commits": {}, "_body": "\n".join(body_lines)}
        memories.append(m)
        if not fm:
            m["findings"].append(finding("error", "front_matter", "no front-matter (`name`, `description`, `metadata.type`)", 1))
        else:
            for key in ("name", "description"):
                if not fm.get(key):
                    m["findings"].append(finding("error", "front_matter", f"front-matter has no `{key}`", 1))
            if kind not in MEMORY_TYPES:
                m["findings"].append(finding("error", "front_matter", f"type `{kind or '—'}` is not one of "
                                             + ", ".join(MEMORY_TYPES), 1))
        if m["name"]:
            names.setdefault(m["name"], []).append(f)
        if kind in ("feedback", "project"):
            missing = [w for w in ("**Why:**", "**How to apply:**") if w not in m["_body"]]
            if missing:
                m["findings"].append(finding("warning", "why_missing", f"a {kind} memory without "
                                             + " or ".join(missing)))
        if f not in listed:
            problems.append(finding("error", "orphan", f"{f} is not in MEMORY.md, so no session knows it is there",
                                    where="index"))
        if kind == "project" and days > conf["stale_days"]:
            m["findings"].append(finding("note", "old", f"unchanged for {days} days"))

        # An index line is one statement: its title says what the hook's clauses are about. A
        # **Why:** line tells what happened, so nothing in it is still to do.
        lines = [(n + start + 1, line, "file", "") for n, line in enumerate(body_lines)]
        if f in listed:
            lines.append((listed[f][0], f"{listed[f][1]} — {listed[f][2]}", "index", listed[f][1]))
        relative = []
        for number, line, where, title in lines:
            plain = MEMORY_URL.sub("", line)
            relative += [(number, where, match.group(0)) for match in MEMORY_RELATIVE.finditer(plain)]
            history = "**Why:**" in line
            for clause in memory_clauses(plain):
                pending = not history and bool(MEMORY_PENDING.search(clause) or MEMORY_PENDING.search(title))
                quote = clause.strip()[:90]
                if pending:
                    days_named = [memory_day(int(y), int(mo), int(d)) for y, mo, d in MEMORY_DATE.findall(clause)]
                    if not MEMORY_DATE.search(clause):
                        for groups in MEMORY_SHORT_DATE.findall(clause):
                            mo, d = [int(g) for g in groups if g]
                            # A month-day with no year is this year's — next year's for January or February, said in December.
                            days_named.append(memory_day(now.year + (now.month == 12 and mo < 3), mo, d))
                    days_named = [d for d in days_named if d]
                    past = [d for d in days_named if d < now]
                    if past and len(past) == len(days_named):
                        m["findings"].append(finding("warning", "past_date", f"“{quote}” — {max(past).isoformat()} "
                                                     "has passed", number, where))
                for prefix, num in id_pattern.findall(clause):
                    ident = f"{prefix}-{num}"
                    state = state_of(ident)
                    m["ids"][ident] = state or "missing"
                    if pending and state in ("closed", "dropped"):
                        m["findings"].append(finding("warning", "item_done", f"{ident} is {state}, but “{quote}” "
                                                     "reads as still to do", number, where))
                for num in MEMORY_REF.findall(clause):
                    refs_wanted.add(int(num))
                    m["refs"].setdefault(int(num), []).append((number, where, pending, quote))
                for sha in MEMORY_COMMIT.findall(clause):
                    m["commits"].setdefault(sha, (number, where))
                older = [v for v in MEMORY_VERSION.findall(clause) if current and version_tuple(v) < current]
                if older and "spry" in line.lower():
                    m["findings"].append(finding("note", "version", f"names {', '.join(older)}; this project is on "
                                                 f"spry {project.config.get('spry')}", number, where))
            for token in MEMORY_PATH.findall(line):
                if tracked and memory_path_exists(tracked, token) is False:
                    m["findings"].append(finding("warning", "path_missing", f"names `{token}`, which is not in "
                                                 "this checkout", number, where))
            for target in MEMORY_WIKI.findall(line):
                m.setdefault("_links", []).append((target.strip(), number))
        if relative:
            said = ", ".join(f"“{w}” ({'index line' if where == 'index' else 'line'} {n})" for n, where, w in relative)
            m["findings"].append(finding("warning", "relative_date", f"says {said} — with no day, nobody can tell "
                                         "when that was"))

    for name, owners in names.items():
        if len(owners) > 1:
            problems.append(finding("error", "same_name", f"{', '.join(owners)} share the name `{name}`", where="index"))
    for m in memories:
        for target, number in m.pop("_links", []):
            if target not in names:
                m["findings"].append(finding("note", "link_dangling", f"links [[{target}]], which no memory has yet",
                                             number))
        missing = [i for i, s in m["ids"].items() if s == "missing"]
        if missing:
            m["findings"].append(finding("note", "item_missing", "names " + ", ".join(missing) + ", not in this "
                                         "project's plan"))
        if m["commits"]:
            m["commits"] = {sha: memory_commit(project, sha, main) for sha in m["commits"]}
            for sha, where in m["commits"].items():
                if where == "missing":
                    m["findings"].append(finding("note", "commit_missing", f"names commit {sha}, which this clone "
                                                 "does not have — fetch, or it was rewritten"))
                elif where == "elsewhere":
                    m["findings"].append(finding("note", "commit_off_main", f"names commit {sha}, which is not on {main}"))
        shingles = memory_shingles(m["_body"])
        if len(shingles) >= 5:
            best = max(((len(shingles & s) / len(shingles), rel) for rel, s in corpus.items()), default=(0, ""))
            if best[0] >= 0.4:
                m["findings"].append(finding("warning", "repeats", f"{round(best[0] * 100)}% of it is already in "
                                             f"{best[1]}, which the repository keeps"))

    words = {m["file"]: {w for w in memory_words(m["description"] + " " + m["_body"])
                         if len(w) > 3 and w not in STOPWORDS and not w.isdigit()} for m in memories}
    for i, a in enumerate(memories):
        for b in memories[i + 1:]:
            wa, wb = words[a["file"]], words[b["file"]]
            if len(wa) >= 8 and len(wb) >= 8 and len(wa & wb) / len(wa | wb) >= 0.45:
                a["findings"].append(finding("note", "overlap", f"overlaps {b['file']} "
                                             f"({round(len(wa & wb) / len(wa | wb) * 100)}% of words shared)"))

    refs = {} if offline else memory_refs(project, sorted(refs_wanted))
    if not offline:
        report["gh"] = "unavailable" if refs is None else "checked" if refs_wanted else "unused"
    for m in memories:
        wanted, m["refs"] = m["refs"], {}
        for num, uses in wanted.items():
            said = (refs or {}).get(num)
            m["refs"][num] = said or {"state": "unknown"}
            if said and said["state"] in ("merged", "closed"):
                for number, where, pending, quote in uses:
                    if pending:
                        m["findings"].append(finding("warning", "ref_done", f"#{num} ({said['kind']}) was "
                                                     f"{said['state']} {said['date']}, but “{quote}” reads as still "
                                                     "to do", number, where))
        del m["_body"]
        m["findings"] = [f for i, f in enumerate(m["findings"]) if f not in m["findings"][:i]]
        m["findings"].sort(key=lambda x: (("error", "warning", "note").index(x["level"]), x["line"]))
    report["memories"] = memories
    return report


def memory_text(report: dict) -> str:
    marks = {"error": "✗", "warning": "!", "note": "·"}
    if not report["exists"]:
        return (f"no memory at {report['dir']} — Claude Code has not saved one for this checkout, or it lives "
                "elsewhere: `autoMemoryDirectory` in Claude Code's settings, or --dir")
    out = [f"memory: {report['dir']}"]
    idx = report["index"]
    if idx:
        out.append(f"index: {idx['lines']} lines, {idx['bytes'] / 1000:.1f} KB "
                   f"(budget {idx['budget_lines']} lines, {idx['budget_bytes'] / 1000:.1f} KB)")
    out.append({"checked": "pull requests and issues: read with gh", "offline": "pull requests and issues: not read (--offline)",
                "unavailable": "pull requests and issues: gh could not answer — not checked",
                "unused": "pull requests and issues: none named"}[report["gh"]])

    def at(f):
        return f"{'index line' if f['where'] == 'index' else 'line'} {f['line']}: " if f["line"] else ""

    if report["problems"]:
        out += ["", "MEMORY.md"] + [f"  {marks[f['level']]} {at(f)}{f['text']}" for f in report["problems"]]
    clean = 0
    for m in report["memories"]:
        named = []
        for what, states in (("items", list(m["ids"].values())), ("pull requests and issues",
                                                                   [r["state"] for r in m["refs"].values()])):
            if states:
                counts = {s: states.count(s) for s in states}
                named.append(f"{len(states)} {what} (" + ", ".join(f"{c} {s}" for s, c in counts.items()) + ")")
        if not m["findings"]:
            clean += 1
            if not named:
                continue
        out += ["", f"{m['file']} · {m['type'] or '?'} · {m['days']}d · {m['description'][:80]}"]
        out += [f"  {marks[f['level']]} {at(f)}{f['text']}" for f in m["findings"]]
        if named:
            out.append("  names " + "; ".join(named))
    found = sum(1 for m in report["memories"] if m["findings"])
    out += ["", f"{len(report['memories'])} memories: {found} with findings, {clean} without"]
    return "\n".join(out)


# ---------------------------------------------------------------- agent hooks

# Claude Code runs these from the plugin's hooks/hooks.json, each filtered so that no process starts
# for a tool call it cannot be about. Each acts only when its key under `hooks` in the config is true;
# `SPRY_HOOKS=off` turns all of them off. A hook's own failure lets the call through: `check`, CI and
# `merge-check` stay the authority, and a hook only says it sooner.
AGENT_HOOKS = ("session", "link_fields", "cited_criteria", "check_edit", "merge", "check_stop")
HOOKS_SINCE = (0, 34, 0)
LINK_FIELDS = ("branch", "pr", "issue", "owner")
IN_PLACE = re.compile(r"\b(?:g?sed|perl)\b[^|;&\n]*\s-[a-zA-Z]*i")
LINK_KEY = re.compile(r"\b(?:branch|pr|issue|owner):")
GH_VALUE_FLAGS = {"-t", "--subject", "-b", "--body", "-F", "--body-file", "-A", "--author-email",
                  "--match-head-commit", "-R", "--repo"}


def version_tuple(text: str) -> tuple:
    return tuple(int(n) for n in re.findall(r"\d+", text)[:3])


def vendored_version(path: str) -> tuple | None:
    """The `VERSION` of a copy of this tool, read from its head without running it."""
    try:
        with open(native(path), encoding="utf-8") as handle:
            m = re.search(r'^VERSION = "([^"]+)"', handle.read(32768), re.M)
    except OSError:
        return None
    return version_tuple(m.group(1)) if m else None


def edited_text(payload: dict, before: str | None) -> str | None:
    """The file as an Edit or Write in the payload would leave it — None when it cannot be known."""
    given = payload.get("tool_input") or {}
    if payload.get("tool_name") == "Write":
        return given.get("content")
    old, new = given.get("old_string"), given.get("new_string")
    if before is None or not isinstance(old, str) or not isinstance(new, str) or old not in before:
        return None
    return before.replace(old, new) if given.get("replace_all") else before.replace(old, new, 1)


def hook_file(project: Project, payload: dict) -> tuple:
    """(absolute path, path from the root, current text or None) of the file an Edit or Write names."""
    path = (payload.get("tool_input") or {}).get("file_path") or ""
    if not path:
        return "", "", None
    path = os.path.abspath(os.path.join(payload.get("cwd") or project.root, path))
    text = read(path) if os.path.isfile(native(path)) else None
    return path, project.rel(path), text


def deny(reason: str) -> dict:
    return {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny",
                                   "permissionDecisionReason": reason}}


def current_branch(project: Project) -> str:
    done = git(project.root, "rev-parse", "--abbrev-ref", "HEAD")
    return done.stdout.strip() if done.returncode == 0 else ""


def hook_session(project: Project, payload: dict) -> dict | None:
    """What a new or compacted session would otherwise look for: the config, the tool, this branch's slice."""
    lines = ["spry project: the config is spry/spry.config.json; run the tool as "
             "`python3 spry/tool/spry.py <command>`; the rules are in spry/process/."]
    branch, main = current_branch(project), main_branch(project)
    if branch and branch not in (main, "HEAD"):
        names = Names(project)
        docs = sorted((ident, d) for ident, places in names.located().items() for kind, d, _ in places if kind == "slice")
        # By file name first, as slice-open names branches; only then each slice's `branch:`.
        named = [(i, d) for i, d in docs if os.path.basename(d)[:-3].lower() == branch.lower()] or \
            [(i, d) for i, d in docs if (parse_front_matter(names.read(d) or "")[0] or {}).get("branch") == branch]
        if named:
            ident, doc = named[0]
            fm = parse_front_matter(names.read(doc) or "")[0] or {}
            owner = f", owner {fm['owner']}" if fm.get("owner") else ""
            lines.append(f"This branch builds {ident} {fm.get('title', '')} — {fm.get('state', '?')}{owner}: "
                         f"{doc}. Its work order is the plan; spry/process/slicing.md says what comes next.")
        else:
            lines.append(f"This branch, `{branch}`, is no slice's branch.")
    elif branch and branch != "HEAD":
        lines.append(f"On `{main}`, the main branch.")
    tone = os.path.join(project.root, ".spry", "tone")
    if os.path.isfile(native(tone)) and read(tone).strip():
        lines.append(f"The person set their tone to {read(tone).strip()} (spry/process/chat.md *Audience*).")
    on = [n for n in AGENT_HOOKS if (project.config.get("hooks") or {}).get(n)]
    lines.append("spry hooks on: " + ", ".join(on) + " (`hooks` in the config; SPRY_HOOKS=off turns them off).")
    return {"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": "\n".join(lines)}}


def hook_link_fields(project: Project, payload: dict) -> dict | None:
    """A slice's `branch`, `pr`, `issue` and `owner` are set by `link`, which checks them, not by hand."""
    given = payload.get("tool_input") or {}
    if payload.get("tool_name") == "Bash":
        command = given.get("command") or ""
        slice_doc = re.search(r"\b" + re.escape(project.ids["slice"]) + r"-\d+[\w-]*\.md\b", command)
        if IN_PLACE.search(command) and slice_doc and LINK_KEY.search(command):
            return deny("A slice's `branch`, `pr`, `issue` and `owner` are set with `python3 spry/tool/spry.py "
                        "link SL-<n> --branch <b> --pr <n> --issue <n> --owner [<name>]`, which checks each one — "
                        "not with an in-place edit.")
        return None
    path, rel, before = hook_file(project, payload)
    if before is None or not rel.startswith("spry/plan/") or not project.slice_file.match(os.path.basename(path)):
        return None
    after = edited_text(payload, before)
    old, new = parse_front_matter(before)[0], parse_front_matter(after or "")[0]
    if old is None or new is None:
        return None  # `check` names a broken front-matter
    changed = [k for k in LINK_FIELDS if str(old.get(k) or "") != str(new.get(k) or "")]
    if not changed:
        return None
    flags = " ".join(f"--{k} {shlex.quote(str(new[k]))}" if new.get(k) else "--owner" if k == "owner" else f"--{k} <{k}>"
                     for k in changed)
    return deny(f"`{'`, `'.join(changed)}` in {old.get('id', rel)} {'is' if len(changed) == 1 else 'are'} set by the "
                f"tool, which checks {'it' if len(changed) == 1 else 'them'}: `python3 spry/tool/spry.py link "
                f"{old.get('id', 'SL-<n>')} {flags}`. Make the rest of the edit without changing "
                f"{'that line' if len(changed) == 1 else 'those lines'}.")


def hook_cited_criteria(project: Project, payload: dict) -> dict | None:
    """Changing a criterion that tests already cite is the story owner's call: ask the person now,
    not at `merge-check`."""
    path, rel, before = hook_file(project, payload)
    if before is None or not rel.startswith("spry/plan/") or os.path.basename(path) != "README.md":
        return None
    fm = parse_front_matter(before)[0] or {}
    story = str(fm.get("id", ""))
    if not story.startswith(project.ids["story"] + "-"):
        return None
    old, new = ac_texts(before, struck=True), ac_texts(edited_text(payload, before) or before, struck=True)
    cited = {}
    for ac in [a for a in old if new.get(a) != old[a]]:
        done = git(project.root, "grep", "-l", "-E", "--untracked", "-e", f"{re.escape(story)}/{ac}([^0-9]|$)", "--", ".",
                   ":(exclude)spry", ":(exclude)*.md")
        if done.returncode == 0 and done.stdout.strip():
            cited[ac] = done.stdout.split()
    if not cited:
        return None
    where = "; ".join(f"{story}/{ac} by {', '.join(files[:3])}{' …' if len(files) > 3 else ''}"
                      for ac, files in cited.items())
    owner = f" ({fm['owner']})" if fm.get("owner") else ""
    return {"hookSpecificOutput": {
        "hookEventName": "PreToolUse", "permissionDecision": "ask",
        "permissionDecisionReason": f"This changes criteria that tests already cite — {where}. The story's owner{owner} "
                                    f"decides a criterion: with code changed on the same branch, the slice needs "
                                    f"`criteria_approved_by:` them before merge-check passes."}}


def check_file(project: Project, path: str, text: str) -> list:
    """`check` of one document by its text: front-matter, budget, guides and placeholders, links, glossary."""
    gloss = os.path.join(project.root, project.config.get("glossary", "spry/knowledge/glossary.md"))
    terms = glossary_terms(read(gloss)) if os.path.isfile(native(gloss)) else []
    project.problems = []
    fm = {}
    if project.rel(path) != "AGENTS.md":
        fm, _start, errors = parse_front_matter(text)
        for line, message in errors:
            project.problem(path, line, message)
    check_text(project, path, text, fm or {}, banned_patterns(terms), budget_patterns(project), gloss)
    return project.problems


def hook_check_edit(project: Project, payload: dict) -> dict | None:
    """After an edit to a document `check` reads, the errors in that one file — not the whole plan."""
    path, rel, text = hook_file(project, payload)
    skipped = ("spry/process/", "spry/tool/", "spry/skills/", "spry/history/")
    if text is None or not rel.endswith(".md") or rel.startswith(skipped) or \
            not (rel.startswith("spry/") or rel == "AGENTS.md"):
        return None
    errors = [p for p in check_file(project, path, text) if p.level == "error"]
    if not errors:
        return None
    return {"decision": "block", "reason": f"spry check of {rel}: {len(errors)} error{'s' if len(errors) != 1 else ''} "
                                           f"— fix {'it' if len(errors) == 1 else 'them'} now:\n" +
                                           "\n".join(str(p) for p in errors[:15])}


def merge_target(command: str):
    """What a `gh pr merge` in the command names — a PR number, a branch, or "" for the current
    branch; False when the command merges no pull request."""
    lexer = shlex.shlex(command.replace("\n", " ; "), posix=True, punctuation_chars=";&|")
    lexer.whitespace_split = True
    try:
        tokens = list(lexer)
    except ValueError:
        return False
    parts, part = [], []
    for token in tokens:
        if token and set(token) <= set(";&|"):
            parts.append(part)
            part = []
        else:
            part.append(token)
    for words in parts + [part]:
        if words[:3] != ["gh", "pr", "merge"]:
            continue
        rest, i, found = words[3:], 0, ""
        while i < len(rest):
            word = rest[i]
            if word in ("-R", "--repo") or word.startswith("--repo="):
                return False  # another repository's pull request
            if word in GH_VALUE_FLAGS:
                i += 2
                continue
            if not word.startswith("-") and not found:
                m = re.search(r"/pull/(\d+)", word)
                found = m.group(1) if m else word.lstrip("#")
            i += 1
        return found
    return False


def hook_merge(project: Project, payload: dict) -> dict | None:
    """`merge-check` before `gh pr merge` of a slice's pull request — it holds even when CI never ran."""
    target = merge_target((payload.get("tool_input") or {}).get("command") or "")
    if target is False:
        return None
    full = Project(project.root)
    slices = full.of_type("slice")
    if target.isdigit():
        found = [s for s in slices if str(s.fm.get("pr", "")).lstrip("#") == target]
    else:
        branch = target or current_branch(full)
        found = [s for s in slices if branch and branch in (branch_of(s), slice_branch(s))]
    if len(found) != 1:
        return None  # not a slice's pull request: a plan PR, or one spry does not track
    if current_branch(full) not in (branch_of(found[0]), slice_branch(found[0])):
        return None  # this tree holds another branch's copy of the slice; merging.md runs merge-check on the PR's
    lines = merge_check(full, found[0].id, f"origin/{main_branch(full)}")
    blocks = [text for level, text in lines if level == "block"]
    if not blocks:
        return None
    return deny(f"merge-check {found[0].id}: {len(blocks)} thing{'s block' if len(blocks) != 1 else ' blocks'} the "
                f"merge —\n" + "\n".join("✗ " + b for b in blocks) + "\n/spry:merge says what to do with each.")


def hook_check_stop(project: Project, payload: dict) -> dict | None:
    """Before the agent stops with documents changed, `check` — once for each state of them."""
    if payload.get("stop_hook_active"):
        return None  # it already went back once this turn: let the person see what is left
    status = git(project.root, "status", "--porcelain", "-z", "--untracked-files=all", "--", "spry", "AGENTS.md")
    if status.returncode != 0:
        return None
    main = main_branch(project)
    fork = git(project.root, "merge-base", f"origin/{main}", "HEAD").stdout.strip() or \
        git(project.root, "merge-base", main, "HEAD").stdout.strip()
    branch = git(project.root, "diff", "--name-only", f"{fork}..HEAD", "--", "spry", "AGENTS.md").stdout if fork else ""
    if not status.stdout.strip() and not branch.strip():
        return None
    top = git(project.root, "rev-parse", "--show-toplevel").stdout.strip() or project.root
    seen = [git(project.root, "rev-parse", "HEAD").stdout.strip(), status.stdout]
    entries = status.stdout.split("\0")
    for i, entry in enumerate(entries):
        if len(entry) < 4 or (i and entries[i - 1][:1] in ("R", "C")):
            continue  # the old name of a rename or copy
        path = os.path.join(top, entry[3:])
        if os.path.isfile(native(path)):
            info = os.stat(native(path))
            seen.append(f"{entry[3:]}:{info.st_size}:{info.st_mtime_ns}")
    mark = hashlib.sha1("\n".join(seen).encode()).hexdigest()
    stamp = os.path.join(project.root, ".spry", "hooks", "check-stop")
    if os.path.isfile(native(stamp)) and read(stamp).strip() == mark:
        return None
    errors = [p for p in check(Project(project.root)) if p.level == "error"]
    os.makedirs(native(os.path.dirname(stamp)), exist_ok=True)
    write(stamp, mark + "\n")  # failing too: the agent goes back once for this state, not at every turn
    if not errors:
        return None
    return {"decision": "block", "reason": f"spry check: {len(errors)} error{'s' if len(errors) != 1 else ''} in the "
                                           f"documents — fix them before you finish, or say why they stay:\n" +
                                           "\n".join(str(p) for p in errors[:15])}


AGENT_HOOK_RUN = {"session": hook_session, "link_fields": hook_link_fields, "cited_criteria": hook_cited_criteria,
                  "check_edit": hook_check_edit, "merge": hook_merge, "check_stop": hook_check_stop}


def agent_hook(name: str, stdin: str, root: str | None = None) -> tuple:
    """(exit code, JSON to print or None) for one hook call. The project's own copy of the tool runs
    it when that copy is another version, so a hook follows the rules the project took."""
    if os.environ.get("SPRY_HOOKS", "").lower() in ("off", "0", "false", "no"):
        return 0, None
    try:
        payload = json.loads(stdin or "{}")
    except ValueError:
        return 0, None
    root = root or find_root(payload.get("cwd") or os.getcwd())
    if not root:
        return 0, None
    try:
        config = json.loads(read(os.path.join(root, "spry", "spry.config.json")))
    except (OSError, ValueError):
        return 0, None
    if not isinstance(config, dict) or not (config.get("hooks") or {}).get(name):
        return 0, None
    own = os.path.join(root, "spry", "tool", "spry.py")
    if os.path.isfile(native(own)) and os.path.realpath(own) != os.path.realpath(__file__):
        version = vendored_version(own)
        if version != version_tuple(VERSION):
            if version is None or version < HOOKS_SINCE:
                return 0, None
            done = subprocess.run([sys.executable, own, "agent-hook", name], input=stdin.encode("utf-8"),
                                  capture_output=True, cwd=root)
            out = done.stdout.decode("utf-8", "replace").strip()
            return 0, (json.loads(out) if out.startswith("{") else None)
    try:
        return 0, AGENT_HOOK_RUN[name](Project(root, load=False, config=config), payload)
    except (Exception, SystemExit) as e:  # noqa: BLE001 — a hook's own failure lets the call through
        print(f"spry hook {name}: {e}", file=sys.stderr)
        return 0, None


def find_root(start: str):
    here = os.path.abspath(start)
    while True:
        if os.path.isfile(native(os.path.join(here, "spry", "spry.config.json"))):
            return here
        parent = os.path.dirname(here)
        if parent == here:
            return None
        here = parent


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="spry", description="spry project tool")
    parser.add_argument("--root", help="project root (default: nearest folder holding spry/spry.config.json)")
    parser.add_argument("--version", action="version", version=VERSION)
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("check", help="consistency of the plan, knowledge and links")
    p.add_argument("--base", help="git ref the branch merges into: warns on cited criteria that changed, "
                                  "refuses generated blocks the branch changed")
    p = sub.add_parser("status", help="done vs total at every level")
    p.add_argument("id", nargs="?", help="only this item's branch")
    p.add_argument("--level", help="stop at this level, e.g. feature")
    p.add_argument("--all", action="store_true", help="every level, however long")
    p = sub.add_parser("coverage", help="defined vs done for the whole plan, and what is built but not proven")
    p = sub.add_parser("backlog", help="what is being built, what to build next, and what stands in the way")
    p = sub.add_parser("done", help="finished stories, tasks and bugs, newest first, with the day each closed")
    p = sub.add_parser("work", help="what one person built in a date range: their closed slices under each story, task or bug")
    p.add_argument("owner", help="a slice owner: a team.members name or GitHub login")
    p.add_argument("--since", required=True, help="first day, YYYY-MM-DD")
    p.add_argument("--until", help="last day, YYYY-MM-DD (default: today)")
    p.add_argument("--json", action="store_true", help="for /spry:work-report: with each file's path")
    p = sub.add_parser("owners", help="once: fill slices' missing owner from their pull requests' authors")
    p.add_argument("--from-prs", required=True, metavar="FILE",
                   help="`gh pr list --state all --limit 5000 --json number,author`, saved, or - for stdin")
    p.add_argument("--replace", action="store_true", help="also change an owner the PR's author contradicts")
    p.add_argument("--dry-run", action="store_true", help="change nothing; say what would change")
    p = sub.add_parser("view", help="write the backlog, coverage and done pages for this working tree to .spry/view/")
    p.add_argument("--since", help="only when the plan or a test changed since this commit (for git hooks)")
    p = sub.add_parser("serve", help="browse the plan and knowledge in a browser, read-only, on this machine")
    p.add_argument("--port", type=int, help=f"default: the first free one from {SERVE_PORT}")
    p.add_argument("--no-open", action="store_true", help="do not open a browser")
    p = sub.add_parser("hooks", help="git hooks that refresh .spry/view/ after a checkout or a pull")
    p.add_argument("--remove", action="store_true", help="remove the hooks spry wrote")
    p = sub.add_parser("index", help="regenerate marker blocks and INDEX.md files")
    g = p.add_mutually_exclusive_group()
    g.add_argument("--check", action="store_true", help="change nothing; exit 1 if anything is stale")
    g.add_argument("--restore", metavar="BASE", help="on a branch: put back BASE's copy of every generated block it changed")
    p = sub.add_parser("related", help="conflict-check candidates for a document")
    p.add_argument("file")
    p = sub.add_parser("link", help="set a slice's branch, pr, issue or owner in its front-matter")
    p.add_argument("slice")
    p.add_argument("--branch")
    p.add_argument("--pr")
    p.add_argument("--issue")
    p.add_argument("--owner", nargs="?", const="", help="who is building it: a team.members name or login; "
                                                        "bare, the person git says is at this clone")
    p = sub.add_parser("claim", help="take a slice before opening it: on the main branch with `mint: main`, then cut its branch")
    p.add_argument("slice")
    p.add_argument("--owner", help="who is building it: a team.members name or login (default: the person at this clone)")
    p.add_argument("--no-switch", action="store_true", help="make the branch without switching to it (for a worktree)")
    p = sub.add_parser("release", help="give back a claimed slice nobody is building: planned again, branch cleared")
    p.add_argument("slice")
    p = sub.add_parser("next", help="next free ID for a type")
    p.add_argument("type")
    p = sub.add_parser("new", help="create items from their templates, with the next IDs, in the right folders")
    p.add_argument("type", nargs="?")
    p.add_argument("--parent")
    p.add_argument("--title", action="append", help="repeat for several items of one type under one parent")
    p.add_argument("--batch", metavar="FILE", help="a JSON list of {type, title, parent, owner, key}, or - for stdin; "
                                                   "a parent may be the key of an earlier entry")
    p.add_argument("--owner")
    p.add_argument("--dependency", help="external: the service the behaviour belongs to")
    p = sub.add_parser("issue-body", help="a slice's issue: the work order as agreed, or with --close its close summary")
    p.add_argument("slice")
    p.add_argument("--close", action="store_true", help="the close summary, for a comment on the issue")
    p = sub.add_parser("pr-body", help="a slice's work order and close summary, for its pull request")
    p.add_argument("slice")
    p.add_argument("--base", help="git ref the PR merges into, to show criteria the branch changed")
    p = sub.add_parser("vendor", help="copy process/ and the tool into a project (run the plugin's copy)")
    p.add_argument("--force", action="store_true", help="overwrite an existing spry/process/")
    p.add_argument("--root", dest="vendor_root", help="the project to copy into (default: current folder)")
    p.add_argument("--diff", action="store_true", help="change nothing; list what differs from the plugin")
    p = sub.add_parser("scrub", help="private words still in a file meant to leave the project")
    p.add_argument("file")
    p = sub.add_parser("find", help="search spry/ and AGENTS.md")
    p.add_argument("query", nargs="+")
    p.add_argument("--limit", type=int, default=10)
    p.add_argument("--rebuild", action="store_true", help="rebuild the local index from scratch")
    p = sub.add_parser("install", help="put the skills where another agent finds them (run the plugin's copy)")
    p.add_argument("--agent", required=True, choices=AGENTS)
    p.add_argument("--root", dest="install_root", help="the project (default: current folder)")
    p = sub.add_parser("codeowners", help="write .github/CODEOWNERS from team.review")
    p.add_argument("--check", action="store_true", help="change nothing; exit 1 if it is stale")
    p = sub.add_parser("tests", help="test-suite reports")
    p.add_argument("--slowest", action="store_true", required=True, help="the slowest tests and files")
    p.add_argument("--junit", help="report file, folder or glob (default: tests.junit)")
    p.add_argument("--limit", type=int, default=10)
    p = sub.add_parser("draw", help="a replayable choice for an exploratory walk")
    p.add_argument("seed", nargs="?")
    p.add_argument("counter", nargs="?", help="the step number; add 1 on every draw")
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--seed", dest="new_seed", action="store_true", help="print a fresh seed")
    g.add_argument("--pick", action="store_true", help="one line from stdin")
    g.add_argument("--sample", type=int, metavar="K", help="K distinct lines from stdin")
    g.add_argument("--shuffle", action="store_true", help="every line from stdin, reordered")
    g.add_argument("--int", type=int, metavar="N", help="a number from 0 to N-1")
    p = sub.add_parser("merge-check", help="is a closed slice ready to merge? exit 1 if anything blocks it")
    p.add_argument("slice")
    p.add_argument("--base", help="git ref the PR merges into, to catch cited criteria that changed")
    p = sub.add_parser("merge-message", help="the squash commit for a slice: subject, summary, trailers")
    p.add_argument("slice")
    p.add_argument("--ci-local", metavar="REASON", help="CI never ran, for this reason; the gate stood in for it")
    p = sub.add_parser("gate", help="spry check, fast checks, affected tests — skipped while no code changed since green")
    p.add_argument("--force", action="store_true", help="run everything even if the code is unchanged")
    p.add_argument("--fast", action="store_true", help="spry check and the fast checks only, no tests; stamps nothing")
    p.add_argument("--full", action="store_true", help="the affected tests even when the branch changes only test files")
    p = sub.add_parser("pace", help="where slices' time went — the agent, checks, waiting on you — from this clone's logs")
    p.add_argument("slice", nargs="?", help="one slice in detail")
    p.add_argument("--since", metavar="YYYY-MM-DD", help="slices active since this day")
    p.add_argument("--last", type=int, metavar="N", help="the last N slices")
    p.add_argument("--compare", metavar="POINT", help="before and after a date, a CH-n or a commit")
    p = sub.add_parser("memory-check", help="Claude Code's memory for this checkout: index against files, dates gone by, "
                                            "and the IDs, pull requests, commits and paths it names")
    p.add_argument("--dir", help="the memory folder (default: this checkout's, under ~/.claude/projects/)")
    p.add_argument("--offline", action="store_true", help="do not ask gh about pull requests and issues")
    p.add_argument("--json", action="store_true")
    p = sub.add_parser("changed", help="for CI: prints code=true when files outside checks.docs changed since --base")
    p.add_argument("--base", required=True, help="git ref to compare with")
    p = sub.add_parser("falsify", help="prove a slice's tests notice its safeguards")
    fsub = p.add_subparsers(dest="action", required=True)
    q = fsub.add_parser("suggest", help="draft a plan from the source lines this branch added")
    q.add_argument("slice")
    q.add_argument("--base", help="branch to diff against (default: main_branch in config)")
    q.add_argument("--out", help="where to write the plan (default: .spry/falsify/<slice>.json)")
    q = fsub.add_parser("run", help="remove each control, run the tests that should notice, restore")
    q.add_argument("plan")
    q.add_argument("--dry-run", action="store_true", help="validate and list what would run")
    q.add_argument("--record", metavar="SLICE", help="write the results into this slice's Falsify table; "
                   "rows of controls not run stay")
    q.add_argument("--replace", action="store_true", help="with --record: drop the rows this run did not write")
    q.add_argument("--jobs", type=int, help="worktrees to run in parallel (default: falsify.parallel; 1 = serial)")
    p = sub.add_parser("agent-hook", help="for Claude Code's hooks: one hook call, its payload on stdin (hooks/hooks.json)")
    p.add_argument("name", choices=AGENT_HOOKS)
    p = sub.add_parser("review-check", help="would GitHub take this review as it stands? exit 1 if not")
    p.add_argument("payload", help="the review's JSON: commit_id, event, body, comments")
    p.add_argument("--diff", required=True, help="the pull request's diff (`gh pr diff <n>`), or - for stdin")
    p.add_argument("--own", action="store_true", help="the reviewer wrote the pull request")
    args = parser.parse_args(argv)

    if args.command == "review-check":
        try:
            payload = json.loads(read(args.payload))
        except (OSError, ValueError) as e:
            print(f"cannot read {args.payload}: {e}", file=sys.stderr)
            return 2
        problems = review_check(payload, sys.stdin.read() if args.diff == "-" else read(args.diff), args.own)
        for p in problems:
            print("✗ " + p)
        comments = payload.get("comments") if isinstance(payload, dict) else None
        count = len(comments) if isinstance(comments, list) else 0
        print(f"ready to post: {count} comment{'s' if count != 1 else ''}" if not problems
              else f"{len(problems)} problem{'s' if len(problems) != 1 else ''} — fix them before posting")
        return 1 if problems else 0

    if args.command == "agent-hook":
        # Bytes in, ASCII out: Windows' console code page would garble both.
        code, reply = agent_hook(args.name, sys.stdin.buffer.read().decode("utf-8", "replace"), args.root)
        if reply:
            print(json.dumps(reply))
        return code
    if args.command == "install":
        for path in install(args.install_root or args.root or os.getcwd(), args.agent):
            print("wrote: " + path)
        return 0
    if args.command == "draw":
        if args.new_seed:
            print(new_seed())
            return 0
        if args.seed is None or args.counter is None:
            print("draw needs <seed> <counter>", file=sys.stderr)
            return 2
        if args.int is not None:
            print("\n".join(draw(args.seed, args.counter, [], "int", args.int)))
            return 0
        choices = [line.strip() for line in sys.stdin.read().split("\n")
                   if line.strip() and not line.strip().startswith("#")]
        mode = "pick" if args.pick else "shuffle" if args.shuffle else "sample"
        print("\n".join(draw(args.seed, args.counter, choices, mode, args.sample or 1)))
        return 0
    if args.command == "vendor" and args.diff:
        lines = vendor_diff(args.vendor_root or args.root or os.getcwd())
        print("\n".join(lines) or "same as the plugin")
        return 0
    if args.command == "vendor":
        for path in vendor(args.vendor_root or args.root or os.getcwd(), args.force):
            print("wrote: " + path)
        return 0

    root = args.root or find_root(os.getcwd())
    if not root:
        print("not inside a spry project — no spry/spry.config.json above here; pass --root", file=sys.stderr)
        return 2
    # `new`, `claim` and `release` open only the files they write (`Names`), `memory-check` only the
    # items a memory names; a document needs the plan.
    light = args.command in ("claim", "release", "memory-check") or (args.command == "new" and args.type not in DOCUMENT_KINDS)
    project = Project(root, load=not light)

    if args.command == "check":
        started = time.time()
        if args.base:
            changed_criteria(project, args.base)
            changed_blocks(project, args.base)
            id_collisions(project, args.base)
        problems = check(project)
        for p in problems:
            print(p)
        errors = sum(1 for p in problems if p.level == "error")
        print(f"{errors} error{'s' if errors != 1 else ''}, {len(problems) - errors} warning{'s' if len(problems) - errors != 1 else ''}")
        pace_log(project, "check", time.time() - started, errors=errors)
        return 1 if errors else 0
    if args.command == "status":
        print(status(project, args.level, args.id, args.all))
        return 0
    if args.command == "coverage":
        print(coverage_block(project, os.path.join(project.spry, "COVERAGE.md")))
        return 0
    if args.command == "backlog":
        print(backlog_block(project, os.path.join(project.spry, "BACKLOG.md")))
        return 0
    if args.command == "done":
        print(done_block(project, os.path.join(project.spry, "DONE.md")))
        return 0
    if args.command == "pace":
        try:
            return pace(project, args.slice, args.since, args.last, args.compare)
        except PlanError as e:
            print(str(e), file=sys.stderr)
            return 2
    if args.command == "memory-check":
        report = memory_check(project, args.dir, args.offline)
        print(json.dumps(report, indent=2, ensure_ascii=False) if args.json else memory_text(report))
        return 0
    if args.command == "work":
        report = work(project, args.owner, args.since, args.until or date.today().isoformat())
        print(json.dumps(report, indent=2, ensure_ascii=False) if args.json else work_text(report))
        return 0
    if args.command == "owners":
        try:
            prs = json.loads(sys.stdin.read() if args.from_prs == "-" else read(args.from_prs))
        except (OSError, ValueError) as e:
            print(f"cannot read {args.from_prs}: {e}", file=sys.stderr)
            return 2
        said = fill_owners(project, prs, args.replace, args.dry_run)
        heads = (("filled", "would fill" if args.dry_run else "filled"),
                 ("replaced", "would replace" if args.dry_run else "replaced"),
                 ("differs", "kept — the PR's author differs; --replace changes it"),
                 ("unknown", "left — the PR's author is not in team.members"),
                 ("no_pr", "left — no pull request to read"))
        for key, head in heads:
            if said[key]:
                print(f"{head}:\n" + "\n".join("  " + line for line in said[key]))
        if not any(said.values()):
            print("every open and closed slice has its owner")
        return 0
    if args.command == "view":
        written = view(project, args.since)
        if written:
            print(("spry: refreshed " if args.since else "wrote: ") + ", ".join(written))
        return 0
    if args.command == "serve":
        serve(project.root, args.port, not args.no_open)
        return 0
    if args.command == "hooks":
        print("\n".join(hooks(project, args.remove)) or "no spry hooks here")
        return 0
    if args.command == "index" and args.restore:
        for path in restore_blocks(project, args.restore):
            print("restored: " + path)
        return 0
    if args.command == "index":
        changed = index(project, dry=args.check)
        for p in project.problems:
            if p.level == "warning":
                print(p)
        for path in changed:
            print(("stale: " if args.check else "updated: ") + path)
        if args.check and changed:
            return 1
        if not changed:
            print("up to date")
        return 0
    if args.command == "related":
        print(related(project, args.file), end="")
        return 0
    if args.command == "link":
        fields = {k: getattr(args, k) for k in ("branch", "pr", "issue") if getattr(args, k) is not None}
        if args.owner is not None:
            fields["owner"] = resolve_owner(project, args.owner)
        print(project.rel(link_slice(project, args.slice, fields)))
        return 0
    if args.command == "next":
        print(next_id(project, args.type))
        return 0
    if args.command == "new":
        if args.batch:
            if args.type or args.title or args.parent or args.owner:
                print("--batch carries the type, title, parent and owner of each item — give nothing else", file=sys.stderr)
                return 2
            try:
                raw = json.loads(sys.stdin.read() if args.batch == "-" else read(args.batch))
            except (OSError, ValueError) as e:
                print(f"cannot read {args.batch}: {e}", file=sys.stderr)
                return 2
            paths = mint_batch(project, batch_entries(raw))
        elif not args.type or not args.title:
            print("new needs a type and --title, or --batch", file=sys.stderr)
            return 2
        elif args.type in DOCUMENT_KINDS:
            if len(args.title) > 1:
                print(f"a {args.type} is made one at a time — one --title", file=sys.stderr)
                return 2
            paths = [mint(project, args.type, args.parent, args.title[0], args.owner, dependency=args.dependency)]
        else:
            paths = mint_batch(project, [{"type": args.type, "title": t, "parent": args.parent, "owner": args.owner,
                                          "key": None} for t in args.title])
        print("\n".join(project.rel(p) for p in paths))
        return 0
    if args.command == "claim":
        # Only `mint: main` writes the claim; with `local`, slice-open's `link --owner` sets it.
        owner = None if mint_mode(project) != "main" else \
            resolve_owner(project, args.owner) if args.owner else whoami(project)
        branch = claim(project, args.slice, owner, switch=not args.no_switch)
        print(f"{args.slice} claimed" + (f" on {main_branch(project)}" if mint_mode(project) == "main" else "")
              + f"; branch `{branch}`" + ("" if args.no_switch else ", checked out"))
        return 0
    if args.command == "release":
        was = release(project, args.slice)
        print(f"{args.slice} released from `{was}` — planned again" + (
            f" on {main_branch(project)}; the branch is left for its owner to delete" if mint_mode(project) == "main"
            else "; commit it"))
        return 0
    if args.command == "find":
        hits = find(project, " ".join(args.query), args.limit, args.rebuild)
        for path, line, heading, snippet in hits:
            print(f"{path}:{line} · {heading}\n    {snippet}")
        if not hits:
            print("nothing found")
        return 0
    if args.command == "codeowners":
        text = codeowners(project)
        for p in project.problems:
            print(p)
        path = os.path.join(project.root, ".github", "CODEOWNERS")
        current = read(path) if os.path.isfile(native(path)) else None
        if args.check:
            print("up to date" if current == text else "stale: .github/CODEOWNERS")
            return 0 if current == text else 1
        if current != text:
            os.makedirs(native(os.path.dirname(path)), exist_ok=True)
            write(path, text)
            print("wrote: .github/CODEOWNERS")
        else:
            print("up to date")
        return 0
    if args.command == "tests":
        print(slowest(project, args.junit, args.limit))
        return 0
    if args.command == "merge-check":
        started = time.time()
        lines = merge_check(project, args.slice, args.base)
        mark = {"ok": "✓", "warn": "!", "block": "✗"}
        for level, text in lines:
            print(f"{mark[level]} {text}")
        blocks = sum(1 for s, _ in lines if s == "block")
        pace_log(project, "merge-check", time.time() - started, slice=args.slice, blocks=blocks)
        if not blocks:
            pace_on_merge_check(project, args.slice)
        print("ready to merge" if not blocks else f"{blocks} thing{'s block' if blocks != 1 else ' blocks'} the merge")
        return 1 if blocks else 0
    if args.command == "gate":
        return gate(project, args.force, fast=args.fast, full=args.full)
    if args.command == "changed":
        print(f"code={'true' if code_changed_since(project, args.base) else 'false'}")
        return 0
    if args.command == "merge-message":
        print(merge_message(project, args.slice, args.ci_local), end="")
        return 0
    if args.command == "falsify":
        try:
            if args.action == "suggest":
                base = args.base or project.config.get("main_branch", "main")
                plan = falsify_suggest(project, args.slice, base)
                out = args.out or os.path.join(project.root, ".spry", "falsify", f"{args.slice}.json")
                os.makedirs(native(os.path.dirname(out)), exist_ok=True)
                write(out, json.dumps(plan, indent=2, ensure_ascii=False) + "\n")
                if not plan and not added_or_none(project, base):
                    print("the branch adds no source lines — nothing to falsify; merge-check accepts an empty table")
                    return 0
                print(f"{len(plan)} candidate control{'s' if len(plan) != 1 else ''} → {project.rel(out)}")
                if plan and not plan[0]["expect"]:
                    print("fill in `expect` — the slice covers no story criteria and is not under a bug or a task; "
                          "name a test file if one guards it")
                print("prune it to the safeguards that matter, then: falsify run " + project.rel(out))
                return 0
            started = time.time()
            results = falsify_run(project, args.plan, dry=args.dry_run, jobs=args.jobs)
            if not args.dry_run:
                pace_log(project, "falsify", time.time() - started, controls=len(results),
                         **{r: sum(1 for _, x, _ in results if x == r) for r in ("caught", "survived", "unreliable")})
        except PlanError as e:
            print("plan refused: " + str(e), file=sys.stderr)
            return 1
        except KeyboardInterrupt:
            print("interrupted — every file was restored", file=sys.stderr)
            return 130
        if results:
            rows = falsify_rows(results)
            print("\n| Control | Mutation | Expect | Result |\n|---|---|---|---|\n" + "\n".join(rows))
            if args.record:
                try:
                    doc, kept = record_falsify(Project(project.root), args.record, rows, replace=args.replace)
                    print("recorded in " + project.rel(doc))
                    if kept:
                        print(f"kept {kept} row{'s' if kept != 1 else ''} this run did not touch — "
                              "a control whose line has changed since keeps its old row: `--replace` with the whole plan drops it")
                except PlanError as e:
                    print(str(e), file=sys.stderr)
                    return 1
            survivors = sum(1 for _, r, _ in results if r == "survived")
            if survivors:
                print(f"{survivors} survived — each needs a new test or a written reason before the slice closes")
        return 0
    if args.command == "scrub":
        hits = scrub(project, args.file)
        for n, word in hits:
            print(f"{args.file}:{n}: {word}")
        print(f"{len(hits)} private word{'s' if len(hits) != 1 else ''}")
        return 1 if hits else 0
    if args.command == "issue-body":
        print(issue_body(project, args.slice, args.close), end="")
        return 0
    if args.command == "pr-body":
        print(pr_body(project, args.slice, args.base), end="")
        return 0
    return 2


if __name__ == "__main__":
    sys.exit(main())
