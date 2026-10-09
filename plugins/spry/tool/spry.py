#!/usr/bin/env python3
"""spry — the project tool. Standard library only, Python 3.10+.

    python3 spry/tool/spry.py check              # is the tree consistent? exit 1 if not
    python3 spry/tool/spry.py status [--level story]
    python3 spry/tool/spry.py index [--check]    # regenerate marker blocks and INDEX.md files (CI on main)
    python3 spry/tool/spry.py index --restore origin/main   # on a branch: undo generated blocks it changed
    python3 spry/tool/spry.py coverage           # defined vs done, and what is built but not proven
    python3 spry/tool/spry.py backlog            # in progress, ready to build, needs slicing, blocked, needs planning
    python3 spry/tool/spry.py view [--since <commit>]   # both pages for this working tree → .spry/view/
    python3 spry/tool/spry.py hooks [--remove]   # refresh .spry/view/ after each checkout and pull
    python3 spry/tool/spry.py related <file>     # candidates for a conflict check
    python3 spry/tool/spry.py next <type>        # next free ID: milestone, story, slice, decision …
    python3 spry/tool/spry.py new <type> --parent <ID> --title "…" [--owner …]
    python3 spry/tool/spry.py pr-body <slice ID> [--base origin/main]   # for the PR: reviewer page + work order
    python3 <plugin>/tool/spry.py vendor --root <project>   # copy process/ and the tool into a project
    python3 <plugin>/tool/spry.py vendor --diff --root <project>   # what differs from the plugin
    python3 spry/tool/spry.py scrub <file>       # private words left in text about to leave the project
    python3 spry/tool/spry.py falsify suggest <slice> [--base main]   # draft a plan from the diff
    python3 spry/tool/spry.py falsify run <plan.json> [--dry-run] [--record <slice>] [--jobs N]
    python3 spry/tool/spry.py find "<words>"     # search spry/ and AGENTS.md, best sections first
    python3 spry/tool/spry.py check --base origin/main   # also warn on cited criteria whose text changed
    python3 spry/tool/spry.py codeowners [--check]       # .github/CODEOWNERS from team.review
    python3 spry/tool/spry.py tests --slowest    # from the JUnit report in tests.junit
    python3 spry/tool/spry.py draw --seed        # a fresh seed for an exploratory walk
    python3 spry/tool/spry.py draw <seed> <n> --pick < choices   # the same choice for ever, per (seed, n)
    python3 spry/tool/spry.py merge-check <slice> [--base origin/main]   # ready to merge? exit 1 if not
    python3 spry/tool/spry.py merge-message <slice> [--ci-local REASON]   # the squash commit: subject, summary, trailers
    python3 spry/tool/spry.py gate [--force]     # check, fast checks, affected tests; skipped while no code changed
    python3 spry/tool/spry.py changed --base <ref>   # for CI: code=true when anything but docs changed
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
import hashlib
import json
import math
import os
import re
import shlex
import shutil
import signal
import subprocess
import sys
import tempfile
import threading
import time
from datetime import date
from dataclasses import dataclass, field

VERSION = "0.12.0"

DEFAULT_LEVELS = ["milestone", "epic", "feature", "story"]
DEFAULT_IDS = {"milestone": "M", "epic": "E", "feature": "F", "story": "S",
               "slice": "SL", "task": "T", "bug": "B", "decision": "D"}
DEFAULT_TEST_MATCH = ["**/*.test.*", "**/*.spec.*", "**/*_test.*", "**/test_*.py", "**/tests/**"]
SKIP_DIRS = {".git", "node_modules", ".spry", "dist", "build", "__pycache__", ".venv", "venv",
             ".idea", ".turbo", "coverage", ".next", "target"}
CONTAINERS = {"tasks": "task", "bugs": "bug"}
# A change to these alone never needs a test run: the gate skips, and CI skips its test jobs.
DEFAULT_DOCS = ["spry/**", "**/*.md"]

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
PLACEHOLDER = re.compile(r"<([a-zA-Z][a-zA-Z0-9 ,/|.'_-]*)>")
FENCE = re.compile(r"^\s*(```|~~~)")
HEADING = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")
DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
SCALAR_KEYS = {"id", "title", "summary", "state", "owner", "audience", "branch", "pr"}
# A citation on one of these lines proves nothing: the test is skipped or not written yet.
NOT_RUN = re.compile(r"\b(?:it|test|describe|context)\.(?:skip|todo)\b|\bx(?:it|test|describe)\s*\(|"
                     r"@pytest\.mark\.(?:skip|xfail)\b|@unittest\.skip|\bt\.Skip\(")
# A citation on a comment line proves nothing: only a test's name says what the test checks.
COMMENT_LINE = re.compile(r"^\s*(#|//|/\*|\*|--|;|<!--)")


# ---------------------------------------------------------------- text helpers

def natural_key(name: str):
    return [int(p) if p.isdigit() else p.lower() for p in re.split(r"(\d+)", name)]


def read(path: str) -> str:
    with open(path, encoding="utf-8") as handle:
        return handle.read()


def write(path: str, text: str) -> None:
    with open(path, "w", encoding="utf-8") as handle:
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
    def __init__(self, root: str):
        self.root = os.path.abspath(root)
        self.spry = os.path.join(self.root, "spry")
        self.plan_dir = os.path.join(self.spry, "plan")
        self.problems: list[Problem] = []
        config_path = os.path.join(self.spry, "spry.config.json")
        try:
            self.config = json.loads(read(config_path))
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
        self._load_plan()
        self._load_decisions()
        self.tests = self._scan_tests()
        self.manual = {s.id: self._manual_checks(s) for s in self.of_type("story")}
        self._memo: dict = {}

    # -- paths

    def rel(self, path: str) -> str:
        return os.path.relpath(path, self.root).replace(os.sep, "/")

    def problem(self, path: str, line: int, message: str, level: str = "error"):
        self.problems.append(Problem(self.rel(path), line, message, level))

    def of_type(self, kind: str):
        return [i for i in self.items.values() if i.type == kind]

    # -- loading

    def _load_plan(self):
        if not os.path.isdir(self.plan_dir):
            self.problem(self.spry, 0, "no spry/plan/ folder")
            return
        self._walk(self.plan_dir, None)

    def _walk(self, folder: str, parent: Item | None):
        for name in sorted(os.listdir(folder), key=natural_key):
            path = os.path.join(folder, name)
            if name.startswith(".") or name in ("__pycache__",):
                continue
            if os.path.isdir(path):
                if name in CONTAINERS and parent is not None:
                    for sub in sorted(os.listdir(path), key=natural_key):
                        sub_path = os.path.join(path, sub)
                        if sub.startswith("."):
                            continue
                        if os.path.isdir(sub_path):
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
        text = read(doc)
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
        if not os.path.isfile(readme):
            self.problem(path, 0, f"{m.group(1)}-{m.group(2)} has no README.md")
            return
        if not self._placed_well(kind, parent, container):
            where = f"{parent.type} {parent.id}" if parent else "the top of the plan"
            self.problem(readme, 1, f"a {kind} cannot sit under {where}" + (f"/{container}" if container else ""))
        item = self._make(kind, f"{m.group(1)}-{m.group(2)}", int(m.group(2)), readme, path, parent, container)
        if kind == "story":
            item.acs = self._acceptance_criteria(item)
        self._walk(path, item)

    def _add_slice(self, path: str, parent: Item | None):
        m = self.slice_file.match(os.path.basename(path))
        if parent is None or parent.type not in ("story", "task", "bug"):
            self.problem(path, 1, "a slice must sit in a story, task or bug folder")
        item = self._make("slice", f"{self.ids['slice']}-{m.group(1)}", int(m.group(1)), path, None, parent, None)
        if "covers" in item.fm and not isinstance(item.fm["covers"], list):
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
        if not os.path.isdir(folder):
            return
        prefix = self.ids["decision"]
        for name in sorted(os.listdir(folder), key=natural_key):
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
        One in a comment or in code is listed in `self.unproving`, so `check` can say why."""
        story = re.escape(self.ids["story"])
        ref = re.compile(r"(?<![A-Za-z0-9])(" + story + r"-\d+)/(AC-\d+)(?!\d)")
        globs, found = self._test_globs(), {}
        self.unproving = []
        for dirpath, dirnames, filenames in os.walk(self.root):
            dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS and not d.startswith(".")]
            if os.path.abspath(dirpath) == self.root and "spry" in dirnames:
                dirnames.remove("spry")
            for name in filenames:
                path = os.path.join(dirpath, name)
                rel = self.rel(path)
                if not any(g.match(rel) for g in globs):
                    continue
                try:
                    if os.path.getsize(path) > 2_000_000:
                        continue
                    text = read(path)
                except (UnicodeDecodeError, OSError):
                    continue
                triple = None
                for n, line in enumerate(text.split("\n"), 1):
                    hits = list(ref.finditer(line)) if "/AC-" in line else []
                    if not hits and '""' not in line and "''" not in line:
                        continue  # no citation, and no triple quote to open or close: nothing to track
                    spans, triple_after = string_spans(line, triple)
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
        if not os.path.isfile(path):
            return {}
        text = read(path)
        for _level, title, at, _end in sections(text):
            m = re.match(r"^(AC-\d+)\b", title)
            if m and m.group(1) not in story.acs:
                self.problem(path, at + 1, f"scenario for {m.group(1)}, which {story.id} does not have")
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
    for dirpath, dirnames, filenames in os.walk(top):
        dirnames[:] = [d for d in dirnames if not d.startswith(".")]
        if os.path.abspath(dirpath) != os.path.abspath(top):
            out += [os.path.join(dirpath, f) for f in filenames if f.endswith(".md")]
    return sorted(out)


