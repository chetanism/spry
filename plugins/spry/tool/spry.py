#!/usr/bin/env python3
"""spry — the project tool. Standard library only, Python 3.10+.

    python3 spry/tool/spry.py check              # is the tree consistent? exit 1 if not
    python3 spry/tool/spry.py status [--level story]
    python3 spry/tool/spry.py index [--check]    # regenerate marker blocks and INDEX.md files
    python3 spry/tool/spry.py related <file>     # candidates for a conflict check
    python3 spry/tool/spry.py next <type>        # next free ID: milestone, story, slice, decision …
    python3 spry/tool/spry.py new <type> --parent <ID> --title "…" [--owner …]
    python3 spry/tool/spry.py pr-body <slice ID> # the slice's work order (+ close summary) for a PR
    python3 <plugin>/tool/spry.py vendor --root <project>   # copy process/ and the tool into a project
    python3 <plugin>/tool/spry.py vendor --diff --root <project>   # what differs from the plugin
    python3 spry/tool/spry.py scrub <file>       # private words left in text about to leave the project

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
import json
import math
import os
import re
import shutil
import sys
from datetime import date
from dataclasses import dataclass, field

VERSION = "0.1.0"

DEFAULT_LEVELS = ["milestone", "epic", "feature", "story"]
DEFAULT_IDS = {"milestone": "M", "epic": "E", "feature": "F", "story": "S",
               "slice": "SL", "task": "T", "bug": "B", "decision": "D"}
DEFAULT_TEST_MATCH = ["**/*.test.*", "**/*.spec.*", "**/*_test.*", "**/test_*.py", "**/tests/**"]
SKIP_DIRS = {".git", "node_modules", ".spry", "dist", "build", "__pycache__", ".venv", "venv",
             ".idea", ".turbo", "coverage", ".next", "target"}
CONTAINERS = {"tasks": "task", "bugs": "bug"}

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
    if not lines or lines[0].strip() != "---":
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
        if value.startswith("["):
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
        cells = [c.strip() for c in s.strip("|").split("|")]
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


def strip_blocks(text: str) -> str:
    return re.sub(r"<!-- spry:(\w+) -->\n.*?<!-- /spry:\1 -->", "", text, flags=re.S)


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
        return [glob_regex(g) for g in (self.config.get("tests", {}).get("match") or DEFAULT_TEST_MATCH)]

    def _scan_tests(self):
        """{"S-1/AC-1": [(rel path, line, test name)]} from every test file outside spry/."""
        story = re.escape(self.ids["story"])
        ref = re.compile(r"(?<![A-Za-z0-9])(" + story + r"-\d+)/(AC-\d+)(?!\d)")
        quoted = re.compile(r"""(["'`])((?:(?!\1).)*?)\1""")
        globs, found = self._test_globs(), {}
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
                for n, line in enumerate(text.split("\n"), 1):
                    for m in ref.finditer(line):
                        name_ = next((q.group(2) for q in quoted.finditer(line)
                                      if q.start() <= m.start() < q.end()), "")
                        found.setdefault(f"{m.group(1)}/{m.group(2)}", []).append((rel, n, name_))
        return found

    def _manual_checks(self, story: Item):
        """{"AC-1": (date, build, by, result, line)} — the latest row per criterion."""
        path = os.path.join(story.folder, "checks.md")
        if not os.path.isfile(path):
            return {}
        text = read(path)
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
        pr = f" · PR #{pr}" if pr.isdigit() else ""
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

def markdown_files(project: Project):
    """Every .md under spry/ except the vendored process/ and tool/, plus AGENTS.md."""
    out = []
    agents = os.path.join(project.root, "AGENTS.md")
    if os.path.isfile(agents):
        out.append(agents)
    for dirpath, dirnames, filenames in os.walk(project.spry):
        rel = project.rel(dirpath)
        if rel in ("spry/process", "spry/tool") or rel.startswith(("spry/process/", "spry/tool/")):
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
                project.problem(path, len(lines), f"{len(lines)} lines, budget {limit} ({pattern}) — split it into INDEX.md + items")

        unfinished_ok = fm.get("state") in ("draft", "planned")
        if not unfinished_ok:
            in_fence = False
            for n, line in enumerate(lines, 1):
                if FENCE.match(line):
                    in_fence = not in_fence
                if not in_fence and "<!-- guide:" in line:
                    project.problem(path, n, "template guide left in a finished document")
            for n, line in prose(text):
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
                resolved = os.path.normpath(os.path.join(os.path.dirname(path), target.split("#")[0]))
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
    for dirpath, dirnames, filenames in os.walk(os.path.join(project.spry, "knowledge")):
        dirnames[:] = [d for d in dirnames if not d.startswith(".")]
        if "INDEX.md" in filenames:
            path = os.path.join(dirpath, "INDEX.md")
            apply(path, "index", index_block(project, path), True)
    return sorted(changed)


# ---------------------------------------------------------------- status

def status(project: Project, level: str | None):
    stop = project.levels.index(level) if level in project.levels else None
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


def new_item(project: Project, kind: str, parent_id: str | None, title: str,
             owner: str | None = None, today: str | None = None) -> str:
    """Create an item from its template at the right place with the next ID. Returns the path."""
    if kind not in project.ids:
        raise SystemExit(f"unknown type `{kind}` — one of {', '.join(project.ids)}")
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

def pr_body(project: Project, slice_id: str) -> str:
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
    return f"**{item.label}**{parent} — `{project.rel(item.doc)}`\n\n{body}\n"


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
    sub.add_parser("check", help="consistency of the plan, knowledge and links")
    p = sub.add_parser("status", help="done vs total at every level")
    p.add_argument("--level", help="stop at this level, e.g. feature")
    p = sub.add_parser("index", help="regenerate marker blocks and INDEX.md files")
    p.add_argument("--check", action="store_true", help="change nothing; exit 1 if anything is stale")
    p = sub.add_parser("related", help="conflict-check candidates for a document")
    p.add_argument("file")
    p = sub.add_parser("next", help="next free ID for a type")
    p.add_argument("type")
    p = sub.add_parser("new", help="create an item from its template, with the next ID, in the right folder")
    p.add_argument("type")
    p.add_argument("--parent")
    p.add_argument("--title", required=True)
    p.add_argument("--owner")
    p = sub.add_parser("pr-body", help="a slice's work order and close summary, for its pull request")
    p.add_argument("slice")
    p = sub.add_parser("vendor", help="copy process/ and the tool into a project (run the plugin's copy)")
    p.add_argument("--force", action="store_true", help="overwrite an existing spry/process/")
    p.add_argument("--root", dest="vendor_root", help="the project to copy into (default: current folder)")
    p.add_argument("--diff", action="store_true", help="change nothing; list what differs from the plugin")
    p = sub.add_parser("scrub", help="private words still in a file meant to leave the project")
    p.add_argument("file")
    args = parser.parse_args(argv)

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
        problems = check(project)
        for p in problems:
            print(p)
        errors = sum(1 for p in problems if p.level == "error")
        print(f"{errors} error{'s' if errors != 1 else ''}, {len(problems) - errors} warning{'s' if len(problems) - errors != 1 else ''}")
        return 1 if errors else 0
    if args.command == "status":
        print(status(project, args.level))
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
        print(project.rel(new_item(project, args.type, args.parent, args.title, args.owner)))
        return 0
    if args.command == "scrub":
        hits = scrub(project, args.file)
        for n, word in hits:
            print(f"{args.file}:{n}: {word}")
        print(f"{len(hits)} private word{'s' if len(hits) != 1 else ''}")
        return 1 if hits else 0
    if args.command == "pr-body":
        print(pr_body(project, args.slice), end="")
        return 0
    return 2


if __name__ == "__main__":
    sys.exit(main())