def markdown_files(project: Project):
    """Every .md under spry/ except the copied process/, tool/ and skills/, and history kept as it
    was (`history_files`), plus AGENTS.md."""
    out = []
    agents = os.path.join(project.root, "AGENTS.md")
    if os.path.isfile(agents):
        out.append(agents)
    for dirpath, dirnames, filenames in os.walk(project.spry):
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
    if not os.path.isfile(path):
        return path, []
    text = read(path)
    out = []
    for _i, cells in table_rows(enumerate(text.split("\n"))):
        if len(cells) >= 3 and cells[0].lower() != "term":
            out += [(b.strip(), cells[0]) for b in cells[2].split(",") if b.strip() and not b.strip().startswith("<")]
    return path, out


def check(project: Project):
    gloss_path, banned = glossary(project)
    banned_res = [(re.compile(r"(?<![\w-])" + re.escape(b) + r"(?![\w-])", re.I), b, t) for b, t in banned]
    budgets = [(glob_regex(g), n, g) for g, n in project.config.get("budgets", {}).items()]
    by_doc = {i.doc: i for i in project.items.values()}

    for path in markdown_files(project):
        text = read(path)
        rel = project.rel(path)
        item = by_doc.get(path)
        fm = item.fm if item else None
        start = item.body_start if item else 0
        if item is None and rel != "AGENTS.md":
            fm, start, errors = parse_front_matter(text)
            for line, message in errors:
                project.problem(path, line, message)
        fm = fm or {}
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
                if not os.path.exists(resolved):
                    project.problem(path, n, f"link to `{target}` does not resolve")
            if check_words and n not in skip:
                for regex, phrase, term in banned_res:
                    if regex.search(line):
                        project.problem(path, n, f"`{phrase}` — the glossary says `{term}`")

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
                project.problem(item.doc, 1, "`covers` lists acceptance criteria, but the parent is not a story")
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

    stories = live("story")
    rows = []
    for kind in project.levels:
        items = live(kind)
        done = sum(map(project.done, items))
        rows.append((PLURAL.get(kind, kind).capitalize(), done, len(items)))
    acs = [(s, a) for s in stories for a in criteria(s)]
    rows.append(("Acceptance criteria proven", sum(1 for s, a in acs if project.proof(s, a)[0]), len(acs)))
    for kind in ("slice", "task", "bug"):
        items = live(kind)
        label = {"slice": "Slices closed", "task": "Tasks", "bug": "Bugs fixed"}[kind]
        rows.append((label, sum(map(project.done, items)), len(items)))
    out = ["### Totals", "", "| | Done | Defined | |", "|---|--:|--:|--:|"]
    out += [f"| {name} | {done} | {total} | {pct(done, total)} |" for name, done, total in rows]

    first = project.levels[0]
    tops = [i for i in project.top if i.type == first and i.state != "dropped"]
    out += ["", f"### By {first}", ""]
    if tops:
        out += [f"| {first.capitalize()} | State | Stories done | Criteria proven | Open bugs |",
                "|---|---|--:|--:|--:|"]
        for m in tops:
            ss = [m] if m.type == "story" else project.descendants(m, "story")
            pairs = [(s, a) for s in ss for a in criteria(s)]
            proven = sum(1 for s, a in pairs if project.proof(s, a)[0])
            out.append(f"| {link(doc, m)} | {m.state} | {sum(map(project.done, ss))} of {len(ss)} | "
                       f"{proven} of {len(pairs)} | {len(project.open_bugs(m))} |")
    else:
        out.append(f"_No {PLURAL.get(first, first)} yet._")

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
                if s.state == "open" or (s.state == "planned" and s.id in branches):
                    where = s.fm.get("branch") if s.state == "open" else branches[s.id]
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
        """Everything the item sits under, from the top: what it is part of, at a glance."""
        return " › ".join(link(doc, a) for a in reversed(item.ancestors())) or "—"

    def section(title, intro, head, rows):
        out = ["", f"### {title}", "", intro, ""]
        if not rows:
            return out + ["_None._"]
        cols = head.count("|") - 1
        return out + [head, "|" + "---|" * cols] + rows

    out = []
    out += section("In progress", "Being built now — open, or on a branch named for the slice. Leave these to their owner.",
                   "| Slice | Part of | Owner | Where | Unblocks |",
                   [f"| {link(doc, s)} | {trail(s)} | {owner(s)} | {branch} | {unblocks(s)} |"
                    for s, branch in items["progress"]])
    out += section("Ready to build", "Planned, and nothing they wait for is unfinished. The first row is next; "
                   "`/spry:slice-open` with no ID offers it. *Unblocks* is what waits on the slice, or on "
                   "something it is part of — between two rows, the one that frees more.",
                   "| # | Slice | Part of | Covers | Owner | Unblocks |",
                   [f"| {n} | {link(doc, s)} | {trail(s)} | {', '.join(s.fm.get('covers') or []) or '—'} | {owner(s)} "
                    f"| {unblocks(s)} |" for n, (s, _) in enumerate(items["ready"], 1)])
    out += section("Needs slicing", "Ready, but no slice is planned for all of it yet — `/spry:slice <ID>` splits it.",
                   "| Item | Part of | Missing | Owner |",
                   [f"| {link(doc, i)} | {trail(i)} | {'slices' if need == 'slices' else 'a slice for ' + need} | {owner(i)} |"
                    for i, need in items["slicing"]])
    out += section("Blocked", "Waiting on unfinished work, named here with where it stands and who owns it.",
                   "| Item | Part of | Waiting on | Owner |",
                   [f"| {link(doc, i)} | {trail(i)} | {'; '.join(status(b) for b in waits)} | {owner(i)} |"
                    for i, waits in items["blocked"]])
    out += section("Needs planning", "Product's next step: finish a draft, or add what an item is still missing.",
                   "| Item | Part of | Needs | Owner |",
                   [f"| {link(doc, i)} | {trail(i)} | {need} | {owner(i)} |" for i, need in items["planning"]])
    return "\n".join(out[1:])


def index_block(project: Project, index_path: str) -> str:
    folder = os.path.dirname(index_path)
    lines = []
    for name in sorted(os.listdir(folder), key=natural_key):
        path = os.path.join(folder, name)
        target = None
        if name.endswith(".md") and name != "INDEX.md":
            target = path
        elif os.path.isdir(path) and os.path.isfile(os.path.join(path, "INDEX.md")):
            target = os.path.join(path, "INDEX.md")
        if not target:
            continue
        fm, _, _ = parse_front_matter(read(target))
        fm = fm or {}
        title = fm.get("title") or name
        if fm.get("id") and not title.startswith(fm["id"]):
            title = f"{fm['id']} {title}"
        summary = fm.get("summary", "")
        if not summary:
            project.problem(target, 1, "no `summary` in front-matter — the index line needs one", "warning")
        rel = os.path.relpath(target, folder).replace(os.sep, "/")
        lines.append(f"- [{title}]({rel})" + (f" — {summary}" if summary else ""))
    return "\n".join(lines) or "_Nothing here yet._"


def index(project: Project, dry: bool):
    """Regenerate every marker block. Returns the files that changed (or would)."""
    changed = []

    def apply(path: str, name: str, content: str, required: bool):
        if not os.path.isfile(path):
            return
        text = read(path)
        new = replace_block(text, name, content)
        if new is None:
            if required:
                project.problem(path, 1, f"no `<!-- spry:{name} -->` block to fill", "warning")
            return
        if new != text:
            changed.append(project.rel(path))
            if not dry:
                write(path, new)

    for item in project.items.values():
        if item.folder:
            apply(item.doc, "children", children_block(project, item), True)
        if item.type == "story":
            apply(item.doc, "proof", proof_block(project, item), True)
    roadmap = os.path.join(project.plan_dir, "README.md")
    apply(roadmap, "children", top_block(project, roadmap, False), True)
    front = os.path.join(project.spry, "README.md")
    apply(front, "children", top_block(project, front, True), False)
    cover = os.path.join(project.spry, "COVERAGE.md")
    apply(cover, "coverage", coverage_block(project, cover), True)
    queue = os.path.join(project.spry, "BACKLOG.md")
    apply(queue, "backlog", backlog_block(project, queue), True)
    for dirpath, dirnames, filenames in os.walk(os.path.join(project.spry, "knowledge")):
        dirnames[:] = [d for d in dirnames if not d.startswith(".")]
        if "INDEX.md" in filenames:
            path = os.path.join(dirpath, "INDEX.md")
            apply(path, "index", index_block(project, path), True)
    return sorted(changed)


# ---------------------------------------------------------------- status

def status(project: Project, level: str | None):
    if level and level not in project.levels:
        raise SystemExit(f"unknown level `{level}` — one of {', '.join(project.levels)}")
    stop = project.levels.index(level) if level else None
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

    for item in project.top:
        show(item, 0)
    return "\n".join(out) or "No plan yet — spry/plan/ is empty."


# ---------------------------------------------------------------- related

def plan_paths(text: str):
    body = section_lines(text, "Plan") or []
    return {p for _, line in body for p in re.findall(r"`([^`\s]+[/.][^`\s]*)`", line.split(" — ")[0])}


def related(project: Project, target_path: str, limit: int = 8):
    target_path = os.path.abspath(target_path)
    if not os.path.isfile(target_path):
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
    section("Always check", [f"- {p}" + ("" if os.path.exists(os.path.join(project.root, p)) else " (missing)") for p in always])

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
            if s is item or s.state != "open":
                continue
            shared = sorted(mine_paths & plan_paths(s.text))
            rows.append(f"- {s.label} — {project.rel(s.doc)}" + (f" · same files: {', '.join(shared)}" if shared else ""))
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
        for _dir, dirnames, filenames in os.walk(project.plan_dir):
            nums += [int(m.group(1)) for n in dirnames + filenames if (m := taken.match(n))]
    return f"{prefix}-{max(nums, default=0) + 1}"


# ---------------------------------------------------------------- new

def slugify(title: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    if len(slug) > 40:
        slug = slug[:40].rsplit("-", 1)[0]
    return slug or "untitled"


def fill_template(template: str, kind: str, ident: str, title: str, owner: str | None, today: str) -> str:
    lines = template.split("\n")
    if lines and lines[0].strip() == "---":
        for i in range(1, len(lines)):
            if lines[i].strip() == "---":
                break
            key = lines[i].split(":", 1)[0]
            value = {"id": ident, "title": title, "state": "planned" if kind == "slice" else "draft",
                     "covers": "[]", "breaks": "[]", "branch": "", "pr": "", "date": today}.get(key)
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
    if not os.path.exists(path):
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
        os.makedirs(folder, exist_ok=True)
        ensure_index(project, folder, "Conventions")
        path = os.path.join(folder, f"{slugify(title)}.md")
        text = template.replace("<area>", title)
    elif kind == "external":
        if not dependency:
            raise SystemExit("an external behaviour needs --dependency: the service it is about")
        folder = os.path.join(knowledge, "external", slugify(dependency))
        os.makedirs(folder, exist_ok=True)
        ensure_index(project, folder, dependency)
        path = os.path.join(folder, f"{slugify(title)}.md")
        text = (template.replace("<dependency>", dependency).replace("<behaviour, as a statement>", title)
                .replace("<behaviour>", title).replace("observed: <YYYY-MM-DD>", f"observed: {today}")
                .replace("dependency: <name>", f"dependency: {dependency}").replace("affects: [<item IDs>]", "affects: []"))
    else:
        folder = os.path.join(knowledge, "audits")
        os.makedirs(folder, exist_ok=True)
        ensure_index(project, folder, "Audits")
        path = os.path.join(folder, f"{today}-{slugify(title)}.md")
        text = re.sub(r"(?m)^title: .*$", f"title: {title}", template, count=1)
        text = text.replace("date: <YYYY-MM-DD>", f"date: {today}").replace("# <title>", f"# {title}")
    if os.path.exists(path):
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
    if not os.path.isfile(template):
        raise SystemExit(f"no template {project.rel(template)} — bring the process in with `vendor`")
    ident, slug = next_id(project, kind), slugify(title)
    parent = None
    if parent_id:
        parent = project.items.get(parent_id)
        if parent is None:
            raise SystemExit(f"no item {parent_id} in the plan")
    if kind == "decision":
        folder = os.path.join(project.spry, "knowledge", "decisions")
        os.makedirs(folder, exist_ok=True)
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
        os.makedirs(folder)
        path = os.path.join(folder, "README.md")
    if os.path.exists(path):
        raise SystemExit(f"{project.rel(path)} already exists")
    write(path, fill_template(read(template), kind, ident, title, owner, today or date.today().isoformat()))
    return path


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
    review = reviewer_page(project, item, base)
    return f"**{item.label}**{parent} — `{project.rel(item.doc)}`\n\n{review}{body}\n"


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
    if not os.path.isdir(source) or os.path.abspath(os.path.dirname(here)) == target:
        raise SystemExit("run `vendor` with the plugin's spry.py, not a project's copy")
    process_target = os.path.join(target, "process")
    if os.path.exists(process_target) and not force:
        raise SystemExit("spry/process/ already exists — it may hold local process changes; "
                         "use /spry:update to merge, or --force to overwrite")
    if os.path.exists(process_target):
        shutil.rmtree(process_target)
    shutil.copytree(source, process_target, ignore=shutil.ignore_patterns("__pycache__", ".DS_Store"))
    os.makedirs(os.path.join(target, "tool"), exist_ok=True)
    shutil.copy2(os.path.abspath(__file__), os.path.join(target, "tool", "spry.py"))
    return ["spry/process/", "spry/tool/spry.py"]


def vendor_diff(root: str) -> list:
    """['changed: process/chat.md', 'new in spry: …', 'only in project: …'] — plugin vs project."""
    here = os.path.dirname(os.path.abspath(__file__))
    plugin = os.path.dirname(here)
    target = os.path.join(os.path.abspath(root), "spry")
    if not os.path.isdir(os.path.join(plugin, "process")) or os.path.abspath(plugin) == target:
        raise SystemExit("run `vendor --diff` with the plugin's spry.py, not a project's copy")

    def files(base):
        out = set()
        for dirpath, dirnames, filenames in os.walk(os.path.join(base, "process")):
            dirnames[:] = [d for d in dirnames if d != "__pycache__" and not d.startswith(".")]
            out |= {os.path.relpath(os.path.join(dirpath, f), base).replace(os.sep, "/")
                    for f in filenames if not f.startswith(".")}
        if os.path.isfile(os.path.join(base, "tool", "spry.py")):
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
    if os.path.isfile(gloss_path):
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


def git(root: str, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", root, *args], capture_output=True, text=True)


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
    return table


def runner_cwd(project: Project, runner: dict, rel: str) -> str:
    """The folder a runner runs in for this test file: the project root, or its nearest package."""
    if runner.get("cwd") != "package":
        return project.root
    folder = os.path.dirname(os.path.join(project.root, rel))
    while os.path.abspath(folder).startswith(project.root):
        if any(os.path.isfile(os.path.join(folder, m)) for m in PACKAGE_MARKERS):
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
        if not os.path.isfile(target):
            raise PlanError(f"{where}: no file {entry['file']}")
        if not git_clean(project.root, entry["file"]):
            raise PlanError(f"{where}: {entry['file']} has uncommitted changes — commit first; restoring would lose them")
        with open(target, "rb") as handle:
            data = handle.read()
        count = data.decode("utf-8").count(in_line_endings(data, entry["find"]))
        if count != 1:
            raise PlanError(f"{where}: `find` occurs {count} times in {entry['file']} — it must occur exactly once")
        if not isinstance(entry["expect"], list):
            raise PlanError(f"{where}: `expect` must be a list such as [\"S-1/AC-2\"]")
        cited = sorted({path for ref in entry["expect"] for path, _, _ in project.tests.get(ref, [])})
        if not cited:
            raise PlanError(f"{where}: no test cites {', '.join(entry['expect'])} — nothing could notice")
        chosen = entry.get("files") or cited
        stray = sorted(set(chosen) - set(cited))
        if stray:
            raise PlanError(f"{where}: {', '.join(stray)} cites none of {', '.join(entry['expect'])}")
        entry["_tests"] = chosen
    return plan


def run_tests(project: Project, runner: dict, cwd: str, files: list, timeout: int, root: str | None = None):
    """('pass' | 'fail' | 'timeout', last lines of output). `root` is the tree the files live in."""
    base = root or project.root
    rels = [os.path.relpath(os.path.join(base, f), cwd) for f in files]
    command = runner["command"].replace("{files}", " ".join(shlex.quote(r) for r in rels))
    # Its own process group, so a timeout or Ctrl-C stops the runner's children too (pnpm → vitest
    # workers) — none may keep running against a mutated file.
    proc = subprocess.Popen(command, shell=True, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            text=True, start_new_session=True)
    try:
        output, _ = proc.communicate(timeout=timeout)
    except BaseException as e:
        stop_group(proc)
        if isinstance(e, subprocess.TimeoutExpired):
            return "timeout", ""
        raise
    tail = "\n".join((output or "").strip().split("\n")[-5:])
    return ("pass" if proc.returncode == 0 else "fail"), tail


def stop_group(proc: subprocess.Popen):
    try:
        if hasattr(os, "killpg"):
            os.killpg(proc.pid, signal.SIGKILL)
        else:
            proc.kill()
    except (ProcessLookupError, PermissionError):
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
        with open(path, "wb") as handle:
            handle.write(data)
        with self.lock:
            self.clock = max(self.clock + 1, int(time.time()))
            stamp = self.clock
        os.utime(path, (stamp, stamp))


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


def run_control(project: Project, entry: dict, table: list, timeout: int, red: dict, root: str) -> tuple:
    """Run the tests one mutated control should fail, in the tree at `root`. Returns (result, note)."""
    outcomes, notes = [], []
    for tier in likely_first(project, entry):
        for key, files in group_files(project, tier).items():
            if key in red:
                outcomes.append("unreliable")
                notes.append(red[key])
                continue
            outcome, _tail = run_tests(project, table[key[0]], in_tree(project, root, key[1]), files, timeout, root)
            outcomes.append({"fail": "caught", "pass": "survived"}.get(outcome, "unreliable"))
            if outcome == "timeout":
                notes.append("timed out")
            if outcome == "fail":
                break
        if "caught" in outcomes:
            break
    if "caught" in outcomes:
        return "caught", "; ".join(notes)
    if "survived" in outcomes and "unreliable" not in outcomes:
        return "survived", "; ".join(notes)
    return "unreliable", "; ".join(notes)


def baseline(project: Project, groups: dict, table: list, timeout: int, root: str, say) -> dict:
    """{group key: why it is red} for every group whose tests fail before anything is changed."""
    red = {}
    for key, files in groups.items():
        outcome, tail = run_tests(project, table[key[0]], in_tree(project, root, key[1]), files, timeout, root)
        if outcome != "pass":
            red[key] = f"baseline {outcome}" + (f": {tail.splitlines()[-1]}" if tail else "")
        say(f"baseline {'green' if outcome == 'pass' else outcome} · {len(files)} test files")
    return red


DEFAULT_SHARE = ("node_modules", ".venv", "venv")


def shared_paths(project: Project) -> list:
    """Untracked folders each worktree borrows from the main tree: installed dependencies."""
    names = set(DEFAULT_SHARE)
    found = list(project.config.get("falsify", {}).get("share", []))
    for dirpath, dirnames, _files in os.walk(project.root):
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
    else:
        os.symlink(source, link)


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


def falsify_serial(project: Project, plan: list, table: list, timeout: int, groups: dict, say) -> list:
    """One control at a time, in this tree; every file restored, whatever happens."""
    red = baseline(project, groups, table, timeout, project.root, say)
    writer, results, touched = Writer(), [], {}

    def restore():
        for path, data in touched.items():
            writer.put(path, data)
        touched.clear()

    try:
        for entry in plan:
            target = os.path.join(project.root, entry["file"])
            with open(target, "rb") as handle:
                original = handle.read()
            touched[target] = original
            writer.put(target, mutate(entry, original))
            try:
                result, note = run_control(project, entry, table, timeout, red, project.root)
            finally:
                restore()
            results.append((entry, result, note))
            say(f"{result}: {entry['control']}")
    finally:
        restore()
    return results


def falsify_parallel(project: Project, plan: list, table: list, timeout: int, groups: dict, jobs: int, say) -> list:
    """Controls spread over `jobs` git worktrees of HEAD. This tree is never written to.

    The baseline runs inside a worktree, not here: a worktree missing something the tests need
    (a dependency not shared, a generated file) must show as a red baseline — `unreliable` —
    never as every control `caught`."""
    from concurrent.futures import ThreadPoolExecutor
    import queue

    parent = tempfile.mkdtemp(prefix="spry-falsify-")
    trees, made, writer, lock = [], [], Writer(), threading.Lock()
    share = shared_paths(project)
    prefix = git_prefix(project.root)
    pnpm = os.path.isdir(os.path.join(project.root, "node_modules", ".pnpm"))
    try:
        for n in range(jobs):
            tree = os.path.join(parent, f"w{n + 1}")
            done = git(project.root, "worktree", "add", "--detach", "-q", tree, "HEAD")
            if done.returncode != 0:
                raise PlanError(f"git worktree add failed: {done.stderr.strip()}")
            made.append(tree)
            tree = os.path.join(tree, prefix)
            trees.append(tree)
            for rel in share:
                link = os.path.join(tree, rel)
                if not os.path.exists(link):
                    os.makedirs(os.path.dirname(link), exist_ok=True)
                    borrow(os.path.join(project.root, rel), link, rel, pnpm)
        say(f"{jobs} worktrees · sharing {', '.join(share) or 'nothing'}")
        red = baseline(project, groups, table, timeout, trees[0], say)

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
                with open(target, "rb") as handle:
                    original = handle.read()
                writer.put(target, mutate(entry, original))
                try:
                    return run_control(project, entry, table, timeout, red, tree)
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
        for tree in made:
            git(project.root, "worktree", "remove", "--force", tree)
        git(project.root, "worktree", "prune")
        shutil.rmtree(parent, ignore_errors=True)


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


def record_falsify(project: Project, slice_id: str, rows: list) -> str:
    """Write rows into the slice's Falsify table, replacing what was there."""
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
    lines[head + 2:end] = rows
    write(item.doc, "\n".join(lines))
    return item.doc


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


def falsify_suggest(project: Project, slice_id: str, base: str) -> list:
    """A draft plan from the source lines this branch added, for a person to prune."""
    item = project.items.get(slice_id)
    if item is None or item.type != "slice":
        raise PlanError(f"no slice {slice_id}")
    story = item.parent.id if item.parent and item.parent.type == "story" else None
    expect = [f"{story}/{ac}" for ac in item.fm.get("covers") or []] if story else []
    diff = git(project.root, "diff", "--relative", "-U0", f"{base}...HEAD", "--", ".", ":(exclude)spry")
    if diff.returncode != 0:
        raise PlanError(f"git diff against {base} failed: {diff.stderr.strip()}")
    tests = project._test_globs()
    plan, current = [], None
    for line in diff.stdout.split("\n"):
        if line.startswith("+++ "):
            path = line[6:] if line.startswith("+++ b/") else None
            current = path if path and not any(g.match(path) for g in tests) else None
            continue
        if not current or not line.startswith("+") or line.startswith("+++"):
            continue
        source = line[1:]
        if not CONTROL_LINE.search(source):
            continue
        try:
            text = read(os.path.join(project.root, current))
        except (OSError, UnicodeDecodeError):
            continue
        if text.count(source) != 1:
            continue
        for with_, label in mutations_for(source)[:1]:
            plan.append({"control": " ".join(source.split())[:70], "file": current, "find": source,
                         "with": with_, "mutation": label, "expect": list(expect)})
    return plan


# ---------------------------------------------------------------- find

def searchable_files(project: Project) -> list:
    out = markdown_files(project) + history_files(project)
    process = os.path.join(project.spry, "process")
    if os.path.isdir(process):
        for dirpath, _dirs, filenames in os.walk(process):
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


def find(project: Project, query: str, limit: int = 10, rebuild: bool = False) -> list:
    """[(rel path, line, heading, snippet)] best first. SQLite FTS5 when the stdlib has it."""
    import sqlite3
    terms = search_terms(query)
    if not terms:
        return []
    files = searchable_files(project)
    db_path = os.path.join(project.root, ".spry", "index.db")
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    if rebuild and os.path.exists(db_path):
        os.remove(db_path)
    con = sqlite3.connect(db_path)
    columns = [r[1] for r in con.execute("PRAGMA table_info(sections)")]
    if columns and "title" not in columns:
        con.close()
        os.remove(db_path)
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
        st = os.stat(path)
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
        rows = con.execute("SELECT path, line, title || ' › ' || heading, snippet(sections, 4, '[', ']', '…', 12) "
                           "FROM sections WHERE sections MATCH ? ORDER BY bm25(sections, 0, 0, 1.5, 2.0, 1.0) LIMIT ?",
                           (match, limit * 3)).fetchall()
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
    if not os.path.isdir(skills):
        raise SystemExit("run `install` with the plugin's spry.py, not a project's copy")
    if agent not in AGENTS:
        raise SystemExit(f"unknown agent `{agent}` — one of {', '.join(AGENTS)}")
    root = os.path.abspath(root)
    written, listing = [], []
    for name in sorted(os.listdir(skills), key=natural_key):
        source = os.path.join(skills, name, "SKILL.md")
        if not os.path.isfile(source):
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
        os.makedirs(os.path.dirname(path), exist_ok=True)
        write(path, content)
        written.append(os.path.relpath(path, root).replace(os.sep, "/"))
    if agent == "generic":
        agents_md = os.path.join(root, "AGENTS.md")
        block = ("When the person types `/spry:<name>`, or asks for what a skill below does, read its file "
                 "and follow it. `$ARGUMENTS` in a skill means what they wrote after the command.\n\n"
                 + "\n".join(listing))
        text = read(agents_md) if os.path.isfile(agents_md) else "# AGENTS.md\n"
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
    paths = sorted(globber.glob(os.path.join(base, "**", "*.xml"), recursive=True)) if os.path.isdir(base) \
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


def criteria_edits(project: Project, base: str) -> list:
    """[(story, AC, text at base, text now or None)] for criteria that existed at `base` and changed."""
    out = []
    for story in project.of_type("story"):
        before = git(project.root, "show", f"{base}:./{project.rel(story.doc)}")
        if before.returncode != 0:
            continue
        old, new = ac_texts(before.stdout, struck=True), ac_texts(story.text, struck=True)
        out += [(story, ac, text, new.get(ac)) for ac, text in sorted(old.items()) if new.get(ac) != text]
    return out


def code_changed(project: Project, base: str) -> list:
    """Files outside spry/ that this branch changed since `base` — code, tests and configuration."""
    done = git(project.root, "diff", "--relative", "--name-only", f"{base}...HEAD", "--", ".", ":(exclude)spry")
    return [line for line in done.stdout.split("\n") if line.strip()] if done.returncode == 0 else []


def changed_criteria(project: Project, base: str):
    """Warn for each acceptance criterion whose text changed since `base` while a test cites it."""
    if git(project.root, "rev-parse", "--verify", "--quiet", f"{base}^{{commit}}").returncode != 0:
        project.problem(project.spry, 0, f"--base {base} is not a commit here — fetch it (a shallow CI "
                                         f"clone needs `fetch-depth: 0`), or nothing was compared")
        return
    for story in project.of_type("story"):
        rel = project.rel(story.doc)
        before = git(project.root, "show", f"{base}:./{rel}")
        if before.returncode != 0:
            continue
        old, new = ac_texts(before.stdout), ac_texts(story.text)
        for ac, text in new.items():
            ref = f"{story.id}/{ac}"
            if ac in old and old[ac] != text and project.tests.get(ref):
                tests = ", ".join(sorted({p for p, _, _ in project.tests[ref]}))
                project.problem(story.doc, story.acs[ac]["line"],
                                f"{ref} changed since {base}, and {tests} cite it — check they still prove it",
                                "warning")


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
        if not os.path.isfile(path) or rel.startswith(("spry/process/", "spry/history/")):
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
        project.problem(path, line, f"`spry:{name}` block differs from {base} — only CI on the main branch "
                                    f"writes it; `spry index --restore {base}` puts it back, "
                                    f"`spry view` shows a fresh copy")


def restore_blocks(project: Project, base: str) -> list:
    """Put back the base's content in every generated block this branch changed. Returns the files."""
    changed = {}
    for path, name, _, content in block_drift(project, base):
        changed[path] = replace_block(changed.get(path) or read(path), name, content)
    for path, text in changed.items():
        write(path, text)
    return sorted(project.rel(p) for p in changed)


# ---------------------------------------------------------------- view / hooks

VIEWS = (("BACKLOG.md", "backlog", backlog_block), ("COVERAGE.md", "coverage", coverage_block))
HOOK_MARK = "# spry: refresh .spry/view/"


def view(project: Project, since: str | None = None) -> list:
    """Write the backlog and coverage pages for this working tree to `.spry/view/`, never committed.

    With `since` (a git hook passes the commit it came from), only when the plan or a test file
    changed since then, or no view exists yet. Returns the files written."""
    folder = os.path.join(project.root, ".spry", "view")
    if since and all(os.path.isfile(os.path.join(folder, name)) for name, _, _ in VIEWS):
        diff = git(project.root, "diff", "--relative", "--name-only", since, "HEAD", "--", ".")
        globs = project._test_globs()
        paths = [p for p in diff.stdout.split("\n") if p]
        if diff.returncode == 0 and not any(p.startswith("spry/") or any(g.match(p) for g in globs) for p in paths):
            return []
    os.makedirs(folder, exist_ok=True)
    stamp = f"> Local view of this working tree, written {time.strftime('%Y-%m-%d %H:%M')} by `spry view`. Not committed."
    written = []
    for name, block, make in VIEWS:
        target = os.path.join(folder, name)
        content = make(project, target)
        source = os.path.join(project.spry, name)
        frame = read(source) if os.path.isfile(source) else f"# {name[:-3].title()}\n\n<!-- spry:{block} -->\n<!-- /spry:{block} -->\n"
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
        ours = os.path.isfile(path) and HOOK_MARK in read(path)
        if remove:
            if ours:
                os.remove(path)
                out.append(f"removed: {name}")
            continue
        if os.path.isfile(path) and not ours:
            out.append(f"kept: {name} is not spry's — add to it: python3 {tool} view --since <previous commit>")
            continue
        os.makedirs(folder, exist_ok=True)
        write(path, f"#!/bin/sh\n{HOOK_MARK} when the plan or a test changed. "
                    f"Remove: python3 {tool} hooks --remove\n{head}{run}")
        os.chmod(path, 0o755)
        out.append(f"wrote: {name}")
    return out


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
    out.append(("ok", f"PR #{item.fm['pr']}") if str(item.fm.get("pr", "")).isdigit()
               else ("block", "no `pr:` number in the slice"))
    rows = falsify_table(item)
    if not rows:
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
    errors = [p for p in check(project) if p.level == "error"]
    out.append(("ok", "spry check clean") if not errors
               else ("block", f"spry check: {len(errors)} error{'s' if len(errors) != 1 else ''} — first: {errors[0]}"))
    for p in project.problems:
        if p.level == "warning" and "changed since" in p.message:
            out.append(("warn", p.message))
    return out


def required_controls(project: Project, item: Item, rows: list, base: str) -> list:
    """Every control `falsify suggest` finds in the diff must have a row: the agent adds, never drops."""
    try:
        wanted = falsify_suggest(project, item.id, base)
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
            with open(full, "rb") as handle:
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


def gate_steps(project: Project) -> list:
    """[(name, command)] — fast checks cheapest first, then the affected tests."""
    steps = []
    for n, entry in enumerate(project.config.get("checks", {}).get("fast") or [], 1):
        name, command = (entry.get("name"), entry.get("run")) if isinstance(entry, dict) else (None, entry)
        command = str(command or "")
        steps.append((name or (command.split()[0] if command.split() else f"check {n}"), command))
    steps.append(("affected tests", str(project.config.get("tests", {}).get("affected") or "")))
    for name, command in steps:
        if not command.strip() or re.search(r"<[a-z][a-z ,/-]*>", command):
            raise SystemExit(f"spry.config.json: `{name}` has no command yet — set "
                             f"{'tests.affected' if name == 'affected tests' else 'checks.fast'}")
    return steps


DEFAULT_RETRY_WHEN = r"timed? ?out|timeout|ETIMEDOUT"


def gate(project: Project, force: bool = False, say=print) -> int:
    """`spry check`, then the fast checks, then the affected tests — stopping at the first failure.
    A pass is stamped with the code's fingerprint; while the code is unchanged, only `check` runs again."""
    started = time.time()
    errors = [p for p in check(project) if p.level == "error"]
    say(f"{'✗' if errors else '✓'} spry check · {time.time() - started:.1f}s")
    if errors:
        for p in errors[:10]:
            say(f"  {p}")
        return 1
    steps = gate_steps(project)
    stamp_path = os.path.join(project.root, ".spry", "green")
    fingerprint = code_fingerprint(project)
    try:
        stamp = json.loads(read(stamp_path))
    except (OSError, ValueError):
        stamp = {}
    if fingerprint and stamp.get("code") == fingerprint and not force:
        say(f"– {', '.join(n for n, _ in steps)} skipped: no code changed since they passed at {stamp.get('at', '?')}")
        return 0
    tests = project.config.get("tests", {})
    retry = str(tests.get("retry") or "").strip()
    retry_when = re.compile(tests.get("retry_when") or DEFAULT_RETRY_WHEN, re.I)
    for name, command in steps:
        started = time.time()
        done = subprocess.run(command, shell=True, cwd=project.root, capture_output=True, text=True)
        say(f"{'✓' if done.returncode == 0 else '✗'} {name} · {time.time() - started:.1f}s")
        if done.returncode != 0 and name == "affected tests" and retry and retry_when.search(done.stdout + done.stderr):
            # A test that times out under load and passes on a quiet machine is load, not code.
            # A real failure fails both runs, so the retry never turns red into green.
            say(f"  timed out under load — once more, quietly: {retry}")
            started = time.time()
            done = subprocess.run(retry, shell=True, cwd=project.root, capture_output=True, text=True)
            say(f"{'✓' if done.returncode == 0 else '✗'} {name}, quiet retry · {time.time() - started:.1f}s")
        if done.returncode != 0:
            tail = (done.stdout + done.stderr).rstrip().split("\n")[-40:]
            say("\n".join("  " + line for line in tail))
            return 1
    if fingerprint:
        os.makedirs(os.path.dirname(stamp_path), exist_ok=True)
        write(stamp_path, json.dumps({"code": fingerprint, "at": time.strftime("%Y-%m-%d %H:%M")}) + "\n")
        say("green — stamped; until the code changes, the gate runs only `spry check`")
    return 0


def code_changed_since(project: Project, base: str) -> bool:
    """Did anything outside `checks.docs` change between `base` and the working tree? True when unsure."""
    if git(project.root, "rev-parse", "--verify", "--quiet", f"{base}^{{commit}}").returncode != 0:
        return True
    done = git(project.root, "diff", "--relative", "--name-only", base, "--", ".")
    if done.returncode != 0:
        return True
    docs = [glob_regex(g) for g in project.config.get("checks", {}).get("docs") or DEFAULT_DOCS]
    return any(not any(g.match(path) for g in docs) for path in done.stdout.split("\n") if path)


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

def find_root(start: str):
    here = os.path.abspath(start)
    while True:
        if os.path.isfile(os.path.join(here, "spry", "spry.config.json")):
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
    p.add_argument("--level", help="stop at this level, e.g. feature")
    p = sub.add_parser("coverage", help="defined vs done for the whole plan, and what is built but not proven")
    p = sub.add_parser("backlog", help="what is being built, what to build next, and what stands in the way")
    p = sub.add_parser("view", help="write the backlog and coverage pages for this working tree to .spry/view/")
    p.add_argument("--since", help="only when the plan or a test changed since this commit (for git hooks)")
    p = sub.add_parser("hooks", help="git hooks that refresh .spry/view/ after a checkout or a pull")
    p.add_argument("--remove", action="store_true", help="remove the hooks spry wrote")
    p = sub.add_parser("index", help="regenerate marker blocks and INDEX.md files")
    g = p.add_mutually_exclusive_group()
    g.add_argument("--check", action="store_true", help="change nothing; exit 1 if anything is stale")
    g.add_argument("--restore", metavar="BASE", help="on a branch: put back BASE's copy of every generated block it changed")
    p = sub.add_parser("related", help="conflict-check candidates for a document")
    p.add_argument("file")
    p = sub.add_parser("next", help="next free ID for a type")
    p.add_argument("type")
    p = sub.add_parser("new", help="create an item from its template, with the next ID, in the right folder")
    p.add_argument("type")
    p.add_argument("--parent")
    p.add_argument("--title", required=True)
    p.add_argument("--owner")
    p.add_argument("--dependency", help="external: the service the behaviour belongs to")
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
    q.add_argument("--record", metavar="SLICE", help="write the results into this slice's Falsify table")
    q.add_argument("--jobs", type=int, help="worktrees to run in parallel (default: falsify.parallel; 1 = serial)")
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
    project = Project(root)

    if args.command == "check":
        if args.base:
            changed_criteria(project, args.base)
            changed_blocks(project, args.base)
        problems = check(project)
        for p in problems:
            print(p)
        errors = sum(1 for p in problems if p.level == "error")
        print(f"{errors} error{'s' if errors != 1 else ''}, {len(problems) - errors} warning{'s' if len(problems) - errors != 1 else ''}")
        return 1 if errors else 0
    if args.command == "status":
        print(status(project, args.level))
        return 0
    if args.command == "coverage":
        print(coverage_block(project, os.path.join(project.spry, "COVERAGE.md")))
        return 0
    if args.command == "backlog":
        print(backlog_block(project, os.path.join(project.spry, "BACKLOG.md")))
        return 0
    if args.command == "view":
        written = view(project, args.since)
        if written:
            print(("spry: refreshed " if args.since else "wrote: ") + ", ".join(written))
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
    if args.command == "next":
        print(next_id(project, args.type))
        return 0
    if args.command == "new":
        print(project.rel(new_item(project, args.type, args.parent, args.title, args.owner, dependency=args.dependency)))
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
        current = read(path) if os.path.isfile(path) else None
        if args.check:
            print("up to date" if current == text else "stale: .github/CODEOWNERS")
            return 0 if current == text else 1
        if current != text:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            write(path, text)
            print("wrote: .github/CODEOWNERS")
        else:
            print("up to date")
        return 0
    if args.command == "tests":
        print(slowest(project, args.junit, args.limit))
        return 0
    if args.command == "merge-check":
        lines = merge_check(project, args.slice, args.base)
        mark = {"ok": "✓", "warn": "!", "block": "✗"}
        for level, text in lines:
            print(f"{mark[level]} {text}")
        blocks = sum(1 for s, _ in lines if s == "block")
        print("ready to merge" if not blocks else f"{blocks} thing{'s block' if blocks != 1 else ' blocks'} the merge")
        return 1 if blocks else 0
    if args.command == "gate":
        return gate(project, args.force)
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
                os.makedirs(os.path.dirname(out), exist_ok=True)
                write(out, json.dumps(plan, indent=2, ensure_ascii=False) + "\n")
                print(f"{len(plan)} candidate control{'s' if len(plan) != 1 else ''} → {project.rel(out)}")
                if plan and not plan[0]["expect"]:
                    print("fill in `expect` — the slice covers no story criteria")
                print("prune it to the safeguards that matter, then: falsify run " + project.rel(out))
                return 0
            results = falsify_run(project, args.plan, dry=args.dry_run, jobs=args.jobs)
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
                    print("recorded in " + project.rel(record_falsify(Project(project.root), args.record, rows)))
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
    if args.command == "pr-body":
        print(pr_body(project, args.slice, args.base), end="")
        return 0
    return 2


if __name__ == "__main__":
    sys.exit(main())
