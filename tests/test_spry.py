"""Tests for plugins/spry/tool/spry.py.  python3 tests/test_spry.py"""

import contextlib
import io
import datetime
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import unittest
import unittest.mock

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(REPO, "plugins", "spry", "tool"))
import spry  # noqa: E402

EXAMPLE = os.path.join(REPO, "docs", "example")
CONFIG = {"product": "Test", "glossary": "spry/knowledge/glossary.md",
          "tests": {"match": ["**/*.test.ts"]}, "budgets": {"spry/knowledge/**": 40}}

GLOSSARY = """---
title: Glossary
summary: terms
audience: 2
---
# Glossary

| Term | Means | Don't say |
|---|---|---|
| Member | a person who borrows | patron, borrower |
"""

CHECKED = "## Conflict check\n\n- Checked 2026-10-01 against: everything\n- No conflicts found.\n"


def item(ident, state="ready", extra="", body="", check=True):
    head = f"---\nid: {ident}\ntitle: Title of {ident}\nstate: {state}\nowner: A\naudience: 3\n{extra}---\n# {ident}\n\n"
    return head + body + ("\n" + CHECKED if check else "") + "\n## Children\n\n<!-- spry:children -->\n<!-- /spry:children -->\n"


def story(ident, acs=("AC-1",), state="ready", check=True):
    rows = "".join(f"| {a} | x | y | z |\n" for a in acs)
    body = f"## Acceptance criteria\n\n| AC | Given | When | Then |\n|---|---|---|---|\n{rows}\n"
    return item(ident, state, body=body, check=check) + "\n## Proof\n\n<!-- spry:proof -->\n<!-- /spry:proof -->\n"


def slice_(ident, state="closed", covers="[AC-1]", plan="", check=True, closed="2026-10-01"):
    date = f"closed: {closed}\n" if state == "closed" and closed else ""
    head = f"---\nid: {ident}\ntitle: Slice {ident}\nstate: {state}\nowner: A\naudience: 8\ncovers: {covers}\npr: 1\n{date}---\n# {ident}\n\n"
    body = "## Work order\n\n### Plan\n\n" + plan + "\n"
    return head + body + ("### Conflict check\n\n- Checked 2026-10-01 against: S-1\n" if check else "")


M, E, F, S = "spry/plan/M-1-m", "spry/plan/M-1-m/E-1-e", "spry/plan/M-1-m/E-1-e/F-1-f", "spry/plan/M-1-m/E-1-e/F-1-f/S-1-s"


def base():
    return {
        "spry/spry.config.json": json.dumps(CONFIG),
        "spry/knowledge/glossary.md": GLOSSARY,
        "spry/plan/README.md": "---\ntitle: Roadmap\naudience: 2\n---\n# Roadmap\n\n<!-- spry:children -->\n<!-- /spry:children -->\n",
        f"{M}/README.md": item("M-1"),
        f"{E}/README.md": item("E-1"),
        f"{F}/README.md": item("F-1"),
        f"{S}/README.md": story("S-1"),
        f"{S}/SL-1-a.md": slice_("SL-1"),
        "src/a.test.ts": 'test("S-1/AC-1 does the thing", () => {})\n',
    }


class Tree:
    def __init__(self, files):
        self.root = tempfile.mkdtemp()
        for rel, text in files.items():
            if text is None:
                continue
            path = os.path.join(self.root, rel)
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w") as handle:
                handle.write(text)

    def project(self):
        return spry.Project(self.root)

    def problems(self):
        return [str(p) for p in spry.check(self.project()) if p.level == "error"]

    def close(self):
        shutil.rmtree(self.root)


class Base(unittest.TestCase):
    def tree(self, **changes):
        files = base()
        for key, value in changes.items():
            files[key.replace("__", "/")] = value
        t = Tree(files)
        self.addCleanup(t.close)
        return t

    def tree_files(self, files):
        t = Tree(files)
        self.addCleanup(t.close)
        return t

    def assertProblem(self, problems, fragment):
        self.assertTrue(any(fragment in p for p in problems), f"no problem containing {fragment!r} in {problems}")


class FrontMatter(unittest.TestCase):
    def test_values_and_lists(self):
        fm, start, errors = spry.parse_front_matter("---\nid: S-1\ncovers: [AC-1, AC-2]\nempty: []\n---\nbody")
        self.assertEqual(fm, {"id": "S-1", "covers": ["AC-1", "AC-2"], "empty": []})
        self.assertEqual((start, errors), (5, []))

    def test_rejects_other_yaml(self):
        _, _, errors = spry.parse_front_matter("---\nid: S-1\n  nested: x\n---\n")
        self.assertTrue(errors)

    def test_unclosed(self):
        fm, _, errors = spry.parse_front_matter("---\nid: S-1\n")
        self.assertIsNone(fm)
        self.assertTrue(errors)

    def test_a_title_in_brackets_is_text_not_a_list(self):
        fm, _, errors = spry.parse_front_matter("---\ntitle: [FR-IAM-07] Sign in\nrelated: [S-1]\n---\n")
        self.assertEqual((fm["title"], fm["related"], errors), ("[FR-IAM-07] Sign in", ["S-1"], []))

    def test_byte_order_mark(self):
        fm, _, errors = spry.parse_front_matter("\ufeff---\nid: S-1\n---\n")
        self.assertEqual((fm, errors), ({"id": "S-1"}, []))


class Glob(unittest.TestCase):
    def test_double_star(self):
        r = spry.glob_regex("spry/plan/**/SL-*.md")
        self.assertTrue(r.match("spry/plan/M-1/S-1/SL-3-x.md"))
        self.assertFalse(r.match("spry/plan/M-1/S-1/README.md"))
        self.assertTrue(spry.glob_regex("**/*.test.ts").match("a.test.ts"))


class Check(Base):
    def test_clean_tree(self):
        self.assertEqual(self.tree().problems(), [])

    def test_duplicate_id(self):
        t = self.tree(**{f"{F}/S-1-other/README.md".replace("/", "__"): story("S-1")})
        self.assertProblem(t.problems(), "S-1 is also")

    def test_misplaced_item(self):
        t = self.tree(**{f"{M}/S-2-x/README.md".replace("/", "__"): story("S-2")})
        self.assertProblem(t.problems(), "a story cannot sit under milestone M-1")

    def test_id_must_match_folder(self):
        t = self.tree(**{f"{F}/README.md".replace("/", "__"): item("F-9")})
        self.assertProblem(t.problems(), "does not match the name `F-1`")

    def test_unknown_file_in_plan(self):
        t = self.tree(**{f"{F}/notes.md".replace("/", "__"): "x"})
        self.assertProblem(t.problems(), "not part of the plan")

    def test_banned_synonym(self):
        t = self.tree(**{f"{F}/README.md".replace("/", "__"): item("F-1", body="- A patron borrows.\n")})
        self.assertProblem(t.problems(), "`patron` — the glossary says `Member`")

    def test_banned_synonym_allowed_in_code_and_conflict_check(self):
        body = "- Uses `patron` in code.\n\n```\npatron\n```\n"
        text = item("F-1", body=body, check=False).replace(
            "## Children", "## Conflict check\n\n- Checked 2026-10-01 against: x\n- Term: said patron → Member\n\n## Children")
        t = self.tree(**{f"{F}/README.md".replace("/", "__"): text})
        self.assertEqual(t.problems(), [])

    def test_broken_link(self):
        t = self.tree(**{f"{F}/README.md".replace("/", "__"): item("F-1", body="- See [x](../nope.md)\n")})
        self.assertProblem(t.problems(), "does not resolve")

    def test_line_numbers_count_generated_blocks(self):
        body = "<!-- spry:x -->\n- a\n- b\n<!-- /spry:x -->\n- See [x](nope.md)\n"
        t = self.tree(**{f"{F}/README.md".replace("/", "__"): item("F-1", body=body)})
        line = item("F-1", body=body).split("\n").index("- See [x](nope.md)") + 1
        self.assertProblem(t.problems(), f"README.md:{line}:")

    def test_a_link_from_the_repository_root(self):
        t = self.tree(**{f"{F}/README.md".replace("/", "__"): item("F-1", body="- See [x](/src/a.test.ts)\n")})
        self.assertEqual(t.problems(), [])

    def test_template_test_glob_is_reported_not_used(self):
        config = dict(CONFIG, tests={"match": ["<glob of test files, e.g. **/*.test.ts>"]})
        t = self.tree(**{"spry__spry.config.json": json.dumps(config)})
        self.assertProblem(t.problems(), "tests.match is still the template's placeholder")
        self.assertIn("S-1/AC-1", t.project().tests, "the defaults still find the test")

    def test_a_skipped_test_proves_nothing(self):
        t = self.tree(**{"src__a.test.ts": 'test.skip("S-1/AC-1 does the thing", () => {})\n'})
        self.assertNotIn("S-1/AC-1", t.project().tests)

    def test_a_citation_in_a_comment_or_code_proves_nothing(self):
        for text in ['// S-1/AC-1 does the thing\ntest("x", () => {})\n',
                     'test("x", () => { expect(f()).toBe(1) }) // "S-1/AC-1"\n',
                     ' * S-1/AC-1 in a doc comment\n']:
            t = self.tree(**{"src__a.test.ts": text})
            p = t.project()
            self.assertNotIn("S-1/AC-1", p.tests, text)
            warnings = [str(x) for x in spry.check(p) if x.level == "warning"]
            self.assertTrue(any("cited outside a test's name" in w for w in warnings), warnings)

    def test_a_citation_in_a_title_or_docstring_proves(self):
        config = dict(CONFIG, tests={"match": ["**/*.test.ts", "**/test_*.py"]})
        t = self.tree(**{"spry__spry.config.json": json.dumps(config), "src__a.test.ts": None,
                         "tests__test_a.py": 'def test_lends():\n    """\n    S-1/AC-1 lends a book\n    """\n',
                         "tests__test_b.py": "@pytest.mark.parametrize('x', [1], ids=['S-1/AC-1 one'])\ndef test_x(x): pass\n"})
        tests = t.project().tests["S-1/AC-1"]
        self.assertEqual(sorted((p, n) for p, n, _ in tests), [("tests/test_a.py", 3), ("tests/test_b.py", 1)])

    def test_string_spans(self):
        self.assertEqual(spry.string_spans('test("a # b", () => {}) // "c"', None), ([(6, 11)], None))
        self.assertEqual(spry.string_spans('    """opens', None), ([(7, 12)], '"""'))
        self.assertEqual(spry.string_spans('still in""" + "x"', '"""'), ([(0, 8), (15, 16)], None))

    def test_skills_copied_for_another_agent_are_not_checked(self):
        t = self.tree()
        spry.install(t.root, "generic")
        self.assertEqual(t.problems(), [])

    def test_guide_left_in_ready_but_not_draft(self):
        guided = item("F-1", body="<!-- guide: fill me -->\n- <thing>\n")
        self.assertProblem(self.tree(**{f"{F}/README.md".replace("/", "__"): guided}).problems(), "template guide left")
        draft = item("F-1", state="draft", body="<!-- guide: fill me -->\n- <thing>\n")
        self.assertEqual(self.tree(**{f"{F}/README.md".replace("/", "__"): draft}).problems(), [])

    def test_placeholder(self):
        t = self.tree(**{f"{F}/README.md".replace("/", "__"): item("F-1", body="- Lent to <member>\n")})
        self.assertProblem(t.problems(), "placeholder `<member>`")

    def test_a_test_name_in_a_generated_block_is_not_a_placeholder(self):
        body = "<!-- spry:proof -->\n- `S-1/AC-1` — keyed by <token>\n<!-- /spry:proof -->\n"
        t = self.tree(**{f"{F}/README.md".replace("/", "__"): item("F-1", body=body)})
        self.assertFalse([p for p in t.problems() if "placeholder" in str(p)])

    def test_ready_needs_conflict_check(self):
        t = self.tree(**{f"{F}/README.md".replace("/", "__"): item("F-1", check=False)})
        self.assertProblem(t.problems(), "without a `Conflict check` section")

    def test_open_finding(self):
        text = item("F-1").replace("- No conflicts found.", "- Contradiction: D-1 → open")
        t = self.tree(**{f"{F}/README.md".replace("/", "__"): text})
        self.assertProblem(t.problems(), "conflict finding still open")

    def test_slice_conflict_check_under_work_order(self):
        t = self.tree(**{f"{S}/SL-1-a.md".replace("/", "__"): slice_("SL-1", check=False)})
        self.assertProblem(t.problems(), "without a `Conflict check`")

    def test_planned_slice_needs_no_check(self):
        t = self.tree(**{f"{S}/SL-1-a.md".replace("/", "__"): slice_("SL-1", state="planned", check=False)})
        self.assertEqual(t.problems(), [])

    def test_slice_covers_unknown_ac(self):
        t = self.tree(**{f"{S}/SL-1-a.md".replace("/", "__"): slice_("SL-1", covers="[AC-1, AC-7]")})
        self.assertProblem(t.problems(), "covers AC-7")

    def test_test_cites_unknown_ac(self):
        t = self.tree(**{"src/a.test.ts": 'test("S-1/AC-9 x", () => {})\n'})
        self.assertProblem(t.problems(), "S-1 has no AC-9")

    def test_unknown_reference(self):
        t = self.tree(**{f"{F}/README.md".replace("/", "__"): item("F-1", extra="blocked_by: [T-9]\n")})
        self.assertProblem(t.problems(), "names T-9")

    def test_budget(self):
        long = GLOSSARY + "\n".join(f"- line {i}" for i in range(40))
        t = self.tree(**{"spry/knowledge/glossary.md".replace("/", "__"): long})
        self.assertProblem(t.problems(), "budget 40")
        self.assertProblem(t.problems(), "/spry:compact")

    def slice_with_falsify(self, prose, rows, after=0):
        table = "| Control | Mutation | Expect | Result |\n|---|---|---|---|\n" + "".join(
            f"| `src/a.ts:{i}` | delete the line | S-1/AC-1 | caught |\n" for i in range(rows))
        text = (slice_("SL-1") + "\n".join(f"- line {i}" for i in range(prose)) + "\n\n### Falsify\n\n" + table
                + "\n### Demo\n\n" + "".join(f"- after {i}\n" for i in range(after)))
        config = dict(CONFIG, budgets={"spry/plan/**/SL-*.md": 60})
        return self.tree(**{"spry__spry.config.json": json.dumps(config), f"{S}/SL-1-a.md".replace("/", "__"): text})

    def test_budget_leaves_a_slices_falsify_table_out(self):
        self.assertEqual([p for p in self.slice_with_falsify(prose=10, rows=200).problems() if "budget" in p], [])

    def test_budget_counts_a_slices_prose_and_says_what_it_left_out(self):
        problems = self.slice_with_falsify(prose=70, rows=200).problems()
        self.assertProblem(problems, "(202 of the Falsify table not counted), budget 60")
        # lines after the table are counted again: only the table is left out, not the rest of the file
        self.assertProblem(self.slice_with_falsify(prose=10, rows=200, after=70).problems(), "budget 60")

    def test_budget_counts_prose_under_falsify(self):
        text = slice_("SL-1") + "\n### Falsify\n\n" + "".join(f"prose {i}\n" for i in range(70))
        config = dict(CONFIG, budgets={"spry/plan/**/SL-*.md": 60})
        t = self.tree(**{"spry__spry.config.json": json.dumps(config), f"{S}/SL-1-a.md".replace("/", "__"): text})
        self.assertProblem(t.problems(), "budget 60")

    def test_budget_counts_a_table_named_falsify_outside_a_slice(self):
        long = GLOSSARY + "\n### Falsify\n\n" + "".join(f"| row {i} |\n" for i in range(40))
        t = self.tree(**{"spry/knowledge/glossary.md".replace("/", "__"): long})
        self.assertProblem(t.problems(), "budget 40")

    def index_with_entries(self, entries, hand=0):
        text = ("---\ntitle: Decisions\nsummary: Every decision.\naudience: 7\n---\n# Decisions\n\n"
                + "".join(f"- note {i}\n" for i in range(hand))
                + "<!-- spry:index -->\n" + "".join(f"- [D-{i}](D-{i}.md) — decision {i}\n" for i in range(entries))
                + "<!-- /spry:index -->\n")
        config = dict(CONFIG, budgets={"spry/knowledge/decisions/INDEX.md": 30})
        return self.tree(**{"spry__spry.config.json": json.dumps(config),
                            "spry/knowledge/decisions/INDEX.md".replace("/", "__"): text})

    def test_budget_leaves_an_indexs_generated_lines_out(self):
        self.assertEqual([p for p in self.index_with_entries(entries=300, hand=3).problems() if "budget" in p], [])

    def test_budget_counts_an_indexs_hand_written_lines_and_says_what_it_left_out(self):
        problems = self.index_with_entries(entries=300, hand=40).problems()
        self.assertProblem(problems, "lines counted (300 of the generated index not counted), budget 30")

    def test_citations_are_in_path_and_line_order_whatever_the_walk(self):
        t = self.tree(**{"src__a.test.ts": 'test("x", () => {})\ntest("S-1/AC-1 two", () => {})\ntest("S-1/AC-1 three", () => {})\n',
                         "src__b.test.ts": 'test("S-1/AC-1 b", () => {})\n', "lib__z.test.ts": 'test("S-1/AC-1 z", () => {})\n'})
        walk = spry.walk_dir

        def backwards(top):
            for dirpath, dirnames, filenames in walk(top):
                dirnames.sort(reverse=True)
                yield dirpath, dirnames, sorted(filenames, reverse=True)
        spry.walk_dir = backwards
        self.addCleanup(setattr, spry, "walk_dir", walk)
        self.assertEqual([(p, n) for p, n, _ in t.project().tests["S-1/AC-1"]],
                         [("lib/z.test.ts", 1), ("src/a.test.ts", 2), ("src/a.test.ts", 3), ("src/b.test.ts", 1)])

    def test_speaks_utf8_on_a_console_that_cannot(self):
        t = self.tree()
        raw = io.BytesIO()
        narrow = io.TextIOWrapper(raw, encoding="cp1252")
        out, err = sys.stdout, sys.stderr
        sys.stdout = sys.stderr = narrow
        try:
            spry.main(["--root", t.root, "status"])
            print("✓")
            narrow.flush()
        finally:
            sys.stdout, sys.stderr = out, err
        self.assertIn("✓".encode("utf-8"), raw.getvalue())

    def test_bug_breaks_must_exist(self):
        bug = item("B-1", extra="breaks: [S-1/AC-4]\n", check=False)
        t = self.tree(**{f"{F}/bugs/B-1-x/README.md".replace("/", "__"): bug})
        self.assertProblem(t.problems(), "`breaks` names S-1/AC-4")

    def test_a_bug_names_the_slice_that_introduced_it_or_nothing(self):
        def problems(extra):
            bug = item("B-1", extra=extra, check=False)
            return self.tree(**{f"{F}/bugs/B-1-x/README.md".replace("/", "__"): bug}).problems()
        self.assertProblem(problems("introduced_by: SL-9\n"), "`introduced_by` names SL-9, which is not a slice")
        self.assertProblem(problems("introduced_by: S-1\n"), "`introduced_by` names S-1, which is not a slice")
        for fine in ("introduced_by: SL-1\n", "introduced_by: [SL-1]\n", "introduced_by:\n", ""):
            self.assertFalse([p for p in problems(fine) if "introduced_by" in p], fine)


class Status(Base):
    def done(self, t, ident):
        p = t.project()
        return p.done(p.items[ident])

    def test_rolls_up_when_everything_is_proven(self):
        t = self.tree()
        for ident in ("SL-1", "S-1", "F-1", "E-1", "M-1"):
            self.assertTrue(self.done(t, ident), ident)

    def test_story_not_done_without_proof(self):
        t = self.tree(**{"src/a.test.ts": "nothing\n"})
        self.assertFalse(self.done(t, "S-1"))
        self.assertFalse(self.done(t, "M-1"))

    def test_story_not_done_while_a_slice_is_open(self):
        t = self.tree(**{f"{S}/SL-1-a.md".replace("/", "__"): slice_("SL-1", state="open")})
        self.assertFalse(self.done(t, "S-1"))

    def test_manual_pass_proves_and_a_later_fail_unproves(self):
        log = "---\ntitle: c\naudience: 4\n---\n# c\n\n## Check log\n\n| Date | AC | Build | By | Result | Notes |\n|---|---|---|---|---|---|\n| 2026-10-01 | AC-1 | x | Q | pass | |\n"
        t = self.tree(**{"src/a.test.ts": "nothing\n", f"{S}/checks.md".replace("/", "__"): log})
        self.assertTrue(self.done(t, "S-1"))
        t = self.tree(**{f"{S}/checks.md".replace("/", "__"): log + "| 2026-10-03 | AC-1 | y | Q | fail | |\n"})
        self.assertFalse(self.done(t, "S-1"), "a failed manual check outranks a test")

    def test_each_scenario_keeps_its_own_latest_run(self):
        head = ("---\ntitle: c\naudience: 4\n---\n# c\n\n## Scenarios\n\n### AC-1 · At the desk\n\n1. a → b\n\n"
                "### AC-1 · By post\n\n1. a → b\n\n## Check log\n\n"
                "| Date | AC | Scenario | Build | By | Result | Notes |\n|---|---|---|---|---|---|---|\n"
                "| 2026-10-01 | AC-1 | at the  desk | x | Q | fail | B-9 |\n"
                "| 2026-10-02 | AC-1 | By post | x | Q | pass | |\n")
        key = f"{S}/checks.md".replace("/", "__")
        t = self.tree(**{"src/a.test.ts": "nothing\n", key: head})
        self.assertFalse(self.done(t, "S-1"), "a pass of one scenario does not hide a failure of another")
        self.assertEqual(t.project().manual["S-1"]["AC-1"][:4], ("2026-10-01", "x", "Q", "fail"))
        t = self.tree(**{"src/a.test.ts": "nothing\n", key: head + "| 2026-10-03 | AC-1 | At the desk | y | Q | pass | |\n"})
        self.assertTrue(self.done(t, "S-1"))
        t = self.tree(**{"src/a.test.ts": "nothing\n", key: head + "| 2026-10-03 | AC-1 | | y | Q | pass | |\n"})
        self.assertTrue(self.done(t, "S-1"), "a row naming no scenario is a run of the whole criterion")
        t = self.tree(**{key: head + "| 2026-10-03 | AC-1 | By bus | y | Q | pass | |\n"})
        self.assertTrue(any("scenario `By bus`, and no scenario for AC-1" in p for p in t.problems()))

    def test_dropped_children_are_not_counted(self):
        t = self.tree(**{f"{F}/S-2-x/README.md".replace("/", "__"): story("S-2", state="dropped")})
        self.assertTrue(self.done(t, "F-1"))

    def test_draft_is_never_done(self):
        t = self.tree(**{f"{F}/README.md".replace("/", "__"): item("F-1", state="draft")})
        self.assertFalse(self.done(t, "F-1"))

    def test_tasks_do_not_count_toward_parent(self):
        task = item("T-1")
        t = self.tree(**{f"{M}/tasks/T-1-x/README.md".replace("/", "__"): task})
        self.assertTrue(self.done(t, "M-1"))
        self.assertFalse(self.done(t, "T-1"))

    def test_tasks_and_bugs_count_in_the_work_not_the_done(self):
        t = self.tree(**{f"{M}/tasks/T-1-x/README.md".replace("/", "__"): item("T-1"),
                         f"{M}/tasks/T-1-x/SL-2-b.md".replace("/", "__"): slice_("SL-2"),
                         f"{F}/bugs/B-1-x/README.md".replace("/", "__"): item("B-1"),
                         f"{E}/tasks/T-2-x/README.md".replace("/", "__"): item("T-2", state="dropped")})
        p = t.project()
        self.assertTrue(p.done(p.items["M-1"]), "an open bug never unfinishes its milestone")
        self.assertEqual(p.work(p.items["M-1"]), {"story": (1, 1), "task": (1, 1), "bug": (0, 1)})
        self.assertEqual(p.progress(p.items["M-1"]), "1 of 1 epics done · stories 1 of 1 · all work 2 of 3 · 1 open bug")
        self.assertEqual(p.progress(p.items["F-1"]), "1 of 1 stories done · all work 1 of 2 · 1 open bug",
                         "no stories figure where the count is stories")
        self.assertEqual(spry.coverage_block(p, os.path.join(t.root, "spry", "COVERAGE.md")).count(
            "| All work: stories, tasks and bugs | 2 | 0 | 3 | 67% |"), 1)

    def test_no_work_figures_without_tasks_or_bugs(self):
        p = self.tree().project()
        self.assertEqual(p.progress(p.items["M-1"]), "1 of 1 epics done")

    def test_unknown_level(self):
        with self.assertRaises(SystemExit):
            spry.status(self.tree().project(), "chapter")

    def test_status_prints_tree(self):
        out = spry.status(self.tree().project(), None)
        self.assertIn("M-1 Title of M-1", out)
        self.assertIn("slice SL-1", out)

    def test_a_big_plan_is_cut_to_the_levels_that_fit(self):
        original = spry.STATUS_LINES
        spry.STATUS_LINES = 3
        self.addCleanup(setattr, spry, "STATUS_LINES", original)
        p = self.tree().project()
        out = spry.status(p, None)
        self.assertNotIn("slice SL-1", out)
        self.assertIn("deeper: `status <ID>` for one branch", out)
        self.assertIn("slice SL-1", spry.status(p, None, everything=True))
        self.assertIn("slice SL-1", spry.status(p, None, "S-1"))
        self.assertTrue(spry.status(p, None, "S-1").startswith("S-1 "))


class Index(Base):
    def test_fills_blocks_and_is_idempotent(self):
        t = self.tree()
        changed = spry.index(t.project(), dry=False)
        self.assertIn(f"{S}/README.md", changed)
        with open(os.path.join(t.root, F, "README.md")) as handle:
            self.assertIn("[S-1 Title of S-1](S-1-s/README.md)", handle.read())
        with open(os.path.join(t.root, S, "README.md")) as handle:
            self.assertIn('S-1/AC-1 does the thing', handle.read())
        self.assertEqual(spry.index(t.project(), dry=True), [])

    def test_knowledge_index(self):
        t = self.tree(**{
            "spry__knowledge__decisions__INDEX.md": "---\ntitle: D\naudience: 6\n---\n# D\n\n<!-- spry:index -->\n<!-- /spry:index -->\n",
            "spry__knowledge__decisions__D-1-x.md": "---\nid: D-1\ntitle: Keep it\nsummary: we keep it\n---\n# D-1\n",
        })
        spry.index(t.project(), dry=False)
        with open(os.path.join(t.root, "spry/knowledge/decisions/INDEX.md")) as handle:
            self.assertIn("- [D-1 Keep it](D-1-x.md) — we keep it", handle.read())

    def test_a_folder_index_without_a_summary_shows_its_count_quietly(self):
        idx = "---\ntitle: {0}\naudience: 6\n---\n# {0}\n\n<!-- spry:index -->\n<!-- /spry:index -->\n"
        t = self.tree(**{
            "spry__knowledge__conventions__INDEX.md": idx.format("Conventions"),
            "spry__knowledge__conventions__auth__INDEX.md": idx.format("Auth"),
            "spry__knowledge__conventions__auth__a.md": "---\ntitle: A\nsummary: a\n---\n# A\n",
            "spry__knowledge__conventions__auth__b.md": "---\ntitle: B\nsummary: b\n---\n# B\n",
        })
        p = t.project()
        spry.index(p, dry=False)
        with open(os.path.join(t.root, "spry/knowledge/conventions/INDEX.md")) as handle:
            self.assertIn("- [Auth](auth/INDEX.md) — 2 entries", handle.read())
        self.assertFalse([x for x in p.problems if "summary" in x.message])


class Link(Base):
    def test_link_sets_and_adds_fields_and_refuses_a_non_number(self):
        t = self.tree(**{f"{S}/SL-1-a.md".replace("/", "__"): slice_("SL-1", state="open")})
        path = spry.link_slice(t.project(), "SL-1", {"pr": "#42", "branch": "sl-1-a"})
        with open(path) as handle:
            head = handle.read().split("\n---\n")[0]
        self.assertIn("pr: 42\n", head + "\n")
        self.assertIn("branch: sl-1-a", head)
        self.assertEqual(head.count("pr:"), 1)
        with self.assertRaises(SystemExit):
            spry.link_slice(t.project(), "SL-1", {"pr": "next"})
        with self.assertRaisesRegex(SystemExit, "link S-1 --issue"):
            spry.link_slice(t.project(), "SL-1", {"issue": "7"})

    def test_covers_under_a_bug_says_what_to_do(self):
        bug = item("B-1").replace("state: ready", "state: ready")
        t = self.tree(**{f"{S}/bugs/B-1-x/README.md".replace("/", "__"): bug,
                         f"{S}/bugs/B-1-x/SL-1-a.md".replace("/", "__"): slice_("SL-1")})
        self.assertProblem(t.problems(), "B-1 is a bug, not a story — leave `covers: []`")



class Coverage(Base):
    PAGE = "---\ntitle: Coverage\naudience: 3\n---\n# Coverage\n\n<!-- spry:coverage -->\n<!-- /spry:coverage -->\n"

    def test_totals_when_everything_is_proven(self):
        out = spry.coverage_block(self.tree().project(), "spry/COVERAGE.md")
        self.assertIn("| Stories | 1 | 0 | 1 | 100% |", out)
        self.assertIn("| Acceptance criteria proven | 1 | — | 1 | 100% |", out)
        self.assertRegex(out, r"\n\[M-1 Title of M-1\]\([^)]*\) — done\.\n")
        self.assertNotIn("#### ", out)
        self.assertEqual(out.count("_None._"), 2)

    def test_built_but_not_proven_and_cited_only_in_a_comment(self):
        t = self.tree(**{f"{S}/README.md".replace("/", "__"): story("S-1", acs=("AC-1", "AC-2")),
                         "src__b.test.ts": "// S-1/AC-2 covered below\ntest('x', () => {})\n"})
        out = spry.coverage_block(t.project(), os.path.join(t.root, "spry/COVERAGE.md"))
        self.assertIn("| Acceptance criteria proven | 1 | — | 2 | 50% |", out)
        self.assertIn("| [S-1 Title of S-1](plan/M-1-m/E-1-e/F-1-f/S-1-s/README.md) | AC-2 |", out)
        self.assertIn("| [S-1/AC-2](plan/M-1-m/E-1-e/F-1-f/S-1-s/README.md) Title of S-1 | `src/b.test.ts:1` |", out)

    def test_an_open_slice_is_not_built_and_dropped_work_is_not_defined(self):
        t = self.tree(**{f"{S}/SL-1-a.md".replace("/", "__"): slice_("SL-1", state="open"),
                         "src__a.test.ts": "nothing\n",
                         f"{F}/S-2-x/README.md".replace("/", "__"): story("S-2", state="dropped")})
        out = spry.coverage_block(t.project(), os.path.join(t.root, "spry/COVERAGE.md"))
        self.assertIn("| Stories | 0 | 1 | 1 | 0% |", out)
        self.assertIn("| Slices closed | 0 | 1 | 1 | 0% |", out)
        self.assertIn("| Milestones | 0 | 1 | 1 | 0% |", out)
        self.assertIn("#### [M-1 Title of M-1](plan/M-1-m/README.md) — ", out)
        self.assertEqual(out.count("| Stories | 0 | 1 | 1 | 0% |"), 2, "the totals and the milestone's own table")
        self.assertEqual(out.count("| Milestones |"), 1, "a milestone's table starts one level down")
        self.assertIn("### Built, not proven", out)
        self.assertNotIn("| AC-1 |", out)

    def test_a_ready_slice_is_not_in_progress(self):
        t = self.tree(**{f"{S}/SL-1-a.md".replace("/", "__"): slice_("SL-1", state="ready"),
                         "src__a.test.ts": "nothing\n"})
        out = spry.coverage_block(t.project(), os.path.join(t.root, "spry/COVERAGE.md"))
        self.assertIn("| Stories | 0 | 0 | 1 | 0% |", out)
        self.assertIn("| Slices closed | 0 | 0 | 1 | 0% |", out)

    def test_index_fills_the_page(self):
        t = self.tree(**{"spry__COVERAGE.md": self.PAGE})
        self.assertIn("spry/COVERAGE.md", spry.index(t.project(), dry=False))
        with open(os.path.join(t.root, "spry/COVERAGE.md")) as handle:
            self.assertIn("[M-1 Title of M-1](plan/M-1-m/README.md)", handle.read())


def git_repo(root):
    def run(*args):
        subprocess.run(["git", *args], cwd=root, check=True, capture_output=True)
    run("init", "-q", "-b", "main")
    run("config", "user.email", "t@t")
    run("config", "user.name", "t")
    run("add", "-A")
    run("commit", "-qm", "init")
    return run


class Backlog(Base):
    PAGE = "---\ntitle: Backlog\naudience: 4\n---\n# Backlog\n\n<!-- spry:backlog -->\n<!-- /spry:backlog -->\n"
    B, T, S2 = f"{F}/bugs/B-1-b", f"{F}/tasks/T-1-t", f"{F}/S-2-x"

    def key(self, path):
        return path.replace("/", "__")

    def sections(self, t):
        items = spry.backlog(t.project())
        return {k: [i.id for i, _ in v] for k, v in items.items()}, items

    def test_plan_order_bugs_then_tasks_then_stories(self):
        t = self.tree(**{self.key(f"{S}/SL-1-a.md"): slice_("SL-1", state="planned"),
                         self.key(f"{self.B}/README.md"): item("B-1", check=False),
                         self.key(f"{self.B}/SL-3-c.md"): slice_("SL-3", state="planned", covers="[]"),
                         self.key(f"{self.T}/README.md"): item("T-1"),
                         self.key(f"{self.T}/SL-2-b.md"): slice_("SL-2", state="planned", covers="[]")})
        ids, _ = self.sections(t)
        self.assertEqual(ids["ready"], ["SL-3", "SL-2", "SL-1"])
        page = spry.backlog_block(t.project(), os.path.join(t.root, "spry/BACKLOG.md"))
        self.assertIn("| [M-1 Title of M-1](plan/M-1-m/README.md) › [E-1 Title of E-1](plan/M-1-m/E-1-e/README.md) › "
                      "[F-1 Title of F-1](plan/M-1-m/E-1-e/F-1-f/README.md) › [S-1 Title of S-1]", page)

    def test_an_owner_still_the_template_shows_as_unset(self):
        """CH-90: `owner: <name>` is no one — the backlog, a blocker and a holder never name `<name>`."""
        waits = slice_("SL-2", state="planned", covers="[]").replace("pr: 1\n", "pr: 1\nblocked_by: [SL-1]\n")
        t = self.tree(**{self.key(f"{S}/SL-1-a.md"): owned(slice_("SL-1", state="planned"), "<name>"),
                         self.key(f"{self.T}/README.md"): item("T-1"),
                         self.key(f"{self.T}/SL-2-b.md"): waits})
        page = spry.backlog_block(t.project(), os.path.join(t.root, "spry/BACKLOG.md"))
        self.assertNotIn("<name>", page)
        row = next(line for line in page.splitlines() if line.startswith("| 1 | [SL-1"))
        self.assertIn("| — |", row)
        self.assertIn("[SL-1 Slice SL-1](plan/M-1-m/E-1-e/F-1-f/S-1-s/SL-1-a.md) · ready to build |", page)
        held = owned(slice_("SL-1", state="open"), "<name>")
        self.assertEqual(spry.holder(self.tree(**{self.key(f"{S}/SL-1-a.md"): held}).project().items["SL-1"]), "open")

    def test_needs_slicing_names_criteria_no_slice_covers(self):
        t = self.tree(**{self.key(f"{S}/README.md"): story("S-1", acs=("AC-1", "AC-2")),
                         self.key(f"{S}/SL-1-a.md"): slice_("SL-1", state="planned"),
                         self.key(f"{self.S2}/README.md"): story("S-2")})
        _, items = self.sections(t)
        self.assertEqual([(i.id, need) for i, need in items["slicing"]], [("S-1", "AC-2"), ("S-2", "slices")])

    def test_blocked_names_what_it_waits_on(self):
        blocked = slice_("SL-1", state="planned").replace("pr: 1\n", "pr: 1\nblocked_by: [T-1]\n")
        t = self.tree(**{self.key(f"{S}/SL-1-a.md"): blocked, self.key(f"{self.T}/README.md"): item("T-1")})
        ids, items = self.sections(t)
        self.assertEqual(ids["blocked"], ["SL-1"])
        self.assertEqual([b.id for b in items["blocked"][0][1]], ["T-1"])
        self.assertEqual(ids["slicing"], ["T-1"])
        self.assertEqual(ids["ready"], [])

    def test_rows_say_what_they_unblock_and_where_a_blocker_stands(self):
        waits = slice_("SL-2", state="planned", covers="[]").replace("pr: 1\n", "pr: 1\nblocked_by: [SL-1]\n")
        t = self.tree(**{self.key(f"{S}/SL-1-a.md"): slice_("SL-1", state="planned"),
                         self.key(f"{self.T}/README.md"): item("T-1", extra="blocked_by: [S-1]\n"),
                         self.key(f"{self.T}/SL-2-b.md"): waits})
        page = spry.backlog_block(t.project(), os.path.join(t.root, "spry/BACKLOG.md"))
        ready = next(line for line in page.splitlines() if line.startswith("| 1 | [SL-1"))
        self.assertTrue(ready.endswith("| [SL-2 Slice SL-2](plan/M-1-m/E-1-e/F-1-f/tasks/T-1-t/SL-2-b.md), "
                                       "[T-1 Title of T-1](plan/M-1-m/E-1-e/F-1-f/tasks/T-1-t/README.md) |"), ready)
        self.assertIn("| [S-1 Title of S-1](plan/M-1-m/E-1-e/F-1-f/S-1-s/README.md) · ready to build (A); "
                      "[SL-1 Slice SL-1](plan/M-1-m/E-1-e/F-1-f/S-1-s/SL-1-a.md) · ready to build (A) | A |", page)

    def test_an_agent_reads_only_the_rows_it_needs(self):
        """CH-77: `backlog --section --rows --plain` — the sections named, a few rows, links as text."""
        waits = slice_("SL-2", state="planned", covers="[]").replace("pr: 1\n", "pr: 1\nblocked_by: [SL-1]\n")
        t = self.tree(**{self.key(f"{S}/SL-1-a.md"): slice_("SL-1", state="planned"),
                         self.key(f"{S}/SL-3-c.md"): slice_("SL-3", state="planned"),
                         self.key(f"{self.T}/README.md"): item("T-1", extra="blocked_by: [S-1]\n"),
                         self.key(f"{self.T}/SL-2-b.md"): waits})
        page = spry.backlog_block(t.project(), os.path.join(t.root, "spry/BACKLOG.md"))
        cut = spry.page_trim(page, ["ready"], 1, True)
        self.assertTrue(cut.startswith("### Ready to build"), cut)
        self.assertNotIn("### Blocked", cut)
        self.assertIn("| 1 | SL-1 Slice SL-1 |", cut)
        self.assertNotIn("| 2 |", cut)
        self.assertIn("… and 1 more", cut)
        self.assertNotIn("](plan/", cut)
        self.assertIn("](plan/", spry.page_trim(page, ["ready", "blocked"], None, False))
        self.assertIn("### Blocked", spry.page_trim(page, ["ready", "blocked"], None, False))
        self.assertEqual(spry.page_trim(page, ["nothing"]), "")

    def test_check_refuses_a_dropped_blocker(self):
        blocked = slice_("SL-1", state="planned").replace("pr: 1\n", "pr: 1\nblocked_by: [T-1]\n")
        t = self.tree(**{self.key(f"{S}/SL-1-a.md"): blocked, self.key(f"{self.T}/README.md"): item("T-1", state="dropped")})
        self.assertProblem(t.problems(), "`blocked_by` names T-1, which is dropped")

    def test_check_refuses_a_circle(self):
        def waits(ident, on):
            return slice_(ident, state="planned", covers="[]").replace("pr: 1\n", f"pr: 1\nblocked_by: [{on}]\n")
        t = self.tree(**{self.key(f"{self.T}/README.md"): item("T-1"),
                         self.key(f"{self.T}/SL-2-b.md"): waits("SL-2", "SL-3"),
                         self.key(f"{self.T}/SL-3-c.md"): waits("SL-3", "SL-2")})
        self.assertProblem(t.problems(), "goes in a circle, so none of it can start: SL-2 waits on SL-3, SL-3 waits on SL-2")
        t = self.tree(**{self.key(f"{S}/SL-1-a.md"): waits("SL-1", "F-1").replace("covers: []", "covers: [AC-1]")})
        self.assertProblem(t.problems(), "F-1 needs S-1, S-1 needs SL-1, SL-1 waits on F-1")

    def test_a_circle_is_reported_once_at_the_entry_that_makes_it(self):
        def waits(ident, on):
            return story(ident).replace("owner: A\n", f"owner: A\nblocked_by: [{on}]\n")
        t = self.tree(**{self.key(f"{S}/README.md"): waits("S-1", "S-2"),
                         self.key(f"{S}/SL-5-e.md"): slice_("SL-5", state="planned"),
                         self.key(f"{self.S2}/README.md"): waits("S-2", "S-1"),
                         self.key(f"{self.S2}/SL-2-b.md"): slice_("SL-2", state="planned")})
        circles = [p for p in t.problems() if "circle" in p]
        self.assertEqual(len(circles), 1, circles)
        self.assertNotIn("SL-1 waits on S-2,", circles[0])

    def test_a_bug_under_a_feature_may_wait_on_the_feature(self):
        # done(F-1) counts its stories, not its bugs: SL-3 starts once S-1 is done
        waits = slice_("SL-3", state="planned", covers="[]").replace("pr: 1\n", "pr: 1\nblocked_by: [F-1]\n")
        t = self.tree(**{self.key(f"{S}/SL-1-a.md"): slice_("SL-1", state="planned"),
                         self.key(f"{self.B}/README.md"): item("B-1", check=False),
                         self.key(f"{self.B}/SL-3-c.md"): waits})
        self.assertFalse([p for p in t.problems() if "circle" in p])

    def test_unblocks_skips_what_is_already_done_and_a_dropped_blocker_says_so(self):
        t = self.tree(**{self.key(f"{self.B}/README.md"): item("B-1", check=False),
                         self.key(f"{self.B}/SL-3-c.md"): slice_("SL-3", state="planned", covers="[]"),
                         "spry/plan/M-1-m/E-2-e/README.md": item("E-2", extra="blocked_by: [F-1]\n"),
                         self.key(f"{self.S2}/README.md"): story("S-2", state="dropped"),
                         self.key(f"{self.B}/SL-4-d.md"): slice_("SL-4", state="planned", covers="[]")
                         .replace("pr: 1\n", "pr: 1\nblocked_by: [S-2]\n")})
        page = spry.backlog_block(t.project(), os.path.join(t.root, "spry/BACKLOG.md"))
        ready = next(line for line in page.splitlines() if "| [SL-3" in line)
        self.assertTrue(ready.endswith("| — |"), ready)
        self.assertIn("· dropped (A)", page)

    def test_a_branch_named_for_a_planned_slice_is_in_progress(self):
        t = self.tree(**{self.key(f"{S}/SL-1-a.md"): slice_("SL-1", state="planned")})
        run = git_repo(t.root)
        run("branch", "sl-1-a")
        _, items = self.sections(t)
        self.assertEqual([(s.id, where) for s, where in items["progress"]], [("SL-1", "`sl-1-a` · PR #1")])
        self.assertEqual(items["ready"], [])

    def test_needs_planning_drafts_and_empty_items(self):
        t = self.tree(**{self.key(f"{E}/F-2-y/README.md"): item("F-2", state="draft", check=False),
                         self.key(f"{E}/F-3-z/README.md"): item("F-3"),
                         self.key(f"{E}/F-2-y/S-3-q/README.md"): story("S-3", state="draft", check=False)})
        _, items = self.sections(t)
        self.assertEqual([(i.id, need) for i, need in items["planning"]],
                         [("F-2", "finishing — it is a draft"), ("F-3", "stories")])

    def test_every_row_says_its_type_and_a_slice_takes_what_it_builds(self):
        blocked = slice_("SL-1", state="planned").replace("pr: 1\n", "pr: 1\nblocked_by: [T-1]\n")
        t = self.tree(**{self.key(f"{S}/SL-1-a.md"): blocked, self.key(f"{self.T}/README.md"): item("T-1"),
                         self.key(f"{self.B}/README.md"): item("B-1", check=False),
                         self.key(f"{self.B}/SL-3-c.md"): slice_("SL-3", state="planned", covers="[]"),
                         self.key(f"{E}/F-3-z/README.md"): item("F-3")})
        page = spry.backlog_block(t.project(), os.path.join(t.root, "spry/BACKLOG.md"))
        for ident, kind in (("SL-3 Slice SL-3", "bug"), ("SL-1 Slice SL-1", "story"), ("T-1 Title of T-1", "task"),
                            ("F-3 Title of F-3", "feature")):
            self.assertRegex(page, r"\| \[" + ident + r"\]\([^)]*\) \| " + kind + r" \|")
        self.assertIn("| # | Slice | Type | Part of |", page)
        self.assertIn("| # | Item | Type | Part of | Waiting on | Owner |\n|--:|", page)
        self.assertRegex(page, r"\| 1 \| \[SL-1 Slice SL-1\]")

    def test_index_fills_the_page(self):
        t = self.tree(**{"spry__BACKLOG.md": self.PAGE})
        self.assertIn("spry/BACKLOG.md", spry.index(t.project(), dry=False))
        with open(os.path.join(t.root, "spry/BACKLOG.md")) as handle:
            self.assertIn("### Ready to build", handle.read())


class Done(Base):
    PAGE = "---\ntitle: Done\naudience: 3\n---\n# Done\n\n<!-- spry:done -->\n<!-- /spry:done -->\n"
    T, B, S2 = f"{F}/tasks/T-1-t", f"{F}/bugs/B-1-b", f"{F}/S-2-x"

    def key(self, path):
        return path.replace("/", "__")

    def test_finished_newest_first_dated_by_the_last_slice(self):
        t = self.tree(**{self.key(f"{S}/SL-2-b.md"): slice_("SL-2", closed="2026-10-05"),
                         self.key(f"{self.T}/README.md"): item("T-1"),
                         self.key(f"{self.T}/SL-3-c.md"): slice_("SL-3", covers="[]", closed="2026-10-03"),
                         self.key(f"{self.B}/README.md"): item("B-1", check=False),
                         self.key(f"{self.B}/SL-4-d.md"): slice_("SL-4", covers="[]", closed=""),
                         self.key(f"{self.S2}/README.md"): story("S-2"),
                         self.key(f"{self.S2}/SL-5-e.md"): slice_("SL-5", state="planned")})
        self.assertEqual([(i.id, d) for i, d in spry.finished(t.project())],
                         [("S-1", "2026-10-05"), ("T-1", "2026-10-03"), ("B-1", "")])
        page = spry.done_block(t.project(), os.path.join(t.root, "spry/DONE.md"))
        self.assertIn("| 1 | [S-1 Title of S-1](plan/M-1-m/E-1-e/F-1-f/S-1-s/README.md) | story | "
                      "[M-1 Title of M-1](plan/M-1-m/README.md) › [E-1 Title of E-1](plan/M-1-m/E-1-e/README.md) › "
                      "[F-1 Title of F-1](plan/M-1-m/E-1-e/F-1-f/README.md) | 2026-10-05 |", page)
        self.assertTrue(page.splitlines()[-1].startswith("| 3 | [B-1") and page.endswith("| — |"), page)

    def test_nothing_done_and_what_is_dropped_stays_off(self):
        t = self.tree(**{"src__a.test.ts": None,
                         self.key(f"{self.T}/README.md"): item("T-1", state="dropped"),
                         self.key(f"{self.T}/SL-3-c.md"): slice_("SL-3", covers="[]")})
        self.assertEqual(spry.done_block(t.project(), os.path.join(t.root, "spry/DONE.md")), "_Nothing done yet._")

    def test_index_fills_the_page(self):
        t = self.tree(**{"spry__DONE.md": self.PAGE})
        self.assertIn("spry/DONE.md", spry.index(t.project(), dry=False))
        with open(os.path.join(t.root, "spry/DONE.md")) as handle:
            self.assertIn("| 2026-10-01 |", handle.read())

    def test_check_refuses_a_closed_that_is_not_a_date(self):
        t = self.tree(**{self.key(f"{S}/SL-1-a.md"): slice_("SL-1", closed="last week")})
        self.assertProblem(t.problems(), "`closed: last week` is not a date")

    def test_merge_check_blocks_without_a_closed_date(self):
        t = self.tree(**{self.key(f"{S}/SL-1-a.md"): slice_("SL-1", closed="")})
        lines = spry.merge_check(t.project(), "SL-1")
        self.assertIn(("block", "no `closed:` date — set it to the day the slice closed (YYYY-MM-DD)"), lines)


TEAM = {**CONFIG, "team": {"members": [{"name": "Asha", "github": "asha-k"}, {"name": "Ravi", "github": "ravi-dev"}]}}


def owned(text, owner):
    return text.replace("owner: A\n", f"owner: {owner}\n" if owner else "")


class Work(Base):
    """What one person built: their closed slices in a range, under the item each builds."""
    T, S2 = f"{F}/tasks/T-1-t", f"{F}/S-2-x"

    def key(self, path):
        return path.replace("/", "__")

    def team_tree(self, **changes):
        return self.tree(**{"spry__spry.config.json": json.dumps(TEAM), **changes})

    def test_groups_closed_slices_newest_first_with_what_others_did_and_what_is_open(self):
        t = self.team_tree(**{
            self.key(f"{S}/SL-1-a.md"): owned(slice_("SL-1", closed="2026-10-02"), "Ravi"),
            self.key(f"{S}/SL-2-b.md"): owned(slice_("SL-2", closed="2026-10-04"), "Asha"),
            self.key(f"{S}/SL-6-f.md"): owned(slice_("SL-6", closed="2026-10-05"), ""),
            self.key(f"{self.T}/README.md"): item("T-1"),
            self.key(f"{self.T}/SL-3-c.md"): owned(slice_("SL-3", covers="[]", closed="2026-10-09"), "ravi"),
            self.key(f"{self.T}/SL-4-d.md"): owned(slice_("SL-4", covers="[]", closed="2026-09-20"), "Ravi"),
            self.key(f"{self.T}/SL-5-e.md"): owned(slice_("SL-5", covers="[]", closed=""), "Ravi"),
            self.key(f"{self.S2}/README.md"): story("S-2"),
            self.key(f"{self.S2}/SL-7-g.md"): owned(slice_("SL-7", state="open"), "Ravi")})
        report = spry.work(t.project(), "ravi-dev", "2026-10-01", "2026-10-31")
        self.assertEqual(report["owner"], "Ravi")
        self.assertEqual([(i["id"], [s["id"] for s in i["slices"]]) for i in report["items"]],
                         [("T-1", ["SL-3"]), ("S-1", ["SL-1"])])
        self.assertEqual(report["items"][1]["others"], {"": 1, "Asha": 1})
        self.assertEqual(report["items"][1]["part_of"], ["M-1 Title of M-1", "E-1 Title of E-1", "F-1 Title of F-1"])
        self.assertEqual([(s["id"], s["state"]) for s in report["in_progress"]], [("SL-7", "open")])
        self.assertEqual((report["unowned"], report["undated"]), (["SL-6"], ["SL-5"]))
        text = spry.work_text(report)
        self.assertIn("# Work by Ravi · 2026-10-01 to 2026-10-31\n\n2 slices closed, under 2 items.", text)
        self.assertIn("## S-1 Title of S-1\n\nstory · ", text)
        self.assertIn("- SL-1 Slice SL-1 — closed 2026-10-02\n- also closed here: 1 with no owner, 1 by Asha", text)
        self.assertIn("## In progress now\n\n- SL-7 Slice SL-7 — open · S-2 Title of S-2", text)
        self.assertIn("1 slice closed in this range names no owner, so may be missing here: SL-6", text)
        self.assertIn("1 of Ravi's closed slices has no `closed:` date and is left out: SL-5", text)

    def test_work_under_a_dropped_story_still_counts_and_a_claim_is_in_progress(self):
        t = self.team_tree(**{
            self.key(f"{S}/README.md"): story("S-1").replace("state: ready", "state: dropped"),
            self.key(f"{S}/SL-1-a.md"): owned(slice_("SL-1", closed="2026-10-02"), "Ravi"),
            self.key(f"{S}/SL-2-b.md"): owned(slice_("SL-2", state="dropped"), "Ravi"),
            self.key(f"{S}/SL-3-c.md"): owned(slice_("SL-3", state="closed", closed="2026-10-03"), "asha-k"),
            self.key(f"{self.S2}/README.md"): story("S-2"),
            self.key(f"{self.S2}/SL-4-d.md"): owned(slice_("SL-4", state="planned"), "Ravi").replace(
                "pr: 1\n", "pr: 1\nbranch: sl-4-d\n")})
        report = spry.work(t.project(), "Ravi", "2026-10-01", "2026-10-31")
        self.assertEqual([[s["id"] for s in i["slices"]] for i in report["items"]], [["SL-1"]])
        self.assertEqual(report["items"][0]["others"], {"Asha": 1})
        self.assertEqual([(s["id"], s["state"]) for s in report["in_progress"]], [("SL-4", "claimed")])

    def test_nobody_by_that_name_and_dates_that_are_not_dates(self):
        t = self.tree()
        self.assertIn("No slice names Bob as its owner. Owners: A.",
                      spry.work_text(spry.work(t.project(), "Bob", "2026-10-01", "2026-10-31")))
        for since, until in (("last week", "2026-10-31"), ("2026-02-31", "2026-10-31"), ("2026-10-31", "2026-10-01")):
            with self.assertRaises(SystemExit):
                spry.work(t.project(), "A", since, until)

    def test_cli_prints_text_or_json(self):
        t = self.tree()
        for extra, expect in (([], "## S-1 Title of S-1"), (["--json"], '"owner": "A"')):
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                self.assertEqual(spry.main(["--root", t.root, "work", "A", "--since", "2026-10-01", *extra]), 0)
            self.assertIn(expect, out.getvalue())


def memory(name, kind, body, description="a fact"):
    return f"---\nname: {name}\ndescription: {description}\nmetadata:\n  type: {kind}\n---\n\n{body}\n"


class MemoryCheck(Base):
    """Claude Code's memory for a checkout: the index against the files, and the claims it can test."""

    def folder(self, files, index=None):
        path = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, path)
        for name, text in files.items():
            with open(os.path.join(path, name), "w") as handle:
                handle.write(text)
        lines = index if index is not None else [f"- [{n}]({n}) — hook" for n in files]
        with open(os.path.join(path, "MEMORY.md"), "w") as handle:
            handle.write("\n".join(lines) + "\n")
        return path

    def check(self, t, files, index=None, refs=None, today="2026-10-31", **given):
        with unittest.mock.patch.object(spry, "memory_refs", return_value=refs if refs is not None else {}):
            return spry.memory_check(spry.Project(t.root, load=False), self.folder(files, index),
                                     today=today, **given)

    def kinds(self, report, file=None):
        found = report["problems"] if file is None else next(m for m in report["memories"] if m["file"] == file)["findings"]
        return [(f["kind"], f["level"]) for f in found]

    def texts(self, report, file):
        return [f["text"] for f in next(m for m in report["memories"] if m["file"] == file)["findings"]]

    def test_index_against_the_files(self):
        t = self.tree(**{"spry__spry.config.json": json.dumps({**CONFIG, "memory": {"index_lines": 3, "line_chars": 60}})})
        why = "Use it.\n\n**Why:** it broke.\n\n**How to apply:** always."
        files = {"a.md": memory("a", "feedback", why), "b.md": memory("b", "project", "No reasons given."),
                 "c.md": memory("a", "habit", why), "lost.md": memory("lost", "user", "Nobody points here."),
                 "bare.md": "no front-matter\n"}
        index = ["# Memory", "", "- [A](a.md) — hook", "- [B](b.md) — a hook long enough to go past the sixty characters",
                 "- [A again](a.md) — hook", "- [Gone](gone.md) — hook", "a loose line", "- [C](c.md)",
                 "- [Bare](bare.md) — hook"]
        report = self.check(t, files, index)
        self.assertEqual(sorted(self.kinds(report)), sorted([
            ("over_budget", "warning"), ("twice", "warning"), ("dead_line", "error"), ("not_a_line", "warning"),
            ("long_line", "warning"), ("orphan", "error"), ("same_name", "error")]))
        problems = {f["kind"]: f for f in report["problems"]}
        self.assertEqual((problems["dead_line"]["line"], problems["twice"]["line"]), (6, 5))
        self.assertIn("b.md (", problems["long_line"]["text"])
        self.assertIn("lost.md is not in MEMORY.md", problems["orphan"]["text"])
        self.assertIn("a.md, c.md share the name `a`", problems["same_name"]["text"])
        self.assertEqual(self.kinds(report, "a.md"), [])
        self.assertEqual(self.kinds(report, "b.md"), [("why_missing", "warning")])
        self.assertEqual(self.kinds(report, "c.md"), [("front_matter", "error")])
        self.assertEqual(self.kinds(report, "bare.md"), [("front_matter", "error")])
        self.assertEqual(report["index"]["lines"], 9)

    def test_an_index_past_two_hundred_lines_is_cut_off(self):
        t = self.tree()
        files = {f"m{i}.md": memory(f"m{i}", "user", "x") for i in range(201)}
        self.assertIn(("cut_off", "error"), self.kinds(self.check(t, files)))

    def test_dates_gone_by_on_what_is_still_to_do(self):
        t = self.tree()
        body = ("Gate cadence: Chetan decides 10-17.\nReminder due 2026-11-04; nothing else.\n"
                "Release queued for 2026-10-20 - the rest is fine.\nShipped 2026-10-01, all done.\n"
                "**Why:** queued on 2026-09-01 and forgotten.\nSay it tomorrow.\n\n**How to apply:** ask.")
        report = self.check(t, {"a.md": memory("a", "project", body)},
                            ["- [Reminder overdue](a.md) — since week of 2026-09-11"])
        texts = self.texts(report, "a.md")
        self.assertEqual([x for x in texts if "has passed" in x], [
            "“since week of 2026-09-11” — 2026-09-11 has passed",
            "“Gate cadence: Chetan decides 10-17.” — 2026-10-17 has passed",
            "“Release queued for 2026-10-20” — 2026-10-20 has passed"])
        self.assertIn("says “tomorrow” (line 13) — with no day, nobody can tell when that was", texts)

    def test_days_that_do_not_exist_ranges_and_causes_are_not_dates_gone_by(self):
        t = self.tree()
        body = ("Reminder pending until 2026-02-31.\nRelease due 02-31.\nDue 0000-01-01 pending.\n"
                "Pending: rerun on 2-3 worktrees.\nThe merge failed due to the stale lock, 2026-10-01.\n"
                "Gate decides 01-05.")
        report = self.check(t, {"a.md": memory("a", "user", body)}, today="2026-12-20")
        self.assertEqual(self.texts(report, "a.md"), [])
        report = self.check(t, {"a.md": memory("a", "user", "Release due on 2026-10-02.")}, today="2026-12-20")
        self.assertEqual(self.texts(report, "a.md"), ["“Release due on 2026-10-02.” — 2026-10-02 has passed"])

    def test_index_paths_quoted_values_and_the_loaded_size(self):
        t = self.tree()
        text = '---\nname: a\ndescription: "says \\"hi\\""\nmetadata:\n  type: \'user\'\n---\n\nPlain.\n'
        report = self.check(t, {"a.md": text}, ["- [A](./a.md) — " + "x" * 26000])
        self.assertEqual(self.kinds(report), [("cut_off", "error"), ("over_budget", "warning"), ("long_line", "warning")])
        a = report["memories"][0]
        self.assertEqual((a["description"], a["type"], a["findings"]), ('says "hi"', "user", []))

    def test_items_paths_versions_and_commits_it_names(self):
        t = self.tree(**{"AGENTS.md": "# Rules\n\nNever merge a slice without running merge-check first, on its own branch.\n"})
        run = git_repo(t.root)
        # The full hash: a short one is all digits now and then, and a number is not taken for a commit.
        head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=t.root, capture_output=True,
                              text=True).stdout.strip()
        files = {
            "a.md": memory("a", "project", "Fix queued as SL-1. S-1 is the story; SL-99 and D-1 are gone.\n"
                           "See `src/a.test.ts`, `a.test.ts:3`, `src/gone.ts`, `src/` and `fix/`.\n"
                           f"spry 0.1.0 then, pushed {head} and deadbee1.\n\n**Why:** x\n\n**How to apply:** y"),
            "b.md": memory("b", "feedback", "Never merge a slice without running merge-check first, on its own "
                           "branch.\n\n**Why:** x\n\n**How to apply:** y"),
            "c.md": memory("c", "reference", "See [[a]] and [[later]]."),
        }
        with open(os.path.join(t.root, "spry", "spry.config.json"), "w") as handle:
            json.dump({**CONFIG, "spry": "0.34.0"}, handle)
        run("commit", "-qam", "version")
        report = self.check(t, files)
        a = next(m for m in report["memories"] if m["file"] == "a.md")
        self.assertEqual(a["ids"], {"SL-1": "closed", "S-1": "ready", "SL-99": "missing", "D-1": "missing"})
        self.assertEqual(a["commits"], {head: "main", "deadbee1": "missing"})
        texts = self.texts(report, "a.md")
        self.assertIn("SL-1 is closed, but “Fix queued as SL-1.” reads as still to do", texts)
        self.assertIn("names SL-99, D-1, not in this project's plan", texts)
        self.assertEqual([x for x in texts if x.startswith("names `")],
                         ["names `src/gone.ts`, which is not in this checkout"])
        self.assertIn("names 0.1.0; this project is on spry 0.34.0", texts)
        self.assertIn("names commit deadbee1, which this clone does not have — fetch, or it was rewritten", texts)
        self.assertIn("60% of it is already in AGENTS.md, which the repository keeps", self.texts(report, "b.md"))
        self.assertEqual(self.texts(report, "c.md"), ["links [[later]], which no memory has yet"])

    def test_overlapping_memories(self):
        t = self.tree()
        words = "falsify worktree database ports migration fixture runner seeds"
        report = self.check(t, {"a.md": memory("a", "user", words + " alpha"), "b.md": memory("b", "user", words + " beta")})
        self.assertEqual(self.kinds(report, "a.md"), [("overlap", "note")])
        self.assertEqual(self.kinds(report, "b.md"), [])

    def test_pull_requests_merged_under_a_line_that_waits_on_them(self):
        t = self.tree()
        refs = {12: {"kind": "pr", "state": "merged", "title": "x", "date": "2026-10-20"},
                13: {"kind": "issue", "state": "open", "title": "y", "date": ""}}
        report = self.check(t, {"a.md": memory("a", "user", "PR #12 awaiting merge. Issue 13 pending. #12 shipped.")},
                            refs=refs)
        self.assertEqual(report["gh"], "checked")
        self.assertEqual(self.texts(report, "a.md"),
                         ["#12 (pr) was merged 2026-10-20, but “PR #12 awaiting merge.” reads as still to do"])
        self.assertEqual(sorted(next(m for m in report["memories"])["refs"]), [12, 13])
        report = self.check(t, {"a.md": memory("a", "user", "PR #12 awaiting merge.")}, refs=None)
        with unittest.mock.patch.object(spry, "memory_refs", return_value=None):
            report = spry.memory_check(spry.Project(t.root, load=False), self.folder({"a.md": memory("a", "user", "#12")}))
        self.assertEqual(report["gh"], "unavailable")
        report = self.check(t, {"a.md": memory("a", "user", "#12 pending")}, offline=True)
        self.assertEqual((report["gh"], self.texts(report, "a.md")), ("offline", []))

    def test_the_folder_is_the_main_checkouts_in_every_worktree(self):
        t = self.tree()
        run = git_repo(t.root)
        home = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, home)
        tree = os.path.join(t.root, ".claude", "worktrees", "one")
        run("worktree", "add", "-q", tree, "-b", "one")
        slug = re.sub(r"[^A-Za-z0-9]", "-", os.path.realpath(t.root))
        with unittest.mock.patch.dict(os.environ, {"CLAUDE_CONFIG_DIR": home}):
            expected = os.path.join(home, "projects", slug, "memory")
            self.assertEqual(spry.memory_dir(spry.Project(tree, load=False)), expected)
            os.makedirs(expected)
            self.assertEqual(spry.memory_dir(spry.Project(t.root, load=False)), expected)
            self.assertEqual(spry.memory_dir(spry.Project(tree, load=False), "~/elsewhere"),
                             os.path.join(os.path.expanduser("~"), "elsewhere"))
            os.makedirs(os.path.join(tree, ".claude"), exist_ok=True)
            with open(os.path.join(tree, ".claude", "settings.local.json"), "w") as handle:
                json.dump({"autoMemoryDirectory": "notes/memory"}, handle)
            self.assertEqual(spry.memory_dir(spry.Project(tree, load=False)), os.path.join(tree, "notes", "memory"))

    def test_cli_prints_text_or_json_and_says_when_there_is_no_memory(self):
        t = self.tree()
        folder = self.folder({"a.md": memory("a", "user", "Plain.")})
        for extra, expect in (([], "1 memories: 0 with findings, 1 without"), (["--json"], '"file": "a.md"'),
                              (["--dir", os.path.join(folder, "none")], "no memory at ")):
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                self.assertEqual(spry.main(["--root", t.root, "memory-check", "--offline", "--dir", folder, *extra]), 0)
            self.assertIn(expect, out.getvalue())


class Owner(Base):
    """A slice's owner is who built it: set at open, required at merge, filled once from PRs for old slices."""

    def key(self, path):
        return path.replace("/", "__")

    def head(self, t, name="SL-1-a.md"):
        with open(os.path.join(t.root, S, name)) as handle:
            return handle.read().split("\n---\n")[0]

    def test_link_takes_a_member_by_name_or_login_and_refuses_anyone_else(self):
        t = self.tree(**{"spry__spry.config.json": json.dumps(TEAM),
                         self.key(f"{S}/SL-1-a.md"): owned(slice_("SL-1", state="open"), "")})
        with contextlib.redirect_stdout(io.StringIO()):
            spry.main(["--root", t.root, "link", "SL-1", "--owner", "RAVI-DEV"])
        self.assertIn("owner: Ravi", self.head(t))
        with self.assertRaises(SystemExit) as caught:
            spry.main(["--root", t.root, "link", "SL-1", "--owner", "Bob"])
        self.assertIn("Bob is not in team.members — one of: Asha, Ravi", str(caught.exception.code))

    def test_bare_owner_is_the_person_git_names_here(self):
        t = self.tree(**{"spry__spry.config.json": json.dumps(TEAM),
                         self.key(f"{S}/SL-1-a.md"): owned(slice_("SL-1", state="open"), "")})
        run = git_repo(t.root)
        run("config", "user.name", "Someone Else")
        run("config", "user.email", "asha-k@example.com")
        with contextlib.redirect_stdout(io.StringIO()):
            spry.main(["--root", t.root, "link", "SL-1", "--owner"])
        self.assertIn("owner: Asha", self.head(t))
        run("config", "user.email", "x@example.com")
        with self.assertRaises(SystemExit) as caught:
            spry.main(["--root", t.root, "link", "SL-1", "--owner"])
        self.assertIn("match no one in team.members", str(caught.exception.code))
        solo = self.tree(**{self.key(f"{S}/SL-1-a.md"): owned(slice_("SL-1", state="open"), "")})
        git_repo(solo.root)("config", "user.name", "Chetan")
        self.assertEqual(spry.whoami(solo.project()), "Chetan")

    def test_check_warns_on_an_open_slice_and_merge_check_blocks_a_closed_one_without_an_owner(self):
        t = self.tree(**{self.key(f"{S}/SL-1-a.md"): owned(slice_("SL-1", state="open"), "<name>")})
        warnings = [str(p) for p in spry.check(t.project()) if p.level == "warning"]
        self.assertProblem(warnings, "open without an `owner:`")
        t = self.tree(**{self.key(f"{S}/SL-1-a.md"): owned(slice_("SL-1"), "")})
        self.assertIn(("block", "no `owner:` — who built it: `link SL-1 --owner`"), spry.merge_check(t.project(), "SL-1"))
        self.assertIn(("ok", "built by A"), spry.merge_check(self.tree().project(), "SL-1"))

    def test_fill_owners_from_pull_requests(self):
        def pr(number, login, name=""):
            return {"number": number, "author": {"login": login, "name": name}}

        def slice_with(ident, owner, pr_number, state="closed"):
            return owned(slice_(ident, state=state), owner).replace("pr: 1\n", f"pr: {pr_number}\n")

        files = {"spry__spry.config.json": json.dumps(TEAM),
                 self.key(f"{S}/SL-1-a.md"): slice_with("SL-1", "", 11),
                 self.key(f"{S}/SL-2-b.md"): slice_with("SL-2", "<name>", 12, state="open"),
                 self.key(f"{S}/SL-3-c.md"): slice_with("SL-3", "Asha", 13),
                 self.key(f"{S}/SL-4-d.md"): slice_with("SL-4", "", 14),
                 self.key(f"{S}/SL-5-e.md"): slice_with("SL-5", "", "<number, once opened>"),
                 self.key(f"{S}/SL-6-f.md"): slice_with("SL-6", "", 16, state="planned")}
        prs = [pr(11, "ravi-dev"), pr(12, "Asha-K"), pr(13, "ravi-dev"), pr(14, "stranger"), pr(16, "ravi-dev")]
        t = self.tree(**files)
        said = spry.fill_owners(t.project(), prs, dry=True)
        self.assertEqual(said, {"filled": ["SL-1: Ravi", "SL-2: Asha"], "replaced": [],
                                "differs": ["SL-3: Asha, PR #13 by Ravi"], "unknown": ["SL-4 (PR #14 by stranger)"],
                                "no_pr": ["SL-5"]})
        self.assertNotIn("owner: Ravi", self.head(t))
        said = spry.fill_owners(t.project(), prs, replace=True)
        self.assertEqual(said["replaced"], ["SL-3: Ravi (was Asha)"])
        self.assertIn("owner: Ravi", self.head(t))
        self.assertIn("owner: Asha", self.head(t, "SL-2-b.md"))
        self.assertIn("owner: Ravi", self.head(t, "SL-3-c.md"))
        self.assertNotIn("owner:", self.head(t, "SL-6-f.md"))
        self.assertEqual(spry.fill_owners(t.project(), prs)["filled"], [])
        solo = self.tree(**{self.key(f"{S}/SL-1-a.md"): slice_with("SL-1", "", 11)})
        spry.fill_owners(solo.project(), [pr(11, "chetan", "Chetan Verma")])
        self.assertIn("owner: Chetan Verma", self.head(solo))


class Branch(Base):
    """Generated blocks on a branch: only the main branch gets them."""

    def setUp(self):
        self.t = self.tree(**{"spry__BACKLOG.md": Backlog.PAGE})
        spry.index(self.t.project(), dry=False)
        self.run_git = git_repo(self.t.root)
        self.run_git("switch", "-qc", "sl-9-x")
        self.feature = os.path.join(self.t.root, F, "README.md")

    def drift(self):
        return [(os.path.basename(p), name) for p, name, _, _ in spry.block_drift(self.t.project(), "main")]

    def test_a_block_the_branch_changed_is_refused_and_restored(self):
        with open(self.feature) as handle:
            text = handle.read()
        with open(self.feature, "w") as handle:
            handle.write(text.replace("| ready |", "| draft |") + "\nWritten on the branch.\n")
        self.assertEqual(self.drift(), [("README.md", "children")])
        project = self.t.project()
        spry.changed_blocks(project, "main")
        self.assertTrue(any("`spry:children` block differs from main" in str(p) for p in project.problems))
        self.assertEqual(spry.restore_blocks(self.t.project(), "main"), [f"{F}/README.md"])
        with open(self.feature) as handle:
            self.assertEqual(handle.read(), text + "\nWritten on the branch.\n")

    def test_main_branch_merged_in_is_not_drift(self):
        self.run_git("switch", "-q", "main")
        with open(self.feature) as handle:
            text = handle.read()
        with open(self.feature, "w") as handle:
            handle.write(text.replace("| ready |", "| draft |"))
        self.run_git("commit", "-qam", "chore(spry): refresh progress")
        self.run_git("switch", "-q", "sl-9-x")
        self.run_git("merge", "-q", "main")
        self.run_git("switch", "-q", "main")
        with open(self.feature, "w") as handle:
            handle.write(text.replace("| ready |", "| dropped |"))
        self.run_git("commit", "-qam", "chore(spry): refresh progress again")
        self.run_git("switch", "-q", "sl-9-x")
        self.assertEqual(self.drift(), [])

    def test_view_writes_both_pages_and_skips_when_nothing_relevant_changed(self):
        written = spry.view(self.t.project())
        self.assertEqual(written, [".spry/view/BACKLOG.md", ".spry/view/COVERAGE.md", ".spry/view/DONE.md"])
        with open(os.path.join(self.t.root, ".spry/view/COVERAGE.md")) as handle:
            text = handle.read()
        self.assertIn("by `spry view`. Not committed.", text)
        self.assertIn("(../../spry/plan/M-1-m/README.md)", text)
        with open(os.path.join(self.t.root, "notes.txt"), "w") as handle:
            handle.write("x")
        self.run_git("add", "-A")
        self.run_git("commit", "-qm", "notes")
        self.assertEqual(spry.view(self.t.project(), since="HEAD~1"), [])
        self.assertEqual(len(spry.view(self.t.project(), since="HEAD~1~1~1")), 3)

    def test_hooks_install_keep_others_and_remove(self):
        os.makedirs(os.path.join(self.t.root, "spry", "tool"))
        shutil.copy(spry.__file__, os.path.join(self.t.root, "spry", "tool", "spry.py"))
        hooks = os.path.join(self.t.root, ".git", "hooks")
        with open(os.path.join(hooks, "post-merge"), "w") as handle:
            handle.write("#!/bin/sh\necho mine\n")
        out = spry.hooks(self.t.project())
        self.assertEqual(out[0], "wrote: post-checkout")
        self.assertTrue(out[1].startswith("kept: post-merge is not spry's"))
        with open(os.path.join(hooks, "post-checkout")) as handle:
            self.assertIn("view --since \"$since\"", handle.read())
        self.run_git("switch", "-q", "main")
        self.assertTrue(os.path.isfile(os.path.join(self.t.root, ".spry/view/BACKLOG.md")))
        self.assertEqual(spry.hooks(self.t.project(), remove=True), ["removed: post-checkout"])
        self.assertTrue(os.path.isfile(os.path.join(hooks, "post-merge")))


class History(Base):
    KEPT = "> writ slice summary, as written.\n\n# Slice SL-WD2 — summary\n\nA patron can rotate [x](nope.md) the signing secret.\n"

    def test_check_skips_kept_history(self):
        t = self.tree(**{"spry__history__writ__slices__SL-WD2.md": self.KEPT})
        self.assertEqual(t.problems(), [])

    def test_find_lists_history_after_current_documents(self):
        t = self.tree(**{"spry__history__writ__slices__SL-WD2.md": self.KEPT,
                         "spry__knowledge__secrets.md": "---\ntitle: Secrets\nsummary: s\naudience: 6\n---\n# Secrets\n\n## Rotate\n\nRotate the signing secret.\n"})
        hits = spry.find(t.project(), "signing secret")
        self.assertEqual(hits[0][0], "spry/knowledge/secrets.md")
        self.assertEqual(hits[-1][0], "spry/history/writ/slices/SL-WD2.md")
        self.assertTrue(hits[-1][2].startswith("history · "))


class Related(Base):
    def test_open_slice_on_same_files(self):
        t = self.tree(**{
            f"{S}/SL-1-a.md".replace("/", "__"): slice_("SL-1", state="open", plan="- `src/loans/lend.ts` — x\n"),
            f"{S}/SL-2-b.md".replace("/", "__"): slice_("SL-2", state="planned", plan="- `src/loans/lend.ts` — y\n"),
        })
        out = spry.related(t.project(), os.path.join(t.root, S, "SL-2-b.md"))
        self.assertIn("SL-1 Slice SL-1", out)
        self.assertIn("same files: src/loans/lend.ts", out)
        self.assertIn("## Parents\n- S-1", out)


class Next(Base):
    def test_a_folder_that_failed_to_load_keeps_its_number(self):
        t = self.tree(**{f"{F}/S-7-broken/notes.txt".replace("/", "__"): "x"})
        self.assertEqual(spry.next_id(t.project(), "story"), "S-8")

    def test_next(self):
        p = self.tree().project()
        self.assertEqual(spry.next_id(p, "story"), "S-2")
        self.assertEqual(spry.next_id(p, "bug"), "B-1")


class New(Base):
    def tree_with_process(self):
        t = self.tree()
        shutil.copytree(os.path.join(REPO, "plugins", "spry", "process"), os.path.join(t.root, "spry", "process"))
        return t

    def test_creates_each_type_in_its_place(self):
        t = self.tree_with_process()
        made = {
            "story": spry.new_item(t.project(), "story", "F-1", "Refuse at the limit", "Asha"),
            "slice": spry.new_item(t.project(), "slice", "S-1", "Second slice"),
            "task": spry.new_item(t.project(), "task", "M-1", "Set up CI"),
            "bug": spry.new_item(t.project(), "bug", "F-1", "Wrong date"),
            "decision": spry.new_item(t.project(), "decision", None, "Keep it", today="2026-10-08"),
        }
        rel = {k: os.path.relpath(v, t.root) for k, v in made.items()}
        self.assertEqual(rel["story"], f"{F}/S-2-refuse-at-the-limit/README.md")
        self.assertEqual(rel["slice"], f"{S}/SL-2-second-slice.md")
        self.assertEqual(rel["task"], f"{M}/tasks/T-1-set-up-ci/README.md")
        self.assertEqual(rel["bug"], f"{F}/bugs/B-1-wrong-date/README.md")
        self.assertEqual(rel["decision"], "spry/knowledge/decisions/D-1-keep-it.md")
        with open(made["story"]) as handle:
            text = handle.read()
        self.assertIn("id: S-2\ntitle: Refuse at the limit\nstate: draft\nowner: Asha", text)
        self.assertIn("# S-2 · Refuse at the limit", text)
        self.assertEqual(t.problems(), [], "a fresh draft and a planned slice pass check")

    def test_documents_without_ids(self):
        t = self.tree_with_process()
        p = t.project()
        checks = spry.new_item(p, "checks", "S-1", "x")
        self.assertEqual(os.path.relpath(checks, t.root), f"{S}/checks.md")
        with open(checks) as handle:
            self.assertIn("# Checks · S-1 · Title of S-1", handle.read())
        conv = spry.new_item(p, "convention", None, "Domain code")
        self.assertEqual(os.path.relpath(conv, t.root), "spry/knowledge/conventions/domain-code.md")
        self.assertTrue(os.path.isfile(os.path.join(t.root, "spry/knowledge/conventions/INDEX.md")))
        ext = spry.new_item(p, "external", None, "Lookups are rate-limited", dependency="Open Library", today="2026-10-08")
        self.assertEqual(os.path.relpath(ext, t.root), "spry/knowledge/external/open-library/lookups-are-rate.md")
        with open(ext) as handle:
            text = handle.read()
        self.assertIn("dependency: Open Library", text)
        self.assertIn("observed: 2026-10-08", text)
        with open(os.path.join(t.root, "spry/knowledge/external/open-library/INDEX.md")) as handle:
            self.assertIn("# Open Library", handle.read())
        audit = spry.new_item(p, "audit", None, "Security audit — M-1", today="2026-10-08")
        self.assertEqual(os.path.relpath(audit, t.root), "spry/knowledge/audits/2026-10-08-security-audit-m-1.md")
        with self.assertRaises(SystemExit):
            spry.new_item(p, "external", None, "x")
        with self.assertRaises(SystemExit):
            spry.new_item(p, "checks", "F-1", "x")

    def test_scenario_for_a_missing_criterion(self):
        checks = ("---\ntitle: c\naudience: 4\n---\n# c\n\n## Scenarios\n\n### AC-1 · fine\n\n### AC-5 · gone\n\n"
                  "### AC-1, AC-6 · second named\n")
        t = self.tree(**{f"{S}/checks.md".replace("/", "__"): checks})
        problems = t.problems()
        self.assertTrue(any("scenario for AC-5" in p for p in problems), problems)
        self.assertTrue(any("scenario for AC-6" in p for p in problems), "every AC a heading names is checked")
        self.assertFalse(any("AC-1" in p for p in problems), problems)

    def test_refuses_wrong_parent(self):
        t = self.tree_with_process()
        with self.assertRaises(SystemExit):
            spry.new_item(t.project(), "story", "M-1", "x")
        with self.assertRaises(SystemExit):
            spry.new_item(t.project(), "slice", "F-1", "x")

    def test_slug(self):
        self.assertEqual(spry.slugify("Lend a book — at the Desk!"), "lend-a-book-at-the")
        self.assertLessEqual(len(spry.slugify("word " * 30)), 20)


class PrBody(Base):
    def test_work_order_without_guides(self):
        text = slice_("SL-1").replace("### Plan\n", "### Plan\n\n<!-- guide: one bullet per file -->\n- `a.ts` — x\n")
        t = self.tree(**{f"{S}/SL-1-a.md".replace("/", "__"): text})
        body = spry.pr_body(t.project(), "SL-1")
        self.assertTrue(body.startswith("**SL-1 Slice SL-1** · S-1 Title of S-1"))
        self.assertIn("## Work order", body)
        self.assertIn("- `a.ts` — x", body)
        self.assertNotIn("guide", body)


    def test_reviewer_page_comes_first(self):
        text = slice_("SL-1").replace("### Plan", "### Plan\n\n- x\n\n## Close summary\n\n### Falsify\n\n"
                                      "| Control | Mutation | Expect | Result |\n|---|---|---|---|\n"
                                      "| g | m | S-1/AC-1 | caught |\n| h | m | S-1/AC-1 | survived — logged only |\n\n### Plan2")
        t = self.tree(**{f"{S}/SL-1-a.md".replace("/", "__"): text})
        body = spry.pr_body(t.project(), "SL-1")
        self.assertLess(body.index("## For the reviewer"), body.index("## Work order"))
        self.assertIn("- `S-1/AC-1` — x · y · z — 1 test", body)
        self.assertIn("- **Falsify:** 1 of 2 caught\n  - `h` — survived — logged only", body)

class Vendor(unittest.TestCase):
    def test_copies_process_and_tool_and_refuses_to_overwrite(self):
        root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, root)
        spry.vendor(root)
        self.assertTrue(os.path.isfile(os.path.join(root, "spry", "process", "templates", "story.md")))
        self.assertTrue(os.path.isfile(os.path.join(root, "spry", "tool", "spry.py")))
        with self.assertRaises(SystemExit):
            spry.vendor(root)
        spry.vendor(root, force=True)


class VendorDiff(unittest.TestCase):
    def test_lists_changed_new_and_local_files(self):
        root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, root)
        spry.vendor(root)
        self.assertEqual(spry.vendor_diff(root), [])
        with open(os.path.join(root, "spry", "process", "chat.md"), "a") as handle:
            handle.write("\n- a local rule\n")
        os.remove(os.path.join(root, "spry", "process", "writing.md"))
        with open(os.path.join(root, "spry", "process", "ours.md"), "w") as handle:
            handle.write("x")
        self.assertEqual(spry.vendor_diff(root), ["changed: process/chat.md", "new in spry: process/writing.md",
                                                  "only in project: process/ours.md"])


class Scrub(Base):
    def test_finds_private_words(self):
        config = dict(CONFIG, product="Shelf", team={"members": [{"name": "Asha", "github": "asha-k"}]})
        t = self.tree(**{"spry__spry.config.json": json.dumps(config)})
        path = os.path.join(t.root, "issue.md")
        with open(path, "w") as handle:
            handle.write("Shelf lets a patron borrow.\nAsk asha-k at a@b.io\nA member is generic now.\nClean line.\n")
        hits = spry.scrub(t.project(), path)
        found = {w.split(" ")[0] for _, w in hits}
        self.assertEqual(found, {"Shelf", "patron", "asha-k", "a@b.io", "member"})
        self.assertNotIn(4, [n for n, _ in hits])


class Draw(unittest.TestCase):
    """A walk is replayable only if (seed, counter) alone decides every choice."""

    CHOICES = [f"operator {i}" for i in range(14)]

    def test_same_seed_and_counter_same_choice(self):
        self.assertEqual(spry.draw("abc", "3", self.CHOICES, "pick"), spry.draw("abc", "3", self.CHOICES, "pick"))

    def test_counter_changes_the_choice(self):
        picks = {spry.draw("abc", str(n), self.CHOICES, "pick")[0] for n in range(30)}
        self.assertGreater(len(picks), 5)

    def test_sample_is_distinct_and_shuffle_is_a_permutation(self):
        sample = spry.draw("abc", "1", self.CHOICES, "sample", 5)
        self.assertEqual(len(set(sample)), 5)
        self.assertEqual(sorted(spry.draw("abc", "1", self.CHOICES, "shuffle")), sorted(self.CHOICES))

    def test_int_in_range(self):
        self.assertTrue(all(0 <= int(spry.draw("s", str(n), [], "int", 6)[0]) < 6 for n in range(50)))

    def test_cli_needs_no_project(self):
        out = subprocess.run([sys.executable, spry.__file__, "draw", "abc", "3", "--pick"], input="a\nb\nc\n",
                             capture_output=True, text=True, cwd=tempfile.gettempdir())
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertEqual(out.stdout.strip(), spry.draw("abc", "3", ["a", "b", "c"], "pick")[0])


class Shared(unittest.TestCase):
    """`mint: main` — two clones of one remote: IDs taken and slices claimed on the remote main branch."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.remote = os.path.join(self.tmp, "remote.git")
        subprocess.run(["git", "init", "-q", "--bare", "-b", "main", self.remote], check=True)
        files = base()
        files["spry/spry.config.json"] = json.dumps({**CONFIG, "mint": "main"})
        files[f"{S}/SL-2-b.md"] = slice_("SL-2", state="planned", check=False)
        seed = Tree(files).root
        self.addCleanup(shutil.rmtree, seed, True)
        shutil.copytree(os.path.join(REPO, "plugins", "spry", "process"), os.path.join(seed, "spry", "process"))
        run = git_repo(seed)
        run("push", "-q", self.remote, "main")
        self.a, self.b = self.clone("a"), self.clone("b")

    def clone(self, name):
        root = os.path.join(self.tmp, name)
        subprocess.run(["git", "clone", "-q", self.remote, root], check=True)
        for key, value in (("user.email", "t@t"), ("user.name", name)):
            self.git(root, "config", key, value)
        return root

    def git(self, root, *args):
        return subprocess.run(["git", *args], cwd=root, check=True, capture_output=True, text=True).stdout.strip()

    def remote_head(self):
        return self.git(self.remote, "rev-parse", "main")

    def worktrees(self, root):
        return len(self.git(root, "worktree", "list").splitlines())

    def refused(self, call):
        with self.assertRaises(SystemExit) as caught, contextlib.redirect_stderr(io.StringIO()):
            call()
        return str(caught.exception.code)

    def test_two_sessions_at_once_get_different_numbers_with_one_retry(self):
        self.git(self.a, "switch", "-qc", "sl-7-a")
        self.git(self.b, "switch", "-qc", "sl-8-b")
        real, raced, made = spry.git, [], {}

        def git(root, *args, **kw):
            if "push" in args and not raced:
                raced.append(True)  # b takes a number between a's commit and a's push
                made["b"] = spry.mint(spry.Project(self.b), "task", "M-1", "Second")
            return real(root, *args, **kw)

        spry.git = git
        self.addCleanup(setattr, spry, "git", real)
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            made["a"] = spry.mint(spry.Project(self.a), "task", "M-1", "First")
        self.assertIn("trying again (1/5)", err.getvalue())
        self.assertEqual(err.getvalue().count("trying again"), 1)
        self.assertEqual((os.path.basename(os.path.dirname(made["b"])), os.path.basename(os.path.dirname(made["a"]))),
                         ("T-1-second", "T-2-first"))
        self.assertEqual((self.worktrees(self.a), self.worktrees(self.b)), (1, 1))
        for root, path in ((self.a, made["a"]), (self.b, made["b"])):
            with open(path, "a") as handle:
                handle.write("\nFilled in on the branch.\n")
            self.git(root, "commit", "-qam", "fill")
        self.git(self.b, "push", "-q", "origin", "sl-8-b")
        self.git(self.a, "fetch", "-q")
        self.git(self.a, "switch", "-q", "main")
        self.git(self.a, "merge", "-q", "--ff-only", "origin/main")
        self.git(self.a, "merge", "-q", "--no-edit", "sl-7-a")
        self.git(self.a, "merge", "-q", "--no-edit", "origin/sl-8-b")
        self.assertEqual([str(p) for p in spry.check(spry.Project(self.a)) if p.level == "error"], [])

    def test_real_processes_at_once_in_two_worktrees_of_one_clone(self):
        tool = os.path.join(REPO, "plugins", "spry", "tool", "spry.py")
        made = []
        for round_ in range(3):
            roots = [os.path.join(self.tmp, f"w{round_}{n}") for n in "xy"]
            for n, root in enumerate(roots):
                self.git(self.a, "worktree", "add", "-q", "-b", f"sl-{round_}{n}-w", root, "origin/main")
            procs = [subprocess.Popen([sys.executable, tool, "--root", root, "new", "task", "--parent", "M-1",
                                       "--title", os.path.basename(root)], stdout=subprocess.PIPE,
                                      stderr=subprocess.PIPE, text=True) for root in roots]
            for proc in procs:
                out, err = proc.communicate(timeout=120)
                self.assertEqual(proc.returncode, 0, err)
                made.append(out.strip().split("/tasks/")[1].split("-")[1])
            self.git(self.a, "fetch", "-q")
        self.assertEqual(sorted(made, key=int), [str(n) for n in range(1, 7)])
        self.assertEqual(self.worktrees(self.a), 7)

    def test_staged_files_or_a_main_branch_ahead_refuse_before_pushing(self):
        head = self.remote_head()
        with open(os.path.join(self.a, "notes.txt"), "w") as handle:
            handle.write("x")
        self.git(self.a, "add", "notes.txt")
        self.assertIn("files are staged", self.refused(lambda: spry.mint(spry.Project(self.a), "task", "M-1", "X")))
        self.git(self.a, "commit", "-qm", "local only")
        self.assertIn("your `main` has commits", self.refused(lambda: spry.mint(spry.Project(self.a), "task", "M-1", "X")))
        self.assertEqual((self.remote_head(), self.worktrees(self.a)), (head, 1))

    def test_on_the_main_branch_the_new_item_arrives_fast_forward(self):
        path = spry.mint(spry.Project(self.a), "bug", "F-1", "Wrong date")
        self.assertTrue(os.path.isfile(path))
        self.assertEqual(self.git(self.a, "rev-parse", "HEAD"), self.remote_head())
        self.assertEqual(self.git(self.a, "log", "-1", "--format=%s"), "docs(plan): new B-1 Wrong date")

    def test_offline_or_refused_writes_nothing(self):
        head, before = self.remote_head(), self.git(self.a, "status", "--porcelain")
        self.git(self.a, "remote", "set-url", "origin", os.path.join(self.tmp, "nowhere.git"))
        self.assertIn("cannot fetch `main` from origin", self.refused(lambda: spry.mint(spry.Project(self.a), "task", "M-1", "X")))
        self.git(self.a, "remote", "set-url", "origin", self.remote)
        hook = os.path.join(self.remote, "hooks", "pre-receive")
        with open(hook, "w") as handle:
            handle.write("#!/bin/sh\necho protected >&2\nexit 1\n")
        os.chmod(hook, 0o755)
        self.assertIn("origin refused the push to `main`", self.refused(lambda: spry.mint(spry.Project(self.a), "task", "M-1", "X")))
        self.assertEqual((self.remote_head(), self.git(self.a, "status", "--porcelain")), (head, before))
        self.assertFalse(os.path.exists(os.path.join(self.a, M, "tasks")))
        self.assertEqual(self.worktrees(self.a), 1)

    def test_a_parent_not_yet_on_the_main_branch_is_refused(self):
        self.assertIn("F-9 is not on origin/main yet", self.refused(lambda: spry.mint(spry.Project(self.a), "story", "F-9", "X")))
        self.assertEqual(self.worktrees(self.a), 1)

    def test_a_second_claim_is_refused_naming_the_branch_and_release_frees_it(self):
        self.assertEqual(spry.claim(spry.Project(self.a), "SL-2", owner="Asha"), "sl-2-b")
        self.assertEqual(self.git(self.a, "branch", "--show-current"), "sl-2-b")
        self.assertEqual(self.git(self.a, "rev-parse", "HEAD"), self.remote_head())
        said = self.refused(lambda: spry.claim(spry.Project(self.b), "SL-2"))
        self.assertIn("SL-2 is taken: claimed on `sl-2-b` by Asha", said)
        self.assertEqual(self.git(self.b, "branch", "--show-current"), "main")
        self.git(self.b, "pull", "-q", "--ff-only")
        project = spry.Project(self.b)
        self.assertEqual([s.id for s, _ in spry.backlog(project)["progress"]], ["SL-2"])
        self.assertEqual(spry.release(project, "SL-2"), "sl-2-b")
        self.assertEqual(spry.claim(spry.Project(self.b), "SL-2", switch=False), "sl-2-b")
        self.assertEqual(self.git(self.b, "branch", "--show-current"), "main")

    def test_a_bare_claim_names_its_owner_or_writes_nothing(self):
        """CH-90: a claim on the main branch always names who holds it."""
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            spry.main(["--root", self.a, "claim", "SL-2", "--no-switch"])
        self.assertEqual(out.getvalue().strip(), "SL-2 claimed by a on main; branch `sl-2-b`")
        self.assertIn("owner: a\n", self.git(self.remote, "show", f"main:{S}/SL-2-b.md"))
        self.git(self.b, "pull", "-q", "--ff-only")
        spry.release(spry.Project(self.b), "SL-2")
        self.git(self.b, "branch", "-D", "sl-2-b") if self.git(self.b, "branch", "--list", "sl-2-b") else None
        self.git(self.a, "branch", "-D", "sl-2-b")
        config = os.path.join(self.a, "spry", "spry.config.json")
        with open(config, "w") as handle:
            handle.write(json.dumps({**TEAM, "mint": "main"}))
        head = self.remote_head()
        said = self.refused(lambda: spry.main(["--root", self.a, "claim", "SL-2", "--no-switch"]))
        self.assertIn("match no one in team.members — pass --owner <name>, one of: Asha, Ravi", said)
        self.assertEqual(self.remote_head(), head)

    def test_claim_reads_the_main_branch_and_refuses_an_existing_branch_before_pushing(self):
        spry.mint(spry.Project(self.b), "slice", "S-1", "Fresh")
        self.assertEqual(spry.claim(spry.Project(self.a), "SL-3", switch=False), "sl-3-fresh")  # a never pulled it
        head = self.remote_head()
        self.git(self.b, "branch", "sl-2-b")
        self.assertIn("a branch `sl-2-b` exists here", self.refused(lambda: spry.claim(spry.Project(self.b), "SL-2")))
        self.git(self.b, "push", "-q", "origin", "sl-2-b")
        self.git(self.b, "branch", "-D", "sl-2-b")
        self.assertIn("`origin/sl-2-b` exists", self.refused(lambda: spry.claim(spry.Project(self.a), "SL-2")))
        with open(os.path.join(self.a, "notes.txt"), "w") as handle:
            handle.write("x")
        self.git(self.a, "add", "notes.txt")
        self.git(self.a, "commit", "-qm", "n")
        with open(os.path.join(self.a, "notes.txt"), "w") as handle:
            handle.write("y")
        self.assertIn("uncommitted changes", self.refused(lambda: spry.claim(spry.Project(self.a), "SL-1")))
        self.assertEqual(self.remote_head(), head)

    def test_nothing_is_checked_out_no_hook_runs_and_the_git_config_is_unchanged(self):
        with open(os.path.join(self.a, "big.txt"), "w") as handle:
            handle.write("not needed to take a number")
        self.git(self.a, "add", "big.txt")
        self.git(self.a, "commit", "-qm", "outside spry")
        self.git(self.a, "push", "-q", "origin", "main")
        fired = os.path.join(self.tmp, "fired")
        for name in ("post-checkout", "pre-commit", "post-commit", "pre-push"):
            hook = os.path.join(self.a, ".git", "hooks", name)
            with open(hook, "w") as handle:
                handle.write(f"#!/bin/sh\necho {name} >> {fired}\n")
            os.chmod(hook, 0o755)
        config = self.git(self.a, "config", "--list", "--local")
        status, before = self.git(self.a, "status", "--porcelain"), self.remote_head()
        real, opened = spry.read, []

        def read(path):
            opened.append(path)
            return real(path)

        spry.read = read
        self.addCleanup(setattr, spry, "read", real)
        project = spry.Project(self.a, load=False)
        opened.clear()

        def step(names):
            self.assertEqual(names.project.config["mint"], "main")
            return None, "docs(plan): new T-1 Sparse", {f"{M}/tasks/T-1-sparse/README.md": "---\nid: T-1\n---\n"}

        _, commit, _ = spry.on_main(project, step)
        self.assertEqual(opened, [], "on_main opened a file in the tree")
        self.assertFalse(os.path.exists(fired), "a project hook ran")
        self.assertEqual(self.git(self.a, "config", "--list", "--local"), config)
        self.assertEqual(self.git(self.a, "status", "--porcelain"), status)
        self.assertEqual(self.remote_head(), commit)
        self.assertEqual(self.git(self.a, "show", f"{commit}:{M}/tasks/T-1-sparse/README.md"), "---\nid: T-1\n---")
        listed = self.git(self.a, "ls-tree", "-r", "--name-only", commit).splitlines()
        self.assertIn("big.txt", listed, "files outside spry/ stay in the commit")
        self.assertEqual(self.worktrees(self.a), 1)
        self.assertEqual(self.git(self.a, "log", "-1", "--format=%P", commit), before)

    def test_new_opens_only_the_files_it_needs(self):
        real, opened = spry.read, []

        def read(path):
            opened.append(os.path.relpath(path, self.a))
            return real(path)

        spry.read = read
        self.addCleanup(setattr, spry, "read", real)
        with contextlib.redirect_stdout(io.StringIO()):
            spry.main(["--root", self.a, "new", "task", "--parent", "M-1", "--title", "Fast"])
        self.assertEqual(opened, [os.path.join("spry", "spry.config.json")])
        self.assertTrue(os.path.isfile(os.path.join(self.a, M, "tasks", "T-1-fast", "README.md")))

    def test_a_batch_is_one_commit_numbered_on_with_parents_from_the_same_batch(self):
        batch = os.path.join(self.tmp, "batch.json")
        with open(batch, "w") as handle:
            json.dump([{"key": "f", "type": "feature", "parent": "E-1", "title": "Renew"},
                       {"type": "story", "parent": "f", "title": "Renew a loan", "owner": "Asha"},
                       {"type": "story", "parent": "f", "title": "Refuse a renewal"},
                       {"type": "story", "parent": "F-1", "title": "Elsewhere"}], handle)
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(spry.main(["--root", self.a, "new", "--batch", batch]), 0)
        self.assertEqual([p.rsplit("/", 2)[-2] for p in out.getvalue().split()],
                         ["F-2-renew", "S-2-renew-a-loan", "S-3-refuse-a-renewal", "S-4-elsewhere"])
        self.assertEqual(self.git(self.a, "rev-parse", "HEAD"), self.remote_head())
        self.assertEqual(self.git(self.a, "rev-list", "--count", "HEAD"), "2")
        self.assertEqual(self.git(self.a, "log", "-1", "--format=%s"), "docs(plan): new F-2, S-2, S-3, S-4")
        with open(os.path.join(self.a, E, "F-2-renew", "S-2-renew-a-loan", "README.md")) as handle:
            self.assertIn("owner: Asha", handle.read())
        with contextlib.redirect_stdout(io.StringIO()):
            spry.main(["--root", self.a, "new", "slice", "--parent", "S-2", "--title", "One", "--title", "Two"])
        self.assertEqual(sorted(os.listdir(os.path.join(self.a, E, "F-2-renew", "S-2-renew-a-loan"))),
                         ["README.md", "SL-3-one.md", "SL-4-two.md"])
        self.assertEqual([str(p) for p in spry.check(spry.Project(self.a)) if p.level == "error"], [])

    def test_a_batch_that_fails_check_or_names_a_missing_parent_writes_nothing(self):
        head = self.remote_head()
        entries = [{"type": "story", "parent": "F-1", "title": "Fine", "owner": None, "key": None},
                   {"type": "story", "parent": "F-1", "title": "Ask a patron", "owner": None, "key": None}]
        said = self.refused(lambda: spry.mint_batch(spry.Project(self.a), entries))
        self.assertIn("the glossary says `Member`", said)
        self.assertIn("S-3-ask-a-patron", said)
        entries[1] = {"type": "story", "parent": "nope", "title": "X", "owner": None, "key": None}
        self.assertIn("nope is not on origin/main yet", self.refused(lambda: spry.mint_batch(spry.Project(self.a), entries)))
        self.assertEqual(self.remote_head(), head)
        self.assertFalse(os.path.exists(os.path.join(self.a, F, "S-2-fine")))
        for bad in ([], [{"type": "story"}], [{"type": "story", "title": "x", "key": "S-1"}],
                    [{"type": "story", "title": "x", "colour": "red"}], [{"type": "story", "title": 5}],
                    [{"type": ["story"], "title": "x"}], [{"type": "story", "title": "x", "parent": "f"},
                                                         {"type": "feature", "title": "y", "key": "f"}]):
            self.assertIn("--batch", self.refused(lambda: spry.batch_entries(bad)))

    def test_a_race_retries_the_whole_batch(self):
        real, raced = spry.git, []

        def git(root, *args, **kw):
            if "push" in args and not raced:
                raced.append(True)
                spry.mint(spry.Project(self.b), "story", "F-1", "Theirs")
            return real(root, *args, **kw)

        spry.git = git
        self.addCleanup(setattr, spry, "git", real)
        with contextlib.redirect_stderr(io.StringIO()):
            paths = spry.mint_batch(spry.Project(self.a), [
                {"type": "story", "parent": "F-1", "title": t, "owner": None, "key": None} for t in ("One", "Two")])
        self.assertEqual([p.rsplit("/", 2)[-2] for p in paths], ["S-3-one", "S-4-two"])

    def test_a_subfolder_with_glob_characters_is_checked_out(self):
        folder = "docs [v2]*"
        os.makedirs(os.path.join(self.a, folder))
        self.git(self.a, "mv", "spry", os.path.join(folder, "spry"))
        self.git(self.a, "commit", "-qm", "move spry")
        self.git(self.a, "push", "-q", "origin", "main")
        path = spry.mint(spry.Project(os.path.join(self.a, folder)), "task", "M-1", "Moved")
        self.assertTrue(path.endswith("T-1-moved/README.md"))
        self.assertEqual(self.git(self.a, "rev-parse", "HEAD"), self.remote_head())

    def test_local_numbers_count_empty_and_hidden_folders_as_the_old_walk_did(self):
        with open(os.path.join(self.a, "spry", "spry.config.json"), "w") as handle:
            handle.write(json.dumps({**CONFIG, "mint": "local"}))
        os.makedirs(os.path.join(self.a, "spry", "plan", "M-2-empty"))
        os.makedirs(os.path.join(self.a, "spry", "plan", ".old", "M-7-x"))
        self.assertTrue(spry.mint(spry.Project(self.a), "milestone", None, "Fresh").endswith("M-8-fresh/README.md"))

    def test_local_mint_behaves_as_before(self):
        with open(os.path.join(self.a, "spry", "spry.config.json"), "w") as handle:
            handle.write(json.dumps({**CONFIG, "mint": "local"}))
        head = self.remote_head()
        path = spry.mint(spry.Project(self.a), "task", "M-1", "Local")
        self.assertTrue(path.endswith("T-1-local/README.md"))
        self.assertEqual(self.remote_head(), head)
        self.assertEqual(spry.claim(spry.Project(self.a), "SL-2"), "sl-2-b")
        self.assertEqual(self.remote_head(), head)

    def test_check_base_names_a_number_both_branches_took(self):
        for root in (self.a, self.b):
            with open(os.path.join(root, "spry", "spry.config.json"), "w") as handle:
                handle.write(json.dumps({**CONFIG, "mint": "local"}))
            self.git(root, "commit", "-qam", "local")
        self.git(self.a, "switch", "-qc", "sl-7-a")
        spry.mint(spry.Project(self.a), "task", "M-1", "Mine")
        self.git(self.a, "mv", S, f"{F}/S-1-renamed")  # a moved item is not a collision
        self.git(self.a, "add", "-A")
        self.git(self.a, "commit", "-qm", "mine")
        spry.mint(spry.Project(self.b), "task", "M-1", "Theirs")
        self.git(self.b, "add", "-A")
        self.git(self.b, "commit", "-qm", "theirs")
        self.git(self.b, "push", "-q", "--force", "origin", "main")
        self.git(self.a, "fetch", "-q")
        project = spry.Project(self.a)
        spry.id_collisions(project, "origin/main")
        self.assertEqual([p.message.split(" — ")[0] for p in project.problems],
                         [f"T-1 is also {M}/tasks/T-1-theirs/README.md on origin/main"])


class Windows(unittest.TestCase):
    """The Windows paths, taken on any machine by setting `spry.WINDOWS`."""

    def setUp(self):
        from unittest import mock
        self.mock = mock
        patcher = mock.patch.object(spry, "WINDOWS", True)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_cmd_takes_double_quotes_not_single(self):
        self.assertEqual(spry.shell_quote("tests/a.py"), "tests/a.py")
        self.assertEqual(spry.shell_quote("tests/a b.py"), '"tests/a b.py"')
        self.assertEqual(spry.shell_quote("tests/a&b.py"), '"tests/a&b.py"')
        with self.assertRaises(spry.PlanError):
            spry.shell_quote("tests/%PATH%.py")

    def test_a_timeout_stops_the_whole_tree(self):
        proc = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(30)"])
        with self.mock.patch.object(spry.subprocess, "run") as run:
            spry.stop_group(proc)
        self.assertEqual(run.call_args[0][0], ["taskkill", "/T", "/F", "/PID", str(proc.pid)])
        self.assertIsNotNone(proc.returncode, "the shell itself is stopped too")

    def test_a_refused_symlink_becomes_a_junction_or_says_what_to_do(self):
        root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, root)
        source, link = os.path.join(root, "node_modules"), os.path.join(root, "w1", "node_modules")
        os.makedirs(source)
        refused = OSError("A required privilege is not held by the client")
        with self.mock.patch.object(spry.os, "symlink", side_effect=refused), \
                self.mock.patch.object(spry.subprocess, "run") as run:
            run.return_value = subprocess.CompletedProcess([], 0, "", "")
            spry.borrow(source, link, "node_modules", pnpm=False)
            self.assertEqual(run.call_args[0][0], ["cmd", "/c", "mklink", "/J", os.path.normpath(link),
                                                   os.path.normpath(source)])
            run.return_value = subprocess.CompletedProcess([], 1, "", "no")
            with self.assertRaises(spry.PlanError) as caught:
                spry.borrow(source, link, "node_modules", pnpm=False)
            self.assertIn("Developer Mode", str(caught.exception))
            with self.mock.patch.object(spry, "WINDOWS", False), self.assertRaises(OSError):
                spry.borrow(source, link, "node_modules", pnpm=False)

    def test_cleanup_removes_a_borrowed_link_never_what_it_points_at(self):
        root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, root)
        source, link = os.path.join(root, "node_modules"), os.path.join(root, "w1", "node_modules")
        os.makedirs(source)
        open(os.path.join(source, "kept"), "w").close()
        os.makedirs(os.path.dirname(link))
        os.symlink(source, link)
        self.assertTrue(spry.unborrow(link))
        self.assertFalse(os.path.lexists(link))
        self.assertTrue(os.path.isfile(os.path.join(source, "kept")))
        self.assertTrue(spry.unborrow(link), "nothing borrowed is nothing to remove")
        os.makedirs(link)
        self.assertFalse(spry.unborrow(link), "a real folder on Windows: leave it to rmtree, not git")

    def test_written_files_keep_lf(self):
        path = os.path.join(tempfile.mkdtemp(), "a.md")
        self.addCleanup(shutil.rmtree, os.path.dirname(path))
        spry.write(path, "one\ntwo\n")
        with open(path, "rb") as handle:
            self.assertEqual(handle.read(), b"one\ntwo\n")


class LongPaths(Base):
    """A plan six folders deep passes Windows' 260 characters; pulse-v2's machines refuse past it."""

    def test_past_260_through_the_extended_prefix(self):
        self.assertEqual(spry.long_path("C:/w/spry/plan/a.md"), "\\\\?\\C:\\w\\spry\\plan\\a.md")
        self.assertEqual(spry.long_path("\\\\srv\\share\\a.md"), "\\\\?\\UNC\\srv\\share\\a.md")
        if os.name != "nt":
            self.assertEqual(spry.native("spry/plan/a.md"), "spry/plan/a.md", "only Windows reads the prefix")

    def test_walk_names_folders_from_the_top_given(self):
        t = self.tree()
        top = os.path.join(t.root, "spry", "plan")
        prefixed = (lambda p: "/" + p if not p.startswith("//") else p)  # stands in for `\\?\`
        with unittest.mock.patch.object(spry, "native", prefixed):
            self.assertEqual([d for d, _, _ in spry.walk_dir(top)], [d for d, _, _ in os.walk(top)])

    def test_a_file_that_cannot_be_read_is_a_problem_not_a_crash(self):
        t = self.tree()
        refused, read = os.path.join(t.root, S, "SL-1-a.md"), spry.read

        def refuse(path):
            if path == refused:
                raise FileNotFoundError(2, "No such file or directory")
            return read(path)
        with unittest.mock.patch.object(spry, "read", refuse):
            problems = t.problems()
        self.assertEqual([p for p in problems if "cannot be read" in p],
                         [f"{S}/SL-1-a.md:0: error: cannot be read: No such file or directory"])

    def test_a_long_path_is_named_before_windows_refuses_it(self):
        deep = f"{S}/bugs/B-1-{'b' * 100}/SL-2-{'s' * 60}.md"
        t = self.tree(**{f"{S}/bugs/B-1-{'b' * 100}/README.md".replace("/", "__"): item("B-1"),
                         deep.replace("/", "__"): slice_("SL-2", covers="[]")})
        warnings = [str(p) for p in spry.check(t.project()) if p.level == "warning"]
        self.assertProblem(warnings, f"{deep}:0: warning: {len(deep)} characters")
        self.assertFalse(any(f"{S}/README.md" in w for w in warnings), warnings)


class Kit(unittest.TestCase):
    """Versions and the changelog agree, so /spry:update has something true to compare against."""

    def test_versions_and_baseline_agree(self):
        plugin = os.path.join(REPO, "plugins", "spry")
        with open(os.path.join(plugin, ".claude-plugin", "plugin.json")) as handle:
            version = json.load(handle)["version"]
        with open(os.path.join(plugin, "process", "templates", "spry.config.json")) as handle:
            template = json.load(handle)
        with open(os.path.join(plugin, "CHANGELOG.md")) as handle:
            changelog = handle.read()
        import re
        entries = re.findall(r"^## (CH-\d+) · .*\n+- \*\*Date:\*\* \S+ · \*\*Version:\*\* (\S+)", changelog, re.M)
        self.assertTrue(entries)
        numbers = [int(e[0].split("-")[1]) for e in entries]
        self.assertEqual(numbers, list(range(1, len(numbers) + 1)), "CH numbers run 1, 2, 3 … with none reused")
        self.assertEqual(spry.VERSION, version)
        self.assertEqual(template["spry"], version)
        self.assertEqual(template["spry_baseline"], entries[-1][0], "a new project starts at the last entry")
        self.assertEqual(entries[-1][1], version, "the last entry ships in the current version")

    # Lines each process file may hold. A session reads these on every slice and every request
    # reads them again, so a rule added is paid for until it is cut. Over budget → cut or merge
    # something first; raise a number only with the reason in the commit message.
    PROCESS_BUDGETS = {"slicing.md": 400, "reviewing.md": 295, "merging.md": 115, "chat.md": 85, "writing.md": 50,
                       "conflicts.md": 55, "planning.md": 145, "interview.md": 65, "testing.md": 160, "qa.md": 70,
                       "setup.md": 115, "updating.md": 80, "compacting.md": 75, "audits.md": 60, "contributing.md": 55,
                       "recording.md": 45, "changing.md": 25, "from-writ.md": 450}

    def test_every_process_file_keeps_to_its_line_budget(self):
        folder = os.path.join(REPO, "plugins", "spry", "process")
        files = sorted(f for f in os.listdir(folder) if f.endswith(".md"))
        self.assertEqual(sorted(self.PROCESS_BUDGETS), files, "every process file has a budget, and no budget is left over")
        for name in files:
            with open(os.path.join(folder, name)) as handle:
                lines = len(handle.read().split("\n")) - 1
            self.assertLessEqual(lines, self.PROCESS_BUDGETS[name],
                                 f"{name} has {lines} lines, over its budget of {self.PROCESS_BUDGETS[name]} — cut or merge a rule "
                                 "before adding one")

    def test_the_reviewer_agent_cannot_edit(self):
        """CH-85: the plugin's reviewer is read-only by its tools, and every command it names exists."""
        path = os.path.join(REPO, "plugins", "spry", "agents", "reviewer.md")
        with open(path) as handle:
            text = handle.read()
        self.assertTrue(text.startswith("---\nname: reviewer\n"))
        tools = re.search(r"^tools: (.*)$", text, re.M).group(1).split(", ")
        self.assertEqual(tools, ["Bash", "Read", "Grep", "Glob"])
        for kind in re.findall(r"proc --for ([\w-]+)", text):
            self.assertIn(kind, spry.PROC_FOR)

    def test_every_skill_names_files_that_exist(self):
        import re
        plugin = os.path.join(REPO, "plugins", "spry")
        for name in os.listdir(os.path.join(plugin, "skills")):
            with open(os.path.join(plugin, "skills", name, "SKILL.md")) as handle:
                text = handle.read()
            self.assertTrue(text.startswith(f"---\nname: {name}\n"), name)
            for ref in re.findall(r"`(?:spry|<plugin root>)/process/([\w/.-]+\.md)`", text):
                self.assertTrue(os.path.isfile(os.path.join(plugin, "process", ref)), f"{name} names {ref}")


LOANS_BEFORE = 'def lend(count, overdue):\n    return "ok"\n'
LOANS_AFTER = ('def lend(count, overdue):\n    if count >= 3:\n        return "limit"\n'
               '    if overdue:\n        return "overdue"\n    return "ok"\n')
# Reports a failed assertion as pytest does; anything else breaks the run, as a missing database would.
RUNNER = ("import runpy, sys\nfor f in sys.argv[1:]:\n    try:\n        runpy.run_path(f)\n"
          "    except AssertionError:\n        print('1 failed')\n        sys.exit(1)\n")
TEST_LIMIT = ('"""S-1/AC-1 refuses a fourth book"""\nimport sys; sys.path.insert(0, "src")\nfrom loans import lend\n'
              'assert lend(3, False) == "limit"\nassert lend(2, False) == "ok"\n')
TEST_OVERDUE = ('"""S-1/AC-2 refuses an overdue member, but never checks it"""\nimport sys; sys.path.insert(0, "src")\n'
                'from loans import lend\nassert lend(0, False) == "ok"\n')


class Falsify(unittest.TestCase):
    """A git repository whose slice adds two guards: one a test notices, one no test checks."""

    def setUp(self):
        self.root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.root)
        story = "spry/plan/M-1-m/E-1-e/F-1-f/S-1-s"
        config = {"main_branch": "main", "tests": {"match": ["tests/test_*.py"]},
                  "falsify": {"runners": [{"match": ["tests/**"], "cwd": "root", "command": "python3 run.py {files}"}]}}
        files = {
            "spry/spry.config.json": json.dumps(config),
            "spry/plan/M-1-m/README.md": "---\nid: M-1\ntitle: m\nstate: draft\n---\n# M-1\n",
            "spry/plan/M-1-m/E-1-e/README.md": "---\nid: E-1\ntitle: e\nstate: draft\n---\n# E-1\n",
            "spry/plan/M-1-m/E-1-e/F-1-f/README.md": "---\nid: F-1\ntitle: f\nstate: draft\n---\n# F-1\n",
            f"{story}/README.md": story_text(),
            "run.py": RUNNER, "src/loans.py": LOANS_BEFORE,
            "tests/test_limit.py": TEST_LIMIT, "tests/test_overdue.py": TEST_OVERDUE,
        }
        self.write(files)
        self.git("init", "-q", "-b", "main")
        self.commit("base")
        self.git("checkout", "-q", "-b", "sl-1")
        self.write({"src/loans.py": LOANS_AFTER, f"{story}/SL-1-refuse.md": (
            "---\nid: SL-1\ntitle: Refuse\nstate: open\ncovers: [AC-1, AC-2]\n---\n# SL-1\n\n"
            "## Close summary\n\n### Falsify\n\n| Control | Mutation | Expect | Result |\n|---|---|---|---|\n")})
        self.commit("slice")
        self.slice_doc = os.path.join(self.root, story, "SL-1-refuse.md")
        self.addCleanup(shutil.rmtree, spry.falsify_home(spry.Project(self.root)), True)

    def write(self, files):
        for rel, text in files.items():
            path = os.path.join(self.root, rel)
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w") as handle:
                handle.write(text)

    def git(self, *args):
        return subprocess.run(["git", "-C", self.root, "-c", "user.name=t", "-c", "user.email=t@t", *args],
                              capture_output=True, text=True, check=True).stdout

    def commit(self, message):
        self.git("add", "-A")
        self.git("commit", "-q", "-m", message)

    def plan(self, entries):
        path = os.path.join(self.root, ".spry", "plan.json")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as handle:
            json.dump(entries, handle)
        return path

    def guard(self, find, expect, **extra):
        return dict({"control": find.strip(), "file": "src/loans.py", "find": find,
                     "with": find.replace("if ", "if False and (").replace(":", "):"), "expect": expect}, **extra)

    def run_plan(self, entries, **kw):
        return spry.falsify_run(spry.Project(self.root), self.plan(entries), say=lambda *_: None, **kw)

    def source(self):
        with open(os.path.join(self.root, "src", "loans.py")) as handle:
            return handle.read()

    def test_caught_and_survived_and_everything_restored(self):
        results = self.run_plan([self.guard("    if count >= 3:", ["S-1/AC-1", "S-1/AC-2"]),
                                 self.guard("    if overdue:", ["S-1/AC-1", "S-1/AC-2"])])
        self.assertEqual([r for _, r, _ in results], ["caught", "survived"],
                         "the second mutation has the first's size: a stale compiled file would make it a false catch")
        self.assertEqual(self.source(), LOANS_AFTER)
        self.assertEqual(self.git("status", "--porcelain", "--untracked-files=no", "--", "src"), "")

    def test_runs_only_the_files_that_cite_expect(self):
        results = self.run_plan([self.guard("    if count >= 3:", ["S-1/AC-2"])])
        self.assertEqual(results[0][1], "survived", "only test_overdue ran, and it cannot notice the limit")

    def test_red_baseline_is_unreliable_not_caught(self):
        self.write({"tests/test_overdue.py": TEST_OVERDUE + "assert False\n"})
        self.commit("red")
        results = self.run_plan([self.guard("    if overdue:", ["S-1/AC-2"])])
        self.assertEqual(results[0][1], "unreliable")

    def test_a_run_that_breaks_before_a_test_fails_is_unreliable_not_caught(self):
        broken = dict(self.guard("    if count >= 3:", ["S-1/AC-1"]), **{"with": "    if count >= 3"})
        result, note = self.run_plan([broken])[0][1:]
        self.assertEqual(result, "unreliable", "a syntax error stops the run before any test fails")
        self.assertIn("failed, but no test did: SyntaxError", note)
        self.configure(runners=[{"match": ["tests/**"], "cwd": "root", "command": "python3 run.py {files}",
                                 "failed": "^(1 failed|SyntaxError)"}])
        self.assertEqual(self.run_plan([broken])[0][1], "caught", "a runner's own `failed` replaces the built-in ones")
        self.configure(runners=[{"match": ["tests/**"], "cwd": "root", "command": "python3 run.py {files}", "failed": "(1 failed"}])
        with self.assertRaises(spry.PlanError) as caught:
            self.run_plan([broken])
        self.assertIn("`failed` is not a pattern", str(caught.exception))

    def test_failed_patterns(self):
        cases = {
            " Test Files  1 failed (1)\n      Tests  1 failed | 2 passed (3)": True,
            " Test Files  1 failed (1)\n      Tests  no tests\nError: connect ECONNREFUSED": False,
            "\x1b[1m      Tests \x1b[22m \x1b[1m\x1b[31m1 failed\x1b[39m\x1b[22m": True,
            "Tests:       1 failed, 4 passed, 5 total": True,
            "Test Suites: 1 failed, 1 total\nTests:       0 total": False,
            "========= 1 failed, 3 passed in 0.12s =========": True,
            "1 failed, 3 passed in 0.12s": True,
            "ERROR tests/test_a.py - ModuleNotFoundError\n!!! Interrupted: 1 error during collection !!!": False,
            "--- FAIL: TestLimit (0.00s)\nFAIL": True,
            "FAIL\texample.com/loans [build failed]": False,
            "  2 passing\n  1 failing": True,
            "test result: FAILED. 1 passed; 1 failed": True,
            "FAILED (failures=1)": True,
            "FAILED (errors=1)": True,
            "ERROR: test_a (unittest.loader._FailedTest.test_a)\nImportError: Failed to import test module: test_a\nFAILED (errors=1)": False,
            '  1 failing\n  1) Loans\n       "before all" hook for "lends":\n     Error: connect ECONNREFUSED': False,
            "api:test:       Tests  1 failed | 2 passed (3)": True,
            "api-1  | ========= 1 failed in 0.12s =========": True,
            "Error: 3 failed attempts to reach the database": False,
            "3 examples, 1 failure": True,
            "3 examples, 0 failures": False,
            "ℹ fail 1": True,
            "ERR_PNPM_VERIFY_DEPS_BEFORE_RUN  Cannot run scripts because node_modules is out of date": False,
        }
        for output, failed in cases.items():
            self.assertEqual(spry.test_failed({}, output), failed, output)

    def test_refusals(self):
        cases = {
            "nothing would change": [dict(self.guard("    if overdue:", ["S-1/AC-2"]), **{"with": "    if overdue:"})],
            "occurs 3 times": [dict(self.guard("    if overdue:", ["S-1/AC-2"]), find="return")],
            "no test cites S-1/AC-9": [self.guard("    if overdue:", ["S-1/AC-9"])],
            "cites none of": [self.guard("    if overdue:", ["S-1/AC-2"], files=["tests/test_limit.py"])],
        }
        for fragment, entries in cases.items():
            with self.assertRaises(spry.PlanError) as caught:
                self.run_plan(entries)
            self.assertIn(fragment, str(caught.exception))

    def test_refuses_a_file_with_uncommitted_changes(self):
        self.write({"src/loans.py": LOANS_AFTER + "# work in progress\n"})
        with self.assertRaises(spry.PlanError) as caught:
            self.run_plan([self.guard("    if overdue:", ["S-1/AC-2"])])
        self.assertIn("uncommitted", str(caught.exception))

    def test_restores_when_interrupted(self):
        original = spry.run_tests
        calls = []

        def interrupt(*args):
            calls.append(1)
            if len(calls) > 1:
                raise KeyboardInterrupt()
            return original(*args)

        spry.run_tests = interrupt
        self.addCleanup(setattr, spry, "run_tests", original)
        with self.assertRaises(KeyboardInterrupt):
            self.run_plan([self.guard("    if overdue:", ["S-1/AC-2"])])
        self.assertEqual(self.source(), LOANS_AFTER)

    def test_dry_run_changes_nothing(self):
        said = []
        spry.falsify_run(spry.Project(self.root), self.plan([self.guard("    if overdue:", ["S-1/AC-2"])]),
                         dry=True, say=said.append)
        self.assertTrue(any("would remove" in s for s in said))
        self.assertEqual(self.source(), LOANS_AFTER)

    def test_suggest_drafts_never_true_guards_with_expect_from_covers(self):
        plan = spry.falsify_suggest(spry.Project(self.root), "SL-1", "main")
        self.assertEqual([e["find"] for e in plan], ["    if count >= 3:", "    if overdue:"])
        self.assertEqual(plan[1]["with"], "    if False and (overdue):")
        self.assertEqual(plan[0]["expect"], ["S-1/AC-1", "S-1/AC-2"])

    def test_a_bugs_slice_expects_the_bug(self):
        bug = "spry/plan/M-1-m/E-1-e/F-1-f/bugs/B-1-limit"
        self.write({f"{bug}/README.md": "---\nid: B-1\ntitle: limit\nstate: open\n---\n# B-1\n",
                    f"{bug}/SL-2-fix.md": "---\nid: SL-2\ntitle: Fix\nstate: open\ncovers: []\n---\n# SL-2\n",
                    "tests/test_bug.py": TEST_LIMIT.replace('"""S-1/AC-1', '"""B-1'),
                    "tests/test_note.py": "# B-1 only in a comment\n" + TEST_OVERDUE.replace("S-1/AC-2", "nothing")})
        self.commit("a bug and its test")
        project = spry.Project(self.root)
        self.assertEqual(sorted(p for p, _, _ in project.item_tests["B-1"]), ["tests/test_bug.py"],
                         "a bug cited only in a comment selects nothing")
        self.assertEqual(spry.falsify_suggest(project, "SL-2", "main")[0]["expect"], ["B-1"])
        results = self.run_plan([self.guard("    if count >= 3:", ["B-1"])])
        self.assertEqual(results[0][1], "caught")
        for fragment, expect in {"not a criterion, a bug, a task or a test file": ["B-9"],
                                 "outside a test's name: tests/test_note.py:1": ["B-1"]}.items():
            if expect == ["B-1"]:
                self.write({"tests/test_bug.py": TEST_LIMIT.replace('"""S-1/AC-1', '"""fixtures/B-1.json, B-1.json')})
                self.commit("only data names the bug")
            with self.assertRaises(spry.PlanError) as caught:
                self.run_plan([self.guard("    if count >= 3:", expect)])
            self.assertIn(fragment, str(caught.exception))

    def test_a_tasks_slice_expects_the_task_or_a_test_file(self):
        task = "spry/plan/M-1-m/tasks/T-1-pool"
        self.write({f"{task}/README.md": "---\nid: T-1\ntitle: pool\nstate: open\n---\n# T-1\n",
                    f"{task}/SL-2-pool.md": "---\nid: SL-2\ntitle: Pool\nstate: open\ncovers: []\n---\n# SL-2\n",
                    "tests/test_pool.py": TEST_LIMIT.replace('"""S-1/AC-1', '"""T-1'),
                    "tests/helper.py": "VALUE = 1\n", "spry/tests/test_x.py": "assert True\n"})
        self.commit("a task and its test")
        project = spry.Project(self.root)
        self.assertEqual(sorted(p for p, _, _ in project.item_tests["T-1"]), ["tests/test_pool.py"])
        self.assertEqual(spry.falsify_suggest(project, "SL-2", "main")[0]["expect"], ["T-1"])
        results = self.run_plan([self.guard("    if count >= 3:", ["T-1"]),
                                 self.guard("    if overdue:", ["./tests/test_limit.py"], files=["tests/test_limit.py"])])
        self.assertEqual([r for _, r, _ in results], ["caught", "survived"])
        for fragment, expect in {"not a criterion, a bug, a task or a test file": ["tests/test_gone.py"],
                                 "not named as a test file": ["tests/helper.py"],
                                 "not a test file inside the project": ["../" + os.path.basename(self.root) + "/tests/test_limit.py"],
                                 "inside the project": ["spry/tests/test_x.py"],
                                 "put the ID in a test's name, or name the test file": ["S-1/AC-9"]}.items():
            with self.assertRaises(spry.PlanError) as caught:
                self.run_plan([self.guard("    if count >= 3:", expect)])
            self.assertIn(fragment, str(caught.exception))

    def test_suggest_offers_value_lines_when_no_guard_was_added(self):
        self.git("checkout", "-q", "-b", "digest")
        self.write({"src/loans.py": LOANS_AFTER + "\ndef key(org, body):\n    salted = org.secret + body\n    return hash(salted)\n",
                    "notes.md": "if this were code it would be a guard\n"})
        self.commit("a keyed digest, no guard")
        plan = spry.falsify_suggest(spry.Project(self.root), "SL-1", "sl-1")
        self.assertEqual([e["find"] for e in plan], ["    salted = org.secret + body", "    return hash(salted)"])
        self.assertTrue(plan[0]["mutation"].startswith("delete the line — no guard was added"))
        self.assertEqual(spry.falsify_suggest(spry.Project(self.root), "SL-1", "sl-1", fallback=False), [],
                         "merge-check never requires a fallback line")

    def test_suggest_drafts_only_the_tests_that_name_the_source(self):
        self.write({"tests/test_far.py": '"""S-1/AC-1 from far away"""\nassert True\n'})
        self.commit("a test citing the criterion that never names the source file")
        plan = spry.falsify_suggest(spry.Project(self.root), "SL-1", "main")
        self.assertEqual(plan[0]["files"], ["tests/test_limit.py", "tests/test_overdue.py"])
        self.assertEqual([r for _, r, _ in self.run_plan(plan)], ["caught", "survived"])

    def test_a_control_no_test_names_is_not_run(self):
        self.write({"tests/test_limit.py": TEST_LIMIT.replace("from loans import lend", "lend = lambda *a: 'limit' if a[0] > 2 else 'ok'"),
                    "tests/test_overdue.py": TEST_OVERDUE.replace("from loans import lend", "lend = lambda *a: 'ok'")})
        self.commit("tests that never name the source file")
        notes = []
        plan = spry.falsify_suggest(spry.Project(self.root), "SL-1", "main", notes=notes)
        self.assertEqual([e["files"] for e in plan], [[], []])
        self.assertTrue(any("`files: []`" in n for n in notes), notes)
        ran = spry.run_tests
        spry.run_tests = lambda *a, **k: self.fail("nothing should run")
        self.addCleanup(setattr, spry, "run_tests", ran)
        results = self.run_plan(plan)
        self.assertEqual([(r, n) for _, r, n in results], [("survived", "no test names loans")] * 2)
        spry.run_tests = ran
        lines = self.merge_lines("\n".join(spry.falsify_rows(results)) + "\n")
        self.assertEqual(sum(1 for s, x in lines if s == "block" and "was not run — no test names loans" in x), 2, lines)
        for entry in plan:
            del entry["files"]
        self.assertEqual([(r, n) for _, r, n in self.run_plan(plan)], [("survived", "")] * 2,
                         "without `files`, every test citing `expect` runs")

    def test_suggest_leaves_out_guards_the_branch_only_moved(self):
        old = "def check(n):\n    if n > 9:\n        raise ValueError(n)\n    return n\n"
        self.write({"src/old.py": old})
        self.commit("a guard, before the slice")
        self.git("checkout", "-q", "-b", "move")
        self.write({"src/old.py": "from fresh import check\n",
                    "src/fresh.py": old.replace("    return n", "    if n < 0:\n        raise KeyError(n)\n    return n")})
        self.commit("the function moves to its own file and gains a guard")
        notes = []
        plan = spry.falsify_suggest(spry.Project(self.root), "SL-1", "sl-1", notes=notes)
        self.assertEqual([(e["find"], e["mutation"]) for e in plan],
                         [("    if n < 0:", "never true"), ("        raise KeyError(n)", "replace with `pass`")])
        self.assertEqual(plan[1]["with"], "        pass", "deleting an `if`'s only statement would not parse")
        self.assertTrue(any(n.startswith("2 guards the branch only moved") for n in notes), notes)

    def test_suggest_drafts_no_line_that_only_builds_a_value(self):
        js = ("export function lend(input, member) {\n"
              "  const name = input.name || 'none';\n"
              "  const extra = { ...(input.note === undefined ? {} : { note: input.note }) };\n"
              "  if (\n    member.loans >= 3 &&\n    member.kind !== 'staff'\n  ) {\n"
              "    throw new Error(\n      'limit'\n    );\n  }\n"
              "  return { name, ...extra };\n}\n")
        self.write({"src/lend.js": js})
        self.commit("javascript with defaults, a pass-through and a condition over several lines")
        project = spry.Project(self.root)
        plan = {e["find"]: e for e in spry.falsify_suggest(project, "SL-1", "main") if e["file"] == "src/lend.js"}
        self.assertEqual(sorted(plan), ["    member.kind !== 'staff'", "    member.loans >= 3 &&", "    throw new Error(", "  if ("])
        self.assertEqual(plan["    member.loans >= 3 &&"]["mutation"], "`>=` → `>`")
        for find in ("    member.kind !== 'staff'", "    throw new Error(", "  if ("):
            self.assertEqual((plan[find]["with"], plan[find]["mutation"]), (None, "write one"), find)
        with self.assertRaises(spry.PlanError) as caught:
            self.run_plan([dict(plan["  if ("], expect=["S-1/AC-1"], files=["tests/test_limit.py"])])
        self.assertIn("no mutation yet", str(caught.exception))
        with open(os.path.join(self.root, "spry", "spry.config.json")) as handle:
            config = json.load(handle)
        config["falsify"]["controls"] = "operators"
        self.write({"spry/spry.config.json": json.dumps(config)})
        self.commit("the old reach")
        wide = [e["find"] for e in spry.falsify_suggest(spry.Project(self.root), "SL-1", "main") if e["file"] == "src/lend.js"]
        self.assertIn("  const name = input.name || 'none';", wide)
        config["falsify"]["controls"] = "everything"
        self.write({"spry/spry.config.json": json.dumps(config)})
        with self.assertRaises(spry.PlanError):
            spry.falsify_suggest(spry.Project(self.root), "SL-1", "main")

    def test_a_branch_that_adds_no_source_needs_no_falsify(self):
        self.git("checkout", "-q", "-b", "tests-only")
        self.write({"tests/test_more.py": '"""S-1/AC-1 more"""\nassert True\n'})
        self.commit("a test only")
        lines = spry.merge_check(spry.Project(self.root), "SL-1", "sl-1")
        self.assertIn(("ok", "falsify: the branch adds no source lines — nothing to falsify"), lines)
        self.assertFalse(any("no falsify results" in x for _s, x in lines))
        self.assertTrue(any("no falsify results" in x for _s, x in spry.merge_check(spry.Project(self.root), "SL-1")),
                        "without a base, nothing is waived")

    def test_check_base_warns_on_a_cited_criterion_that_changed(self):
        path = os.path.join(self.root, "spry/plan/M-1-m/E-1-e/F-1-f/S-1-s/README.md")
        with open(path) as handle:
            text = handle.read()
        with open(path, "w") as handle:
            handle.write(text.replace("| AC-1 | a | b | c |", "| AC-1 | a | b | something else |"))
        p = spry.Project(self.root)
        spry.changed_criteria(p, "main")
        warnings = [str(x) for x in p.problems if x.level == "warning"]
        self.assertEqual(len(warnings), 1, warnings)
        self.assertIn("S-1/AC-1 changed since main, and tests/test_limit.py cite it", warnings[0])

    def test_check_base_warns_on_a_criterion_that_changed_under_its_scenarios(self):
        story = "spry/plan/M-1-m/E-1-e/F-1-f/S-1-s"
        checks = ("# Checks\n\n## Scenarios\n\n### Before you start (data for AC-1)\n\n1. log in → home\n\n"
                  "### AC-1 · limit · unlike AC-2\n\n1. lend → refused\n\n### AC-1, AC-2 · both\n\n1. lend → refused\n\n"
                  "### Limit, unlike AC-2\n\n1. x → y\n\n"
                  "## Check log\n\n| Date | AC | Build | By | Result | Notes |\n|---|---|---|---|---|---|\n"
                  "| 2026-10-01 | AC-2 | b1 | Q | pass | |\n| x | AC-2 |\n\n## Runs under writ\n\n### AC-2 run\n")
        self.assertEqual({ac: [n for n, _ in spry.manual_reliance(checks, ac)] for ac in ("AC-1", "AC-2", "AC-3")},
                         {"AC-1": [9, 13], "AC-2": [13, 25], "AC-3": []},
                         "only scenarios whose heading starts with the AC, and dated log rows")
        self.git("checkout", "-q", "main")
        self.write({f"{story}/checks.md": checks})
        self.commit("scenarios")
        self.git("checkout", "-q", "sl-1")
        self.git("merge", "-q", "--no-edit", "main")
        path = os.path.join(self.root, story, "README.md")
        with open(path) as handle:
            text = handle.read()
        self.write({f"{story}/README.md": text.replace("| a | b | c |", "| a | b | changed |"),
                    f"{story}/checks.md": checks, "tests/test_overdue.py": "assert True\n"})

        def warnings():
            p = spry.Project(self.root)
            spry.changed_criteria(p, "main")
            return [str(x) for x in p.problems if x.level == "warning"]
        found = warnings()
        self.assertEqual(len(found), 3, found)
        self.assertIn("S-1/AC-1 changed since main, and tests/test_limit.py cite it", found[0])
        self.assertIn("S-1/AC-1 changed since main, and checks.md:9, 13 still check the old wording", found[1])
        self.assertIn("S-1/AC-2 changed since main, and checks.md:13, 25 still check", found[2],
                      "no test cites AC-2, and the scenarios alone still warn")
        self.git("checkout", "-q", "main")
        self.write({f"{story}/checks.md": checks.replace("| x | AC-2 |", "| 2026-10-13 | AC-2 | b9 | Q | pass | |")})
        self.commit("a run on main after the branch left it")
        self.git("checkout", "-q", "sl-1")
        self.write({f"{story}/README.md": text.replace("| a | b | c |", "| a | b | changed |"),
                    f"{story}/checks.md": checks, "tests/test_overdue.py": "assert True\n"})
        self.assertEqual(len(warnings()), 3, "main's later run is not the branch's re-read")
        edited = checks.replace("1. lend → refused\n\n### AC-1, AC-2", "1. lend a fourth → refused\n\n### AC-1, AC-2")
        self.write({f"{story}/checks.md": edited.replace("## Check log", "### AC-1 · a new one\n\n1. a → b\n\n## Check log")})
        found = warnings()
        self.assertIn("checks.md:13 still check", found[1], "each scenario on its own; a new one re-reads none")
        self.write({f"{story}/checks.md": edited.replace("| Q | pass | |", "| Q | pass | typo fixed |")})
        self.assertIn("checks.md:13 still check", warnings()[2], "an edited old row is off the list, and is not a new run")
        self.write({f"{story}/checks.md": edited.replace("### AC-1, AC-2 · both\n", "### AC-1, AC-2 · both\n\n#### Steps\n\n1. new → step\n")})
        self.assertIn("S-1/AC-2 changed since main, and checks.md:29 still check the old wording — log a new run",
                      warnings()[1], "a scenario changed under its sub-heading is off the list; a log row is run again, not changed")
        today = datetime.date.today().isoformat()
        self.write({f"{story}/checks.md": edited.replace("| x | AC-2 |", f"| {today} | AC-2 | b2 | Q | pass | |")})
        self.assertEqual(len(warnings()), 2, "a new run re-checks every scenario of its criterion")
        self.write({f"{story}/README.md": text.replace("| AC-2 | a | b | c |", "| ~~AC-2~~ | a | b | changed |")
                    .replace("| AC-1 | a | b | c |", "| AC-1 | a | b | changed |")})
        self.assertEqual(len(warnings()), 2, "a struck criterion needs no re-read")

    def test_a_scenario_ends_at_the_next_heading(self):
        text = "## Scenarios\n\n### AC-1 · a\n\n1. x → y\n\n#### AC-2 · variant\n\n1. z → w\n"
        self.assertEqual(spry.manual_reliance(text, "AC-1"), [(3, "### AC-1 · a\n\n1. x → y")])

    def test_check_base_ignores_scenarios_the_branch_wrote(self):
        story = "spry/plan/M-1-m/E-1-e/F-1-f/S-1-s"
        path = os.path.join(self.root, story, "README.md")
        with open(path) as handle:
            text = handle.read()
        self.write({f"{story}/README.md": text.replace("| AC-2 | a | b | c |", "| AC-2 | a | b | changed |"),
                    f"{story}/checks.md": "# Checks\n\n## Scenarios\n\n### AC-2 · new\n\n1. x → y\n",
                    "tests/test_overdue.py": "assert True\n"})
        p = spry.Project(self.root)
        spry.changed_criteria(p, "main")
        self.assertEqual([x for x in p.problems if x.level == "warning"], [])

    def test_check_base_reports_a_ref_it_cannot_read(self):
        p = spry.Project(self.root)
        spry.changed_criteria(p, "origin/nowhere")
        self.assertTrue(any("is not a commit here" in str(x) and x.level == "error" for x in p.problems))

    def test_check_base_when_spry_sits_in_a_subfolder(self):
        outer = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, outer)
        shutil.copytree(self.root, os.path.join(outer, "app"), ignore=shutil.ignore_patterns(".git"))
        run = lambda *a: subprocess.run(["git", "-C", outer, "-c", "user.name=t", "-c", "user.email=t@t", *a],
                                        capture_output=True, text=True, check=True)
        run("init", "-q", "-b", "main")
        run("add", "-A")
        run("commit", "-q", "-m", "base")
        path = os.path.join(outer, "app", "spry/plan/M-1-m/E-1-e/F-1-f/S-1-s/README.md")
        with open(path) as handle:
            text = handle.read()
        with open(path, "w") as handle:
            handle.write(text.replace("| AC-1 | a | b | c |", "| AC-1 | a | b | changed |"))
        p = spry.Project(os.path.join(outer, "app"))
        spry.changed_criteria(p, "main")
        self.assertEqual(len([x for x in p.problems if x.level == "warning"]), 1, p.problems)

    def configure(self, **falsify):
        path = os.path.join(self.root, "spry", "spry.config.json")
        with open(path) as handle:
            config = json.load(handle)
        config["falsify"].update(falsify)
        with open(path, "w") as handle:
            json.dump(config, handle)

    def both_guards(self):
        return [self.guard("    if count >= 3:", ["S-1/AC-1", "S-1/AC-2"]),
                self.guard("    if overdue:", ["S-1/AC-1", "S-1/AC-2"])]

    def worktrees(self):
        return [l for l in self.git("worktree", "list").splitlines() if l.strip()]

    def test_parallel_matches_serial_and_never_touches_this_tree(self):
        self.configure(keep_worktrees=False)
        self.commit("worktrees not kept")
        self.run_plan(self.both_guards(), jobs=2)
        self.assertEqual(len(self.worktrees()), 1, "every worktree removed")
        self.configure(keep_worktrees=True)
        self.commit("worktrees kept")
        before = os.stat(os.path.join(self.root, "src", "loans.py")).st_mtime_ns
        said = []
        results = spry.falsify_run(spry.Project(self.root), self.plan(self.both_guards()), say=said.append, jobs=2)
        self.assertEqual([r for _, r, _ in results], ["caught", "survived"])
        self.assertTrue(any(s.startswith("2 worktrees") for s in said), said)
        self.assertEqual(os.stat(os.path.join(self.root, "src", "loans.py")).st_mtime_ns, before)
        self.assertEqual(len(self.worktrees()), 3, "both worktrees kept for the next run")

    def test_kept_worktrees_are_reset_like_fresh_ones(self):
        said = []
        spry.falsify_run(spry.Project(self.root), self.plan(self.both_guards()), say=said.append, jobs=2)
        stray = os.path.join(spry.falsify_home(spry.Project(self.root)), "w1", "dist", "old.js")
        os.makedirs(os.path.dirname(stray))
        with open(stray, "w") as handle:
            handle.write("built from an older commit\n")
        self.write({"tests/test_limit.py": TEST_LIMIT + "# newer\n"})
        self.commit("a newer commit")
        said = []
        results = spry.falsify_run(spry.Project(self.root), self.plan(self.both_guards()), say=said.append, jobs=2)
        self.assertEqual([r for _, r, _ in results], ["caught", "survived"])
        self.assertTrue(any(s.startswith("2 worktrees · 2 kept from the last run") for s in said), said)
        self.assertFalse(os.path.exists(stray), "an ignored or untracked file never outlives its run")
        with open(os.path.join(os.path.dirname(os.path.dirname(stray)), "tests", "test_limit.py")) as handle:
            self.assertTrue(handle.read().endswith("# newer\n"), "checked out at the new commit")
        home = spry.falsify_home(spry.Project(self.root))
        held = spry.take_home(home)
        said = []
        spry.falsify_run(spry.Project(self.root), self.plan(self.both_guards()), say=said.append, jobs=2)
        held.close()
        self.assertIn("another run holds the kept worktrees — fresh ones for this run", said)
        self.assertEqual(len(self.worktrees()), 3, "the fresh ones are removed, the kept ones stay")

    def test_a_kept_worktree_a_cleaner_deleted_is_made_again(self):
        # The temporary folder inside a repository, as a project-local tmp in CI would be.
        home = os.path.join(self.root, "tmp", "kept")
        original = spry.falsify_home
        spry.falsify_home = lambda _project: home
        self.addCleanup(setattr, spry, "falsify_home", original)
        self.run_plan(self.both_guards(), jobs=2)
        shutil.rmtree(os.path.join(home, "w1"))
        os.remove(os.path.join(home, "w2", ".git"))
        results = self.run_plan(self.both_guards(), jobs=2)
        self.assertEqual([r for _, r, _ in results], ["caught", "survived"])
        self.assertEqual(self.git("branch", "--show-current").strip(), "sl-1", "the repository above was never checked out")
        self.assertTrue(os.path.isfile(os.path.join(home, "w2", ".git")))

    def slot_config(self, setup):
        """A test that needs its slot prepared — its own database, say — and a setup that logs what it sees."""
        log = os.path.join(self.root, ".git", "slots.log")
        self.write({"tests/test_limit.py": "import os\nif not os.path.exists('.slot-' + os.environ['SPRY_FALSIFY_SLOT']):\n"
                    "    raise SystemExit('no database for this slot')\n" + TEST_LIMIT, ".gitignore": ".slot-*\n__pycache__/\n"})
        self.configure(setup=setup.replace("LOG", log))
        self.commit("a test that needs its slot prepared")
        return log

    def test_each_slot_is_set_up_before_its_first_test(self):
        log = self.slot_config("python3 -c \"import os; e = os.environ; open('.slot-' + e['SPRY_FALSIFY_SLOT'], 'w'); "
                               "open('LOG', 'a').write(e['SPRY_FALSIFY_SLOT'] + '/' + e['SPRY_FALSIFY_SLOTS'] + ' ' "
                               "+ e.get('npm_config_verify_deps_before_run', '-') + '\\n')\"")
        for jobs, seen in ((1, ["1/1 -"]), (2, ["1/2 false", "2/2 false"])):
            open(log, "w").close()
            results = self.run_plan(self.both_guards(), jobs=jobs)
            self.assertEqual([r for _, r, _ in results], ["caught", "survived"], jobs)
            with open(log) as handle:
                self.assertEqual(handle.read().split("\n")[:-1], seen)
        self.configure(setup="")
        os.remove(os.path.join(self.root, ".slot-1"))
        results = self.run_plan(self.both_guards())
        self.assertEqual([r for _, r, _ in results], ["unreliable", "unreliable"], "no slot set up: a red baseline")

    def test_worktrees_setup_readies_a_slot_with_its_worktree_and_slot(self):
        log = self.slot_config("")
        path = os.path.join(self.root, "spry", "spry.config.json")
        with open(path) as handle:
            config = json.load(handle)
        config["falsify"]["setup"] = "python3 -c \"raise SystemExit('the old name is not used')\""
        config["worktrees"] = {"setup": "python3 -c \"import os; e = os.environ; open('.slot-' + e['SPRY_FALSIFY_SLOT'], 'w'); "
                               "open('LOG', 'a').write(e['SPRY_WORKTREE'] + '/' + e['SPRY_WORKTREE_NAME'] + '/' "
                               "+ e['SPRY_FALSIFY_SLOT'] + '\\n')\"".replace("LOG", log)}
        with open(path, "w") as handle:
            json.dump(config, handle)
        self.commit("worktrees.setup")
        for jobs, seen in ((1, ["0/main/1"]), (2, ["0/main/1", "0/main/2"])):
            open(log, "w").close()
            results = self.run_plan(self.both_guards(), jobs=jobs)
            self.assertEqual([r for _, r, _ in results], ["caught", "survived"], jobs)
            with open(log) as handle:
                self.assertEqual(sorted(handle.read().split("\n")[:-1]), seen)

    def test_a_slot_with_a_red_baseline_says_why_once_and_hands_its_controls_on(self):
        # The set-up readies every slot but the second: its baseline breaks, the others' do not.
        self.slot_config("python3 -c \"import os; n = os.environ['SPRY_FALSIFY_SLOT']; "
                         "n == '2' or open('.slot-' + n, 'w')\"")
        said = []
        results = spry.falsify_run(spry.Project(self.root), self.plan(self.both_guards()), say=said.append, jobs=3)
        self.assertEqual([(r, note) for _, r, note in results], [("caught", ""), ("survived", "")])
        left = [s for s in said if "left out" in s]
        self.assertEqual(left, ["slot 2 left out — baseline broken · 2 test files · `python3 run.py {files}` — "
                                "no database for this slot — its controls run in the other slots"])
        self.assertEqual([s for s in said if s.startswith("baseline")], ["baseline green · 2 test files"])

    def test_every_slot_green_says_what_it_always_said(self):
        said = []
        spry.falsify_run(spry.Project(self.root), self.plan(self.both_guards()), say=said.append, jobs=2)
        self.assertEqual([s for s in said if "baseline" in s or "left out" in s], ["baseline green · 2 test files"])

    def test_a_baseline_red_in_every_slot_is_the_tests_own(self):
        self.slot_config("")
        for jobs in (1, 2):
            said = []
            results = spry.falsify_run(spry.Project(self.root), self.plan(self.both_guards()), say=said.append, jobs=jobs)
            self.assertEqual([(r, note) for _, r, note in results],
                             [("unreliable", "baseline broken: no database for this slot")] * 2)
            self.assertEqual([s for s in said if "baseline" in s],
                             ["baseline broken · 2 test files · `python3 run.py {files}` — no database for this slot"])

    def test_a_failed_setup_stops_the_run(self):
        self.slot_config("python3 -c \"import sys; sys.exit('no database server')\"")
        for jobs in (1, 2):
            with self.assertRaises(spry.PlanError) as caught:
                self.run_plan(self.both_guards(), jobs=jobs)
            self.assertIn("falsify.setup failed in slot 1 (exit 1: no database server) — no control was run",
                          str(caught.exception))
            self.assertEqual(self.source(), LOANS_AFTER)

    def test_parallel_falls_back_to_serial_with_uncommitted_changes(self):
        self.write({"run.py": RUNNER + "# edited\n"})
        said = []
        results = spry.falsify_run(spry.Project(self.root), self.plan(self.both_guards()), say=said.append, jobs=2)
        self.assertTrue(any(s.startswith("serial: tracked files") for s in said), said)
        self.assertEqual([r for _, r, _ in results], ["caught", "survived"])

    def needs_untracked_dependency(self, folder):
        self.write({".gitignore": f"{folder}/\n__pycache__/\n", f"{folder}/helper.py": "READY = True\n",
                    "tests/test_limit.py": f"import sys; sys.path.insert(0, '{folder}')\nimport helper\n" + TEST_LIMIT})
        self.commit("tests need an installed dependency")

    def test_installed_dependencies_are_shared_into_worktrees(self):
        self.needs_untracked_dependency("node_modules")
        results = self.run_plan(self.both_guards(), jobs=2)
        self.assertEqual([r for _, r, _ in results], ["caught", "survived"])

    def test_a_worktree_missing_a_dependency_is_unreliable_never_caught(self):
        self.needs_untracked_dependency("deps")
        results = self.run_plan(self.both_guards(), jobs=2)
        self.assertEqual([r for _, r, _ in results], ["unreliable", "unreliable"])
        self.configure(share=["deps"])
        results = self.run_plan(self.both_guards(), jobs=2)
        self.assertEqual([r for _, r, _ in results], ["caught", "survived"])

    def test_a_serial_runner_still_runs_in_a_worktree(self):
        self.configure(runners=[{"match": ["tests/**"], "cwd": "root", "parallel": False,
                                 "command": "python3 run.py {files}"}])
        results = self.run_plan(self.both_guards(), jobs=2)
        self.assertEqual([r for _, r, _ in results], ["caught", "survived"])
        self.assertEqual(self.source(), LOANS_AFTER)

    def test_jobs_setting(self):
        p = spry.Project(self.root)
        self.assertEqual(spry.jobs_for(p, None, 5), 1, "serial unless asked")
        self.assertEqual(spry.jobs_for(p, 8, 3), 3, "never more worktrees than controls")
        self.configure(parallel=True)
        self.assertGreaterEqual(spry.jobs_for(spry.Project(self.root), None, 5), 2)

    def test_record_writes_the_slice_table(self):
        results = self.run_plan([self.guard("    if overdue:", ["S-1/AC-2"])])
        spry.record_falsify(spry.Project(self.root), "SL-1", spry.falsify_rows(results))
        with open(self.slice_doc) as handle:
            self.assertIn("| if overdue: <!-- f:", handle.read())
        rows = spry.falsify_table(spry.Project(self.root).items["SL-1"])
        self.assertEqual(rows, [["if overdue:", "`if overdue:` → `if False and (overdue):`", "S-1/AC-2", "survived"]])

    def test_recording_a_subset_keeps_the_other_rows(self):
        first = spry.falsify_rows(self.run_plan(self.both_guards()))
        spry.record_falsify(spry.Project(self.root), "SL-1", first + ["| No key | — | S-1/AC-1 | skipped — clock |"])
        # The survivor got a test and is run again alone, renamed in plain words; its key still matches.
        again = first[1].replace("survived", "caught").replace("| if overdue: <!--", "| An overdue member <!--")
        spry.record_falsify(spry.Project(self.root), "SL-1",
                            [again, "| No key | — | S-1/AC-1 | skipped — no clock here |", "| New | — | S-1/AC-2 | caught |"])
        rows = spry.falsify_table(spry.Project(self.root).items["SL-1"])
        self.assertEqual([(r[0], r[3]) for r in rows],
                         [("if count >= 3:", "caught"), ("An overdue member", "caught"),
                          ("No key", "skipped — no clock here"), ("New", "caught")])
        # A row written by hand, then run from the plan, is replaced — not added a second time.
        keyed = "| New <!-- f:0000abcd --> | m | S-1/AC-2 | caught |"
        _, kept = spry.record_falsify(spry.Project(self.root), "SL-1", [keyed, keyed.replace("caught", "survived")])
        rows = spry.falsify_table(spry.Project(self.root).items["SL-1"])
        self.assertEqual([r[0] for r in rows], ["if count >= 3:", "An overdue member", "No key", "New", "New"],
                         "two mutations of one line in one run keep both rows")
        self.assertEqual(kept, 3)
        _, kept = spry.record_falsify(spry.Project(self.root), "SL-1", first, replace=True)
        self.assertEqual(len(spry.falsify_table(spry.Project(self.root).items["SL-1"])), 2)
        self.assertEqual(kept, 0)

        results = self.run_plan(self.both_guards())
        rows = [r.replace("| if count >= 3: <!--", "| A fourth book is refused <!--")
                 .replace("| if overdue: <!--", "| An overdue member is refused <!--") for r in spry.falsify_rows(results)]
        lines = self.merge_lines("\n".join(rows) + "\n")
        self.assertIn(("ok", "falsify: all 2 controls the diff adds were run"), lines)

    def test_tests_naming_the_source_run_first(self):
        self.write({"tests/test_other.py": '"""S-1/AC-1 elsewhere"""\nassert True\n'})
        entry = {"file": "src/loans.py", "_tests": ["tests/test_limit.py", "tests/test_other.py"]}
        self.assertEqual(spry.likely_first(spry.Project(self.root), entry),
                         [["tests/test_limit.py"], ["tests/test_other.py"]])
        entry["_tests"] = ["tests/test_other.py"]
        self.assertEqual(spry.likely_first(spry.Project(self.root), entry), [["tests/test_other.py"]])


    def merge_lines(self, rows):
        with open(self.slice_doc) as handle:
            text = handle.read()
        with open(self.slice_doc, "w") as handle:
            handle.write(text + rows)
        return spry.merge_check(spry.Project(self.root), "SL-1", "main")

    def test_merge_needs_every_control_the_diff_adds(self):
        lines = self.merge_lines("| if count >= 3: | m | S-1/AC-1 | caught |\n")
        self.assertIn(("block", "falsify: `if overdue:` (src/loans.py) was not run — run it, or record it as "
                                "`skipped — <reason>` for a person to accept"), lines)
        self.assertFalse(any("`if count >= 3:`" in x and s == "block" for s, x in lines))

    def test_a_skipped_control_waits_for_a_person(self):
        lines = self.merge_lines("| if count >= 3: | m | S-1/AC-1 | caught |\n| if overdue: | m | S-1/AC-2 | skipped — needs a clock |\n")
        self.assertIn(("ok", "falsify: all 2 controls the diff adds were run"), lines)
        self.assertTrue(any(s == "warn" and '"needs a clock"' in x for s, x in lines), lines)

    def test_criteria_changed_with_the_code_need_the_owner(self):
        path = os.path.join(self.root, "spry/plan/M-1-m/E-1-e/F-1-f/S-1-s/README.md")
        with open(path) as handle:
            text = handle.read()
        with open(path, "w") as handle:
            handle.write(text.replace("state: draft\n", "state: draft\nowner: Asha\n")
                             .replace("| AC-2 | a | b | c |", "| AC-2 | a | b | anything |"))
        blocked = [x for s, x in self.merge_lines("") if s == "block" and "criteria changed" in x]
        self.assertEqual(len(blocked), 1)
        self.assertIn('S-1/AC-2: "a | b | c" → "a | b | anything". Only Asha approves this', blocked[0])
        with open(self.slice_doc) as handle:
            text = handle.read()
        with open(self.slice_doc, "w") as handle:
            handle.write(text.replace("covers:", "criteria_approved_by: Asha\ncovers:"))
        lines = spry.merge_check(spry.Project(self.root), "SL-1", "main")
        self.assertTrue(any(s == "ok" and "approved by Asha" in x for s, x in lines), lines)

    def gate_config(self, fast, affected="python3 run.py tests/test_limit.py"):
        log = os.path.join(tempfile.mkdtemp(), "ran")
        self.addCleanup(shutil.rmtree, os.path.dirname(log))
        path = os.path.join(self.root, "spry", "spry.config.json")
        with open(path) as handle:
            config = json.load(handle)
        config["checks"] = {"fast": [{"name": "lint", "run": fast.replace("LOG", log)}]}
        config["tests"]["affected"] = f"{affected} && echo t >> {log}"
        with open(path, "w") as handle:
            json.dump(config, handle)
        with open(self.slice_doc) as handle:
            text = handle.read()
        with open(self.slice_doc, "w") as handle:
            handle.write(text.replace("## Close summary", "## Work order\n\n### Conflict check\n\n"
                                      "- Checked 2026-10-01 against: S-1\n\n## Close summary"))
        return log

    def gate(self):
        said = []
        code = spry.gate(spry.Project(self.root), say=said.append)
        return code, said

    def ran(self, log):
        return open(log).read().split() if os.path.exists(log) else []

    def test_gate_skips_checks_and_tests_until_code_changes(self):
        log = self.gate_config("echo f >> LOG")
        self.assertEqual(self.gate()[0], 0)
        self.assertEqual(self.ran(log), ["f", "t"])
        code, said = self.gate()
        self.assertEqual(code, 0)
        self.assertTrue(any("skipped: no code changed" in x for x in said), said)
        with open(self.slice_doc, "a") as handle:
            handle.write("\nA note.\n")
        self.gate()
        self.assertEqual(self.ran(log), ["f", "t"], "a document change runs nothing")
        self.write({"src/loans.py": LOANS_AFTER + "# changed\n"})
        self.gate()
        self.assertEqual(self.ran(log), ["f", "t", "f", "t"], "a code change runs everything")

    def lock_on(self):
        """`checks.lock` on, with a lock file of the test's own. Returns its path."""
        lock = os.path.join(tempfile.mkdtemp(), "heavy.lock")
        self.addCleanup(shutil.rmtree, os.path.dirname(lock))
        path = os.path.join(self.root, "spry", "spry.config.json")
        with open(path) as handle:
            config = json.load(handle)
        config.setdefault("checks", {}).update({"lock": True, "lock_path": lock})
        with open(path, "w") as handle:
            json.dump(config, handle)
        return lock

    def hold(self, lock, seconds=None):
        """Another run holds the lock; it lets go after `seconds`, or when the test ends."""
        import fcntl
        handle = open(lock, "w")
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        handle.write(json.dumps({"pid": 4242, "what": "falsify run", "root": "/work/other", "at": time.time() - 125}))
        handle.flush()
        self.addCleanup(handle.close)
        if seconds is not None:
            timer = threading.Timer(seconds, handle.close)
            timer.start()
            self.addCleanup(timer.join)

    @unittest.skipIf(os.name == "nt", "holds the lock with flock")
    def test_a_gate_waits_for_the_lock_and_says_who_holds_it(self):
        log = self.gate_config("echo f >> LOG")
        lock = self.lock_on()
        self.hold(lock, 0.3)
        with unittest.mock.patch.object(spry, "LOCK_POLL", 0.05):
            code, said = self.gate()
        self.assertEqual(code, 0, said)
        waiting = [x for x in said if "waiting for the lock" in x]
        self.assertEqual(len(waiting), 1, "one line, however long the wait")
        self.assertTrue(waiting[0].startswith("– waiting for the lock: falsify run in /work/other (pid 4242) "
                                              "has held it for 2m0"), waiting)
        self.assertLess(said.index(waiting[0]), next(i for i, x in enumerate(said) if "lint" in x), "spry check does not wait")
        self.assertEqual(self.ran(log), ["f", "t"])
        self.assertNotIn("SPRY_LOCK_HELD", os.environ)
        with open(os.path.join(spry.pace_home(spry.Project(self.root)), "steps.jsonl")) as handle:
            step = json.loads(handle.read().strip().split("\n")[-1])
        self.assertGreaterEqual(step["waited"], 0.2)
        self.assertLess(step["seconds"], step["waited"] + 5, "the wait is not the gate's own time")

    @unittest.skipIf(os.name == "nt", "holds the lock with flock")
    def test_a_call_under_a_held_lock_runs_directly(self):
        log = self.gate_config("echo f >> LOG")
        self.hold(self.lock_on())
        with unittest.mock.patch.dict(os.environ, {"SPRY_LOCK_HELD": "1"}):
            code, said = self.gate()
        self.assertEqual(code, 0, said)
        self.assertFalse([x for x in said if "lock" in x], said)
        self.assertEqual(self.ran(log), ["f", "t"])

    def test_the_gate_s_commands_see_that_the_lock_is_held(self):
        log = self.gate_config("echo held=$SPRY_LOCK_HELD >> LOG")
        lock = self.lock_on()
        self.assertEqual(self.gate()[0], 0)
        self.assertEqual(self.ran(log), [f"held={lock}", "t"])
        with open(lock) as handle:
            self.assertEqual(handle.read(), "", "nobody holds it after the run")

    def test_the_lock_is_off_unless_asked_for_and_one_per_clone(self):
        project = spry.Project(self.root)
        self.assertIsNone(spry.lock_path(project))
        path = os.path.join(self.root, "spry", "spry.config.json")
        with open(path) as handle:
            config = json.load(handle)
        with open(path, "w") as handle:
            json.dump({**config, "checks": {"lock": True}}, handle)
        self.commit("lock")
        other = os.path.join(tempfile.mkdtemp(), "wt")
        self.addCleanup(shutil.rmtree, os.path.dirname(other))
        self.git("worktree", "add", "-q", other, "-b", "sl-2")
        here, there = spry.lock_path(spry.Project(self.root)), spry.lock_path(spry.Project(other))
        self.assertEqual(here, there, "every worktree of a clone shares one lock")
        self.assertTrue(here.startswith(tempfile.gettempdir()), here)
        with open(path, "w") as handle:
            json.dump({**config, "checks": {"lock": "yes"}}, handle)
        with self.assertRaises(SystemExit):
            spry.lock_path(spry.Project(self.root))

    def test_falsify_run_holds_the_lock(self):
        lock = self.lock_on()
        self.commit("lock")
        with unittest.mock.patch.object(spry, "heavy_lock", wraps=spry.heavy_lock) as taken:
            results = self.run_plan([self.guard("    if count >= 3:", ["S-1/AC-1"])])
        self.assertEqual([r for _e, r, _n in results], ["caught"])
        self.assertEqual(taken.call_args[0][1], "falsify run")
        self.assertTrue(os.path.exists(lock))
        with unittest.mock.patch.object(spry, "heavy_lock", wraps=spry.heavy_lock) as taken:
            self.run_plan([self.guard("    if count >= 3:", ["S-1/AC-1"])], dry=True)
        taken.assert_not_called()

    def red_config(self, log, output="FAIL  tests/test_limit.py > nothing"):
        """The affected tests fail with this output, and count their runs as `r`."""
        path = os.path.join(self.root, "spry", "spry.config.json")
        with open(path) as handle:
            config = json.load(handle)
        config["tests"]["affected"] = f"echo r >> {log}; echo '{output}'; false"
        with open(path, "w") as handle:
            json.dump(config, handle)

    def gate_state(self):
        with open(os.path.join(self.root, ".spry", "gate", "last.json")) as handle:
            return json.load(handle)

    def test_a_red_gate_ends_on_a_line_saying_where_its_output_is(self):
        log = self.gate_config("echo f >> LOG")
        self.red_config(log)
        code, said = self.gate()
        self.assertEqual(code, 1)
        self.assertEqual(said[-1], "✗ affected tests — failing: tests/test_limit.py · full output .spry/gate/last.log", said)
        with open(os.path.join(self.root, ".spry", "gate", "last.log")) as handle:
            self.assertIn("FAIL  tests/test_limit.py > nothing", handle.read())
        state = self.gate_state()
        self.assertEqual((state["steps"], state["files"], state["load"]), (["affected tests"], ["tests/test_limit.py"], False))

    def test_a_red_gate_does_not_run_again_on_the_same_code(self):
        log = self.gate_config("echo f >> LOG")
        self.red_config(log)
        self.gate()
        code, said = self.gate()
        self.assertEqual((code, self.ran(log)), (1, ["f", "r"]), "nothing ran the second time")
        self.assertTrue(any("not run again" in x for x in said) and any("gate --force" in x for x in said), said)
        self.assertTrue(said[-1].startswith("✗ affected tests — failing: tests/test_limit.py"), said)
        self.assertEqual(spry.gate(spry.Project(self.root), force=True, say=lambda *_: None), 1)
        self.assertEqual(self.ran(log), ["f", "r", "f", "r"], "--force runs it all")
        self.write({"src/loans.py": LOANS_AFTER + "# changed\n"})
        self.gate()
        self.assertEqual(self.ran(log)[4:], ["f", "r"], "changed code runs it")
        self.red_config(log, "FAIL  tests/test_limit.py > another")
        self.gate()
        self.assertEqual(self.ran(log)[6:], ["f", "r"], "a changed command runs it too")

    def test_a_red_gate_from_load_runs_again_on_the_same_code(self):
        log = self.gate_config("echo f >> LOG")
        self.red_config(log, "Error: [vitest-pool]: Failed to start forks worker")
        self.gate()
        self.assertTrue(self.gate_state()["load"])
        self.gate()
        self.assertEqual(self.ran(log), ["f", "r", "f", "r"], "the machine broke it, not the code")

    def test_a_pass_forgets_the_red_before_it_and_a_fast_pass_only_its_own(self):
        log = self.gate_config("echo f >> LOG")
        self.red_config(log)
        self.gate()
        spry.gate(spry.Project(self.root), say=lambda *_: None, fast=True)
        self.assertTrue(os.path.exists(os.path.join(self.root, ".spry", "gate", "last.json")),
                        "fast checks passing say nothing of the tests")
        self.write({"src/loans.py": LOANS_AFTER + "# changed\n"})
        path = os.path.join(self.root, "spry", "spry.config.json")
        with open(path) as handle:
            config = json.load(handle)
        config["tests"]["affected"] = f"echo t >> {log}"
        with open(path, "w") as handle:
            json.dump(config, handle)
        self.assertEqual(self.gate()[0], 0)
        self.assertFalse(os.path.exists(os.path.join(self.root, ".spry", "gate", "last.json")))
        self.assertFalse(os.path.exists(os.path.join(self.root, ".spry", "gate", "last.log")))

    def two_failing_fast_checks(self, keep=None):
        log = self.gate_config("echo f >> LOG; echo bad lint; exit 1")
        path = os.path.join(self.root, "spry", "spry.config.json")
        with open(path) as handle:
            config = json.load(handle)
        config["checks"]["fast"].append({"name": "types", "run": f"echo y >> {log}; echo bad type; exit 2"})
        if keep:
            config["gate"] = {"keep_going": keep}
        with open(path, "w") as handle:
            json.dump(config, handle)
        return log

    def test_every_fast_check_runs_and_the_tests_wait_for_them(self):
        log = self.two_failing_fast_checks()
        code, said = self.gate()
        self.assertEqual((code, self.ran(log)), (1, ["f", "y"]), "both fast checks ran, the tests did not")
        self.assertTrue(any("tests did not run" in x for x in said), said)
        self.assertEqual(said[-1], "✗ lint, types · full output .spry/gate/last.log")
        self.assertEqual(self.gate_state()["steps"], ["lint", "types"])

    def test_keep_going_off_stops_at_the_first_failure_and_all_runs_the_tests_too(self):
        log = self.two_failing_fast_checks("off")
        self.assertEqual((self.gate()[0], self.ran(log)), (1, ["f"]))
        log = self.two_failing_fast_checks("all")
        shutil.rmtree(os.path.join(self.root, ".spry", "gate"))
        self.assertEqual((self.gate()[0], self.ran(log)), (1, ["f", "y", "t"]))
        self.assertEqual(self.gate_state()["steps"], ["lint", "types"])

    def test_keep_going_takes_only_the_values_it_knows(self):
        self.two_failing_fast_checks("sometimes")
        with self.assertRaises(SystemExit) as raised:
            self.gate()
        self.assertIn("gate.keep_going is `sometimes`", str(raised.exception))

    def test_a_failing_test_step_stops_the_gate_with_no_note_about_checks(self):
        log = self.gate_config("echo f >> LOG")
        self.red_config(log)
        code, said = self.gate()
        self.assertFalse(any("did not run" in x for x in said), said)

    def test_gate_failed_reruns_only_the_files_the_red_gate_named(self):
        log = self.gate_config("echo f >> LOG")
        self.red_config(log, "FAILED tests/test_limit.py::t - boom")
        self.gate()
        code, said = [], []
        said = []
        self.assertEqual(spry.gate(spry.Project(self.root), say=said.append, failed=True), 0, said)
        self.assertEqual(self.ran(log), ["f", "r"], "only the runner ran, not the fast checks or the affected tests")
        self.assertTrue(any("nothing stamped" in x for x in said), said)
        self.assertFalse(os.path.exists(os.path.join(self.root, ".spry", "green")))
        self.assertEqual(self.gate_state()["cleared"], ["affected tests"], "the record stays, with the step marked cleared")
        self.gate()
        self.assertEqual(self.ran(log)[2:], ["f", "r"], "so the full gate runs, though the code is the same")

    def test_gate_failed_that_fails_keeps_the_red_for_the_next_one(self):
        log = self.gate_config("echo f >> LOG")
        self.red_config(log, "FAILED tests/test_limit.py::t - boom")
        self.gate()
        path = os.path.join(self.root, "spry", "spry.config.json")
        with open(path) as handle:
            config = json.load(handle)
        config["falsify"]["runners"][0]["command"] = "echo 'FAILED {files}::t'; false"
        with open(path, "w") as handle:
            json.dump(config, handle)
        said = []
        self.assertEqual(spry.gate(spry.Project(self.root), say=said.append, failed=True), 1)
        self.assertEqual(said[-1], "✗ affected tests — failing: tests/test_limit.py · full output .spry/gate/last.log", said)
        self.assertEqual(self.gate_state()["steps"], ["affected tests"])

    def test_gate_failed_says_why_it_has_nothing_to_run(self):
        said = []
        self.assertEqual(spry.gate(spry.Project(self.root), say=said.append, failed=True), 1)
        self.assertTrue(any("no red gate" in x for x in said), said)
        log = self.gate_config("echo f >> LOG; echo bad; exit 1")
        self.gate()
        said = []
        self.assertEqual(spry.gate(spry.Project(self.root), say=said.append, failed=True), 1)
        self.assertTrue(any("named no test file" in x for x in said), said)
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(spry.main(["--root", self.root, "gate", "--failed"]), 1)

    def test_gate_failed_is_no_pass_when_a_named_file_is_missing(self):
        log = self.gate_config("echo f >> LOG")
        self.red_config(log, "FAILED tests/test_limit.py::t\nFAILED tests/test_gone.py::t")
        self.gate()
        said = []
        self.assertEqual(spry.gate(spry.Project(self.root), say=said.append, failed=True), 1, said)
        self.assertTrue(any("tests/test_gone.py" in x for x in said), said)
        self.assertEqual(self.gate_state().get("cleared", []), [], "a run that missed a file clears nothing")
        self.assertEqual(self.gate()[0], 1)
        self.assertEqual(self.ran(log), ["f", "r"], "the red still stands for the full gate")

    def test_gate_failed_does_not_clear_a_check_that_is_still_red(self):
        log = self.two_failing_fast_checks("all")
        path = os.path.join(self.root, "spry", "spry.config.json")
        with open(path) as handle:
            config = json.load(handle)
        config["checks"]["fast"] = config["checks"]["fast"][:1]
        config["tests"]["affected"] = f"echo r >> {log}; echo 'FAILED tests/test_limit.py::t'; false"
        with open(path, "w") as handle:
            json.dump(config, handle)
        self.gate()
        self.assertEqual(self.gate_state()["steps"], ["lint", "affected tests"])
        said = []
        self.assertEqual(spry.gate(spry.Project(self.root), say=said.append, failed=True), 1, said)
        self.assertTrue(any("lint is still red" in x for x in said), said)
        code, said = self.gate()
        self.assertEqual(code, 1)
        self.assertTrue(said[-1].startswith("✗ lint"), said)
        self.assertNotIn("affected tests", said[-1])

    def test_a_failed_gate_failed_leaves_the_record_as_the_red_gate_made_it(self):
        log = self.gate_config("echo f >> LOG")
        self.red_config(log, "FAILED tests/test_limit.py::t - boom")
        self.gate()
        before = self.gate_state()
        path = os.path.join(self.root, "spry", "spry.config.json")
        with open(path) as handle:
            config = json.load(handle)
        config["falsify"]["runners"][0]["command"] = "echo 'FAILED {files}::t'; false"
        with open(path, "w") as handle:
            json.dump(config, handle)
        self.write({"src/loans.py": LOANS_AFTER + "# changed\n"})
        spry.gate(spry.Project(self.root), say=lambda *_: None, failed=True)
        after = self.gate_state()
        self.assertEqual((after["code"], after["steps"], after["commands"]), (before["code"], before["steps"], before["commands"]))

    def test_the_machine_is_told_from_the_code_by_a_list_a_project_can_replace(self):
        log = self.gate_config("echo f >> LOG")
        self.red_config(log, "connect ECONNREFUSED 127.0.0.1:5432")
        self.gate()
        self.assertTrue(self.gate_state()["load"], "a service that was down is not the code")
        self.gate()
        self.assertEqual(self.ran(log), ["f", "r", "f", "r"])
        path = os.path.join(self.root, "spry", "spry.config.json")
        with open(path) as handle:
            config = json.load(handle)
        config["tests"]["load_when"] = "my own worker message"
        with open(path, "w") as handle:
            json.dump(config, handle)
        shutil.rmtree(os.path.join(self.root, ".spry", "gate"))
        self.gate()
        self.assertFalse(self.gate_state()["load"], "load_when replaces the built-in list")

    def test_pace_does_not_count_a_red_gate_that_was_not_run_again_as_another_failure(self):
        gates = [{"fast": False, "ok": False}, {"fast": False, "ok": False, "skipped": "failed"},
                 {"fast": False, "ok": True, "skipped": "stamp"}]
        self.assertEqual(len(spry.pace_full_gates({"gates": gates})), 2)

    def test_failing_files_reads_what_vitest_jest_and_pytest_print(self):
        out = ("\x1b[41m FAIL \x1b[49m unit src/routes/users.test.ts > inviting > refuses\n"
               "@connect/web:test: FAIL  src/a.spec.tsx\nFAILED tests/test_x.py::test_a - boom\n"
               "FAIL  src/routes/users.test.ts > again\nFAIL  |integration| src/send.integration.test.ts > sends > S-1/AC-1 x\n"
               "Tests  3 failed\n")
        self.assertEqual(spry.failing_files(out), ["src/routes/users.test.ts", "src/a.spec.tsx", "tests/test_x.py",
                                                   "src/send.integration.test.ts"])
        self.assertEqual(spry.failing_files("ERROR tests/test_y.py - ImportError\nFAIL  src\\win.test.ts > x\n"),
                         ["tests/test_y.py", "src/win.test.ts"], "a test that would not load, and a Windows path")
        self.assertEqual(spry.failing_files("all fine\nFAIL\tgithub.com/x/pkg\t0.1s\n--- FAIL: TestX (0.00s)\nFAIL: test_y (m.C)\n"), [])
        self.assertEqual(spry.gate_pointer(["affected tests"], list("abcde")),
                         "✗ affected tests — failing: a, b, c (+2 more) · full output .spry/gate/last.log")

    def test_gate_fast_runs_no_tests_and_stamps_nothing(self):
        log = self.gate_config("echo f >> LOG")
        said = []
        self.assertEqual(spry.gate(spry.Project(self.root), say=said.append, fast=True), 0)
        self.assertEqual(self.ran(log), ["f"], "fast checks only")
        self.assertTrue(any("tests not run" in x for x in said), said)
        self.assertFalse(os.path.exists(os.path.join(self.root, ".spry", "green")), "never stamped green")
        self.gate()
        self.assertEqual(self.ran(log), ["f", "f", "t"], "the full gate still runs everything")
        spry.gate(spry.Project(self.root), say=lambda *_: None, fast=True)
        self.assertEqual(self.ran(log), ["f", "f", "t"], "green already covers the fast checks")

    def test_gate_fast_from_the_command_line_and_its_failure(self):
        log = self.gate_config("echo f >> LOG && exit 3", affected="<affected tests command>")
        with contextlib.redirect_stdout(io.StringIO()):
            code = spry.main(["--root", self.root, "gate", "--fast"])
        self.assertEqual(code, 1, "a failing fast check fails, and an unset tests.affected is no matter")
        self.assertEqual(self.ran(log), ["f"])

    def test_gate_skips_a_documents_only_branch_after_a_rebase(self):
        remote = os.path.join(tempfile.mkdtemp(), "remote.git")
        self.addCleanup(shutil.rmtree, os.path.dirname(remote))
        subprocess.run(["git", "init", "-q", "--bare", "-b", "main", remote], check=True)
        self.git("remote", "add", "origin", remote)
        self.git("push", "-q", "origin", "sl-1:main")
        self.git("checkout", "-q", "-b", "other", "sl-1")
        self.write({"src/loans.py": LOANS_AFTER + "# another merge\n"})
        self.commit("code")
        self.git("checkout", "-q", "-b", "docs", "sl-1")
        log = self.gate_config("echo f >> LOG")
        self.commit("docs")
        self.git("push", "-q", "origin", "other:main")
        self.git("fetch", "-q", "origin")
        code, said = self.gate()
        self.assertEqual((code, self.ran(log)), (0, []), "main moved on with code: not the branch's")
        self.git("rebase", "-q", "origin/main")
        code, said = self.gate()
        self.assertEqual((code, self.ran(log)), (0, []), said)
        self.assertTrue(any("skipped: only documents changed since origin/main" in x for x in said), said)
        self.assertEqual(spry.gate(spry.Project(self.root), force=True, say=lambda *_: None), 0)
        self.assertEqual(self.ran(log), ["f", "t"], "--force runs everything")
        os.remove(os.path.join(self.root, ".spry", "green"))
        self.git("mv", "tests/test_overdue.py", "tests/test_overdue.md")
        self.gate()
        self.assertEqual(self.ran(log), ["f", "t", "f"], "a test renamed to a document is a test removed: tests-only")
        self.git("mv", "tests/test_overdue.md", "tests/test_overdue.py")
        self.write({"src/new.py": "x = 1\n"})
        self.gate()
        self.assertEqual(self.ran(log), ["f", "t", "f"] + ["f", "t"], "an untracked code file runs everything")
        os.remove(os.path.join(self.root, "src/new.py"))
        self.write({"src/loans.py": LOANS_AFTER + "# dirty\n"})
        self.gate()
        self.assertEqual(self.ran(log), ["f", "t", "f"] + ["f", "t"] * 2, "a dirty code file runs everything")
        self.commit("code on the branch")
        os.remove(os.path.join(self.root, ".spry", "green"))
        self.gate()
        self.assertEqual(self.ran(log), ["f", "t", "f"] + ["f", "t"] * 3, "a committed code change runs everything")

    def origin_main(self):
        remote = os.path.join(tempfile.mkdtemp(), "remote.git")
        self.addCleanup(shutil.rmtree, os.path.dirname(remote))
        subprocess.run(["git", "init", "-q", "--bare", "-b", "main", remote], check=True)
        self.git("remote", "add", "origin", remote)
        self.git("push", "-q", "origin", "HEAD:main")
        self.git("fetch", "-q", "origin")

    def config_tests_only(self, log):
        path = os.path.join(self.root, "spry", "spry.config.json")
        with open(path) as handle:
            config = json.load(handle)
        config["tests"]["always"] = [{"name": "words", "run": f"echo a >> {log}"}]
        config["falsify"]["runners"][0]["command"] += f" && echo c >> {log}"
        with open(path, "w") as handle:
            json.dump(config, handle)

    def test_gate_runs_only_the_changed_tests_when_the_branch_changed_only_tests(self):
        log = self.gate_config("echo f >> LOG")
        self.config_tests_only(log)
        self.commit("config")
        self.origin_main()
        self.git("checkout", "-q", "-b", "steadier")
        self.write({"tests/test_limit.py": TEST_LIMIT + "# steadier\n"})
        self.commit("a steadier test")
        code, said = self.gate()
        self.assertEqual((code, self.ran(log)), (0, ["f", "c", "a"]), said)
        self.assertTrue(any("tests-only: the branch changes only test files since origin/main" in x for x in said), said)
        with open(os.path.join(self.root, ".spry", "green")) as handle:
            self.assertEqual(json.load(handle)["mode"], "tests-only", "the stamp says what it vouches for")
        self.gate()
        self.assertEqual(self.ran(log), ["f", "c", "a"], "stamped: nothing runs again")
        said = []
        self.assertEqual(spry.gate(spry.Project(self.root), say=said.append, full=True), 0)
        self.assertEqual(self.ran(log), ["f", "c", "a", "f", "t", "a"], "--full runs the affected tests past a tests-only stamp")
        self.assertFalse(any("tests-only" in x for x in said), said)
        self.git("rm", "-q", "tests/test_overdue.py")
        self.git("commit", "-q", "-m", "a test removed")
        self.gate()
        self.assertEqual(self.ran(log)[6:], ["f", "c", "a"], "a removed test file is not run; the changed one still is")
        self.write({"src/loans.py": LOANS_AFTER + "# changed\n"})
        self.gate()
        self.assertEqual(self.ran(log)[9:], ["f", "t", "a"], "a source change runs the affected tests")

    def test_gate_takes_the_long_way_when_another_file_mentions_a_changed_test(self):
        log = self.gate_config("echo f >> LOG")
        self.config_tests_only(log)
        self.write({"tests/shared.py": "from test_limit import lend\n"})
        self.commit("a helper that imports a test file")
        self.origin_main()
        self.git("checkout", "-q", "-b", "steadier")
        self.write({"tests/test_limit.py": TEST_LIMIT + "# steadier\n"})
        code, said = self.gate()
        self.assertEqual((code, self.ran(log)), (0, ["f", "t", "a"]), said)
        self.assertTrue(any("tests/shared.py mentions tests/test_limit.py" in x for x in said), said)
        with open(os.path.join(self.root, ".spry", "green")) as handle:
            self.assertNotIn("mode", json.load(handle))

    def test_gate_takes_the_long_way_when_no_runner_takes_a_changed_test(self):
        log = self.gate_config("echo f >> LOG")
        path = os.path.join(self.root, "spry", "spry.config.json")
        with open(path) as handle:
            config = json.load(handle)
        config["falsify"]["runners"][0]["match"] = ["other/**"]
        with open(path, "w") as handle:
            json.dump(config, handle)
        self.commit("config")
        self.origin_main()
        self.git("checkout", "-q", "-b", "steadier")
        self.write({"tests/test_limit.py": TEST_LIMIT + "# steadier\n"})
        code, said = self.gate()
        self.assertEqual((code, self.ran(log)), (0, ["f", "t"]), said)
        self.assertTrue(any("no falsify runner matches tests/test_limit.py" in x for x in said), said)

    def test_gate_takes_the_long_way_for_a_test_file_not_named_as_one(self):
        log = self.gate_config("echo f >> LOG")
        self.config_tests_only(log)
        path = os.path.join(self.root, "spry", "spry.config.json")
        with open(path) as handle:
            config = json.load(handle)
        config["tests"]["match"] = ["tests/**"]
        with open(path, "w") as handle:
            json.dump(config, handle)
        self.commit("config")
        self.origin_main()
        self.git("checkout", "-q", "-b", "fixture")
        self.write({"tests/conftest.py": "LIMIT = 3\n"})
        code, said = self.gate()
        self.assertEqual((code, self.ran(log)), (0, ["f", "t", "a"]), said)
        self.assertTrue(any("tests/conftest.py is not named as a test file" in x for x in said), said)

    def test_gate_tests_only_takes_an_uncommitted_test_and_always_waits_for_tests(self):
        log = self.gate_config("echo f >> LOG")
        self.config_tests_only(log)
        self.commit("config")
        self.origin_main()
        self.git("checkout", "-q", "-b", "new-test")
        self.write({"tests/test_more.py": TEST_LIMIT})
        spry.gate(spry.Project(self.root), say=lambda *_: None, fast=True)
        self.assertEqual(self.ran(log), ["f"], "--fast runs no tests, so not tests.always either")
        code, said = self.gate()
        self.assertEqual((code, self.ran(log)), (0, ["f", "f", "c", "a"]), said)
        self.write({"tests/test_more.py": TEST_LIMIT + "# again\n"})
        path = os.path.join(self.root, "spry", "spry.config.json")
        with open(path) as handle:
            config = json.load(handle)
        config["tests"]["always"] = ["exit 4"]
        with open(path, "w") as handle:
            json.dump(config, handle)
        self.assertEqual(self.gate()[0], 1, "a failing tests.always fails the gate")
        config["tests"]["always"] = ["<banned words>"]
        with open(path, "w") as handle:
            json.dump(config, handle)
        with self.assertRaises(SystemExit):
            self.gate()

    def test_gate_runs_everything_when_it_cannot_find_the_main_branch(self):
        log = self.gate_config("echo f >> LOG")
        self.git("checkout", "-q", "-b", "docs", "sl-1")
        self.commit("docs")
        self.gate()
        self.assertEqual(self.ran(log), ["f", "t"], "no origin/main: unsure, so it runs")

    def test_gate_stops_at_the_first_failure(self):
        log = self.gate_config("echo f >> LOG && exit 3")
        code, said = self.gate()
        self.assertEqual(code, 1)
        self.assertEqual(self.ran(log), ["f"], "tests never ran after lint failed")
        self.assertIn("✗ lint", " ".join(said))
        code, _ = self.gate()
        self.assertEqual((code, self.ran(log)), (1, ["f"]), "the same red on the same code is shown, not run again")
        self.assertFalse(os.path.exists(os.path.join(self.root, ".spry", "green")), "a failure is never stamped green")
        spry.gate(spry.Project(self.root), force=True, say=lambda *_: None)
        self.assertEqual(self.ran(log), ["f", "f"], "--force runs it again")

    def test_gate_retries_a_timeout_quietly_but_never_a_real_failure(self):
        flag = os.path.join(self.root, "busy")
        retry = "python3 run.py tests/test_limit.py"
        flaky = f"if [ -f {flag} ]; then rm {flag}; echo 'Test timed out in 5000ms'; exit 1; fi; {retry}"
        log = self.gate_config("true", affected=flaky)
        path = os.path.join(self.root, "spry", "spry.config.json")
        with open(path) as handle:
            config = json.load(handle)
        config["tests"]["retry"] = f"{retry} && echo r >> {log}"
        with open(path, "w") as handle:
            json.dump(config, handle)
        open(flag, "w").close()
        code, said = self.gate()
        self.assertEqual(code, 0, said)
        self.assertEqual(self.ran(log), ["r"], "the quiet retry ran, once")
        with open(os.path.join(self.root, ".spry", "pace", "steps.jsonl")) as handle:
            line = [json.loads(x) for x in handle][-1]
        self.assertTrue(line["retried"])
        self.assertGreaterEqual(line["retry_lost"], 0, "the first attempt's seconds stand in the step log")
        self.write({"src/loans.py": "broken(\n"})
        code, said = self.gate()
        self.assertEqual(code, 1)
        self.assertFalse(any("quiet retry" in x for x in said), "an assertion or syntax error is not retried")

    def test_gate_refuses_a_placeholder(self):
        self.gate_config("<lint command>")
        with self.assertRaises(SystemExit):
            self.gate()

    def test_gate_logs_no_tests_when_a_fast_check_stops_it(self):
        self.gate_config("false")
        self.gate()
        with open(os.path.join(self.root, ".spry", "pace", "steps.jsonl")) as handle:
            line = json.loads(handle.read())
        self.assertEqual((line["ok"], line["tests"], [s[0] for s in line["steps"]]), (False, False, ["spry check", "lint"]))

    def test_gate_logs_the_rules_a_red_check_names(self):
        self.gate_config("echo 'a.ts:1:2: error oxc(no-map-spread): slow'; echo 'a.ts:9:2: error oxc(no-map-spread): slow'; "
                         "echo 'b.ts(3,7): error TS2741: missing'; exit 1")
        self.gate()
        with open(os.path.join(self.root, ".spry", "pace", "steps.jsonl")) as handle:
            line = json.loads(handle.read())
        self.assertEqual(line["red"], {"lint": {"oxc(no-map-spread)": 2, "TS2741": 1}})
        self.gate_config("echo 'x.ts (0ms)'; echo 'Format issues found in above 1 files.'; exit 1")
        self.gate()
        with open(os.path.join(self.root, ".spry", "pace", "steps.jsonl")) as handle:
            line = [json.loads(x) for x in handle][-1]
        self.assertNotIn("red", line, "a check that names no rule adds nothing: its failed step already says it was red")

    def test_a_rule_is_read_from_each_linter_s_own_line(self):
        said = {"a.ts:1:2: error unicorn(no-array-sort): Use toSorted": "unicorn(no-array-sort)",
                "  × eslint(no-unused-vars): 'x' is declared but never used.": "eslint(no-unused-vars)",
                "@app/api:typecheck: src/a.ts(33,7): error TS2741: Property 'x' is missing": "TS2741",
                "  12:5  error  Unexpected any. Specify a different type  @typescript-eslint/no-explicit-any": "@typescript-eslint/no-explicit-any",
                "src/a.py:1:8: F401 `os` imported but unused": "F401",
                "F401 [*] `os` imported but unused": "F401",
                "src/a.py:3: error: Argument 1 has incompatible type \"str\"  [arg-type]": "arg-type",
                "a.ts:2:1 lint/style/noVar  FIXABLE": "lint/style/noVar"}
        for line, rule in said.items():
            self.assertEqual(spry.gate_rules(line), {rule: 1}, line)
        self.assertEqual(spry.gate_rules("Checking formatting...\napps/a.ts (0ms)\n  12:5  warning  later  no-console\n"
                                         "see index of(things): here\n"), {})
        many = "\n".join(f"a.ts:1:1: error p(rule-{n}): x" for n in range(30)) + "\na.ts:1:1: error p(rule-7): x"
        self.assertEqual((len(spry.gate_rules(many)), next(iter(spry.gate_rules(many)))), (spry.GATE_RULES_KEPT, "p(rule-7)"))

    def test_gate_writes_each_run_to_the_step_log(self):
        self.gate_config("echo f >> LOG")
        self.gate()
        self.gate()
        with open(os.path.join(self.root, ".spry", "pace", "steps.jsonl")) as handle:
            first, second = [json.loads(line) for line in handle]
        self.assertEqual((first["command"], first["branch"], first["ok"], first["tests"]), ("gate", "sl-1", True, True))
        self.assertEqual([s[0] for s in first["steps"]], ["spry check", "lint", "affected tests"])
        self.assertEqual(second["skipped"], "stamp")
        self.assertEqual(second["steps"][0][0], "spry check")

    def test_gate_says_each_step_as_it_starts_and_how_long_it_usually_takes(self):
        self.gate_config("echo f >> LOG")
        code, said = self.gate()
        self.assertEqual(code, 0)
        self.assertIn("→ lint", said, "no history: the step is named, with no estimate")
        self.assertFalse(any(x.startswith("– about") for x in said), said)
        rows = [{"command": "gate", "steps": [["spry check", 0.1, True], ["lint", lint, ok], ["affected tests", tests, True],
                                              ["changed tests", 9.0, True]]}
                for lint, ok, tests in [(1.0, True, 60.0), (2.0, True, 240.0), (3.0, True, 200.0), (100.0, False, 200.0)]]
        with open(os.path.join(self.root, ".spry", "pace", "steps.jsonl"), "w") as handle:
            handle.write("".join(json.dumps(r) + "\n" for r in rows) + "not json\n")
        self.assertEqual(spry.step_estimates(spry.Project(self.root), ["lint", "affected tests", "changed tests"]),
                         {"lint": 2.0, "affected tests": 200.0}, "the median of green runs; a red one and given files never count")
        said = []
        self.assertEqual(spry.gate(spry.Project(self.root), force=True, say=said.append), 0)
        self.assertIn("– about 3m22s by the last green runs", said)
        self.assertLess(said.index("→ lint · usually 2s"), said.index("→ affected tests · usually 3m20s"))
        self.assertEqual([spry.duration(s) for s in (42, 220, 3900)], ["42s", "3m40s", "1h05m"])

    def test_the_tool_writes_each_line_as_it_goes_even_into_a_pipe(self):
        done = subprocess.run([sys.executable, "-c", "import sys; sys.path.insert(0, sys.argv[1]); import spry\n"
                               "try: spry.main(['--version'])\nexcept SystemExit: pass\n"
                               "sys.stderr.write(str(sys.stdout.line_buffering))", os.path.dirname(spry.__file__)],
                              capture_output=True, text=True)
        self.assertEqual(done.stderr, "True")

    def test_changed_tells_ci_whether_tests_must_run(self):
        p = spry.Project(self.root)
        self.assertTrue(spry.code_changed_since(p, "main"))
        self.git("checkout", "-q", "-b", "docs-only", "main")
        self.write({"spry/plan/M-1-m/README.md": "---\nid: M-1\ntitle: m2\nstate: draft\n---\n# M-1\n", "notes.md": "x\n"})
        self.commit("docs")
        self.assertFalse(spry.code_changed_since(spry.Project(self.root), "main"))
        self.assertTrue(spry.code_changed_since(spry.Project(self.root), "0000000000000000000000000000000000000000"))

class Mutations(unittest.TestCase):
    def test_javascript_guard_is_made_never_true(self):
        self.assertEqual(spry.mutations_for("  if (existing) {")[0], ("  if (false && (existing)) {", "never true"))

    def test_boundary_flip_and_throw(self):
        self.assertEqual(spry.mutations_for("  const ok = n <= max;")[0][1], "`<=` → `<`")
        self.assertEqual(spry.mutations_for("  throw new Conflict();")[0], ("", "delete the line"))

    def test_never_negation_and_never_a_generic(self):
        for line in ("  const same = a === b;", "  return items as Array<Item> || [];",
                     "  const p: Promise<boolean> = check(a && b);"):
            self.assertEqual(spry.mutations_for(line), [("", "delete the line")], line)
        self.assertEqual(spry.mutations_for("  const late = days > limit;")[0][1], "` > ` → ` >= `")

    def test_a_control_refuses_stops_or_decides(self):
        for line in ("  if (a) {", "  } else if (b) {", "    raise Limit()", "  return null;", "  WHERE org_id = $1",
                     "    AND deleted_at IS NULL", "    .where(eq(loans.org, org))", "  assert(count < 3);"):
            self.assertTrue(spry.is_control(line), line)
        for line in ("  const name = input || 'x';", "  ...(x === undefined ? {} : { x }),", "  {open && <Menu />}",
                     "  // if a == b, refuse", "  const same = a === b;", "  return a.id === b.id;"):
            self.assertFalse(spry.is_control(line), line)
            self.assertTrue(spry.is_control(line, rule="operators"), line)

    def test_a_clause_of_a_condition_over_several_lines_is_a_control(self):
        condition = "function f() {\n  if (\n    a === b &&\n    g(c, (d)) !== e\n  ) {\n    stop();\n  }\n}\n"
        self.assertTrue(spry.is_control("    a === b &&", condition))
        self.assertTrue(spry.is_control("    g(c, (d)) !== e", condition))
        call = "function f() {\n  if (ready) {\n    send(\n      a === b,\n    );\n  }\n}\n"
        self.assertFalse(spry.is_control("      a === b,", call), "an argument, inside an `if`'s block but not its condition")

    def test_never_a_deletion_that_cannot_parse(self):
        write_one = (None, "write one")
        self.assertEqual(spry.mutations_for("  throw new Conflict();", "  if (x) {", "  }")[0], ("", "delete the line"))
        self.assertEqual(spry.mutations_for("  throw new Conflict(", "  if (x) {", "    'no'")[0], write_one)
        self.assertEqual(spry.mutations_for("    throw new Conflict();", "  if (x)", "  next();")[0], write_one,
                         "the only statement of an `if` without braces: deleting it would guard the next line")
        self.assertEqual(spry.mutations_for("    a === b,", "  const o = {", "  };")[0], write_one)
        self.assertEqual(spry.mutations_for("    a === b", "    ready &&", "  ) {")[0], write_one)
        self.assertEqual(spry.mutations_for("  const y = a === b", "  go();", "    ? one")[0], write_one)
        self.assertEqual(spry.mutations_for("        raise Limit()", "    if n > 3:", "    return n")[0],
                         ("        pass", "replace with `pass`"))
        self.assertEqual(spry.mutations_for("        raise Limit()", "        log(n)", "    return n")[0], ("", "delete the line"))
        self.assertEqual(spry.mutations_for("    WHERE id = $1", "    SELECT * FROM loans", "      AND org_id = $2")[0], write_one,
                         "the query would no longer parse, and every test would fail: a false catch")
        self.assertEqual(spry.mutations_for("      AND org_id = $2", "    WHERE id = $1", "      AND gone IS NULL")[0], ("", "delete the line"))
        self.assertEqual(spry.mutations_for("    WHERE id = $1", "    SELECT * FROM loans", "  `, [id]);")[0], ("", "delete the line"))

    def test_a_guard_with_its_statement_on_the_same_line_is_made_never_true(self):
        self.assertEqual(spry.mutations_for("  if (!ok(a, ')')) throw new Gone('no (such) loan');", "", "")[0],
                         ("  if (false && (!ok(a, ')'))) throw new Gone('no (such) loan');", "never true"))
        self.assertEqual(spry.mutations_for("  } else if (late) {", "", "")[0], ("  } else if (false && (late)) {", "never true"))
        self.assertEqual(spry.mutations_for("\tif count >= limit {", "", "")[0], ("\tif false && (count >= limit) {", "never true"))
        self.assertEqual(spry.mutations_for("\tif err := save(x); err != nil {", "\tx := 1", "\t\treturn err")[0], (None, "write one"),
                         "a condition that also declares cannot be wrapped")

    def test_a_pipe_in_a_cell_is_escaped_and_read_back(self):
        entry = {"control": "a || b", "find": "a || b", "with": "", "expect": ["S-1/AC-1"]}
        row = spry.falsify_rows([(entry, "caught", "")])[0]
        cells = next(spry.table_rows([(0, row)]))[1]
        self.assertEqual((len(cells), cells[-1]), (4, "caught"))


class Controls(unittest.TestCase):
    def test_a_survivor_in_one_group_and_a_red_one_in_another_is_unreliable(self):
        groups = {(0, "a"): ["a.test.ts"], (0, "b"): ["b.test.ts"]}
        original = spry.group_files, spry.run_tests
        spry.group_files = lambda _p, _f: groups
        spry.run_tests = lambda *_a: ("pass", "")
        try:
            result = spry.run_control(type("P", (), {"root": "/"})(), {"_tests": []}, [{}], 1, {(0, "b"): "baseline fail"}, "/")
        finally:
            spry.group_files, spry.run_tests = original
        self.assertEqual(result[0], "unreliable")

    def test_pnpm_package_links_resolve_inside_the_worktree(self):
        root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, root)
        main, tree = os.path.join(root, "main"), os.path.join(root, "tree")
        for folder in ("main/node_modules/.pnpm", "main/packages/dom", "main/apps/api/node_modules",
                       "tree/packages/dom", "tree/apps/api"):
            os.makedirs(os.path.join(root, folder))
        os.symlink("../../../packages/dom", os.path.join(main, "apps/api/node_modules/dom"))
        spry.borrow(os.path.join(main, "apps/api/node_modules"), os.path.join(tree, "apps/api/node_modules"),
                    "apps/api/node_modules", True)
        self.assertEqual(os.path.realpath(os.path.join(tree, "apps/api/node_modules/dom")),
                         os.path.realpath(os.path.join(tree, "packages/dom")))


def story_text():
    return ("---\nid: S-1\ntitle: Lend\nstate: draft\n---\n# S-1\n\n## Acceptance criteria\n\n"
            "| AC | Given | When | Then |\n|---|---|---|---|\n| AC-1 | a | b | c |\n| AC-2 | a | b | c |\n")


class Find(Base):
    def test_ranks_the_section_that_matters(self):
        t = self.tree(**{"spry__knowledge__decisions__D-1-x.md":
                         "---\nid: D-1\ntitle: Store the due date\nsummary: s\n---\n# D-1\n\n## Decision\n\n- The due date is stored on the loan.\n"})
        hits = spry.find(t.project(), "due date")
        self.assertEqual(hits[0][0], "spry/knowledge/decisions/D-1-x.md")
        self.assertIn("D-1 Store the due date › Decision", hits[0][2])
        self.assertEqual(spry.find(t.project(), "nothing-like-this"), [])

    def test_index_follows_edits(self):
        t = self.tree()
        self.assertEqual(spry.find(t.project(), "zebra"), [])
        with open(os.path.join(t.root, F, "README.md"), "a") as handle:
            handle.write("\n## Notes\n\n- A zebra crossing.\n")
        self.assertEqual(spry.find(t.project(), "zebra")[0][0], f"{F}/README.md")

    def test_plain_search_without_fts(self):
        t = self.tree(**{f"{F}/README.md".replace("/", "__"): item("F-1", body="## Notes\n\n- A zebra crossing.\n")})
        p = t.project()
        hits = spry.find_plain(p, spry.searchable_files(p), ["zebra"], 5)
        self.assertEqual(hits[0][0], f"{F}/README.md")


class Install(unittest.TestCase):
    def test_each_agent(self):
        root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, root)
        skills = sorted(os.listdir(os.path.join(REPO, "plugins", "spry", "skills")))
        for agent in spry.AGENTS:
            spry.install(root, agent)
        self.assertEqual(sorted(f[:-3] for f in os.listdir(os.path.join(root, "spry", "skills"))), skills)
        self.assertTrue(os.path.isfile(os.path.join(root, ".claude", "skills", "spry-story", "SKILL.md")))
        self.assertTrue(os.path.isfile(os.path.join(root, ".cursor", "commands", "spry-story.md")))
        with open(os.path.join(root, ".gemini", "commands", "spry", "story.toml")) as handle:
            toml = handle.read()
        self.assertIn("{{args}}", toml)
        self.assertNotIn("$ARGUMENTS", toml)
        with open(os.path.join(root, ".claude", "skills", "spry-init", "SKILL.md")) as handle:
            self.assertIn("name: spry-init\n", handle.read())
        spry.install(root, "generic")
        with open(os.path.join(root, "AGENTS.md")) as handle:
            agents = handle.read()
        self.assertEqual(agents.count("<!-- spry:skills -->"), 1, "a second install replaces the block")
        self.assertIn("`/spry:story`", agents)


class Codeowners(Base):
    def test_owners_by_role(self):
        config = dict(CONFIG, team={"members": [{"name": "A", "github": "a", "roles": ["product"]},
                                                {"name": "B", "github": "b", "roles": ["developer", "product"]}],
                                    "review": {"spry/plan/**": ["product"], "src/**": ["developer"], "ops/**": ["ops"]}})
        p = self.tree(**{"spry__spry.config.json": json.dumps(config)}).project()
        text = spry.codeowners(p)
        self.assertIn("/spry/plan/** @a @b\n", text)
        self.assertIn("/src/** @b\n", text)
        self.assertNotIn("ops", text)
        self.assertTrue(any("ops/**" in str(x) for x in p.problems))


class Slowest(Base):
    def test_reads_junit(self):
        t = self.tree(**{"reports__junit.xml": '<testsuite><testcase file="a.test.ts" name="fast" time="0.1"/>'
                                               '<testcase file="b.test.ts" name="slow" time="3.5"/></testsuite>'})
        out = spry.slowest(t.project(), "reports/junit.xml", 5)
        self.assertTrue(out.startswith("2 tests, 3.6s in total"))
        self.assertLess(out.index("slow"), out.index("fast"))


class Merge(Base):
    def closed_slice(self, falsify_rows, covers="[AC-1]"):
        text = slice_("SL-1", covers=covers).replace("### Plan", "### Summary\n\n- Lends a book.\n\n### Plan")
        return text + "\n## Close summary\n\n### Falsify\n\n| Control | Mutation | Expect | Result |\n|---|---|---|---|\n" + falsify_rows

    def check(self, rows, **files):
        t = self.tree(**{f"{S}/SL-1-a.md".replace("/", "__"): self.closed_slice(rows)}, **files)
        return spry.merge_check(t.project(), "SL-1")

    def blocks(self, lines):
        return [text for status, text in lines if status == "block"]

    def test_ready(self):
        lines = self.check("| guard | never true | S-1/AC-1 | caught |\n")
        self.assertEqual(self.blocks(lines), [])
        self.assertIn(("ok", "S-1/AC-1 proven — 1 test"), lines)

    def test_a_bare_survivor_blocks_and_a_reasoned_one_waits_for_a_person(self):
        self.assertTrue(self.blocks(self.check("| guard | never true | S-1/AC-1 | survived |\n")))
        lines = self.check("| guard | never true | S-1/AC-1 | survived — logged only |\n")
        self.assertEqual(self.blocks(lines), [])
        self.assertTrue(any(s == "warn" and '"logged only" — a person accepts this' in x for s, x in lines), lines)

    def test_no_falsify_results_blocks(self):
        self.assertIn("no falsify results", " ".join(self.blocks(self.check(""))))

    def design(self, section, on=True):
        """merge-check's design-review lines for a slice whose work order ends with `section`."""
        text = self.closed_slice("| g | m | S-1/AC-1 | caught |\n").replace("\n## Close summary", section + "\n## Close summary")
        config = {**CONFIG, "slices": {"design_review": True}} if on else CONFIG
        t = self.tree(**{f"{S}/SL-1-a.md".replace("/", "__"): text, "spry__spry.config.json": json.dumps(config)})
        lines = spry.merge_check(t.project(), "SL-1")
        self.assertEqual(self.blocks(lines), [], "a design review never blocks")
        return [(status, said) for status, said in lines if said.startswith("design review")]

    def test_without_the_switch_a_design_review_is_not_looked_for(self):
        self.assertEqual(self.design("", on=False), [])
        self.assertEqual(self.design("\n### Design review\n\n- 1 Blocker, 0 Should — 0 asked\n", on=False), [])

    def test_with_the_switch_a_work_order_nobody_reviewed_warns(self):
        (status, said), = self.design("")
        self.assertEqual(status, "warn")
        self.assertIn("none recorded", said)
        (status, said), = self.design("\n### Design review\n\n- It looked fine.\n")
        self.assertEqual(status, "warn", "a section without the counts is not a review")

    def test_a_recorded_design_review_is_shown(self):
        self.assertEqual(self.design("\n### Design review\n\n- 2 Blocker, 5 Should — 2 asked\n- Blocker: tenant on the table — asked\n"),
                         [("ok", "design review: 2 Blocker, 5 Should — 2 asked")])
        self.assertEqual(self.design("\n### Design review\n\n0 Blockers, 1 Should - 0 asked\n"),
                         [("ok", "design review: 0 Blocker, 1 Should — 0 asked")])

    def test_a_blocker_that_was_not_asked_warns(self):
        (status, said), = self.design("\n### Design review\n\n- 3 Blocker, 1 Should — 1 asked\n")
        self.assertEqual(status, "warn")
        self.assertIn("2 went unasked", said)

    def test_design_review_is_true_or_false(self):
        t = self.tree(**{"spry__spry.config.json": json.dumps({**CONFIG, "slices": {"design_review": "yes"}})})
        self.assertProblem(t.problems(), "`slices.design_review` is `yes`")

    def test_planning_review_is_always_or_offer(self):
        t = self.tree(**{"spry__spry.config.json": json.dumps({**CONFIG, "planning": {"review": "never"}})})
        self.assertProblem(t.problems(), "`planning.review` is `never`")
        for value in ("always", "offer"):
            t = self.tree(**{"spry__spry.config.json": json.dumps({**CONFIG, "planning": {"review": value}})})
            self.assertFalse([p for p in t.problems() if "planning.review" in str(p)])

    def test_open_slice_blocks(self):
        t = self.tree(**{f"{S}/SL-1-a.md".replace("/", "__"): slice_("SL-1", state="open")})
        self.assertIn("state is `open`", " ".join(self.blocks(spry.merge_check(t.project(), "SL-1"))))

    def test_unproven_criterion_warns_but_does_not_block(self):
        t = self.tree(**{f"{S}/SL-1-a.md".replace("/", "__"): self.closed_slice("| g | m | S-1/AC-1 | caught |\n"),
                         "src/a.test.ts": "nothing\n"})
        lines = spry.merge_check(t.project(), "SL-1")
        self.assertEqual(self.blocks(lines), [])
        self.assertTrue(any(s == "warn" and "QA must check it" in x for s, x in lines))

    def test_message_carries_the_trailers(self):
        t = self.tree(**{f"{S}/SL-1-a.md".replace("/", "__"): self.closed_slice("")})
        message = spry.merge_message(t.project(), "SL-1")
        subject, _, body = message.partition("\n\n")
        self.assertEqual(subject, "SL-1 Slice SL-1 (#1)")
        self.assertIn("- Lends a book.", body)
        self.assertTrue(body.rstrip().endswith("Slice: SL-1\nParent: S-1\nCovers: S-1/AC-1"))

    def test_message_says_when_the_gate_stood_in_for_ci(self):
        t = self.tree(**{f"{S}/SL-1-a.md".replace("/", "__"): self.closed_slice("")})
        message = spry.merge_message(t.project(), "SL-1", "billing  lock")
        self.assertRegex(message.rstrip().split("\n")[-1], r"^CI: did not run \(billing lock\); gate green locally at \S+$")


T0 = 1_790_000_000  # a fixed moment, so the logs below read the same on every run


def at(seconds):
    return datetime.datetime.fromtimestamp(T0 + seconds, datetime.timezone.utc).isoformat().replace("+00:00", "Z")


def said(t, text, branch="sl-1-a", origin="human"):
    return {"type": "user", "timestamp": at(t), "gitBranch": branch, "origin": {"kind": origin} if origin else None,
            "message": {"role": "user", "content": text}}


def tool(t, ident, name="Bash", branch="sl-1-a", **given):
    return {"type": "assistant", "timestamp": at(t), "gitBranch": branch, "message": {
        "stop_reason": "tool_use", "content": [{"type": "tool_use", "id": ident, "name": name, "input": given}]}}


def result(t, ident, out="", branch="sl-1-a"):
    return {"type": "user", "timestamp": at(t), "gitBranch": branch,
            "message": {"content": [{"type": "tool_result", "tool_use_id": ident, "content": out}]}}


def reply(t, branch="sl-1-a"):
    return {"type": "assistant", "timestamp": at(t), "gitBranch": branch,
            "message": {"stop_reason": "end_turn", "content": [{"type": "text", "text": "done"}]}}


def used(record, request, **usage):
    """`record`, an assistant record, as part of the request `request` that used these tokens."""
    record["requestId"] = request
    record["message"]["usage"] = usage
    return record


GATE_OUT = "✓ spry check · 1.0s\n✗ lint · 20.0s\n"


class AgentHooks(Base):
    """Claude Code's hooks: each acts only when the config turns it on, and says what the checks would say later."""

    ON = {**CONFIG, "main_branch": "main", "hooks": {name: True for name in spry.AGENT_HOOKS}}

    def setUp(self):
        self.t = self.tree(**{"spry__spry.config.json": json.dumps(self.ON)})
        self.run_git = git_repo(self.t.root)
        self.slice = os.path.join(self.t.root, S, "SL-1-a.md")
        self.story = os.path.join(self.t.root, S, "README.md")

    def hook(self, name, **payload):
        code, reply = spry.agent_hook(name, json.dumps({"cwd": self.t.root, **payload}))
        self.assertEqual(code, 0)
        return reply

    def edit(self, name, path, old, new, tool="Edit"):
        given = {"file_path": path, "old_string": old, "new_string": new}
        return self.hook(name, tool_name=tool, tool_input=given)

    def decision(self, reply):
        return (reply or {}).get("hookSpecificOutput", {}).get("permissionDecision")

    def test_off_unless_the_config_turns_it_on(self):
        self.t = self.tree()
        git_repo(self.t.root)
        self.assertIsNone(self.edit("link_fields", os.path.join(self.t.root, S, "SL-1-a.md"), "pr: 1", "pr: 7"))
        self.assertIsNone(spry.agent_hook("session", json.dumps({"cwd": tempfile.gettempdir()}))[1])

    def test_spry_hooks_off_turns_every_one_off(self):
        with unittest.mock.patch.dict(os.environ, {"SPRY_HOOKS": "off"}):
            self.assertIsNone(self.edit("link_fields", self.slice, "pr: 1", "pr: 7"))

    def test_link_fields_are_set_by_the_tool(self):
        reply = self.edit("link_fields", self.slice, "pr: 1", "pr: 7")
        self.assertEqual(self.decision(reply), "deny")
        self.assertIn("link SL-1 --pr 7", reply["hookSpecificOutput"]["permissionDecisionReason"])
        self.assertIsNone(self.edit("link_fields", self.slice, "### Plan", "### Plan\n\n- More."))
        self.assertIsNone(self.edit("link_fields", self.story, "owner: A", "owner: B"), "only a slice's fields")
        sed = {"command": f"sed -i '' 's/^pr: 1/pr: 7/' {S}/SL-1-a.md"}
        self.assertEqual(self.decision(self.hook("link_fields", tool_name="Bash", tool_input=sed)), "deny")
        grep = {"command": f"grep -n 'pr:' {S}/SL-1-a.md"}
        self.assertIsNone(self.hook("link_fields", tool_name="Bash", tool_input=grep))

    def test_a_cited_criterion_asks_the_person(self):
        reply = self.edit("cited_criteria", self.story, "| AC-1 | x | y | z |", "| AC-1 | x | y | w |")
        self.assertEqual(self.decision(reply), "ask")
        self.assertIn("S-1/AC-1 by src/a.test.ts", reply["hookSpecificOutput"]["permissionDecisionReason"])
        self.assertIsNone(self.edit("cited_criteria", self.story, "| AC-1 | x | y | z |",
                                    "| AC-1 | x | y | z |\n| AC-2 | a | b | c |"), "a new criterion no test cites")
        with open(os.path.join(self.t.root, "src", "a.test.ts"), "w") as handle:
            handle.write('test("S-1/AC-10 another", () => {})\n')
        self.assertIsNone(self.edit("cited_criteria", self.story, "| AC-1 | x | y | z |", "| AC-1 | x | y | w |"),
                          "AC-10 is not AC-1")

    def test_check_edit_names_the_errors_in_that_file(self):
        doc = os.path.join(self.t.root, F, "README.md")
        with open(doc) as handle:
            text = handle.read()
        with open(doc, "w") as handle:
            handle.write(text + "\nA patron borrows. See [x](nowhere.md).\n")
        reply = self.hook("check_edit", tool_name="Edit", tool_input={"file_path": doc})
        self.assertEqual(reply["decision"], "block")
        self.assertIn("the glossary says `Member`", reply["reason"])
        self.assertIn("`nowhere.md` does not resolve", reply["reason"])
        self.assertIsNone(self.hook("check_edit", tool_name="Edit", tool_input={"file_path": self.story}))

    def test_merge_runs_merge_check_for_a_slices_pr(self):
        self.run_git("switch", "-qc", "sl-1-a")
        with open(self.slice) as handle:
            text = handle.read()
        with open(self.slice, "w") as handle:
            handle.write(text.replace("state: closed", "state: open"))
        reply = self.hook("merge", tool_name="Bash", tool_input={"command": "gh pr merge 1 --squash --subject 'x y'"})
        self.assertEqual(self.decision(reply), "deny")
        self.assertIn("state is `open`", reply["hookSpecificOutput"]["permissionDecisionReason"])
        self.assertIsNone(self.hook("merge", tool_name="Bash", tool_input={"command": "gh pr merge 99 --squash"}),
                          "a pull request no slice names")
        self.assertIsNone(self.hook("merge", tool_name="Bash", tool_input={"command": "gh pr view 1"}))
        self.run_git("switch", "-qc", "elsewhere")
        self.assertIsNone(self.hook("merge", tool_name="Bash", tool_input={"command": "gh pr merge 1"}),
                          "this tree holds another branch's copy of the slice")

    def test_utf8_in_and_out_whatever_the_console(self):
        with open(self.slice) as handle:
            edited = handle.read().replace("pr: 1", "pr: 7") + "\nLends — at the desk.\n"
        payload = {"cwd": self.t.root, "tool_name": "Write", "tool_input": {"file_path": self.slice, "content": edited}}
        tool = os.path.join(REPO, "plugins", "spry", "tool", "spry.py")
        done = subprocess.run([sys.executable, tool, "agent-hook", "link_fields"], capture_output=True,
                              input=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
                              env={**os.environ, "PYTHONIOENCODING": "cp1252"})
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual(json.loads(done.stdout)["hookSpecificOutput"]["permissionDecision"], "deny")

    def test_merge_target(self):
        self.assertEqual(spry.merge_target("gh pr merge 12 --squash -t 'a b'"), "12")
        self.assertEqual(spry.merge_target("git fetch && gh pr merge --subject 9 --squash"), "")
        self.assertEqual(spry.merge_target("gh pr merge https://github.com/o/r/pull/34"), "34")
        self.assertEqual(spry.merge_target("gh pr merge sl-3-x"), "sl-3-x")
        self.assertIs(spry.merge_target("gh pr list"), False)
        body = 'gh pr merge 12 --squash --subject "feat: a; b" --body "Lends.\n\nSlice: SL-3 | x" --delete-branch'
        self.assertEqual(spry.merge_target(body), "12", "merging.md step 7, a body over several lines")
        self.assertEqual(spry.merge_target('gh pr merge 5 --body "$(spry merge-message SL-1 | tail -n +3)"'), "5")
        self.assertIs(spry.merge_target("gh pr merge 12 --repo other/repo"), False)

    def test_check_stop_once_for_each_state_of_the_documents(self):
        self.assertIsNone(self.hook("check_stop"), "nothing changed")
        doc = os.path.join(self.t.root, F, "README.md")
        with open(doc, "a") as handle:
            handle.write("\nSee [x](nowhere.md).\n")
        reply = self.hook("check_stop")
        self.assertEqual(reply["decision"], "block")
        self.assertIn("nowhere.md", reply["reason"])
        self.assertIsNone(self.hook("check_stop", stop_hook_active=True), "it went back once already")
        self.assertIsNone(self.hook("check_stop"), "once for this state, not at every turn")
        with open(doc, "w") as handle:
            handle.write(item("F-1") + "\nFixed.\n")
        self.assertIsNone(self.hook("check_stop"))
        with unittest.mock.patch.object(spry, "check", side_effect=AssertionError("ran again")):
            self.assertIsNone(self.hook("check_stop"), "the same state passed already")
        new = os.path.join(self.t.root, F, "S-9-new", "README.md")
        os.makedirs(os.path.dirname(new))
        with open(new, "w") as handle:
            handle.write(story("S-9"))
        self.assertIsNone(self.hook("check_stop"))
        with open(new, "a") as handle:
            handle.write("\nSee [x](nowhere.md).\n")
        self.assertEqual(self.hook("check_stop")["decision"], "block", "a file inside a new folder")

    def test_session_names_this_branchs_slice(self):
        self.run_git("switch", "-qc", "sl-1-a")
        os.makedirs(os.path.join(self.t.root, ".spry"), exist_ok=True)
        with open(os.path.join(self.t.root, ".spry", "tone"), "w") as handle:
            handle.write("3\n")
        text = self.hook("session", source="startup")["hookSpecificOutput"]["additionalContext"]
        self.assertIn("spry/spry.config.json", text)
        self.assertIn(f"This branch builds SL-1 Slice SL-1 — closed, owner A: {S}/SL-1-a.md", text)
        self.assertIn("tone to 3", text)
        self.assertIn("spry hooks on: session, link_fields", text)
        self.run_git("switch", "-qc", "custom-name")
        with open(self.slice) as handle:
            text = handle.read()
        with open(self.slice, "w") as handle:
            handle.write(text.replace("pr: 1", "pr: 1\nbranch: custom-name"))
        self.assertIn("This branch builds SL-1", self.hook("session")["hookSpecificOutput"]["additionalContext"])

    def test_another_version_of_the_tool_runs_the_hook_itself(self):
        own = os.path.join(self.t.root, "spry", "tool", "spry.py")
        os.makedirs(os.path.dirname(own))
        with open(own, "w") as handle:
            handle.write('VERSION = "0.33.0"\n')
        self.assertIsNone(self.edit("link_fields", self.slice, "pr: 1", "pr: 7"), "a copy from before hooks")
        with open(own, "w") as handle:
            handle.write('import json, sys\nVERSION = "9.0.0"\nprint(json.dumps({"from": sys.argv[1:]}))\n')
        self.assertEqual(self.edit("link_fields", self.slice, "pr: 1", "pr: 7"), {"from": ["agent-hook", "link_fields"]})

    def test_hooks_file_names_only_hooks_the_tool_has(self):
        with open(os.path.join(REPO, "plugins", "spry", "hooks", "hooks.json")) as handle:
            text = handle.read()
        named = set(re.findall(r"agent-hook (\w+)", text))
        self.assertEqual(named, set(spry.AGENT_HOOKS))
        with open(os.path.join(REPO, "plugins", "spry", "process", "templates", "spry.config.json")) as handle:
            self.assertEqual(set(json.load(handle)["hooks"]), set(spry.AGENT_HOOKS))


class Pace(Base):
    """`spry pace` (DESIGN.md §17): what a session log says, and what the page makes of it."""

    def setUp(self):
        self.home = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.home)
        patcher = unittest.mock.patch.dict(os.environ, {"CLAUDE_CONFIG_DIR": self.home})
        patcher.start()
        self.addCleanup(patcher.stop)

    def log(self, t, name, records):
        folder = os.path.join(self.home, "projects", re.sub(r"[^A-Za-z0-9]", "-", os.path.realpath(t.root)))
        os.makedirs(folder, exist_ok=True)
        path = os.path.join(folder, name + ".jsonl")
        with open(path, "w") as handle:
            handle.write('{"type":"custom-title","customTitle":"x"}\n')
            handle.write("".join(json.dumps(r) + "\n" for r in records))
        return path

    def session(self):
        return [said(0, "<command-name>/spry:slice-close</command-name>"),
                tool(10, "g", command="python3 spry/tool/spry.py gate"),
                result(70, "g", GATE_OUT),
                tool(75, "q", command="pnpm --filter api exec vitest run src/a.test.ts 2>&1 | tail"),
                result(95, "q"),
                reply(100),
                said(220, "fix lint"),          # 120 s waiting on you
                reply(230),
                said(230 + 3600, "back"),       # an hour away
                reply(3840)]

    def test_shell_lines_take_their_costliest_kind(self):
        kind = spry.pace_bash_kind
        self.assertEqual(kind("cd x && python3 spry/tool/spry.py gate --fast"), "gate")
        self.assertEqual(kind("PATH=a pnpm --filter db exec vitest run x.test.ts | tail"), "tests")
        self.assertEqual(kind("grep vitest package.json"), "tool")
        self.assertEqual(kind("python3 - <<'EOF'\nimport os\nprint('pnpm test')\nEOF"), "tool", "a heredoc body is not a command")
        self.assertEqual(kind("until grep -q done log; do sleep 5; done"), "polling")
        self.assertEqual(kind("git add -A && gh pr create"), "gh")
        self.assertEqual(kind("spry falsify run plan.json"), "falsify")
        self.assertTrue(spry.pace_runs_suite("cd a && turbo run test 2>&1", ["turbo run test"]))
        self.assertFalse(spry.pace_runs_suite("turbo run test --filter=api", ["turbo run test"]))

    def test_a_log_splits_time_into_tools_the_agent_you_and_away(self):
        t = self.tree()
        data = spry.pace_read_log(self.log(t, "a", self.session()), 1800, [])
        d = data["branches"]["sl-1-a"]
        self.assertEqual(d["kinds"], {"agent": 10 + 5 + 5 + 10 + 10, "gate": 60, "tests": 20, "you": 120, "away": 3600})
        self.assertEqual(d["phases"]["close"]["gate"], 60)
        self.assertEqual(d["gates"][0]["steps"], {"spry check": 1.0, "lint": 20.0})
        self.assertFalse(d["gates"][0]["ok"])
        self.assertEqual(d["prompts"], 3)

    def test_a_wait_for_the_check_lock_is_its_own_category(self):
        t = self.tree()
        self.log(t, "a", [said(0, "<command-name>/spry:slice-close</command-name>"),
                          tool(10, "g", command="python3 spry/tool/spry.py gate"), result(1210, "g", GATE_OUT),
                          tool(1215, "f", command="spry falsify run plan.json"), result(1300, "f"),
                          tool(1305, "h", command="python3 spry/tool/spry.py gate"), result(1405, "h", GATE_OUT),
                          reply(1410)])
        # the gate sat 15 minutes behind another worktree's; falsify waited 30 s; the second gate's
        # line was written by another session and ends outside the call, so it stays gate time
        steps = [{"command": "gate", "at": T0 + 1209, "seconds": 300, "waited": 900, "ok": False, "steps": []},
                 {"command": "falsify", "at": T0 + 1299, "seconds": 55, "waited": 30, "controls": 1},
                 {"command": "gate", "at": T0 + 2000, "seconds": 60, "waited": 40, "ok": True, "steps": []}]
        os.makedirs(os.path.join(t.root, ".spry", "pace"))
        with open(os.path.join(t.root, ".spry", "pace", "steps.jsonl"), "w") as handle:
            handle.write("".join(json.dumps({"branch": "sl-1-a", **step}) + "\n" for step in steps))
        p = t.project()
        s = spry.pace_slices(p, spry.pace_logs(p))["SL-1"]
        self.assertEqual((s["kinds"]["gate"], s["kinds"]["falsify"], s["kinds"]["lock"]), (1200 + 100 - 900, 85 - 30, 930))
        self.assertEqual(s["phases"]["close"]["lock"], 930)
        self.assertIn("waiting for the check lock took 66% (15m30) — other sessions' gates held it", spry.pace_flags(p, s))
        self.assertIn("lock", dict(spry.PACE_GROUPS)["waits"])

    def test_a_wait_while_a_background_task_runs_is_not_on_you(self):
        t = self.tree()
        records = [said(0, "review it"),
                   tool(5, "r", name="Agent", description="review SL-1", run_in_background=True),
                   result(6, "r"), reply(10),
                   said(300, "still there?"),      # you typed, but the review was still running
                   reply(310),
                   said(400, "<task-notification>done</task-notification>", origin="task-notification"),
                   reply(420)]
        d = spry.pace_read_log(self.log(t, "a", records), 1800, [])["branches"]["sl-1-a"]
        self.assertEqual(d["kinds"].get("you", 0), 0)
        self.assertEqual(d["kinds"]["background"], 290 + 90)
        self.assertIn("fixes", d["phases"], "the review agent ending starts the fixes")

    def test_a_rerun_after_a_failure_or_with_full_is_not_a_stamp_miss(self):
        t = self.tree()
        s = {"id": "SL-1", "kinds": {"agent": 100}, "phases": {}, "reviews": [], "limit": 0, "compactions": 0, "suite": 0,
             "gates": [{"at": 0, "ok": False, "tests": True, "code": "x"}, {"at": 1, "ok": True, "tests": True, "code": "x"},
                       {"at": 2, "ok": True, "tests": True, "code": "x", "full": True}]}
        self.assertFalse([f for f in spry.pace_flags(t.project(), s) if "stamp missed" in f])

    def test_a_long_gap_is_away_whatever_ends_it(self):
        t = self.tree()
        records = [said(0, "go"), reply(10),
                   said(10 + 7200, "<cross-session-message>hi</cross-session-message>", origin="peer"), reply(7220),
                   said(7230, "<task-notification>x</task-notification>", origin="task-notification")]
        d = spry.pace_read_log(self.log(t, "a", records), 1800, [])["branches"]["sl-1-a"]
        self.assertEqual(d["kinds"]["away"], 7200)
        self.assertNotIn("session", d["kinds"])

    def test_a_background_task_counts_until_its_own_notice_or_a_clear(self):
        t = self.tree()
        records = [said(0, "go"),
                   tool(5, "b1", command="sleep 100", run_in_background=True), result(6, "b1"),
                   tool(7, "b2", command="sleep 900", run_in_background=True), result(8, "b2"), reply(10),
                   said(100, "<task-notification><tool-use-id>b1</tool-use-id></task-notification>", origin="task-notification"),
                   reply(110),
                   said(200, "anything?"), reply(210),        # b2 still runs: not on you
                   {"type": "system", "subtype": "local_command", "timestamp": at(220), "gitBranch": "sl-1-a"},
                   said(400, "next")]                       # after /clear nothing runs: on you
        d = spry.pace_read_log(self.log(t, "a", records), 1800, [])["branches"]["sl-1-a"]
        self.assertEqual(d["kinds"]["background"], 90 + 90 + 10)
        self.assertEqual(d["kinds"]["you"], 180)

    def test_a_project_in_a_subfolder_keeps_its_own_step_log(self):
        t = self.tree()
        sub = os.path.join(t.root, "app")
        shutil.copytree(os.path.join(t.root, "spry"), os.path.join(sub, "spry"))
        subprocess.run(["git", "init", "-q", t.root], check=True)
        self.assertEqual(os.path.realpath(spry.pace_home(spry.Project(sub))),
                         os.path.realpath(os.path.join(sub, ".spry", "pace")))

    def test_kept_command_heads_drop_secrets(self):
        self.assertEqual(spry.pace_head("GH_TOKEN=abc gh pr merge 3\nmore"), "gh pr merge 3")
        self.assertEqual(spry.pace_head('curl -H "Authorization: Bearer xyz" u'), 'curl -H "Authorization: Bearer … u')

    def test_slice_numbers_come_from_every_log_and_outlive_them(self):
        t = self.tree()
        self.log(t, "a", self.session())
        self.log(t, "b", [said(150, "something else", branch="main"), reply(160, branch="main")])
        p = t.project()
        slices = spry.pace_slices(p, spry.pace_logs(p))
        s = slices["SL-1"]
        self.assertEqual((s["kinds"]["you"], s["kinds"]["elsewhere"]), (0, 120), "you typed in another session meanwhile")
        self.assertEqual(s["sessions"], 1)
        kept = os.path.join(t.root, ".spry", "pace", "slices", "SL-1.json")
        self.assertTrue(os.path.isfile(kept), "a closed slice's numbers are kept")
        shutil.rmtree(os.path.join(self.home, "projects"))
        again = spry.pace_slices(p, spry.pace_logs(p))
        self.assertEqual(spry.pace_active(again["SL-1"]), spry.pace_active(s))

    def test_logs_are_read_once_per_size_and_mtime(self):
        t = self.tree()
        self.log(t, "a", self.session())
        p = t.project()
        spry.pace_logs(p)
        with unittest.mock.patch.object(spry, "pace_read_log", side_effect=AssertionError("read again")):
            self.assertEqual(len(spry.pace_logs(p)), 1)

    def test_flags_name_what_stands_out(self):
        t = self.tree()
        s = {"id": "SL-1", "kinds": {"agent": 100, "falsify": 100, "session": 100}, "phases": {}, "reviews": [1] * 4,
             "gates": [{"at": 0, "ok": False, "tests": False, "code": "y"}, {"at": 1, "ok": True, "tests": True, "code": "x"},
                       {"at": 2, "ok": True, "tests": True, "code": "x", "retried": True}],
             "limit": 1, "compactions": 1, "suite": 1}
        flags = " | ".join(spry.pace_flags(t.project(), s))
        for words in ("full gate failed 1×", "through the full gate 2×", "again 1× on code that had passed", "1 quiet retry",
                      "10-minute limit", "another session took 33%", "4 review agents", "1 compaction",
                      "falsify took 33%", "whole suite 1×"):
            self.assertIn(words, flags)

    def test_a_failed_full_gate_names_the_step_that_went_red(self):
        t = self.tree()

        def gate(at, *red):
            return {"at": at, "ok": not red, "steps": [["lint", 1.0, "lint" not in red], ["affected tests", 9.0, "affected tests" not in red]]}

        def flag(*gates):
            s = {"id": "SL-1", "kinds": {"agent": 100}, "phases": {}, "reviews": [], "gates": list(gates)}
            return [f for f in spry.pace_flags(t.project(), s) if "full gate failed" in f][0]
        tests = flag(gate(0, "affected tests"), gate(1, "affected tests"), gate(2, "lint"))
        self.assertIn("the full gate failed 3×: affected tests 2×, lint 1×", tests)
        self.assertIn("`gate --failed` reruns the tests", tests)
        self.assertIn("`slices.steps.tests`", flag(gate(0, "affected tests")))
        self.assertIn("fast checks while building catch most of that earlier", flag(gate(0, "lint")))
        self.assertEqual("the full gate failed 1× — fast checks while building catch most of that earlier",
                         flag({"at": 0, "ok": False, "steps": [["lint", 1.0]]}), "a log line from before steps were marked")
        s = {"id": "SL-1", "kinds": {"agent": 100}, "phases": {}, "gates": [gate(0, "lint", "affected tests"), gate(1, "lint"), gate(2)]}
        measured = spry.pace_measures(s)
        self.assertEqual((measured["full gates failed"], measured["full gates failed in tests"]), (2, 1))

    def test_the_page_compares_before_and_after_a_change(self):
        t = self.tree(**{"spry__knowledge__process-changes.md": "| Date | Change | Kind | Files | Why |\n|---|---|---|---|---|\n"
                         "| 2026-09-01 | Gate once per slice | local | x | y |\n"})
        change = datetime.datetime(2026, 9, 1).timestamp()

        def one(n, offset, agent):
            return {"id": f"SL-{n}", "kinds": {"agent": agent, "you": 60}, "phases": {}, "first": change + offset - 100,
                    "last": change + offset, "sessions": 1, "prompts": 1, "questions": 0, "compactions": 0,
                    "reviews": [], "limit": 0, "slowest": [], "suite": 0, "gates": [], "lines": 100}
        slices = {s["id"]: s for s in [one(n, -1000 * n, 600) for n in range(1, 11)] + [one(n, 1000 * n, 300) for n in range(11, 21)]}
        page = spry.pace_page(t.project(), slices)
        self.assertIn("process change: Gate once per slice", page)
        self.assertIn("| median active time | 11m00 | 6m00 |", page)
        self.assertIn("| median agent share | 91% | 83% |", page)
        few = spry.pace_page(t.project(), {k: v for k, v in slices.items() if int(k[3:]) > 5})
        self.assertIn("too few slices to tell: 5 before, 10 after", few)

    def test_compare_takes_a_day_or_refuses_what_it_cannot_read(self):
        t = self.tree()
        self.assertEqual(spry.pace_point(t.project(), "2026-09-01")[1], "the day you named")
        with self.assertRaises(spry.PlanError):
            spry.pace_point(t.project(), "CH-99")
        with self.assertRaises(spry.PlanError):
            spry.pace_point(t.project(), "nonsense")

    def test_the_command_writes_the_page_and_serve_shows_it(self):
        t = self.tree()
        self.log(t, "a", self.session())
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(spry.main(["--root", t.root, "pace"]), 0)
            self.assertEqual(spry.main(["--root", t.root, "pace", "SL-1"]), 0)
        self.assertIn("page: .spry/view/pace.md", out.getvalue())
        self.assertIn("| gate | 1m00 |", out.getvalue())
        code, _, body, _ = spry.serve_response(t.project(), "/-/pace")
        self.assertEqual(code, 200)
        self.assertIn("Where the time went", body.decode())
        self.assertIn('href="/-/pace"', body.decode())

    def test_a_passing_merge_check_keeps_the_slice_numbers(self):
        t = self.tree()
        self.log(t, "a", self.session())
        spry.pace_on_merge_check(t.project(), "SL-1")
        self.assertTrue(os.path.isfile(os.path.join(t.root, ".spry", "pace", "slices", "SL-1.json")))

    def spent(self):
        """A session of three requests — the second written as two records — and one subagent."""
        return [said(0, "go"),
                used(reply(10), "r1", input_tokens=1000, output_tokens=100),
                said(20, "<command-name>/spry:slice-close</command-name>"),
                used(tool(30, "g", command="git status"), "r2", input_tokens=10, cache_read_input_tokens=50_000,
                     cache_creation={"ephemeral_1h_input_tokens": 2000, "ephemeral_5m_input_tokens": 400}, output_tokens=200),
                used(tool(31, "h", command="git diff"), "r2", input_tokens=10, cache_read_input_tokens=50_000,
                     cache_creation={"ephemeral_1h_input_tokens": 2000, "ephemeral_5m_input_tokens": 400}, output_tokens=200),
                result(32, "g"), result(33, "h"),
                used(reply(40), "r3", input_tokens=5, cache_read_input_tokens=60_000, cache_creation_input_tokens=1000,
                     output_tokens=10)]

    def test_tokens_are_counted_once_a_request_with_the_subagents_apart(self):
        t = self.tree()
        path = self.log(t, "a", self.spent())
        os.makedirs(os.path.join(path[:-6], "subagents"))
        with open(os.path.join(path[:-6], "subagents", "agent-1.jsonl"), "w") as handle:
            handle.write("".join(json.dumps(r) + "\n" for r in [
                said(34, "build step 1", origin=None), used(reply(36), "s1", input_tokens=3000, output_tokens=400)]))
        d = spry.pace_read_log(path, 1800, [])["branches"]["sl-1-a"]
        self.assertEqual(d["tokens"], {"input": 1015, "cache_read": 110_000, "cache_write_5m": 1400,
                                       "cache_write_1h": 2000, "output": 310})
        self.assertEqual((d["requests"], d["peak"], d["close"][1]), (3, 61_005, 52_410),
                         "a request written as two records counts once; close starts at the request after the skill")
        p = t.project()
        s = spry.pace_slices(p, spry.pace_logs(p))["SL-1"]
        s["lines"] = 400
        weights = spry.pace_config(p)["weights"]
        n = spry.pace_token_numbers(s, weights)
        self.assertEqual(n["main"], 1015 + 110_000 * 0.1 + 1400 * 1.25 + 2000 * 2 + 310 * 5)
        self.assertEqual((n["sub"], n["agents"], n["requests"]), (3000 + 400 * 5, 1, 3))
        self.assertEqual(n["per100"], (n["main"] + n["sub"]) / 4)
        lines = "\n".join(spry.pace_slice_lines(s, [], spry.pace_config(p)))
        self.assertIn("- tokens: 24k spend, in input-token equivalents — the main session 19k over 3 requests, "
                      "1 subagent 5k (21%); peak context 61k, 52k entering close; 6k per 100 lines", lines)
        self.assertIn("- size: 300–699 lines; ", lines)
        self.assertIn("- spend by phase: close 23k (94%; subagents 5k), other 2k (6%)", lines,
                      "CH-76: each request counted in the phase it fell in; CH-77: a subagent in the phase it started in")
        self.assertIn("- requests that called a tool: 1, 0% of them called one", lines, "r2 made two calls in one request")

    def test_a_step_commit_says_when_the_next_step_belongs_in_a_fresh_session(self):
        """CH-83: a build that outgrew `slices.fresh_context` stops between steps, where nothing is lost."""
        p = self.tree().project()
        with unittest.mock.patch.object(spry, "session_context", return_value=200_000):
            stop = spry.context_stop(p, "/spry:slice-build SL-1")
        self.assertIn("over `slices.fresh_context` (150k)", stop)
        self.assertIn("`/spry:slice-build SL-1`", stop)

    def test_a_build_brief_names_the_rules_that_failed_the_checks_most(self):
        """CH-84: read from the step log's newest gates; a rule that failed fewer than three is not a pattern."""
        t = self.tree()
        p = t.project()
        self.assertNotIn("## Rules that failed", spry.brief(p, "SL-1", skill="slice-build"), "no log yet")
        home = spry.pace_home(p)
        os.makedirs(home, exist_ok=True)
        rows = [{"command": "gate", "ok": False, "red": {"lint": {"eslint(no-shadow)": 2, "eslint(once)": 1}}},
                {"command": "gate", "ok": False, "red": {"lint": {"eslint(no-shadow)": 1}, "types": {"TS2345": 4}}},
                {"command": "falsify"}, {"command": "gate", "ok": True},
                {"command": "gate", "ok": False, "red": {"lint": {"eslint(no-shadow)": 1}, "types": {"TS2345": 1}}},
                {"command": "gate", "ok": False, "red": {"types": {"TS2345": 1}}},
                {"command": "gate", "ok": False, "red": {"types": {"TS2345": 1}}}]
        with open(os.path.join(home, "steps.jsonl"), "w") as handle:
            handle.write("".join(json.dumps(r) + "\n" for r in rows) + "not json\n")
        out = spry.brief(p, "SL-1", skill="slice-build")
        self.assertIn("## Rules that failed the checks most\n\nIn this project's last 6 gates.", out)
        self.assertIn("- types `TS2345` — 4 red gates\n- lint `eslint(no-shadow)` — 3 red gates\n", out)
        self.assertNotIn("eslint(once)", out)
        self.assertNotIn("## Rules that failed", spry.brief(p, "SL-1", skill="slice-close"), "only where code is written")

    def test_brief_says_when_the_session_is_too_big_to_close_in(self):
        """CH-76: past `slices.fresh_context`, the close starts after /clear; a reviewer's --diff never asks."""
        t = self.tree()
        self.log(t, "a", [said(0, "go"), used(reply(10), "r1", input_tokens=10, cache_read_input_tokens=200_000)])
        p = t.project()
        out = spry.brief(p, "SL-1")
        self.assertIn("! this session carries 200k tokens of context, over `slices.fresh_context` (150k)", out)
        self.assertIn("`/spry:slice-close SL-1`", out)
        p.items["SL-1"].fm["state"] = "planned"
        self.assertIn("`/spry:slice-open SL-1`", spry.brief(p, "SL-1"), "CH-77: the open checks too")
        self.assertNotIn("this session carries", spry.brief(p, "SL-1", diff=True))
        p.config.setdefault("slices", {})["fresh_context"] = 0
        self.assertNotIn("this session carries", spry.brief(p, "SL-1"), "0 turns the check off")
        p.config["slices"]["fresh_context"] = 300_000
        self.assertNotIn("this session carries", spry.brief(p, "SL-1"))
        p.config["slices"]["fresh_context"] = "big"
        self.assertTrue(any("slices.fresh_context" in str(e) for e in spry.check(p)))

    def test_plan_and_build_are_sessions_of_their_own(self):
        """CH-78: the context stop restarts the skill that is running; pace counts plan as open, build as build."""
        t = self.tree()
        self.log(t, "a", [said(0, "go"), used(reply(10), "r1", input_tokens=10, cache_read_input_tokens=200_000)])
        p = t.project()
        self.assertIn("`/spry:slice-build SL-1`", spry.brief(p, "SL-1", skill="slice-build"))
        p.items["SL-1"].fm["state"] = "planned"
        self.assertIn("`/spry:slice-plan SL-1`", spry.brief(p, "SL-1", skill="slice-plan"))
        self.assertIn("`/spry:slice-open SL-1`", spry.brief(p, "SL-1"), "no skill named: by the slice's state")
        self.assertEqual([spry.pace_phase_of(s) for s in ("spry:slice-plan", "/spry:slice-build", "slice-open")],
                         ["open", "build", "open"])

    def test_a_session_of_one_call_a_request_is_flagged(self):
        """CH-77: nearly every request that called a tool called one — each re-read the whole session."""
        t = self.tree()
        records = [said(0, "<command-name>/spry:slice-open</command-name>")]
        for n in range(25):
            records += [used(tool(10 + 2 * n, f"c{n}", command="sed -n 1,5p a"), f"r{n}", input_tokens=10),
                        result(11 + 2 * n, f"c{n}")]
        self.log(t, "a", records + [reply(80)])
        p = t.project()
        s = spry.pace_slices(p, spry.pace_logs(p))["SL-1"]
        self.assertEqual((s["tool_requests"], s["lone"]), (25, 25))
        self.assertTrue(any(f.startswith("100% of 25 requests that called a tool called one — alone: Bash tool 100% —")
                            for f in spry.pace_flags(p, s)), "CH-92: the flag names what went alone")
        s["lone"] = 20
        self.assertFalse(any("called one" in f for f in spry.pace_flags(p, s)), "80% is under lone_share")

    def test_lone_calls_are_split_by_kind(self):
        """CH-92: a file tool by its name, a shell line by its kind — the largest is the one to batch."""
        t = self.tree()
        records = [said(0, "go")]
        calls = [("Read", {"file_path": "a"})] * 3 + [("Bash", {"command": "git status"})] * 2 + [("Grep", {"pattern": "x"})]
        for n, (name, given) in enumerate(calls):
            records += [used(tool(10 + 2 * n, f"c{n}", name=name, **given), f"r{n}", input_tokens=10), result(11 + 2 * n, f"c{n}")]
        self.log(t, "a", records + [reply(80)])
        p = t.project()
        s = spry.pace_slices(p, spry.pace_logs(p))["SL-1"]
        self.assertEqual(s["lone_kinds"], {"Read": 3, "Bash git": 2, "Grep": 1})
        self.assertEqual(spry.pace_lone_line(s), "alone: Read 50%, Bash git 33%, Grep 17%")

    def test_a_subagent_away_is_not_its_own_work(self):
        """CH-92: a subagent resumed hours later did not work in between — the session's `away` rule holds."""
        t = self.tree()
        path = self.log(t, "a", [said(0, "go")] + self.launched(10, "a", "r1", "Review SL-1") + [reply(20), reply(30_000)])
        self.subagent(path, "r1", "Review SL-1", 11, 611)
        with open(os.path.join(path[:-6], "subagents", "agent-r1.jsonl"), "a") as handle:
            handle.write(json.dumps(reply(20_000)) + "\n" + json.dumps(reply(20_300)) + "\n")
        agents = spry.pace_read_log(path, 1800, [])["agents"]
        self.assertEqual(agents[0][1], 600 + 300, "the five-hour gap is left out")

    def test_a_slice_shows_its_design_review(self):
        text = slice_("SL-1") + "\n### Design review\n\n- 1 Blocker, 4 Should — 1 asked\n"
        t = self.tree(**{f"{S}/SL-1-a.md".replace("/", "__"): text})
        self.log(t, "a", self.session())
        p = t.project()
        s = spry.pace_slices(p, spry.pace_logs(p))["SL-1"]
        self.assertIn("- design review: 1 Blocker, 4 Should — 1 asked", spry.pace_slice_lines(s, [], spry.pace_config(p)))
        t = self.tree()
        self.log(t, "a", self.session())
        p = t.project()
        s = spry.pace_slices(p, spry.pace_logs(p))["SL-1"]
        self.assertFalse(any("design review" in line for line in spry.pace_slice_lines(s, [], spry.pace_config(p))))

    def launched(self, t, ident, agent, description, branch="sl-1-a"):
        """The two records of a subagent started and left to work: the call and its launch notice."""
        return [tool(t, ident, name="Agent", branch=branch, description=description, prompt="go", subagent_type="general-purpose"),
                result(t + 1, ident, f"Async agent launched successfully.\nagentId: {agent} (internal ID)", branch=branch)]

    def handed_back(self, t, agent, branch="sl-1-a"):
        record = said(t, f"Another Claude session sent a message:\n<agent-message from=\"{agent}\">\n[Subagent hand-back] done", branch=branch)
        record["origin"] = {"kind": "peer", "from": agent, "senderTaskId": agent}
        return record

    def subagent(self, path, agent, description, first, last, **usage):
        folder = os.path.join(path[:-6], "subagents")
        os.makedirs(folder, exist_ok=True)
        with open(os.path.join(folder, f"agent-{agent}.jsonl"), "w") as handle:
            # A record at least every ten minutes, as a working agent writes: a longer gap is time away.
            handle.write("".join(json.dumps(r) + "\n" for r in [said(first, "your task", origin=None)]
                                 + [reply(at) for at in range(first + 600, last, 600)]
                                 + [used(reply(last), f"u-{agent}", **usage)]))
        if description:
            with open(os.path.join(folder, f"agent-{agent}.meta.json"), "w") as handle:
                json.dump({"agentType": "general-purpose", "description": description}, handle)

    def test_a_wait_for_its_own_subagent_is_not_another_session(self):
        t = self.tree()
        records = ([said(0, "close it")] + self.launched(10, "a", "r1", "Review SL-1 step 1") + self.launched(12, "b", "r2", "Review SL-1 seams")
                   + [reply(20),
                      self.handed_back(2500, "r1"),            # 41 minutes on: longer than `away`, and the slice was not idle
                      reply(2510),
                      self.handed_back(2600, "r2"), reply(2610),
                      said(2700, "<agent-message from=\"zz\">hello</agent-message>", origin="peer"), reply(2710)]
                   + self.launched(2720, "c", "f1", "Fix SL-1 step 1 finding") + [reply(2730), said(2790, "and?"), reply(2800),
                                                                                  said(4000, "still there?"), reply(4010)])
        path = self.log(t, "a", records)
        self.subagent(path, "r1", "Review SL-1 step 1", 11, 2490, input_tokens=1000)
        self.subagent(path, "r2", "Review SL-1 seams", 13, 2590, input_tokens=1000)
        self.subagent(path, "f1", "Fix SL-1 step 1 finding", 2722, 2795, input_tokens=4000)
        self.subagent(path, "old", "", 30, 40, input_tokens=10)
        d = spry.pace_read_log(path, 1800, [])
        kinds = d["branches"]["sl-1-a"]["kinds"]
        self.assertEqual(kinds["subagent"], 3 + (2500 - 20) + (2600 - 2510) + (2790 - 2730),
                         "a second for each launch, the hand-back's wait, and a prompt typed while one still worked")
        self.assertEqual(kinds["session"], 90, "a message from a session it did not start is still another session")
        self.assertEqual(kinds["you"], 1200, "a subagent that stopped without reporting takes no later wait")
        phases = d["branches"]["sl-1-a"]["phases"]
        self.assertEqual(phases["review"]["subagent"], 2 + 2480 + 90, "the review lasts until the last reviewer reports")
        self.assertEqual([a[4] for a in d["agents"]], ["fix", "other", "review", "review"])
        p = t.project()
        s = spry.pace_slices(p, spry.pace_logs(p))["SL-1"]
        self.assertEqual(len(s["reviews"]), 2)
        lines = "\n".join(spry.pace_slice_lines(s, [], spry.pace_config(p)))
        self.assertIn("- subagents: 4, 1h25 of their own work — review 2 (1h24, 2k), fix 1 (1m13, 4k), other 1 (0m10, 10)", lines)
        self.assertIn("| subagents waited on | 43m53 |", lines)
        self.assertIn("- requests that called a tool: 3, 100% of them called one — alone: Agent 100%", lines)
        page = spry.pace_page(p, {"SL-1": s})
        self.assertIn("| review | 2 | 1 | 1h24 | 42m08 | 2k |", page)
        self.assertIn("| **subagents** | 43m53 |", page)

    def test_a_subagent_s_kind_is_the_first_word_that_says_one(self):
        said_for = {"Review SL-886 step 5": "review", "Fresh-eyes review of SL-489": "review", "Design review of SL-580": "design review",
                    "Fix SL-582 step 2 review findings": "fix", "Build SL-580 step 3": "build", "Implement the limit": "build",
                    "Falsify tests for SL-573 db": "tests", "SL-576 step 2 survivor tests": "tests", "Docs pass: security pages": "other"}
        for words, kind in said_for.items():
            self.assertEqual(spry.pace_agent_kind(words), kind, words)

    def test_a_slice_shows_what_its_reviews_found_and_the_checks_that_went_red(self):
        text = (slice_("SL-1") + "\n### Choices taken\n\n- **A** — because\n  more of it\n- **B** — because\n"
                "\n### Design review\n\n- 1 Blocker, 4 Should — 1 asked\n\n## Close summary\n"
                "\n### Review\n\n- 1 Blocker, 3 Should, 2 Nit — 4 fixed\n- 0 Blocker, 1 Should — 1 fixed\n")
        t = self.tree(**{f"{S}/SL-1-a.md".replace("/", "__"): text})
        self.log(t, "a", self.session())
        steps = [{"command": "gate", "at": 1, "seconds": 9, "ok": False, "fast": True, "tests": False,
                  "steps": [["spry check", 1, True], ["lint", 5, False], ["format", 1, False]], "red": {"lint": {"oxc(no-map-spread)": 6, "TS1": 1}}},
                 {"command": "gate", "at": 2, "seconds": 9, "ok": False, "fast": True, "tests": False,
                  "steps": [["lint", 5, False]], "red": {"lint": {"oxc(no-map-spread)": 1}}},
                 {"command": "gate", "at": 3, "seconds": 90, "ok": False, "fast": False, "tests": True,
                  "steps": [["lint", 5, True], ["affected tests", 80, False]]}]
        os.makedirs(os.path.join(t.root, ".spry", "pace"))
        with open(os.path.join(t.root, ".spry", "pace", "steps.jsonl"), "w") as handle:
            handle.write("".join(json.dumps({"branch": "sl-1-a", **step}) + "\n" for step in steps))
        p = t.project()
        s = spry.pace_slices(p, spry.pace_logs(p))["SL-1"]
        self.assertEqual(s["review"], {"reviews": 2, "blockers": 1, "shoulds": 4, "nits": 2, "fixed": 5})
        lines = spry.pace_slice_lines(s, [], spry.pace_config(p))
        self.assertIn("- review: 1 Blocker, 4 Should, 2 Nit — 5 fixed, over 2 reviews", lines)
        self.assertIn("- choices taken without asking: 2", lines)
        self.assertIn("- red checks: lint 2× — oxc(no-map-spread) 7, TS1 1; format 1×", lines, "a failed test step is not a red check")
        page = spry.pace_page(p, {"SL-1": s})
        self.assertIn("| SL-1 | 1 | 4 | 1 | 1 | 4 | 2 | 5 | 0 | 2 |", page)
        self.assertIn("| lint | 2 | 1 |", page)
        self.assertIn("| lint | `oxc(no-map-spread)` | 2 | 7 | 1 |", page)
        self.assertIn(("ok", "review: 1 Blocker, 4 Should, 2 Nit — 5 fixed, over 2 reviews"), spry.merge_check(p, "SL-1"))
        self.assertEqual(spry.pace_measures(s)["fast checks failed"], 3)
        plain = self.tree()
        self.log(plain, "a", self.session())
        p = plain.project()
        s = spry.pace_slices(p, spry.pace_logs(p))["SL-1"]
        said_of = "\n".join(spry.pace_slice_lines(s, [], spry.pace_config(p))) + spry.pace_page(p, {"SL-1": s})
        for words in ("- review:", "choices taken", "red checks", "## Findings", "## Red checks", "## Subagents"):
            self.assertNotIn(words, said_of)
        self.assertFalse([said for _mark, said in spry.merge_check(p, "SL-1") if said.startswith("review:")])

    def test_a_change_is_judged_within_a_size(self):
        t = self.tree()

        def one(n, at, lines, spend):
            return {"id": f"SL-{n}", "kinds": {"agent": 600}, "phases": {}, "first": T0 + at - 50, "last": T0 + at, "sessions": 1,
                    "prompts": 1, "questions": 0, "compactions": 0, "reviews": [], "limit": 0, "slowest": [], "suite": 0,
                    "gates": [], "lines": lines, "tokens": {"input": spend}}
        slices = [one(n, -1000 * n, 1000, 100_000 * n) for n in range(1, 13)]             # 12 before, of 700–1299 lines
        slices += [one(20, 1000, 1000, 2_000_000), one(21, 2000, 1000, 400_000)]          # 2 after, of that size
        slices += [one(30 + n, -500 * n, 200, 50_000) for n in range(1, 4)] + [one(40, 500, 200, 50_000)]   # too few before
        rows = spry.pace_compare(slices, T0, "a change", spry.PACE_WEIGHTS, [300, 700, 1300, 2500])
        self.assertIn("- too few slices to tell: 3 before, 3 after (10 a side needed)", rows)
        self.assertIn("| 700–1299 | spend per 100 lines | 12 | 40k / 65k / 100k | 2 | 40k / 120k / 200k |", rows)
        self.assertIn("| 700–1299 | active time per 100 lines | 12 | 1m00 / 1m00 / 1m00 | 2 | 1m00 / 1m00 / 1m00 |", rows)
        self.assertFalse([r for r in rows if r.startswith("| under 300")], "a size with fewer than 10 slices before has no row")
        self.assertEqual(spry.pace_compare(slices, T0, "a change", spry.PACE_WEIGHTS)[-1], "", "no buckets, no table")
        conf = spry.pace_config(t.project())
        by_id = {s["id"]: s for s in slices}
        self.assertEqual(spry.pace_against_size(by_id["SL-20"], by_id, conf),
                         "- against the 13 other slices of 700–1299 lines (p25 / median / p75): spend per 100 lines 200k against "
                         "40k / 60k / 90k; active time per 100 lines 1m00 against 1m00 / 1m00 / 1m00")
        self.assertIsNone(spry.pace_against_size(by_id["SL-40"], by_id, conf), "three others are too few to set it against")
        page = spry.pace_page(t.project(), by_id)
        self.assertIn("| 700–1299 | 14 | 10m00 | 1m00 / 1m00 / 1m00 | 650k | 40k / 65k / 100k | – |", page)
        self.assertEqual(spry.pace_quartiles([4, None, 1, 3, 2]), (2, 2.5, 4))
        self.assertIsNone(spry.pace_quartiles([None]))

    def test_a_bug_shows_on_the_slice_that_introduced_it(self):
        def bug(ident, extra, state="ready"):
            return item(ident, state, extra=f"severity: major\n{extra}", check=False)
        bugs = {f"{F}/bugs/B-1-x/README.md": bug("B-1", "introduced_by: SL-1\n"),
                f"{F}/bugs/B-2-y/README.md": bug("B-2", "introduced_by: SL-1\n", state="dropped"),
                f"{F}/bugs/B-3-z/README.md": bug("B-3", "introduced_by:\n"),
                f"{S}/SL-2-b.md": slice_("SL-2")}
        t = self.tree(**{k.replace("/", "__"): v for k, v in bugs.items()})
        self.log(t, "a", self.session())
        self.log(t, "b", [{**r, "gitBranch": "sl-2-b"} for r in self.session()])
        p = t.project()
        slices = spry.pace_slices(p, spry.pace_logs(p))
        self.assertEqual(slices["SL-1"]["bugs"], [["B-1", "major"]], "a dropped bug and a bug that names no slice are not counted")
        self.assertEqual(slices["SL-2"]["bugs"], [])
        self.assertIn("- bugs filed later: 1 — B-1 (major)", spry.pace_slice_lines(slices["SL-1"], [], spry.pace_config(p)))
        self.assertFalse([r for r in spry.pace_slice_lines(slices["SL-2"], [], spry.pace_config(p)) if "bugs filed" in r])
        page = spry.pace_page(p, slices)
        self.assertIn("| SL-1 | – | – | – | – | – | – | – | 0 | – | B-1 (major) |", page)
        self.assertEqual((spry.pace_measures(slices["SL-1"])["bugs filed later"], spry.pace_measures(slices["SL-2"])["bugs filed later"]), (1, 0))
        plain = self.tree()
        self.log(plain, "a", self.session())
        p = plain.project()
        s = spry.pace_slices(p, spry.pace_logs(p))["SL-1"]
        self.assertIsNone(s["bugs"], "no bug names a slice: the count is unknown, not zero")
        self.assertIsNone(spry.pace_measures(s)["bugs filed later"])
        self.assertNotIn("## Findings", spry.pace_page(p, {"SL-1": s}))

    def test_compare_counts_bugs_per_slice_before_and_after(self):
        def one(n, at, lines, bugs):
            return {"id": f"SL-{n}", "kinds": {"agent": 600}, "phases": {}, "first": T0 + at - 50, "last": T0 + at, "sessions": 1,
                    "prompts": 1, "questions": 0, "compactions": 0, "reviews": [], "limit": 0, "slowest": [], "suite": 0,
                    "gates": [], "lines": lines, "bugs": [[f"B-{n}-{i}", "minor"] for i in range(bugs)]}
        slices = [one(n, -1000 * n, 200, 1 if n <= 3 else 0) for n in range(1, 11)]                # small: 3 bugs in 10; the 10 before mix both sizes
        slices += [one(n, 1000 * (n - 10), 1000, 2 if n <= 15 else 0) for n in range(11, 21)]      # after, larger: 10 bugs in 10
        slices += [one(n, -1000 * (n - 20) - 500, 1000, 1 if n <= 22 else 0) for n in range(21, 31)]   # before, larger: 2 in 10
        rows = spry.pace_compare(slices, T0, "a change", spry.PACE_WEIGHTS, [300, 700, 1300, 2500])
        self.assertIn("| bugs filed later, per slice | 0.50 | 1.00 |", rows)
        self.assertIn("| 700–1299 | 10 | 2 | 0.20 | 10 | 10 | 1.00 |", rows)
        self.assertFalse([r for r in rows if r.startswith("| under 300 | 10 | 3")], "a size with no slice after has no row")
        unknown = [{**s, "bugs": None} for s in slices]
        said_of = "\n".join(spry.pace_compare(unknown, T0, "a change", spry.PACE_WEIGHTS, [300, 700, 1300, 2500]))
        self.assertNotIn("bugs", said_of.lower())
        page = spry.pace_page(self.tree().project(), {s["id"]: s for s in slices})
        self.assertIn("| 700–1299 | 20 | 10m00 | 1m00 / 1m00 / 1m00 | – | – | – | 12 (0.60 a slice) |", page)

    def test_token_weights_and_size_buckets_come_from_the_config(self):
        t = self.tree(**{"spry__spry.config.json": json.dumps({**CONFIG, "pace": {"token_weights": {"output": 4}, "buckets": [100, 50]}})})
        conf = spry.pace_config(t.project())
        self.assertEqual((conf["weights"]["output"], conf["weights"]["cache_read"], conf["buckets"]), (4.0, 0.1, [50, 100]))
        self.assertEqual(spry.pace_spend({"input": 10, "output": 10}, conf["weights"]), 50)
        self.assertEqual([spry.pace_bucket(n, [300, 700]) for n in (0, 1, 299, 300, 699, 700)],
                         [None, "under 300", "under 300", "300–699", "300–699", "700 or more"])
        self.assertEqual([spry.pace_tokens(n) for n in (None, 999, 1500, 999_949, 2_340_000)], ["–", "999", "2k", "1000k", "2.3M"])
        bad = self.tree(**{"spry__spry.config.json": json.dumps({**CONFIG, "pace": {"token_weights": {"output": "dear"}}})})
        with self.assertRaises(SystemExit):
            spry.pace_config(bad.project())

    def test_falsify_runs_and_gate_reruns_come_from_the_step_log(self):
        t = self.tree()
        self.log(t, "a", self.session())
        steps = [{"command": "falsify", "at": 1, "seconds": 300, "controls": 20, "caught": 12, "survived": 6, "unreliable": 2},
                 {"command": "falsify", "at": 2, "seconds": 100, "controls": 6, "caught": 6, "survived": 0, "unreliable": 0, "waited": 30},
                 {"command": "gate", "at": 3, "seconds": 200, "ok": False, "fast": False, "tests": True, "code": "x",
                  "retried": True, "steps": [["spry check", 2, True], ["affected tests", 80, False]]},
                 {"command": "gate", "at": 4, "seconds": 90, "ok": True, "fast": False, "tests": True, "code": "x", "force": True,
                  "retried": True, "retry_lost": 40, "steps": [["affected tests", 80, True]]},
                 {"command": "gate", "at": 5, "seconds": 70, "ok": True, "fast": False, "tests": True, "code": "y", "steps": []},
                 {"command": "gate", "at": 6, "seconds": 9, "ok": True, "fast": True, "tests": False, "steps": []}]
        os.makedirs(os.path.join(t.root, ".spry", "pace"))
        with open(os.path.join(t.root, ".spry", "pace", "steps.jsonl"), "w") as handle:
            handle.write("".join(json.dumps({"branch": "sl-1-a", **step}) + "\n" for step in steps))
        p = t.project()
        s = spry.pace_slices(p, spry.pace_logs(p))["SL-1"]
        f = spry.pace_falsify(s)
        self.assertEqual((f["runs"], f["controls"], f["caught"], f["survived"], f["unreliable"], f["each"]), (2, 26, 18, 6, 2, 400 / 26))
        self.assertEqual(spry.pace_reruns(s), {"tested": 3, "repeats": 2, "same": 1, "retries": 2, "lost": 118 + 40},
                         "a line with no retry_lost falls back to the gate's seconds less its steps'")
        lines = "\n".join(spry.pace_slice_lines(s, spry.pace_flags(p, s), spry.pace_config(p)))
        self.assertIn("- falsify: 2 runs, 26 controls — 18 caught, 6 survived, 2 unreliable; 6m40, 15.4s a control; "
                      "the last run: 6 caught, 0 survived, 0 unreliable of 6", lines)
        self.assertIn("- reruns: 3 full gates ran tests, 1 on code a full gate had already tested; "
                      "2 quiet retries lost 2m38 to the first attempt\n", lines)
        self.assertIn("- flag: 2 quiet retries, 2m38 lost to the first attempt", lines)
        self.assertNotIn("- tokens:", lines, "a log with no usage adds no token line")

    def test_the_page_sets_slices_against_their_size_and_shows_tokens_only_where_counted(self):
        t = self.tree()

        def one(n, lines, tokens):
            return {"id": f"SL-{n}", "kinds": {"agent": 600}, "phases": {}, "first": T0 + n, "last": T0 + 100 + n, "sessions": 1,
                    "prompts": 1, "questions": 0, "compactions": 0, "reviews": [], "limit": 0, "slowest": [], "suite": 0,
                    "gates": [], "lines": lines, **tokens}
        plain = {s["id"]: s for s in [one(1, 200, {}), one(2, 400, {})]}   # summaries kept before CH-57, or an agent with no log
        page = spry.pace_page(t.project(), plain)
        self.assertNotIn("tokens", page.lower())
        self.assertIn("| under 300 | 1 | 10m00 | 5m00 | – | – | – |", page)
        counted = {**plain, "SL-3": one(3, 500, {"tokens": {"input": 2_000_000}, "sub_tokens": {"output": 100_000}, "requests": 9,
                                                 "agents": 2, "peak": 250_000, "close": [T0, 180_000],
                                                 "falsify": [{"at": 1, "seconds": 50, "controls": 10, "caught": 7, "survived": 3, "unreliable": 0}]})}
        page = spry.pace_page(t.project(), counted)
        self.assertIn("- tokens, in input-token equivalents: median 2.5M a slice, 500k per 100 lines; median peak context 250k; "
                      "subagents 20% of the spend", page)
        self.assertIn("| 300–699 | 2 | 10m00 | 2m15 | 2.5M | 500k | 250k |", page)
        self.assertIn("| SL-3 | 500 | 2.5M | 500k | 20% | 250k | 180k | 1 | 10 | 7 | 3 | 0 | 5.0s | 0 (0) | 0 |", page)
        self.assertIn("| SL-1 | 200 | – | – | – | – | – | – | – | – | – | – | – | 0 (0) | 0 |", page)

    def test_the_page_names_limits_set_looser_than_spry_ships_them(self):
        def one(n, lines, peak, bugs):
            return {"id": f"SL-{n}", "kinds": {"agent": 600}, "phases": {}, "first": T0 + n, "last": T0 + 100 + n, "sessions": 1,
                    "prompts": 1, "questions": 0, "compactions": 0, "reviews": [], "limit": 0, "slowest": [], "suite": 0,
                    "gates": [], "lines": lines, "tokens": {"input": 1_000_000}, "requests": 9, "peak": peak, "bugs": bugs}
        slices = {s["id"]: s for s in [one(1, 200, 100_000, []), one(2, 900, 300_000, [["B-1", "major"]]), one(3, 2000, 400_000, [])]}
        self.assertNotIn("Limits loosened", spry.pace_page(self.tree().project(), slices), "the defaults are no finding")
        t = self.tree()
        config = json.loads(open(os.path.join(t.root, "spry/spry.config.json")).read())
        config["slices"] = {"fresh_context": 1_000_000, "steps": {"max_lines": 2500}}
        config["hooks"] = {"check_edit": False}
        open(os.path.join(t.root, "spry/spry.config.json"), "w").write(json.dumps(config))
        page = spry.pace_page(t.project(), slices)
        self.assertIn("- `slices.fresh_context` is 1000000 — spry ships 150000: 2 of 3 slices peaked above the default, "
                      "median peak 300k; no session is told to start fresh", page)
        self.assertIn("- `slices.steps.max_lines` is 2500 — spry ships 800: 2 of 3 slices changed more than the default — "
                      "1 bug filed later (0.50 a slice), against 0 bugs filed later (0.00 a slice) in the rest", page)
        self.assertIn("- hooks switched off: `hooks.check_edit`", page)
        config["slices"] = {"fresh_context": 0, "steps": {"max_lines": 0}}
        open(os.path.join(t.root, "spry/spry.config.json"), "w").write(json.dumps(config))
        page = spry.pace_page(t.project(), slices)
        self.assertIn("`slices.fresh_context` is off (0)", page)
        self.assertIn("`slices.steps.max_lines` is off (0)", page)

    def test_light_slices_are_set_against_the_rest_of_their_size(self):
        t = self.tree()

        def one(n, lines, rigor, blockers, bugs):
            return {"id": f"SL-{n}", "kinds": {"agent": 600}, "phases": {}, "first": T0 + n, "last": T0 + 100 + n, "sessions": 1,
                    "prompts": 1, "questions": 0, "compactions": 0, "reviews": [1] * (1 if rigor == 0 else 3), "limit": 0,
                    "slowest": [], "suite": 0, "gates": [], "lines": lines, "tokens": {"input": lines * 5000}, "requests": 9,
                    "peak": 100_000, "bugs": bugs, "rigor": rigor, "review": {"blockers": blockers, "shoulds": 1, "nits": 0, "fixed": 1}}
        slices = {s["id"]: s for s in [one(1, 100, 0, 0, []), one(2, 200, 0, 1, [["B-1", "minor"]]), one(3, 200, 1, 0, []),
                                       one(4, 900, 1, 2, [])]}
        page = spry.pace_page(t.project(), slices)
        self.assertIn("## By level", page)
        self.assertIn("no bigger than the largest of them (200 lines)", page)
        self.assertIn("| 0 · light | 2 | 750k | 500k | 1.00 | 0.50 | 1.00 | 1 (0.50 a slice) |", page)
        self.assertIn("| 1 | 1 | 1.0M | 500k | 3.00 | 0.00 | 1.00 | 0 (0.00 a slice) |", page)
        self.assertIn("## By level", spry.pace_summary(page))
        for s in slices.values():
            s["rigor"] = 1
        self.assertNotIn("## By level", spry.pace_page(t.project(), slices), "absent until a slice is light")

    def test_flags_are_counted_and_one_on_a_third_of_the_slices_is_marked(self):
        t = self.tree()

        def one(n, **more):
            return {"id": f"SL-{n}", "kinds": {"agent": 600}, "phases": {}, "first": T0 + n, "last": T0 + 100 + n, "sessions": 1,
                    "prompts": 1, "questions": 0, "compactions": 0, "reviews": [], "limit": 0, "slowest": [], "suite": 0,
                    "gates": [], **more}
        slices = {s["id"]: s for s in [one(1, suite=2, compactions=1), one(2, suite=1), one(3, suite=1)] + [one(n) for n in (4, 5, 6)]}
        page = spry.pace_page(t.project(), slices)
        self.assertIn("| **the agent ran the whole suite** | 3 | 50% |", page)
        self.assertIn("| compactions | 1 | 17% |", page)
        self.assertIn("not fixed by wording it again", page)
        few = spry.pace_page(t.project(), {k: slices[k] for k in ("SL-1", "SL-2")})
        self.assertIn("| the agent ran the whole suite | 2 | 100% |", few, "two slices are too few to mark")
        self.assertEqual([kind for kind, _ in spry.pace_flag_pairs(t.project(), slices["SL-1"])],
                         ["compactions", "the agent ran the whole suite"])

    def test_the_summary_keeps_what_a_reader_judges_from(self):
        page = ("# Pace\n\n- 2 slices\n\n## Limits loosened or off\n\n- a\n\n## Where the time went\n\n| x |\n\n"
                "## Before and after each change\n\n### 2026-01-01 — c\n\n- b\n\n## Flags, counted\n\n| f |\n\n## Flags\n\n- SL-1: f\n\n"
                "## Slices, newest first\n\n| SL-1 |\n\n## By size\n\n| under 300 |\n\n## Gate steps\n\n| lint |\n")
        short = spry.pace_summary(page)
        self.assertEqual([line for line in short.split("\n") if line.startswith("## ")],
                         ["## Limits loosened or off", "## Before and after each change", "## Flags, counted", "## By size"])
        self.assertIn("- 2 slices", short)
        self.assertIn("### 2026-01-01 — c", short)
        self.assertNotIn("SL-1", short)
        t = self.tree()
        said = []
        with unittest.mock.patch.object(spry, "pace_page", return_value=page):
            self.assertEqual(spry.pace(t.project(), say=said.append, summary=True), 0)
        self.assertIn("## By size", said[0])
        self.assertIn(".spry/view/pace.md", said[1])
        with open(os.path.join(t.root, ".spry/view/pace.md")) as handle:
            self.assertEqual(handle.read(), page, "the whole page is still written")


STEPS = ("### Steps\n\n#### Step 1 · Refuse a fifth book\n\nCovers: AC-1\n\n- `src/lend.ts` — the limit\n\n"
         "#### Step 2 · Show the limit\n\nCovers: AC-2\n\n- `src/page.ts` — the count\n\n")


class Steps(Base):
    """Steps mode (DESIGN.md §15): one slice built in steps, one commit each, made and checked by the tool."""

    def setUp(self):
        text = slice_("SL-1", state="open", covers="[AC-1, AC-2]").replace("pr: 1\n", "pr: 1\nbranch: sl-1-a\n")
        self.text = text.replace("### Plan\n\n\n", STEPS)
        self.t = self.tree(**{f"{S}/README.md".replace("/", "__"): story("S-1", acs=("AC-1", "AC-2")),
                              f"{S}/SL-1-a.md".replace("/", "__"): self.text,
                              "src__b.test.ts": 'test("S-1/AC-2 shows it", () => {})\n', ".gitignore": ".spry/\n"})
        self.doc = os.path.join(self.t.root, S, "SL-1-a.md")

    def write(self, rel, text):
        path = os.path.join(self.t.root, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as handle:
            handle.write(text)

    def with_steps(self, steps):
        self.write(f"{S}/SL-1-a.md", self.text.replace(STEPS, steps))
        return self.t.problems()

    def say(self, *call, **given):
        lines = []
        code = spry.step_command(self.t.project(), "SL-1", "main", *call, say=lines.append, **given)
        return code, "\n".join(lines)

    def on_branch(self):
        self.run_git = git_repo(self.t.root)
        self.run_git("checkout", "-qb", "sl-1-a")

    def test_steps_are_read_from_the_work_order(self):
        steps = spry.slice_steps(self.text)
        self.assertEqual([(s["n"], s["title"], s["covers"]) for s in steps],
                         [(1, "Refuse a fifth book", ["AC-1"]), (2, "Show the limit", ["AC-2"])])
        self.assertEqual(spry.slice_steps(slice_("SL-2")), [], "a slice without Steps is one step")
        self.assertEqual(self.t.problems(), [])

    def test_check_refuses_a_steps_section_that_does_not_add_up(self):
        self.assertProblem(self.with_steps(STEPS.replace("Step 2", "Step 3")), "numbered 1, 2, 3")
        self.assertProblem(self.with_steps(STEPS.replace("Covers: AC-2\n", "")), "step 2 has no `Covers:` line")
        self.assertProblem(self.with_steps(STEPS.replace("Covers: AC-2", "Covers: AC-3")), "covers AC-3, which the slice")
        self.assertProblem(self.with_steps(STEPS.replace("Covers: AC-2", "Covers: —")), "covers AC-2, but no step does")
        many = "### Steps\n\n" + "".join(f"#### Step {k} · s{k}\n\nCovers: AC-1, AC-2\n\n" for k in range(1, 7))
        self.assertProblem(self.with_steps(many), "6 steps, over `slices.steps.max` (5)")

    def test_each_step_is_one_commit_made_by_the_tool(self):
        self.on_branch()
        code, out = self.say(False, False, False)
        self.assertEqual(code, 0)
        self.assertIn("SL-1 · step 1 of 2: Refuse a fifth book", out)
        self.assertEqual(self.say(True, False, False)[0], 1, "nothing changed yet")
        self.write("src/lend.ts", "export const limit = 4\n")
        code, out = self.say(True, False, False)
        self.assertEqual(code, 0, out)
        log = subprocess.run(["git", "log", "-1", "--format=%s%n%b"], cwd=self.t.root, capture_output=True, text=True).stdout
        self.assertIn("SL-1 step 1: Refuse a fifth book", log)
        self.assertIn("Step: SL-1/1", log)
        self.assertIn("step 2 of 2: Show the limit", self.say(False, False, False)[1])
        self.write("src/page.ts", "export const shown = true\n")
        self.assertEqual(self.say(True, False, False)[0], 0)
        code, out = self.say(False, False, False)
        self.assertIn("all 2 steps committed", out)
        code, out = self.say(False, True, False)
        self.assertRegex(out, r"step 1 · git diff \w+\^ \w+ · Refuse a fifth book · AC-1")
        self.assertIn("seams · git diff", out)

    def set_rigor(self, level, **light):
        path = os.path.join(self.t.root, "spry/spry.config.json")
        with open(path) as handle:
            config = json.load(handle)
        config["rigor"] = level
        config.setdefault("slices", {})["light"] = light
        with open(path, "w") as handle:
            json.dump(config, handle)

    def test_a_light_slice_skips_the_design_review_and_is_read_once(self):
        self.on_branch()
        project = self.t.project()
        self.assertIsNone(spry.light(project, project.items["SL-1"], "main", "HEAD"), "level 1 unless asked")
        self.assertNotIn("## Rigor", spry.brief(project, "SL-1", skill="slice-build"))
        self.set_rigor(0, max_lines=3)
        self.assertEqual(self.t.problems(), [])
        project = self.t.project()
        self.assertEqual(spry.rigor_of(project, project.items["SL-1"]), 0)
        said = spry.brief(project, "SL-1", skill="slice-build")
        self.assertIn("**Light (level 0):** no design review — skip *Plan* step 4", said)
        self.assertIn("at most 3 lines of code changed", said)
        self.write("src/lend.ts", "export const limit = 4\n")
        self.say(True, False, False)
        self.write("src/page.ts", "export const shown = true\n")
        self.say(True, False, False)
        project = self.t.project()
        self.assertEqual(spry.light(project, project.items["SL-1"], "main", "HEAD"),
                         (True, "2 lines of code changed, `slices.light.max_lines` is 3"))
        code, out = self.say(False, True, False)
        self.assertRegex(out, r"^light · one reviewer reads the whole diff · git diff \w+ \w+ · 2 lines")
        self.assertNotIn("step 1 ·", out)
        self.assertIn("One reviewer reads the whole diff at step 5", spry.brief(project, "SL-1", skill="slice-close"))
        self.assertIn(("ok", "design review: not asked — light (level 0): 2 lines of code changed, `slices.light.max_lines` is 3"),
                      spry.design_review_lines(project, project.items["SL-1"], "main"))

    def test_a_slice_that_outgrows_light_is_reviewed_in_full(self):
        self.on_branch()
        self.set_rigor(0, max_lines=1)
        self.write("src/lend.ts", "export const limit = 4\nexport const more = 1\n")
        self.say(True, False, False)
        project = self.t.project()
        self.assertEqual(spry.light(project, project.items["SL-1"], "main", "HEAD"),
                         (False, "2 lines of code changed, over `slices.light.max_lines` (1)"))
        code, out = self.say(False, True, False)
        self.assertIn("not light: 2 lines of code changed", out)
        self.assertIn("step 1 · git diff", out)
        self.assertIn("seams · git diff", out)
        self.run_git("update-ref", "refs/remotes/origin/main", "main")   # the brief measures against the remote's main
        self.assertIn("**No longer light:** 2 lines of code changed", spry.brief(project, "SL-1", skill="slice-close"))
        status, line = spry.design_review_lines(project, project.items["SL-1"], "main")[0]
        self.assertEqual(status, "warn")
        self.assertIn("planned light (level 0), and it is not", line)
        self.set_rigor(0, max_lines=300, never=["src/lend.*"])   # the plan names a file light never takes
        project = self.t.project()
        self.assertEqual(spry.light(project, project.items["SL-1"]), (False, "`src/lend.ts` is under `slices.light.never`"))
        self.assertIn("**Level 0 asked, not light:**", spry.brief(project, "SL-1", skill="slice-build"))

    def test_the_nearest_rigor_wins_and_only_built_levels_are_taken(self):
        self.set_rigor(0)
        project = self.t.project()
        self.assertEqual(spry.rigor_of(project, project.items["SL-1"]), 0)
        story_doc = os.path.join(self.t.root, S, "README.md")
        with open(story_doc) as handle:
            text = handle.read()
        self.write(f"{S}/README.md", text.replace("\nstate:", "\nrigor: 1\nstate:", 1))
        project = self.t.project()
        self.assertEqual(spry.rigor_of(project, project.items["SL-1"]), 1, "the story above it says 1")
        self.assertIsNone(spry.light(project, project.items["SL-1"]))
        self.write(f"{S}/SL-1-a.md", self.text.replace("\nstate:", "\nrigor: 0\nstate:", 1))
        project = self.t.project()
        self.assertEqual(spry.rigor_of(project, project.items["SL-1"]), 0, "the slice's own value is nearest")
        self.write(f"{S}/SL-1-a.md", self.text.replace("\nstate:", "\nrigor: 3\nstate:", 1))
        self.assertProblem(self.t.problems(), "`rigor: 3` — 0 (light")
        self.write(f"{S}/SL-1-a.md", self.text)
        self.set_rigor(4)
        self.assertProblem(self.t.problems(), "`rigor` is `4`")
        self.set_rigor(0, max_lines=0)
        self.assertProblem(self.t.problems(), "`slices.light` is")

    def test_merge_check_wants_every_step_once_in_order_and_nothing_left_to_fold(self):
        self.on_branch()
        self.write("src/lend.ts", "export const limit = 4\n")
        self.say(True, False, False)
        blocks = [x for s, x in spry.step_merge_lines(self.t.project(), self.t.project().items["SL-1"], "main") if s == "block"]
        self.assertTrue(any("step 2 \"Show the limit\" has no commit" in b for b in blocks), blocks)
        self.write("src/page.ts", "export const shown = true\n")
        self.say(True, False, False)
        lines = spry.step_merge_lines(self.t.project(), self.t.project().items["SL-1"], "main")
        self.assertIn(("ok", "steps: all 2 committed, one commit each, in order"), lines)
        first = subprocess.run(["git", "log", "--format=%H", "--grep", "Step: SL-1/1"], cwd=self.t.root,
                               capture_output=True, text=True).stdout.strip()
        self.write("src/lend.ts", "export const limit = 3\n")
        self.run_git("commit", "-qam", "fix the limit")
        blocks = [x for s, x in spry.step_merge_lines(self.t.project(), self.t.project().items["SL-1"], "main") if s == "block"]
        self.assertTrue(any("without a `Step:` trailer" in b for b in blocks), blocks)
        self.run_git("reset", "-q", "--soft", "HEAD~1")
        self.run_git("commit", "-q", f"--fixup={first}")
        blocks = [x for s, x in spry.step_merge_lines(self.t.project(), self.t.project().items["SL-1"], "main") if s == "block"]
        self.assertTrue(any("fixup commit not folded in" in b for b in blocks), blocks)
        self.assertEqual(self.say(False, False, True)[0], 0)
        lines = spry.step_merge_lines(self.t.project(), self.t.project().items["SL-1"], "main")
        self.assertIn(("ok", "steps: all 2 committed, one commit each, in order"), lines)
        with open(os.path.join(self.t.root, "src", "lend.ts")) as handle:
            self.assertEqual(handle.read(), "export const limit = 3\n", "the fix is in step 1 now")

    def step_tests_on(self, **steps):
        runner = {"match": ["src/**"], "cwd": "root", "command": "! grep -l BROKEN {files}"}
        self.write("spry/spry.config.json", json.dumps({**CONFIG, "falsify": {"runners": [runner]},
                                                        "slices": {"steps": {"tests": True, **steps}}}))
        self.run_git("commit", "-qam", "docs: step tests")

    def commits(self):
        return subprocess.run(["git", "rev-list", "--count", "HEAD"], cwd=self.t.root, capture_output=True, text=True).stdout.strip()

    def test_a_step_runs_the_test_files_it_added_or_changed(self):
        self.on_branch()
        self.step_tests_on()
        before = self.commits()
        self.write("src/lend.ts", "export const limit = 4\n")
        self.write("src/lend.test.ts", 'test("S-1/AC-1 refuses a fifth", () => BROKEN)\n')
        code, out = self.say(True, False, False)
        self.assertEqual(code, 1, out)
        self.assertIn("– the step's tests: src/lend.test.ts", out)
        self.assertIn("✗ step tests", out)
        self.assertIn("step 1 not committed: its tests are red — src/lend.test.ts", out)
        self.assertEqual(self.commits(), before, "a red test is found in the step that wrote it")
        self.write("src/lend.test.ts", 'test("S-1/AC-1 refuses a fifth", () => {})\n')
        code, out = self.say(True, False, False)
        self.assertEqual(code, 0, out)
        self.assertIn("✓ step tests", out)
        self.assertIn("fast checks and the step's tests green — the affected tests not run", out)
        self.assertNotIn("b.test.ts", out, "only the files the step touched, not the affected set")
        with open(os.path.join(self.t.root, ".spry", "pace", "steps.jsonl")) as handle:
            line = json.loads(handle.read().strip().split("\n")[-1])
        self.assertTrue(line["fast"] and ["step tests", line["steps"][-1][1], True] == line["steps"][-1], line)
        self.write("src/page.ts", "export const shown = true\n")
        code, out = self.say(True, False, False)
        self.assertEqual(code, 0, out)
        self.assertNotIn("step tests", out, "a step that touched no test file runs none")

    def test_step_tests_are_off_by_default_and_leave_out_what_the_config_skips(self):
        self.on_branch()
        self.write("src/lend.ts", "export const limit = 4\n")
        self.write("src/lend.test.ts", 'test("S-1/AC-1 refuses a fifth", () => BROKEN)\n')
        code, out = self.say(True, False, False)
        self.assertEqual(code, 0, out)
        self.assertNotIn("step tests", out, "off: the fast checks only, as before")
        self.step_tests_on(tests_skip=["**/*.int.test.ts"])
        self.write("src/page.ts", "export const shown = true\n")
        self.write("src/page.int.test.ts", 'test("S-1/AC-2 shows it", () => BROKEN)\n')
        self.write("lib/other.test.ts", 'test("S-1/AC-2 shows it too", () => BROKEN)\n')
        code, out = self.say(True, False, False)
        self.assertEqual(code, 0, out)
        self.assertNotIn("step tests", out, "a skipped file needs the stack: the gate runs it")
        self.assertIn("– left to the gate, no falsify runner takes them: lib/other.test.ts", out)

    def test_step_tests_without_a_runner_refuse_the_commit(self):
        self.on_branch()
        self.write("spry/spry.config.json", json.dumps({**CONFIG, "slices": {"steps": {"tests": True}}}))
        self.run_git("commit", "-qam", "docs: step tests")
        self.write("src/lend.test.ts", 'test("S-1/AC-1 refuses a fifth", () => {})\n')
        code, out = self.say(True, False, False)
        self.assertEqual(code, 2, out)
        self.assertIn("`slices.steps.tests` is on, but spry.config.json has no falsify.runners", out)

    def fast_checks(self, fix="python3 .spry/fmt.py {files}"):
        """A formatter that minds `UGLY` and can take it out, and a linter that minds `LINT` and cannot."""
        self.write(".spry/fmt.py", "import sys\nfor f in sys.argv[1:]:\n    text = open(f).read()\n"
                             "    open(f, 'w').write(text.replace(' UGLY', ''))\n")
        fmt = {"name": "format", "run": "! grep -rl UGLY src", **({"fix": fix} if fix else {})}
        self.write("spry/spry.config.json", json.dumps({**CONFIG, "checks": {"fast": [
            fmt, {"name": "lint", "run": "! grep -rl LINT src"}]}}))
        self.run_git("add", "spry/spry.config.json")
        self.run_git("commit", "-qm", "docs: fast checks")

    def read(self, rel):
        with open(os.path.join(self.t.root, rel)) as handle:
            return handle.read()

    def test_past_the_context_limit_a_step_commit_ends_the_session_before_the_next_step(self):
        """CH-83: said after the commit, and never after the last step — the close starts fresh anyway."""
        self.on_branch()
        self.write("src/lend.ts", "export const limit = 4\n")
        with unittest.mock.patch.object(spry, "session_context", return_value=200_000):
            code, out = self.say(True, False, False)
            self.assertEqual(code, 0, out)
            self.assertIn("committed step 1 of 2", out)
            self.assertIn("! this session carries 200k tokens of context, over `slices.fresh_context` (150k)", out)
            self.assertIn("[Run] `/clear`, then `/spry:slice-build SL-1`", out)
            self.assertTrue(out.rstrip().endswith("`spry.py step SL-1` there names step 2"), out)
            self.write("src/page.ts", "export const shown = true\n")
            code, out = self.say(True, False, False)
            self.assertIn("committed step 2 of 2", out)
            self.assertNotIn("this session carries", out)
        self.write("src/more.ts", "export const more = 1\n")
        self.run_git("reset", "-q", "--hard", "HEAD~2")
        self.write("src/lend.ts", "export const limit = 4\n")
        with unittest.mock.patch.object(spry, "session_context", return_value=100_000):
            self.assertNotIn("this session carries", self.say(True, False, False)[1])

    def test_a_step_whose_only_fault_is_formatting_is_formatted_and_committed(self):
        self.on_branch()
        self.fast_checks()
        before = self.commits()
        self.write("src/lend.ts", "export const limit = 4 UGLY\n")
        self.write("src/it's new.ts", "export const shown = true UGLY\n")
        code, out = self.say(True, False, False)
        self.assertEqual(code, 0, out)
        self.assertNotIn("✗ format", out, "CH-84: the fix runs first, so the check never goes red")
        self.assertIn("– format: the `fix` ran before the checks — files changed: src/it's new.ts, src/lend.ts", out)
        self.assertIn("committed step 1 of 2", out)
        self.assertEqual(int(self.commits()), int(before) + 1, "one `step --commit`, one commit")
        self.assertEqual(self.read("src/lend.ts"), "export const limit = 4\n")
        show = subprocess.run(["git", "show", "HEAD:src/lend.ts"], cwd=self.t.root, capture_output=True, text=True).stdout
        self.assertEqual(show, "export const limit = 4\n", "the commit holds the formatted file")
        self.assertEqual(subprocess.run(["git", "status", "--porcelain"], cwd=self.t.root, capture_output=True, text=True).stdout, "")
        rows = [json.loads(line) for line in self.read(".spry/pace/steps.jsonl").strip().split("\n")]
        self.assertEqual([(r["command"], r.get("ok")) for r in rows[-2:]], [("fix", None), ("gate", True)], "one gate, not two")
        self.assertEqual((rows[-2]["checks"], rows[-2]["files"], rows[-2]["first"]), (["format"], 2, True))

    def test_a_lint_failure_still_refuses_the_step_but_the_formatting_is_already_done(self):
        self.on_branch()
        self.fast_checks()
        before = self.commits()
        self.write("src/lend.ts", "export const limit = 4 UGLY LINT\n")
        code, out = self.say(True, False, False)
        self.assertEqual(code, 1, out)
        self.assertIn("✗ lint", out)
        self.assertNotIn("✗ format", out, "CH-84: only what the agent must mend is red")
        self.assertIn("step 1 not committed: the fast checks are red", out)
        self.assertEqual(self.read("src/lend.ts"), "export const limit = 4 LINT\n", "formatted; the lint fault is the agent's")
        self.assertEqual(self.commits(), before)
        self.write("src/lend.ts", "export const limit = 4 UGLY\n")
        self.write("src/page.ts", "export const shown = true\n")
        code, out = self.say(True, False, False)
        self.assertEqual(code, 0, out)
        self.assertTrue(out.split("\n")[0].endswith("files changed: src/lend.ts"), "only the files the formatter changed are named")

    def test_without_a_fix_command_a_format_failure_refuses_the_step_as_before(self):
        self.on_branch()
        self.fast_checks(fix="")
        before = self.commits()
        self.write("src/lend.ts", "export const limit = 4 UGLY\n")
        code, out = self.say(True, False, False)
        self.assertEqual(code, 1, out)
        self.assertNotIn("fixed by", out)
        self.assertEqual(self.read("src/lend.ts"), "export const limit = 4 UGLY\n")
        for fix, why in (("<formatter in write mode> {files}", "a placeholder is not a command"), ("true", "")):
            self.fast_checks(fix=fix)
            before = self.commits()
            code, out = self.say(True, False, False)
            self.assertEqual(code, 1, out + why)
            self.assertEqual(self.commits(), before)
        self.assertIn("– the `fix` of format changed no file, so the red stands", out)
        self.assertIn("step 1 not committed: the fast checks are red", out)
        self.fast_checks(fix="echo cannot parse >&2; exit 3")
        code, out = self.say(True, False, False)
        self.assertEqual(code, 1, out)
        self.assertIn("✗ format, fix", out)
        self.assertIn("cannot parse", out)
        self.fast_checks()
        code, out = self.say(True, False, False)
        self.assertEqual(code, 0, out)
        self.assertIn("– format: the `fix` ran before the checks — files changed: src/lend.ts", out,
                      "CH-84: a red an earlier gate found is fixed before the checks run again")
        self.assertIn("committed step 1 of 2", out)

    def test_a_slice_over_the_size_cap_is_the_person_s_call(self):
        self.on_branch()
        self.write("spry/spry.config.json", json.dumps({**CONFIG, "slices": {"steps": {"max_lines": 2}}}))
        self.run_git("commit", "-qam", "docs: cap")
        self.write("src/lend.ts", "a\nb\nc\n")
        self.say(True, False, False)
        lines = spry.step_merge_lines(self.t.project(), self.t.project().items["SL-1"], "main")
        self.assertTrue(any(s == "warn" and "3 lines of code changed, over" in x for s, x in lines), lines)

    def test_a_step_over_its_own_cap_is_named_at_its_commit_and_at_the_merge(self):
        self.on_branch()
        self.write("spry/spry.config.json", json.dumps({**CONFIG, "slices": {"steps": {"max_lines": 0, "step_lines": 2}}}))
        self.run_git("commit", "-qam", "docs: cap")
        self.write("src/lend.ts", "a\nb\nc\n")
        code, out = self.say(True, False, False)
        self.assertEqual(code, 0, out)
        self.assertIn("committed step 1 of 2", out)
        self.assertIn("! step 1: 3 lines of code changed, over `slices.steps.step_lines` (2)", out)
        self.write("src/due.ts", "d\n")
        code, out = self.say(True, False, False)
        self.assertEqual(code, 0, out)
        self.assertNotIn("step_lines", out, "a step under the cap says nothing")
        lines = spry.step_merge_lines(self.t.project(), self.t.project().items["SL-1"], "main")
        warns = [x for s, x in lines if s == "warn"]
        self.assertEqual(len(warns), 1, lines)
        self.assertIn("step 1: 3 lines of code changed", warns[0])
        self.assertFalse([x for x in warns if "max_lines" in x], "max_lines 0 turns the slice cap off")

    def test_the_step_cap_is_off_by_default(self):
        self.on_branch()
        self.write("src/lend.ts", "x\n" * 900)
        code, out = self.say(True, False, False)
        self.assertEqual(code, 0, out)
        self.assertNotIn("step_lines", out)
        self.assertEqual(spry.steps_config(self.t.project())["step_lines"], 0)
        lines = spry.step_merge_lines(self.t.project(), self.t.project().items["SL-1"], "main")
        self.assertFalse([x for s, x in lines if s == "warn" and "step_lines" in x], lines)
        self.assertTrue([x for s, x in lines if s == "warn" and "max_lines" in x], "the slice cap still holds")

    def test_generated_files_are_counted_beside_the_size_not_in_it(self):
        self.on_branch()
        self.write("spry/spry.config.json", json.dumps({**CONFIG, "checks": {"generated": ["src/client/**"]},
                                                        "slices": {"steps": {"max_lines": 2}}}))
        self.run_git("commit", "-qam", "docs: cap")
        self.write("src/client/api.ts", "x\n" * 50)
        self.say(True, False, False)
        project = self.t.project()
        self.assertEqual(spry.code_lines(project, "main"), (0, 50), "a slice that only regenerates a client")
        lines = spry.step_merge_lines(project, project.items["SL-1"], "main")
        self.assertIn(("ok", "steps: 0 lines of code changed (50 generated, not counted)"), lines)
        self.assertFalse([x for s, x in lines if s == "warn"], lines)
        self.write("src/lend.ts", "a\nb\nc\n")
        self.say(True, False, False)
        lines = spry.step_merge_lines(self.t.project(), self.t.project().items["SL-1"], "main")
        self.assertTrue(any(s == "warn" and "3 lines of code changed (50 generated, not counted), over" in x
                            for s, x in lines), lines)

    def test_pace_counts_generated_lines_apart(self):
        self.write("spry/spry.config.json", json.dumps({**CONFIG, "checks": {"generated": ["src/client/**"]}}))
        self.run_git = git_repo(self.t.root)
        self.write("src/client/api.ts", "x\n" * 40)
        self.write("src/lend.ts", "a\nb\nc\n")
        self.run_git("add", "-A")
        self.run_git("commit", "-qm", "feat: lend\n\nSlice: SL-1")
        self.write("src/client/api.ts", "y\n" * 40)
        self.run_git("commit", "-qam", "chore: client\n\nSlice: SL-2")
        self.assertEqual(spry.pace_lines(self.t.project()), {"SL-1": (3, 40), "SL-2": (0, 80)})
        self.assertEqual(spry.pace_size({"lines": 0, "generated": 80}), ", 0 lines changed and 80 generated")
        self.assertEqual(spry.pace_size({"lines": 3, "generated": 0}), ", 3 lines changed")
        self.assertEqual(spry.pace_size({"lines": None}), "")

    def test_the_pull_request_and_the_squash_list_the_steps(self):
        project = self.t.project()
        self.assertIn("**Built in 2 steps**", spry.pr_body(project, "SL-1"))
        self.assertIn("Steps:\n1. Refuse a fifth book\n2. Show the limit\n\nSlice: SL-1", spry.merge_message(project, "SL-1"))

    def wrong(self):
        return spry.step_state(self.t.project(), self.t.project().items["SL-1"], "main")["wrong"]

    def test_a_step_committed_twice_or_out_of_order_is_wrong(self):
        self.on_branch()
        self.write("src/lend.ts", "a\n")
        self.run_git("add", "-A")
        self.run_git("commit", "-qm", "two first", "-m", "Step: SL-1/2")
        self.assertTrue(any("out of order: 2" in w for w in self.wrong()), self.wrong())
        self.run_git("reset", "-q", "--hard", "main")
        self.write("src/lend.ts", "a\n")
        self.say(True, False, False)
        self.write("src/lend.ts", "b\n")
        self.run_git("commit", "-qam", "again", "-m", "Step: SL-1/1")
        self.assertTrue(any("step 1 committed twice" in w for w in self.wrong()), self.wrong())
        self.assertEqual(self.say(True, False, False)[0], 1, "--commit refuses while the steps are wrong")

    def test_a_squash_fold_is_not_a_fixup(self):
        self.on_branch()
        self.write("src/lend.ts", "a\n")
        self.say(True, False, False)
        self.write("src/lend.ts", "b\n")
        self.run_git("commit", "-qa", "--squash=HEAD", "-m", "more")
        self.assertTrue(any("without a `Step:` trailer" in w for w in self.wrong()), self.wrong())

    def test_check_base_warns_on_the_slice_s_branch(self):
        self.on_branch()
        self.write("src/lend.ts", "a\n")
        self.run_git("add", "-A")
        self.run_git("commit", "-qm", "by hand")
        project = self.t.project()
        spry.step_warnings(project, "main")
        self.assertTrue(any(p.level == "warning" and "without a `Step:` trailer" in p.message for p in project.problems))

    def test_commit_and_squash_only_on_the_slice_s_branch(self):
        self.run_git = git_repo(self.t.root)
        self.write("src/lend.ts", "a\n")
        code, out = self.say(True, False, False)
        self.assertEqual(code, 1)
        self.assertIn("not SL-1's branch", out)
        self.assertIn("not SL-1's branch", self.say(False, False, True)[1])

    FAKE_AGENT = r'''
import json, os, subprocess, sys
args, root, here = sys.argv[1:], os.getcwd(), os.path.dirname(os.path.abspath(__file__))
prompt = args[args.index("-p") + 1]
mode = open(os.path.join(here, "mode")).read().strip()
calls = os.path.join(here, "calls")
seen = [json.loads(line) for line in open(calls)] if os.path.exists(calls) else []
with open(calls, "a") as handle:
    handle.write(json.dumps({"args": args, "run": os.environ.get("SPRY_RUN")}) + "\n")
def git(*a):
    subprocess.run(["git", *a], cwd=root, check=True, capture_output=True)
reply, denied = "DONE\n- [Built] one step", []
if mode == "idle":
    reply = "DONE\n- [Checked] nothing to do"
elif mode == "denied":
    reply, denied = "I could not run it.", [{"tool_name": "Bash", "tool_input": {"command": "pnpm test"}}]
elif prompt.startswith("/spry:slice-build"):
    k = sum(1 for c in seen if "/spry:slice-build SL-1" in c["args"]) + 1
    os.makedirs(os.path.join(root, "src"), exist_ok=True)
    open(os.path.join(root, "src", f"f{k}.ts"), "w").write("export const x = 1\n")
    git("add", "-A")
    git("commit", "-qm", f"SL-1 step {k}: t\n\nStep: SL-1/{k}")
elif "--resume" in args:
    doc = os.path.join(root, open(os.path.join(here, "doc")).read().strip())
    text = open(doc).read().replace("state: open", "state: closed")
    open(doc, "w").write(text)
    git("commit", "-qam", "docs(slice): SL-1 close summary")
    reply = "DONE\n- [Closed] SL-1"
else:
    reply = "DONE\n- [Reviewed] 1 Should\nASK\n1. Fix it?\n   a. Yes (recommended): it is the finding's own suggestion\n   b. No"
print(json.dumps({"result": reply, "session_id": f"sess-{len(seen) + 1}", "num_turns": 2, "permission_denials": denied}))
'''

    def fake_agent(self, mode="normal", **run):
        folder = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, folder)
        for name, text in (("agent.py", self.FAKE_AGENT), ("mode", mode), ("doc", f"{S}/SL-1-a.md")):
            with open(os.path.join(folder, name), "w") as handle:
                handle.write(text)
        self.write("spry/spry.config.json", json.dumps({**CONFIG, "main_branch": "main",
                                                        "run": {"command": [sys.executable, os.path.join(folder, "agent.py")], **run}}))
        if not os.path.isdir(os.path.join(self.t.root, ".git")):
            self.on_branch()
            self.run_git("update-ref", "refs/remotes/origin/main", "main")

        def calls():
            with open(os.path.join(folder, "calls")) as handle:
                return [json.loads(line) for line in handle]

        def go(**given):
            lines = []
            return spry.run_slice(self.t.project(), "SL-1", say=lines.append, **given), "\n".join(lines)
        return go, calls

    def test_run_takes_a_slice_through_fresh_sessions_and_stops_when_one_asks(self):
        go, calls = self.fake_agent(models={"build": "small"}, args=["--permission-mode", "acceptEdits"])
        code, out = go(dry_run=True)
        self.assertEqual(code, 0)
        self.assertIn("SL-1 · next: build (0 of 2 steps)", out)
        code, out = go()
        self.assertEqual(code, 3, out)
        self.assertIn("→ build · /spry:slice-build SL-1 · a fresh session · 0 of 2 steps", out)
        self.assertIn("→ build · /spry:slice-build SL-1 · a fresh session · 1 of 2 steps", out)
        self.assertIn("→ close · /spry:slice-close SL-1 · a fresh session · not reviewed, 0 falsify rows", out)
        self.assertIn("! the close session needs you", out)
        self.assertIn("1. Fix it?", out, "the question is shown whole")
        self.assertIn('spry.py run SL-1 --answer "<your answer>"', out)
        made = calls()
        self.assertEqual([c["run"] for c in made], ["1", "1", "1"], "every session knows a runner started it")
        self.assertIn("--model", made[0]["args"])
        self.assertNotIn("--model", made[2]["args"], "only the build was given a model")
        self.assertEqual(made[0]["args"][-2:], ["--permission-mode", "acceptEdits"])
        note = made[0]["args"][made[0]["args"].index("--append-system-prompt") + 1]
        self.assertIn("never answer it yourself", note)
        self.assertIn("Never merge", note)
        code, out = go(answer="1a")
        self.assertEqual(code, 0, out)
        self.assertIn("→ close · the answer, to the session that asked", out)
        self.assertIn("✓ SL-1 is closed and its pull request is ready — the merge is yours: /spry:merge SL-1", out)
        last = calls()[-1]["args"]
        self.assertEqual((last[last.index("-p") + 1], last[last.index("--resume") + 1]), ("1a", "sess-3"))

    def test_run_stops_on_a_refused_call_a_session_that_did_nothing_and_a_missing_answer(self):
        go, calls = self.fake_agent("denied")
        code, out = go()
        self.assertEqual(code, 3)
        self.assertIn("was refused 1 call it had no permission for — the first: `pnpm test`", out)
        self.assertIn("`run.args`", out)
        go, calls = self.fake_agent("idle")
        code, out = go()
        self.assertEqual(code, 3)
        self.assertEqual(len(calls()), 1, "one session that changed nothing is enough")
        self.assertIn("the build session ended with SL-1 where it was (0 of 2 steps) and no question", out)
        os.remove(os.path.join(self.t.root, ".spry/run/SL-1.json"))
        code, out = go(answer="yes")
        self.assertEqual(code, 1)
        self.assertIn("no session of SL-1 is waiting for an answer", out)

    def test_a_run_session_never_merges_and_a_review_answer_can_be_given_ahead(self):
        go, calls = self.fake_agent(review="b")
        self.assertEqual(self.t.problems(), [])
        project = self.t.project()
        payload = {"tool_input": {"command": "gh pr merge 1 --squash"}}
        with unittest.mock.patch.dict(os.environ, {"SPRY_RUN": "1"}):
            denied = spry.hook_merge(project, payload)
            said = []
            self.assertEqual(spry.merge_finish(project, "SL-1", None, say=said.append), 1)
        self.assertIn("the merge is the person's", json.dumps(denied, ensure_ascii=False))
        self.assertIn("the merge is the person's", said[0])
        go()
        close = [c["args"] for c in calls() if "/spry:slice-close SL-1" in c["args"]][0]
        note = close[close.index("--append-system-prompt") + 1]
        self.assertIn("answered in advance, in `run.review`: b", note)
        self.write("spry/spry.config.json", json.dumps({**CONFIG, "run": {"review": "a"}}))
        self.assertProblem(self.t.problems(), "never `a`: the merge is the person's")

    def test_ranges_read_the_branch_without_checking_it_out(self):
        self.on_branch()
        self.write("src/lend.ts", "a\n")
        self.say(True, False, False)
        self.run_git("checkout", "-q", "main")
        code, out = self.say(False, True, False, head="sl-1-a")
        self.assertEqual(code, 0, out)
        self.assertIn("· Refuse a fifth book · AC-1", out)
        self.assertIn("cannot find SL-1's branch", self.say(False, True, False)[1], "no remote to fall back on")

    def test_related_reads_the_steps_plan(self):
        self.assertEqual(spry.plan_paths(self.text), {"src/lend.ts", "src/page.ts"})

    def test_pace_allows_a_reviewer_per_step(self):
        project = self.t.project()
        s = {"id": "SL-1", "kinds": {}, "phases": {}, "gates": [], "reviews": [{}] * 5}
        self.assertFalse(any("review agents" in f for f in spry.pace_flags(project, s)), "3 + 2 steps")
        s["reviews"] = [{}] * 6
        self.assertTrue(any("6 review agents" in f for f in spry.pace_flags(project, s)))

    def test_slices_mode_is_gone_and_split_still_means_one_change_a_slice(self):
        """CH-88: every slice is built in steps. A config that still says `split` keeps one step a
        slice until it is migrated; `check` says how, as a warning."""
        def warned():
            return [str(p) for p in spry.check(self.t.project()) if p.level == "warning"]
        self.assertEqual(spry.steps_config(self.t.project())["max"], 5)
        self.assertEqual(warned(), [])
        self.write("spry/spry.config.json", json.dumps({**CONFIG, "slices": {"mode": "split"}}))
        self.assertEqual(spry.steps_config(self.t.project())["max"], 1)
        self.assertProblem(warned(), "`slices.mode` is gone (CH-88)")
        self.assertProblem(warned(), "set `slices.steps.max` to 1")
        self.assertProblem(self.t.problems(), "2 steps, over `slices.steps.max` (1)")
        self.write("spry/spry.config.json", json.dumps({**CONFIG, "slices": {"mode": "split", "steps": {"max": 3}}}))
        self.assertEqual(spry.steps_config(self.t.project())["max"], 3, "a value the project set wins")
        self.write("spry/spry.config.json", json.dumps({**CONFIG, "slices": {"mode": "steps"}}))
        self.assertEqual(spry.steps_config(self.t.project())["max"], 5)
        self.assertProblem(warned(), "remove the key")
        self.assertEqual(self.t.problems(), [])

    def test_a_slice_of_one_step_has_one_reviewer(self):
        one = STEPS.split("#### Step 2")[0].replace("Covers: AC-1", "Covers: AC-1, AC-2")
        self.assertEqual(self.with_steps(one), [])
        self.on_branch()
        self.write("src/lend.ts", "export const limit = 4\n")
        self.assertEqual(self.say(True, False, False)[0], 0)
        code, out = self.say(False, True, False)
        self.assertRegex(out, r"^one step · one reviewer reads the whole diff · git diff \w+ \w+ · Refuse a fifth book$")

    def test_the_hook_sends_a_code_commit_to_the_tool(self):
        self.write("spry/spry.config.json", json.dumps({**CONFIG, "main_branch": "main", "hooks": {"step_commit": True}}))
        self.on_branch()

        def hook(command):
            code, reply = spry.agent_hook("step_commit", json.dumps({"cwd": self.t.root, "tool_name": "Bash",
                                                                    "tool_input": {"command": command}}))
            return (reply or {}).get("hookSpecificOutput", {}).get("permissionDecision")

        self.write("spry/spry.config.json", json.dumps({**CONFIG, "main_branch": "main",
                                                        "hooks": {"step_commit": True, "session": True}}))
        told = spry.agent_hook("session", json.dumps({"cwd": self.t.root}))[1]
        self.assertIn("SL-1 is built in 2 steps", told["hookSpecificOutput"]["additionalContext"])
        self.write("src/lend.ts", "export const limit = 4\n")
        self.assertEqual(hook("git add -A && git commit -m 'limit'"), "deny")
        self.assertIsNone(hook("git commit --fixup=HEAD"))
        self.assertIsNone(hook("git status"))
        os.remove(os.path.join(self.t.root, "src", "lend.ts"))
        self.write(f"{S}/SL-1-a.md", self.text + "\n")
        self.write("src/lend.ts", "export const limit = 4\n")
        self.run_git("add", f"{S}/SL-1-a.md")
        self.assertIsNone(hook("git commit -m 'docs(slice): SL-1 work order'"), "only documents are staged")
        self.assertEqual(hook("git commit -am 'docs(slice): SL-1 work order'"), "deny", "-a takes the code too")
        os.remove(os.path.join(self.t.root, "src", "lend.ts"))
        self.assertIsNone(hook("git commit -am 'docs(slice): SL-1 work order'"), "documents alone")
        self.run_git("checkout", "-q", "main")
        self.write("src/lend.ts", "export const limit = 4\n")
        self.assertIsNone(hook("git commit -am x"), "not a steps branch")


class Issues(Base):
    """GitHub issues are requests: a plan item names the ones it came from, and spry shows them its stage."""

    def named(self, text, numbers="[5]"):
        return text.replace("audience: 3\n", f"audience: 3\nissues: {numbers}\n", 1)

    def key(self, rel):
        return rel.replace("/", "__")

    def test_check_names_a_bad_issues_list_and_the_removed_switch(self):
        t = self.tree(**{self.key(f"{S}/README.md"): self.named(story("S-1"), "[5, #6]")})
        self.assertFalse([p for p in t.problems() if "issue" in p])
        t = self.tree(**{self.key(f"{S}/README.md"): self.named(story("S-1"), "[soon]")})
        self.assertProblem(t.problems(), "`issues` names 'soon'")
        t = self.tree(**{self.key(f"{S}/SL-1-a.md"): slice_("SL-1").replace("pr: 1\n", "pr: 1\nissues: [5]\n")})
        self.assertProblem(t.problems(), "a slice names no issue")
        t = self.tree(**{self.key(f"{S}/SL-1-a.md"): slice_("SL-1").replace("pr: 1\n", "pr: 1\nissue: 12\n")})
        self.assertFalse([p for p in t.problems() if "issue" in p], "an old slice's issue is history")
        on = json.dumps(dict(CONFIG, slices={"issue": True}))
        warned = [str(p) for p in spry.check(self.tree(**{"spry__spry.config.json": on}).project())]
        self.assertTrue(any("`slices.issue` is gone" in p for p in warned))

    def test_link_adds_an_issue_to_a_plan_item_once(self):
        t = self.tree()
        spry.link_issue(t.project(), "S-1", "#5")
        path = spry.link_issue(t.project(), "S-1", "5")
        spry.link_issue(t.project(), "S-1", "6")
        with open(path) as handle:
            self.assertIn("issues: [5, 6]\n", handle.read())
        with self.assertRaises(SystemExit):
            spry.link_issue(t.project(), "S-1", "next")
        with self.assertRaisesRegex(SystemExit, "no item"):
            spry.link_issue(t.project(), "S-9", "5")

    def test_an_items_stage_is_derived_from_the_plan(self):
        stage = lambda **files: spry.issue_stages(self.tree(**files).project())[5]["stage"]  # noqa: E731
        sk, sl = self.key(f"{S}/README.md"), self.key(f"{S}/SL-1-a.md")
        self.assertEqual(stage(**{sk: self.named(story("S-1"))}), "done", "closed slice, criterion proven")
        self.assertEqual(stage(**{sk: self.named(story("S-1")), sl: slice_("SL-1", state="open")}), "in-progress")
        self.assertEqual(stage(**{sk: self.named(story("S-1")), sl: slice_("SL-1", state="planned", check=False)}), "ready")
        self.assertEqual(stage(**{sk: self.named(story("S-1", state="draft", check=False)), sl: None}), "accepted")
        self.assertEqual(stage(**{sk: self.named(story("S-1", state="dropped")), sl: None}), "declined")
        self.assertEqual(stage(**{self.key(f"{F}/README.md"): self.named(item("F-1"))}), "done", "every story done")

    def test_an_issue_several_items_name_is_done_when_all_of_them_are(self):
        other = "spry/plan/M-1-m/E-1-e/F-1-f/S-2-t/README.md"
        files = {self.key(f"{S}/README.md"): self.named(story("S-1")),
                 self.key(other): self.named(story("S-2", state="draft", check=False))}
        entry = spry.issue_stages(self.tree(**files).project())[5]
        self.assertEqual(entry["stage"], "in-progress", "one built, one still being planned")
        self.assertEqual([(i.id, s) for i, s in entry["items"]], [("S-1", "done"), ("S-2", "accepted")])
        files[self.key(other)] = self.named(story("S-2", state="dropped"))
        self.assertEqual(spry.issue_stages(self.tree(**files).project())[5]["stage"], "done", "dropped ones do not count")

    def test_sync_labels_open_issues_and_comments_only_when_the_stage_changes(self):
        stages = {n: {"stage": "done", "items": []} for n in (1, 2, 3, 4, 5, 6)}
        current = {1: {"state": "open", "labels": ["bug"]},
                   2: {"state": "open", "labels": ["spry:done"]},
                   3: {"state": "open", "labels": ["spry:in-progress", "phase:A"]},
                   4: {"state": "closed", "labels": ["spry:in-progress"]},
                   5: None,
                   6: {"state": "open", "labels": ["spry:done", "spry:ready"]}}
        got = {a["n"]: a for a in spry.issue_actions(stages, current)}
        self.assertEqual((got[1]["add"], got[1]["remove"], got[1]["comment"]), ("spry:done", [], True))
        self.assertNotIn(2, got, "already shows its stage")
        self.assertEqual((got[3]["remove"], got[3]["comment"]), (["spry:in-progress"], True), "other labels stay")
        self.assertNotIn(4, got, "a person closed it: left alone")
        self.assertIn("no such issue", got[5]["skip"])
        self.assertEqual((got[6]["remove"], got[6]["comment"]), (["spry:ready"], False), "the stage did not change")

    def test_the_comment_is_plain_and_never_closes_the_issue(self):
        files = {self.key(f"{S}/README.md"): self.named(story("S-1"))}
        p = self.tree(**files).project()
        text = spry.issue_comment(p, spry.issue_stages(p)[5], "https://github.com/o/r")
        self.assertIn("**Built.**", text)
        self.assertIn("Close this issue once it has been tested", text)
        self.assertIn("[S-1 Title of S-1](https://github.com/o/r/blob/main/", text)
        self.assertIn("— built", text)
        self.assertNotRegex(text, r"(?i)\b(closes|fixes|resolves) #")

    def test_a_merge_closes_no_issue(self):
        text = slice_("SL-1").replace("pr: 1\n", "pr: 1\nissue: 12\n")
        p = self.tree(**{self.key(f"{S}/SL-1-a.md"): text}).project()
        self.assertNotIn("Closes", spry.merge_message(p, "SL-1"))
        self.assertNotIn("issue", spry.pr_body(p, "SL-1").split("\n")[0])
        self.assertEqual([(s.id, n) for s, n in spry.legacy_issues(p)], [("SL-1", 12)])
        titles = {12: "SL-1 Slice SL-1", 30: "SL-1 again", 31: "SL-9 not in this plan", 32: "Lend more books"}
        self.assertEqual([(s.id, n) for s, n in spry.legacy_issues(p, titles)], [("SL-1", 12), ("SL-1", 30)],
                         "a slice still on its branch has its issue: there; its title names it")

    def test_issues_sync_edits_then_comments_through_gh(self):
        p = self.tree(**{self.key(f"{S}/README.md"): self.named(story("S-1"))}).project()
        calls = []

        def gh(_project, *args, input=None):
            calls.append(args)
            out = "[]" if args[:2] == ("label", "list") else ""
            return subprocess.CompletedProcess(args, 0, out, "")

        args = spry.argparse.Namespace(legacy=False, close=False, sync=True, dry_run=False, offline=False, json=False)
        with unittest.mock.patch.object(spry, "gh_run", gh), \
                unittest.mock.patch.object(spry, "issue_states", lambda *_: {5: {"state": "open", "labels": []}}), \
                contextlib.redirect_stdout(io.StringIO()) as out:
            self.assertEqual(spry.issues_command(p, args), 0)
        self.assertEqual(sum(1 for c in calls if c[:2] == ("label", "create")), len(spry.ISSUE_STAGES))
        self.assertIn(("issue", "edit", "5", "--add-label", "spry:done"), calls)
        self.assertEqual(calls[-1][:3], ("issue", "comment", "5"))
        self.assertIn("#5 done: S-1 Title of S-1 — set spry:done", out.getvalue())
        calls.clear()
        args.dry_run = True
        with unittest.mock.patch.object(spry, "gh_run", gh), \
                unittest.mock.patch.object(spry, "issue_states", lambda *_: {5: {"state": "open", "labels": []}}), \
                contextlib.redirect_stdout(io.StringIO()) as out:
            spry.issues_command(p, args)
        self.assertEqual(calls, [], "a dry run changes nothing")
        self.assertIn("would set spry:done", out.getvalue())


class ReviewCheck(unittest.TestCase):
    DIFF = (
        "diff --git a/story.md b/story.md\n--- a/story.md\n+++ b/story.md\n"
        "@@ -1,3 +1,4 @@\n # S-1\n-Old line\n+A member borrows.\n+Up to five books.\n end\n"
        "@@ -20,2 +21,2 @@\n tail\n-old tail\n+new tail\n"
    )

    def payload(self, *comments, event="COMMENT"):
        return {"commit_id": "abc", "event": event, "body": "Two fixes.", "comments": list(comments)}

    def suggest(self, line, text, start=None):
        c = {"path": "story.md", "line": line, "side": "RIGHT", "body": f"Say it plainly.\n```suggestion\n{text}\n```"}
        if start:
            c.update(start_line=start, start_side="RIGHT")
        return c

    def test_a_good_review_passes(self):
        good = self.payload(self.suggest(3, "A member borrows up to five books.", start=2),
                            {"path": "story.md", "line": 21, "body": "Why tail?"})
        self.assertEqual(spry.review_check(good, self.DIFF), [])

    def test_lines_outside_the_diff_or_across_parts_are_refused(self):
        far = spry.review_check(self.payload(self.suggest(9, "x")), self.DIFF)
        self.assertIn("outside the diff", far[0])
        across = spry.review_check(self.payload(self.suggest(21, "x", start=4)), self.DIFF)
        self.assertIn("outside the diff", across[0])
        missing = spry.review_check(self.payload({"path": "other.md", "line": 1, "body": "?"}), self.DIFF)
        self.assertIn("not in the pull request's diff", missing[0])

    def test_suggestions_never_overlap_and_never_repeat_the_lines(self):
        twice = spry.review_check(self.payload(self.suggest(3, "a", start=2), self.suggest(3, "b")), self.DIFF)
        self.assertEqual(len(twice), 1)
        self.assertIn("overlaps comment 1", twice[0])
        same = spry.review_check(self.payload(self.suggest(2, "A member borrows.")), self.DIFF)
        self.assertIn("same as the lines", same[0])
        open_block = self.payload({"path": "story.md", "line": 2, "body": "```suggestion\nx\n"})
        self.assertIn("not closed", spry.review_check(open_block, self.DIFF)[0])

    def test_your_own_pull_request_takes_only_a_comment(self):
        own = spry.review_check(self.payload(event="REQUEST_CHANGES"), self.DIFF, own=True)
        self.assertIn("use COMMENT", own[0])
        self.assertEqual(spry.review_check(self.payload(event="REQUEST_CHANGES"), self.DIFF), [])

    def test_cli(self):
        with tempfile.TemporaryDirectory() as tmp:
            for name, text in (("p.json", json.dumps(self.payload(self.suggest(9, "x")))), ("d.diff", self.DIFF)):
                with open(os.path.join(tmp, name), "w") as handle:
                    handle.write(text)
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                code = spry.main(["review-check", os.path.join(tmp, "p.json"), "--diff", os.path.join(tmp, "d.diff")])
            self.assertEqual(code, 1)
            self.assertIn("fix them before posting", out.getvalue())


SETUP_SEEN = ("python3 -c \"import os; e = os.environ; open('.setup-seen', 'w').write("
              "e['SPRY_WORKTREE'] + ' ' + e['SPRY_WORKTREE_NAME'] + ' ' + e.get('SPRY_FALSIFY_SLOT', '-'))\"")


class Worktrees(Base):
    """Worktrees made, claimed, sent home and pruned by the tool; the progress log `watch` reads (§24)."""

    def setUp(self):
        config = {**CONFIG, "main_branch": "main", "hooks": {"session": True, "session_end": True},
                  "worktrees": {"max": 2, "setup": SETUP_SEEN, "share": [".env.example"]}}
        self.t = self.tree(**{"spry__spry.config.json": json.dumps(config), ".gitignore": ".claude/\n.spry/\n.setup-seen\n",
                              ".env.example": "PORT=1\n"})
        self.run_git = git_repo(self.t.root)
        self.root = os.path.realpath(self.t.root)
        patch = unittest.mock.patch.dict(os.environ, {"SPRY_SESSION_PID": str(os.getpid())})
        patch.start()
        self.addCleanup(patch.stop)
        for name in ("CLAUDE_CODE_SESSION_ID", "CLAUDE_PID", "SPRY_SESSION"):  # as if not run by an agent
            os.environ.pop(name, None)

    def other_session(self):
        proc = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"])
        self.addCleanup(proc.wait)
        self.addCleanup(proc.kill)
        return proc.pid

    def run_tool(self, *args, root=None):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = spry.main(["--root", root or self.root, *args])
        return code, out.getvalue()

    def path(self, name):
        return os.path.join(self.root, ".claude", "worktrees", name)

    def git_in(self, root, *args):
        return subprocess.run(["git", "-C", root, "-c", "user.name=t", "-c", "user.email=t@t", *args],
                              capture_output=True, text=True, check=True).stdout

    def test_new_makes_a_set_up_worktree_on_its_home_branch(self):
        code, out = self.run_tool("worktree", "new")
        name = os.path.basename(self.root) + "1"
        self.assertEqual(code, 0, out)
        tree = self.path(name)
        self.assertIn(f"{name} · index 1 · `alt1` at main · set up", out)
        self.assertEqual(self.git_in(tree, "branch", "--show-current").strip(), "alt1")
        self.assertEqual(self.git_in(tree, "rev-parse", "HEAD"), self.git_in(self.root, "rev-parse", "main"))
        with open(os.path.join(tree, ".setup-seen")) as handle:
            self.assertEqual(handle.read(), f"1 {name} -", "the set-up sees its index and name, and no slot")
        with open(os.path.join(tree, ".env.example")) as handle:
            self.assertEqual(handle.read(), "PORT=1\n", "worktrees.share is copied in")
        self.assertEqual(self.run_tool("worktree", "new", "second")[0], 0)
        code, out = self.run_tool("worktree", "new", "third")
        self.assertEqual(code, 1)
        self.assertIn("already 2 worktrees, `worktrees.max`", out)
        self.assertEqual(self.run_tool("worktree", "new", "main")[0], 2, "main is the main checkout's name")

    def test_a_failed_setup_says_so_and_keeps_the_worktree(self):
        path = os.path.join(self.root, "spry", "spry.config.json")
        with open(path) as handle:
            config = json.load(handle)
        config["worktrees"]["setup"] = "python3 -c \"import sys; sys.exit('no database server')\""
        with open(path, "w") as handle:
            json.dump(config, handle)
        code, out = self.run_tool("worktree", "new", "one")
        self.assertEqual(code, 1)
        self.assertIn("worktrees.setup failed (exit 1: no database server)", out)
        self.assertIn("one · #1 · `alt1` · free", self.run_tool("worktree", "list")[1])

    def test_two_sessions_cannot_hold_one_worktree_and_a_dead_ones_claim_is_taken(self):
        self.run_tool("worktree", "new", "one")
        code, out = self.run_tool("worktree", "claim", "1")
        self.assertEqual(code, 0, out)
        self.assertIn("one claimed · index 1", out)
        other = self.other_session()
        with unittest.mock.patch.dict(os.environ, {"SPRY_SESSION_PID": str(other)}):
            code, out = self.run_tool("worktree", "claim", "one")
            self.assertEqual(code, 1)
            self.assertIn("one is claimed by another session", out)
            self.assertEqual(self.run_tool("worktree", "release", "one")[0], 1, "nor can it drop the claim")
        self.assertEqual(self.run_tool("worktree", "claim", "one")[0], 0, "the holder claims again")
        dead = subprocess.Popen([sys.executable, "-c", "pass"])
        dead.wait()
        self.run_tool("worktree", "release", "one")
        with unittest.mock.patch.dict(os.environ, {"SPRY_SESSION_PID": str(dead.pid)}):
            self.assertEqual(self.run_tool("worktree", "claim", "one")[0], 0)
        code, out = self.run_tool("worktree", "claim", "one")
        self.assertEqual(code, 0)
        self.assertIn(f"the claim of pid {dead.pid} was stale — taken", out)
        self.assertIn("claimed by pid", self.run_tool("worktree", "list")[1])
        code, out = self.run_tool("worktree", "release", root=self.path("one"))
        self.assertEqual((code, out.strip()), (0, "one released"), "release takes the worktree it runs in")
        self.assertEqual(self.run_tool("worktree", "claim", "main")[0], 2, "the main checkout is never claimed")

    def test_a_claim_goes_stale_when_nothing_is_written(self):
        self.run_tool("worktree", "new", "one")
        other = self.other_session()
        with unittest.mock.patch.dict(os.environ, {"SPRY_SESSION_PID": str(other)}):
            self.run_tool("worktree", "claim", "one")
        record = os.path.join(self.root, ".spry", "worktrees", "one.json")
        with open(record) as handle:
            data = json.load(handle)
        data["claim"]["at"] -= 13 * 3600
        with open(record, "w") as handle:
            json.dump(data, handle)
        self.assertIn("· stale", self.run_tool("worktree", "list")[1])
        self.assertIn("was stale — taken", self.run_tool("worktree", "claim", "one")[1])

    def test_a_worktree_made_by_hand_is_claimed_with_the_index_its_name_ends_in(self):
        self.run_git("worktree", "add", "-q", "-b", "alt2", self.path("app2"), "main")
        code, out = self.run_tool("worktree", "claim", "app2")
        self.assertEqual(code, 0, out)
        self.assertIn("app2 claimed · index 2", out)

    def test_home_puts_the_worktree_back_at_the_main_branchs_head(self):
        self.run_tool("worktree", "new", "one")
        tree = self.path("one")
        self.git_in(tree, "switch", "-qc", "sl-1-a")
        with open(os.path.join(tree, "src", "b.ts"), "w") as handle:
            handle.write("x\n")
        self.git_in(tree, "add", "-A")
        self.git_in(tree, "commit", "-qm", "work")
        with open(os.path.join(tree, "src", "b.ts"), "w") as handle:
            handle.write("y\n")
        code, out = self.run_tool("worktree", "home", root=tree)
        self.assertEqual(code, 1)
        self.assertIn("uncommitted changes", out)
        self.git_in(tree, "checkout", "-q", "--", "src/b.ts")
        code, out = self.run_tool("worktree", "home", root=tree)
        self.assertEqual(code, 0, out)
        self.assertEqual(self.git_in(tree, "branch", "--show-current").strip(), "alt1")
        self.assertEqual(self.git_in(tree, "rev-parse", "HEAD"), self.git_in(self.root, "rev-parse", "main"))
        events = spry.progress_events(spry.Project(self.root, load=False))
        self.assertEqual([(e["worktree"], e["stage"]) for e in events], [("one", "home")])
        self.assertEqual(self.run_tool("worktree", "home")[0], 1, "the main checkout rests on main")

    def test_prune_removes_slot_trees_no_run_owns(self):
        self.run_tool("worktree", "new", "one")
        temp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, temp, True)
        left, busy = os.path.join(temp, "spry-falsify-run-abc"), os.path.join(temp, "spry-falsify-run-def")
        kept = spry.falsify_home(spry.Project(self.root, load=False))
        self.addCleanup(shutil.rmtree, kept, True)
        for parent in (left, busy, kept):
            os.makedirs(parent, exist_ok=True)
            self.run_git("worktree", "add", "-q", "--detach", os.path.join(parent, "w1"), "main")
        held = spry.take_home(busy)
        self.addCleanup(held.close)
        shutil.rmtree(self.path("one"))
        code, out = self.run_tool("worktree", "prune")
        self.assertEqual(code, 0)
        self.assertIn(f"removed: {os.path.realpath(os.path.join(left, 'w1'))}", out)
        self.assertIn("in use by a falsify run", out)
        self.assertIn("forgot: one — its worktree is gone", out)
        self.assertFalse(os.path.exists(left))
        listed = self.run_git and self.git_in(self.root, "worktree", "list")
        self.assertIn("spry-falsify-run-def", listed)
        self.assertIn(os.path.basename(kept), listed, "kept trees stay warm for the next run")
        held.close()
        self.run_tool("worktree", "prune", "--kept")
        listed = self.git_in(self.root, "worktree", "list")
        self.assertNotIn("spry-falsify", listed)

    def test_each_command_writes_the_log_in_the_main_checkout(self):
        self.run_tool("worktree", "new", "one")
        tree = self.path("one")
        self.run_tool("worktree", "claim", "one")
        record = os.path.join(self.root, ".spry", "worktrees", "one.json")
        with open(record) as handle:
            before = json.load(handle)["claim"]["at"]
        time.sleep(0.15)
        self.assertEqual(self.run_tool("say", "routes", "written", "--slice", "SL-1", root=tree)[0], 0)
        self.run_tool("gate", "--fast", root=tree)
        events = spry.progress_events(spry.Project(self.root, load=False))
        self.assertEqual([(e["worktree"], e["stage"], e["said"]) for e in events],
                         [("one", "say", "routes written"), ("one", "gate", "gate --fast green")])
        self.assertEqual(events[0]["slice"], "SL-1")
        with open(record) as handle:
            self.assertGreater(json.load(handle)["claim"]["at"], before, "a worktree that reports keeps its claim")
        with unittest.mock.patch.object(spry, "PROGRESS_LIMIT", 200):
            for n in range(30):
                spry.progress_event(spry.Project(self.root, load=False), "say", f"line {n}")
        self.assertLessEqual(len(spry.progress_events(spry.Project(self.root, load=False))), 40)

    def test_gate_said(self):
        steps = [["spry check", 0.1, True], ["lint", 2.0, False], ["types", 1.0, False]]
        self.assertEqual(spry.gate_said(1, {"steps": steps}, False, False), "gate red: lint, types")
        self.assertEqual(spry.gate_said(0, {"steps": [], "skipped": "stamp"}, False, False),
                         "gate skipped: no code changed since green")
        self.assertEqual(spry.gate_said(0, {"steps": []}, True, False), "gate --fast green")

    def test_watch_shows_each_worktree_its_slice_and_step(self):
        self.run_tool("worktree", "new", "one")
        tree = self.path("one")
        self.run_tool("worktree", "claim", "one")
        doc = os.path.join(tree, S, "SL-1-a.md")
        steps = "### Steps\n\n#### Step 1 · Routes\n\nCovers: AC-1\n\n#### Step 2 · Page\n\nCovers: AC-1\n"
        with open(doc) as handle:
            text = handle.read().replace("state: closed", "state: open").replace("### Plan\n", "### Plan\n\n" + steps)
        self.git_in(tree, "switch", "-qc", "sl-1-a")
        with open(doc, "w") as handle:
            handle.write(text)
        self.git_in(tree, "commit", "-qam", "SL-1 step 1: Routes", "-m", "Step: SL-1/1")
        self.run_tool("say", "routes done", root=tree)
        page = spry.watch_render(spry.Project(self.root, load=False), width=200)
        self.assertIn("one #1 · sl-1-a", page)
        self.assertIn("claimed by pid", page)
        self.assertIn("S-1 › SL-1 Slice SL-1 · step 2 of 2 · Page", page, "the story the slice belongs to")
        self.assertIn("routes done", page)
        self.assertNotIn("quiet for", page)
        later = spry.watch_render(spry.Project(self.root, load=False), width=200, now=time.time() + 2 * 3600)
        self.assertRegex(later, r"quiet for (1h5\d|2h0\d)")

    def test_transcripts_say_what_a_session_waits_on(self):
        log = os.path.join(self.root, "log.jsonl")
        stamp = "2026-11-15T10:00:00Z"
        rows = [{"type": "assistant", "timestamp": stamp, "requestId": "r1",
                 "message": {"stop_reason": "tool_use", "usage": {"input_tokens": 1000, "output_tokens": 10},
                             "content": [{"type": "tool_use", "id": "t1", "name": "AskUserQuestion", "input": {}}]}}]
        with open(log, "w") as handle:
            handle.write("\n".join(json.dumps(r) for r in rows) + "\n")
        transcript = spry.Transcript(log)
        transcript.read(spry.PACE_WEIGHTS)
        now = spry.pace_stamp(stamp) + 90
        self.assertEqual(transcript.state(now), ("asked you a question · 1m", True))
        self.assertEqual(transcript.context, 1000)
        with open(log, "a") as handle:
            handle.write(json.dumps({"type": "user", "timestamp": stamp, "message": {"content": [
                {"type": "tool_result", "tool_use_id": "t1"}]}}) + "\n")
            handle.write(json.dumps({"type": "assistant", "timestamp": stamp, "requestId": "r2",
                                     "message": {"stop_reason": "end_turn", "content": []}}) + "\n")
        transcript.read(spry.PACE_WEIGHTS)
        self.assertEqual(transcript.state(now), ("waiting on you · 1m", True))
        self.assertEqual((transcript.begun, transcript.cleared), (spry.pace_stamp(stamp), False), "never cleared")

    def test_transcripts_say_when_a_session_was_cleared(self):
        log = os.path.join(self.root, "log.jsonl")
        rows = [{"type": "user", "timestamp": "2026-11-15T09:00:00Z", "message": {"content": "<command-name>/clear</command-name>"}},
                {"type": "user", "timestamp": "2026-11-15T09:01:00Z", "message": {"content": "build SL-1"}},
                {"type": "assistant", "timestamp": "2026-11-15T09:02:00Z", "requestId": "r1",
                 "message": {"stop_reason": "end_turn", "content": []}}]
        with open(log, "w") as handle:
            handle.write("\n".join(json.dumps(r) for r in rows) + "\n")
        transcript = spry.Transcript(log)
        transcript.read(spry.PACE_WEIGHTS)
        self.assertEqual((transcript.begun, transcript.cleared), (spry.pace_stamp("2026-11-15T09:00:00Z"), True))

    def test_the_session_hooks_name_the_worktree_and_release_its_claim(self):
        self.run_tool("worktree", "new", "one")
        tree = self.path("one")

        def context(cwd):
            reply = spry.agent_hook("session", json.dumps({"cwd": cwd, "session_id": "abc12345"}))[1]
            return reply["hookSpecificOutput"]["additionalContext"]
        self.assertIn("worktree one (index 1), not claimed — `python3 spry/tool/spry.py worktree claim one`", context(tree))
        self.assertIn("The main checkout, with 1 worktree beside it", context(self.root))
        code, out = self.run_tool("worktree", "claim", "one")
        self.assertIn("claimed by this session", context(tree))
        with open(os.path.join(self.root, ".spry", "worktrees", "one.json")) as handle:
            self.assertEqual(json.load(handle)["claim"]["session"], "abc12345", "the session the hook noted")
        other = self.other_session()
        with unittest.mock.patch.dict(os.environ, {"SPRY_SESSION_PID": str(other)}):
            self.assertIn("another live session claimed", context(tree))
            spry.agent_hook("session_end", json.dumps({"cwd": tree, "session_id": "zzz"}))
        self.assertIn("claimed by pid", self.run_tool("worktree", "list")[1], "another session's end leaves it")
        spry.agent_hook("session_end", json.dumps({"cwd": tree, "session_id": "abc12345", "reason": "clear"}))
        self.assertIn("claimed by pid", self.run_tool("worktree", "list")[1], "a /clear keeps it")
        spry.agent_hook("session", json.dumps({"cwd": tree, "session_id": "def67890", "source": "clear"}))
        with open(os.path.join(self.root, ".spry", "worktrees", "one.json")) as handle:
            self.assertEqual(json.load(handle)["claim"]["session"], "def67890", "the cleared session's new id")
        spry.agent_hook("session_end", json.dumps({"cwd": tree, "session_id": "def67890", "reason": "exit"}))
        self.assertIn("one · #1 · `alt1` · free", self.run_tool("worktree", "list")[1])

    def test_no_worktrees_block_no_change(self):
        t = self.tree(**{"spry__spry.config.json": json.dumps({**CONFIG, "hooks": {"session": True}})})
        git_repo(t.root)
        code, out = self.run_tool("worktree", "list", root=t.root)
        self.assertEqual(code, 2)
        self.assertIn("no `worktrees` block", out)
        text = spry.agent_hook("session", json.dumps({"cwd": t.root}))[1]["hookSpecificOutput"]["additionalContext"]
        self.assertNotIn("worktree", text)
        self.assertEqual(spry.worktree_env(spry.Project(t.root, load=False)), {})


class Example(unittest.TestCase):
    """The worked example in docs/example must stay clean and freshly indexed."""

    def test_check(self):
        problems = spry.check(spry.Project(EXAMPLE))
        self.assertEqual([str(p) for p in problems], [])

    def test_index_is_current(self):
        self.assertEqual(spry.index(spry.Project(EXAMPLE), dry=True), [])

    def test_cli(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = spry.main(["--root", EXAMPLE, "status", "--level", "feature"])
        self.assertEqual(code, 0)
        self.assertIn("F-1 Lend at the desk", out.getvalue())
        self.assertNotIn("S-1", out.getvalue())


class Markdown(unittest.TestCase):
    def test_blocks(self):
        out = spry.md_html("# S-1 Lend a book\n\n## Notes\n\n## Notes\n\n<!-- spry:children -->\n<!-- /spry:children -->\n"
                           "| AC | Then |\n|---|:-:|\n| AC-1 | a \\| b |\n\n- one\n  - two\n- [x] done\n\n"
                           "1. first\n2. second\n\n```ts\nif (a < b) {}\n```\n\n> quoted\n\n---\n")
        self.assertIn('<h1 id="s-1-lend-a-book">S-1 Lend a book</h1>', out)
        self.assertIn('<h2 id="notes-1">', out)
        self.assertNotIn("spry:children", out)
        self.assertIn('<td style="text-align:center">a | b</td>', out)
        self.assertIn("<li>one\n<ul><li>two</li></ul></li>", out)
        self.assertIn('<li class="task"><input type="checkbox" disabled checked> done</li>', out)
        self.assertIn("<ol><li>first</li><li>second</li></ol>", out)
        self.assertIn('<pre><code class="language-ts">if (a &lt; b) {}</code></pre>', out)
        self.assertIn("<blockquote><p>quoted</p></blockquote>", out)
        self.assertIn("<hr>", out)

    def test_inline_escapes_all_but_safe_tags(self):
        out = spry.md_inline("[`a` **b**](x.md) <n> <b>ok</b> <script>x</script> [c](javascript:alert(1)) "
                             '<a href="javascript:x" onclick="y">d</a> snake_case_name')
        self.assertIn('<a href="x.md"><code>a</code> <strong>b</strong></a>', out)
        self.assertIn("&lt;n&gt; <b>ok</b> &lt;script&gt;", out)
        self.assertIn('<a href="#">c</a>', out)
        self.assertIn('<a href="#">d</a>', out)
        self.assertNotIn("onclick", out)
        self.assertIn("snake_case_name", out)

    def test_hostile_input(self):
        self.assertIn("a \ufffd b", spry.md_html("a \x00 b `\x00` \x0099\x00"))  # once hung the server
        for href in ("java\tscript:x", "\x01javascript:x", "java\nscript:x", " javascript:x"):
            self.assertIn('<a href="#">', spry.md_inline(f'<a href="{href}">x</a>'), repr(href))
        self.assertIn('<a href="#">', spry.md_html('see <a href="java\nscript:alert(1)">x</a>'))
        started = __import__("time").time()
        spry.md_inline("*a " * 20000)
        self.assertLess(__import__("time").time() - started, 2)

    def test_longer_fences_hold_shorter_ones(self):
        out = spry.md_html("````md\n```suggestion\nfix\n```\n````\n")
        self.assertEqual(out, '<pre><code class="language-md">```suggestion\nfix\n```</code></pre>')


class Serve(Base):
    def get(self, t, path):
        return spry.serve_response(t.project(), path, "https://github.com/o/r")

    def test_a_dropped_item_is_green_and_struck_in_the_tree(self):
        t = self.tree(**{f"{F}/S-2-x/README.md".replace("/", "__"): story("S-2", state="dropped")})
        page = self.get(t, f"/{F}/README.md")[2].decode()
        self.assertRegex(page, r'<a href="[^"]*S-2-x/README.md" class="dropped"[^>]*><i class="mark dropped">')
        self.assertIn(".mark.dropped{background:var(--accent)", page)
        self.assertIn("aside a.dropped span", page)

    def test_the_qa_page_says_what_to_test_next(self):
        checks = ("---\ntitle: c\naudience: 4\n---\n# c\n\n## Scenarios\n\n"
                  "### AC-1 · One\n\n**Type** happy path · **Where** desk · **Ready** yes\n\n1. a → b\n\n"
                  "### AC-2 · Two\n\n**Type** negative · **Where** desk · **Ready** yes\n\n1. a → b\n\n"
                  "### AC-3 · Three\n\n**Type** negative · **Where** desk · **Ready** yes\n\n1. a → b\n\n"
                  "### AC-5 · Later\n\n**Type** boundary · **Where** desk · **Ready** no — waits for S-1\n\n1. a → b\n\n"
                  "## Check log\n\n| Date | AC | Scenario | Build | By | Result | Notes |\n|---|---|---|---|---|---|---|\n"
                  "| 2026-09-20 | AC-2 | Two | b1 | Q | pass | |\n"
                  "| 2026-10-05 | AC-3 | Three | b2 | Q | fail | see S-1 |\n")
        t = self.tree(**{self.key(f"{S}/README.md"): story("S-1", acs=("AC-1", "AC-2", "AC-3", "AC-4", "AC-5")),
                         self.key(f"{S}/SL-1-a.md"): slice_("SL-1", covers="[AC-1, AC-2, AC-3, AC-4]"),
                         self.key(f"{S}/checks.md"): checks, "src/a.test.ts": "nothing\n"})
        page = self.get(t, "/-/qa")[2].decode()
        self.assertIn('<a href="/-/qa">QA</a>', page)
        lists = {h: page.split(f"<h2>{h}</h2>")[1].split("<h2>")[0]
                 for h in ("Ready to test", "Failing", "Run again", "Needs scenarios", "Waiting")}
        self.assertIn("AC-1</td>", lists["Ready to test"])
        self.assertIn("AC-2</td>", lists["Run again"], "passed 2026-09-20, built again 2026-10-01")
        self.assertIn("AC-3</td>", lists["Failing"])
        self.assertIn('title="Title of S-1">S-1</a>', lists["Failing"].split("<td>")[4], "IDs in the notes link")
        self.assertIn("AC-4</td>", lists["Needs scenarios"])
        self.assertIn("Later", lists["Waiting"])
        for h, body in lists.items():
            self.assertEqual(body.count("<tr>") - 1, 1, h)

    def key(self, rel):
        return rel.replace("/", "__")

    def test_item_page_has_fresh_blocks_and_links(self):
        t = self.tree()
        self.assertEqual(self.get(t, "/")[3], {"Location": "/spry/plan/README.md"})
        code, ctype, body, _ = self.get(t, f"/{F}/README.md")
        page = body.decode()
        self.assertEqual((code, ctype), (200, "text/html; charset=utf-8"))
        self.assertIn('href="S-1-s/README.md">S-1 Title of S-1</a>', page)  # the children block, built now
        self.assertIn('aria-current="page"', page)
        code, _, body, _ = self.get(t, f"/{S}/SL-1-a.md")
        self.assertIn('<a class="badge" href="https://github.com/o/r/pull/1">PR #1</a>', body.decode())
        self.assertIn(f'<a href="/{S}/README.md" title="Title of S-1">S-1/AC-1</a>', body.decode())

    def test_work_bar_on_items_and_the_home_page(self):
        home = "---\ntitle: Home\naudience: 2\n---\n# Home\n"
        t = self.tree(**{f"{F}/bugs/B-1-x/README.md".replace("/", "__"): item("B-1"), "spry__README.md": home})
        page = self.get(t, f"/{E}/README.md")[2].decode()
        self.assertIn('<i class="story" style="width:50.00%"></i>', page)
        self.assertNotIn('<i class="bug"', page, "an open bug leaves its part empty")
        self.assertIn('<b style="left:100%" title="stories 1 of 1"></b>', page)
        self.assertIn('aria-label="all work 1 of 2 (50%) · stories alone 1 of 1 (100%)"', page)
        self.assertNotIn('class="bar"', self.get(t, f"/{S}/README.md")[2].decode(), "no bar on a story")
        self.assertIn('aria-label="M-1 Title of M-1: all work 1 of 2', self.get(t, "/spry/README.md")[2].decode())

    def test_folders_items_and_search(self):
        t = self.tree()
        self.assertEqual(self.get(t, f"/{M}")[3], {"Location": f"/{M}/README.md"})
        self.assertEqual(self.get(t, "/-/item/S-1")[3], {"Location": f"/{S}/README.md"})
        self.assertEqual(self.get(t, "/-/item/S-9")[0], 404)
        self.assertIn("Member", self.get(t, "/-/search?q=borrows")[2].decode())
        self.assertIn("<pre><code>test(&quot;S-1/AC-1", self.get(t, "/src/a.test.ts")[2].decode())

    def test_nothing_outside_the_project_or_hidden(self):
        t = self.tree(**{".env": "SECRET=1"})
        os.makedirs(os.path.join(t.root, ".git"))
        with open(os.path.join(t.root, ".git", "config"), "w") as handle:
            handle.write("x")
        os.symlink(os.path.join(t.root, ".git"), os.path.join(t.root, "gitlink"))
        os.symlink(os.path.join(t.root, ".env"), os.path.join(t.root, "envlink"))
        for path in ("/../etc/passwd", "/%2e%2e/x", "/.env", "/.git/config", "/spry/../../x", "/gitlink/config", "/envlink"):
            self.assertEqual(self.get(t, path)[0], 404, path)

    def test_listings_redirects_and_raw_files_run_no_script(self):
        t = self.tree(**{"docs__javascript:alert(1)": "x", "docs__evil.html": "<script>x</script>\xe9",
                         "docs__pic.svg": "<svg/>"})
        with open(os.path.join(t.root, "docs", "latin.html"), "wb") as handle:
            handle.write(b"<script>x</script>\xe9")
        page = self.get(t, "/docs/")[2].decode()
        self.assertIn('href="./javascript%3Aalert%281%29"', page)
        self.assertEqual(self.get(t, "/%2Fdocs")[3], {"Location": "/docs/"})
        code, ctype, _, headers = self.get(t, "/docs/latin.html")
        self.assertEqual((ctype, headers), ("application/octet-stream", {"Content-Security-Policy": "sandbox; script-src 'none'"}))
        self.assertIn("&lt;script&gt;", self.get(t, "/docs/evil.html")[2].decode())
        self.assertEqual(self.get(t, "/docs/pic.svg")[1:4:2], ("image/svg+xml", {"Content-Security-Policy": "sandbox; script-src 'none'"}))

    def test_answers_only_on_localhost(self):
        import socket
        import urllib.error
        import urllib.request
        t = self.tree()
        with socket.socket() as s:
            s.bind(("127.0.0.1", 0))
            port = s.getsockname()[1]
        import threading
        threading.Thread(target=spry.serve, args=(t.root, port, False, lambda *a: None), daemon=True).start()
        for _ in range(100):
            try:
                with urllib.request.urlopen(f"http://127.0.0.1:{port}/spry/plan/README.md") as response:
                    self.assertEqual(response.status, 200)
                break
            except (ConnectionError, urllib.error.URLError):
                import time
                time.sleep(0.05)
        request = urllib.request.Request(f"http://127.0.0.1:{port}/", headers={"Host": "evil.example"})
        with self.assertRaises(urllib.error.HTTPError) as caught:
            urllib.request.urlopen(request)
        self.assertEqual(caught.exception.code, 403)
        caught.exception.close()


class MergeFlow(unittest.TestCase):
    """`merge-ready` and `merge-finish` (CH-70): merging.md's steps, run by the tool against a real remote,
    with gh faked."""

    def setUp(self):
        self.tmp = os.path.realpath(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.remote = os.path.join(self.tmp, "remote.git")
        subprocess.run(["git", "init", "-q", "--bare", "-b", "main", self.remote], check=True)
        files = base()
        files[f"{S}/SL-1-a.md"] = Merge().closed_slice("| guard | never true | S-1/AC-1 | caught |\n")
        files[f"{S}/SL-2-b.md"] = slice_("SL-2", state="planned", check=False).replace("pr: 1\n", "")
        files[f"{S}/SL-1-a.md"] = files[f"{S}/SL-1-a.md"].replace("state: closed", "state: open")
        seed = Tree(files).root
        self.addCleanup(shutil.rmtree, seed, True)
        git_repo(seed)("push", "-q", self.remote, "main")
        self.root = os.path.join(self.tmp, "clone")
        subprocess.run(["git", "clone", "-q", self.remote, self.root], check=True)
        for key, value in (("user.email", "t@t"), ("user.name", "t")):
            self.git("config", key, value)
        self.git("switch", "-qc", "sl-1-a")
        self.edit(f"{S}/SL-1-a.md", "state: open", "state: closed")
        self.git("commit", "-qam", "docs(slice): SL-1 close summary")
        self.git("push", "-q", "origin", "sl-1-a")
        self.checks = [{"name": "test", "bucket": "pass", "link": "https://x/actions/runs/7/job/1"}]
        self.jobs = [{"name": "test", "steps": [{"name": "run"}]}]
        self.body, self.calls, self.decision, self.author = "old body", [], "", "t"

    def git(self, *args, root=None):
        return subprocess.run(["git", *args], cwd=root or self.root, check=True, capture_output=True, text=True).stdout.strip()

    def edit(self, rel, old, new):
        path = os.path.join(self.root, rel)
        with open(path) as handle:
            text = handle.read()
        with open(path, "w") as handle:
            handle.write(text.replace(old, new))

    def gh(self, _project, *args, input=None):
        self.calls.append(args)
        ok = lambda out="": subprocess.CompletedProcess(args, 0, out, "")
        if args[:2] == ("pr", "view"):
            head = self.git("rev-parse", "origin/sl-1-a")
            return ok(json.dumps({"state": "OPEN", "isDraft": False, "headRefName": "sl-1-a", "headRefOid": head,
                                  "body": self.body, "reviewDecision": self.decision,
                                  "author": {"login": self.author}}))
        if args[:2] == ("pr", "checks"):
            return ok(json.dumps(self.checks))
        if args[:2] == ("run", "view"):
            return ok(json.dumps({"jobs": self.jobs}))
        if args[:2] == ("pr", "edit"):
            self.body = input
            return ok()
        if args[:2] == ("pr", "merge"):  # squash, as GitHub would: one commit on main with the PR's tree
            work = os.path.join(self.tmp, "github")
            subprocess.run(["git", "clone", "-q", self.remote, work], check=True)
            self.git("config", "user.email", "g@g", root=work)
            self.git("config", "user.name", "g", root=work)
            self.git("merge", "-q", "--squash", "origin/sl-1-a", root=work)
            subprocess.run(["git", "commit", "-qF", "-"], cwd=work, input=args[args.index("--subject") + 1] + "\n\n"
                           + args[args.index("--body") + 1], text=True, check=True)
            self.git("push", "-q", "origin", "main", root=work)
            shutil.rmtree(work)
            return ok()
        return ok("[]")

    def run_tool(self, *args):
        out = io.StringIO()
        with unittest.mock.patch.object(spry, "gh_run", self.gh), contextlib.redirect_stdout(out):
            code = spry.main(["--root", self.root, *args])
        return code, out.getvalue()

    def test_ready_refreshes_the_body_and_names_the_command_that_merges(self):
        code, out = self.run_tool("merge-ready", "1")
        self.assertEqual(code, 0, out)
        self.assertIn("✓ checks: 1 check green", out)
        self.assertIn("✓ PR body refreshed from the slice file", out)
        self.assertIn("SL-1", self.body)
        self.assertIn("ready — ask: squash PR #1 `SL-1 Slice SL-1` into main with `Slice: SL-1`", out)
        self.assertTrue(out.rstrip().endswith("then: spry.py merge-finish 1"), out)
        code, out = self.run_tool("merge-ready")
        self.assertIn("✓ PR body is the slice file's", out, "the current branch's slice, with no target")

    def test_red_and_pending_checks_block(self):
        self.checks[0]["bucket"] = "fail"
        code, out = self.run_tool("merge-ready", "SL-1")
        self.assertEqual(code, 1)
        self.assertIn("✗ checks red: test — never merge a red PR", out)
        self.checks[0]["bucket"] = "pending"
        self.assertIn("✗ checks pending: test — `spry.py merge-ready 1 --wait`", self.run_tool("merge-ready", "1")[1])

    def test_wait_waits_for_pending_checks_on_this_machine(self):
        """CH-76: one call waits for CI, rather than a look by the agent each time."""
        self.checks[0]["bucket"] = "pending"
        looks = []

        def nap(_seconds):
            looks.append(1)
            if len(looks) == 2:
                self.checks[0]["bucket"] = "pass"
        with unittest.mock.patch.object(spry.time, "sleep", nap):
            code, out = self.run_tool("merge-ready", "1", "--wait", "5")
        self.assertEqual((code, len(looks)), (0, 2), out)
        self.assertIn("… checks pending: test — waiting up to 5 min", out)
        self.assertIn("✓ checks: 1 check green", out)
        self.checks[0]["bucket"] = "pending"
        with unittest.mock.patch.object(spry.time, "sleep", lambda _s: None), \
                unittest.mock.patch.object(spry.time, "monotonic", side_effect=[0, 0, 400, 400]):
            code, out = self.run_tool("merge-ready", "1", "--wait", "5")
        self.assertEqual(code, 1, "still pending when the wait runs out: blocked, as without --wait")
        self.assertIn("✗ checks pending: test", out)

    def test_a_session_too_big_is_told_to_clear_before_the_ask(self):
        """CH-77: the context check before a merge's ask."""
        with unittest.mock.patch.object(spry, "session_context", lambda _p: 400_000):
            out = self.run_tool("merge-ready", "1")[1]
        self.assertIn("… this session carries 400k tokens of context", out)
        self.assertIn("then `/spry:merge 1`", out)
        self.assertNotIn("this session carries", self.run_tool("merge-ready", "1")[1])

    def test_brief_gives_the_slice_and_its_changes_in_one_call(self):
        """CH-76: the work order, the criteria in words and the files changed; --diff adds the diff."""
        with open(os.path.join(self.root, "lend.py"), "w") as handle:
            handle.write("def lend():\n    return 1\n")
        self.git("add", "lend.py")
        self.git("commit", "-qm", "lend")
        code, out = self.run_tool("brief", "SL-1")
        self.assertEqual(code, 0)
        self.assertIn("**SL-1", out)
        self.assertIn("## Work order", out)
        self.assertIn("## Changed since origin/main", out)
        self.assertIn("lend.py", out)
        self.assertNotIn("## Diff", out)
        self.assertIn("+    return 1", self.run_tool("brief", "SL-1", "--diff")[1])

    def test_a_close_brief_says_whether_a_rebase_is_due(self):
        """CH-82: the close's first facts come with the brief — the tree, and how far the main branch moved."""
        code, out = self.run_tool("brief", "SL-1", "--as", "slice-close")
        self.assertEqual(code, 0, out)
        self.assertIn("## Before the close\n\n- working tree: committed\n- `origin/main` has not moved: no rebase", out)
        self.assertIn("## Close — `/spry:slice-close [SL-n]`", out)
        other = os.path.join(self.tmp, "other")
        subprocess.run(["git", "clone", "-q", self.remote, other], check=True)
        for key, value in (("user.email", "t@t"), ("user.name", "t")):
            self.git("config", key, value, root=other)
        self.git("commit", "-q", "--allow-empty", "-m", "moved", root=other)
        self.git("push", "-q", "origin", "main", root=other)
        with open(os.path.join(self.root, "new.py"), "w") as handle:
            handle.write("x = 1\n")
        out = self.run_tool("brief", "SL-1", "--as", "slice-close")[1]
        self.assertIn("- working tree: 1 uncommitted file — commit first", out)
        self.assertIn("- `origin/main` has 1 commit this branch lacks — `git rebase origin/main`", out, "it fetched")
        self.assertNotIn("## Before the close", self.run_tool("brief", "SL-1")[1])

    def test_ci_that_never_started_is_stood_in_for_by_the_gate(self):
        self.checks[0]["bucket"], self.jobs[0]["steps"] = "fail", []
        with unittest.mock.patch.object(spry, "gate", lambda *a, **k: 0) as _:
            code, out = self.run_tool("merge-ready", "1")
        self.assertEqual(code, 0, out)
        self.assertIn("! CI did not run (CI could not start — test ran no step); gate green locally", out)
        self.assertIn('then: spry.py merge-finish 1 --ci-local "CI could not start — test ran no step"', out)
        with unittest.mock.patch.object(spry, "gate", lambda *a, **k: 1):
            self.assertIn("the gate on the PR's head is red", self.run_tool("merge-ready", "1")[1])

    def test_another_branch_a_team_without_approval_and_a_moved_base_block(self):
        self.git("switch", "-q", "main")
        self.assertIn("✗ this tree is on `main` — `git checkout sl-1-a`", self.run_tool("merge-ready", "1")[1])
        self.git("switch", "-q", "sl-1-a")
        work = os.path.join(self.tmp, "other")
        subprocess.run(["git", "clone", "-q", self.remote, work], check=True)
        with open(os.path.join(work, S, "SL-1-a.md"), "a") as handle:
            handle.write("\nmoved\n")
        self.git("-c", "user.name=o", "-c", "user.email=o@o", "commit", "-qam", "touch", root=work)
        self.git("push", "-q", "origin", "main", root=work)
        code, out = self.run_tool("merge-ready", "1")
        self.assertEqual(code, 1)
        self.assertIn(f"✗ main gained 1 commit touching this PR's files ({S}/SL-1-a.md) — the checks are against "
                      "an old base: rebase, push, and run this again", out)

    def team(self, approval=None):
        path = os.path.join(self.root, "spry", "spry.config.json")
        with open(path) as handle:
            conf = json.load(handle)
        conf["team"] = {"members": [{"name": "A", "github": "lead"}, {"name": "B", "github": "dev"}]}
        if approval is not None:
            conf["team"]["approval"] = approval
        with open(path, "w") as handle:
            json.dump(conf, handle)

    def test_a_team_pr_merges_approved_unless_its_author_is_exempt_or_a_missing_approval_only_warns(self):
        self.author = "dev"
        self.team()
        code, out = self.run_tool("merge-ready", "1")
        self.assertEqual(code, 1, out)
        self.assertIn("✗ review decision is none — a team PR merges approved", out)
        self.decision = "APPROVED"
        self.assertIn("✓ approved", self.run_tool("merge-ready", "1")[1])
        self.decision = "REVIEW_REQUIRED"
        self.team({"exempt": ["@Lead"]})
        self.assertIn("✗ review decision is review required — a team PR merges approved",
                      self.run_tool("merge-ready", "1")[1], "only the exempt login's own PRs")
        self.author = "lead"
        code, out = self.run_tool("merge-ready", "1")
        self.assertEqual(code, 0, out)
        self.assertIn("✓ review decision is review required — @lead merges without an approval", out)
        self.author = "dev"
        self.team({"missing": "warn"})
        code, out = self.run_tool("merge-ready", "1")
        self.assertEqual(code, 0, out)
        self.assertIn("! review decision is review required — the person merges without an approval", out)
        self.assertIn("the person accepting the 1 `!` above", out)
        self.decision = "CHANGES_REQUESTED"
        self.team({"missing": "warn", "exempt": ["dev"]})
        self.assertIn("✗ review decision is changes requested — answer the review first",
                      self.run_tool("merge-ready", "1")[1], "neither setting waives an objection")

    def test_a_malformed_team_approval_is_a_check_error(self):
        self.team({"missing": "maybe"})
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            spry.main(["--root", self.root, "check"])
        self.assertIn("`team.approval` is", out.getvalue())

    def test_finish_squashes_comes_home_writes_the_tables_and_names_what_is_unblocked(self):
        head = self.git("rev-parse", "HEAD")
        code, out = self.run_tool("merge-finish", "1")
        self.assertEqual(code, 0, out)
        self.assertIn("✓ merged PR #1 — SL-1 Slice SL-1 (#1)", out)
        merge = [c for c in self.calls if c[:2] == ("pr", "merge")][0]
        self.assertIn("--match-head-commit", merge)
        self.assertIn(head, merge)
        self.assertIn("Slice: SL-1", merge[merge.index("--body") + 1])
        self.assertEqual(self.git("branch", "--show-current"), "main")
        self.assertEqual(self.git("branch", "--list", "sl-1-a"), "", "the local branch is deleted")
        self.assertIn("✓ main gained no code the PR's checks did not see — nothing to run", out)
        self.assertIn("✓ progress tables written and pushed", out)
        self.assertEqual(self.git("log", "-1", "--format=%s", "main", root=self.remote),
                         "chore(spry): refresh progress after #1 [skip ci]")
        self.assertIn("→ unblocked: SL-2 Slice SL-2 — the next planned slice of S-1", out)

    def test_finish_refuses_what_ready_would(self):
        self.checks[0]["bucket"] = "fail"
        code, out = self.run_tool("merge-finish", "1")
        self.assertEqual(code, 1)
        self.assertIn("never merge a red or pending PR", out)
        self.checks[0]["bucket"] = "pass"
        self.assertIn("✗ --ci-local, but CI ran", self.run_tool("merge-finish", "1", "--ci-local", "x")[1])
        self.assertFalse([c for c in self.calls if c[:2] == ("pr", "merge")], "nothing merged")


class Publish(unittest.TestCase):
    """`publish` (CH-71): a slice's commits, pushes and pull request at open, before the review and at close."""

    def setUp(self):
        self.tmp = os.path.realpath(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.remote = os.path.join(self.tmp, "remote.git")
        subprocess.run(["git", "init", "-q", "--bare", "-b", "main", self.remote], check=True)
        files = base()
        files[f"{S}/SL-2-b.md"] = slice_("SL-2", state="planned").replace("pr: 1\n", "").replace("owner: A\n", "")
        seed = Tree(files).root
        self.addCleanup(shutil.rmtree, seed, True)
        git_repo(seed)("push", "-q", self.remote, "main")
        self.root = os.path.join(self.tmp, "clone")
        subprocess.run(["git", "clone", "-q", self.remote, self.root], check=True)
        for key, value in (("user.email", "t@t"), ("user.name", "Tess")):
            self.git("config", key, value)
        self.git("switch", "-qc", "sl-2-b")
        self.doc = os.path.join(self.root, S, "SL-2-b.md")
        self.calls, self.inputs = [], []

    def git(self, *args):
        return subprocess.run(["git", *args], cwd=self.root, check=True, capture_output=True, text=True).stdout.strip()

    def gh(self, _project, *args, input=None):
        self.calls.append(args)
        self.inputs.append(input)
        out = "https://github.com/o/r/pull/12\n" if args[:2] == ("pr", "create") else ""
        return subprocess.CompletedProcess(args, 0, out, "")

    def run_tool(self, *args, gate=0):
        out = io.StringIO()
        with unittest.mock.patch.object(spry, "gh_run", self.gh), \
                unittest.mock.patch.object(spry, "gate", lambda *a, **k: gate), contextlib.redirect_stdout(out):
            code = spry.main(["--root", self.root, *args])
        return code, out.getvalue()

    def fm(self):
        return spry.Project(self.root).items["SL-2"].fm

    def test_open_commits_the_work_order_pushes_and_opens_a_draft(self):
        code, out = self.run_tool("publish", "SL-2", "open")
        self.assertEqual(code, 0, out)
        fm = self.fm()
        self.assertEqual((fm["state"], fm["branch"], fm["owner"], str(fm["pr"])), ("open", "sl-2-b", "Tess", "12"))
        self.assertEqual(self.git("log", "--format=%s", "main..HEAD").splitlines(),
                         ["docs(slice): SL-2 PR #12", "docs(slice): SL-2 work order"])
        self.assertEqual(self.git("rev-parse", "HEAD"), self.git("rev-parse", "origin/sl-2-b"), "pushed")
        create = [c for c in self.calls if c[:2] == ("pr", "create")][0]
        self.assertIn("--draft", create)
        self.assertEqual(create[create.index("--title") + 1], "SL-2 Slice SL-2")
        self.assertIn("✓ draft PR #12 opened", out)
        self.assertEqual(self.git("status", "--porcelain", "--", ".", ":!.spry"), "")

    def test_open_refuses_code_and_a_work_order_check_refuses(self):
        with open(os.path.join(self.root, "src", "a.test.ts"), "a") as handle:
            handle.write("// more\n")
        with self.assertRaises(SystemExit) as caught:
            self.run_tool("publish", "SL-2", "open")
        self.assertIn("outside spry/ not committed (src/a.test.ts)", str(caught.exception))
        self.git("checkout", "--", "src")
        with open(self.doc) as handle:
            text = handle.read()
        with open(self.doc, "w") as handle:
            handle.write(text.split("### Conflict check")[0])
        code, out = self.run_tool("publish", "SL-2", "open")
        self.assertEqual(code, 1)
        self.assertIn("nothing committed; finish the work order", out)
        self.assertEqual(self.fm()["state"], "planned", "the file is put back")
        self.assertEqual(self.git("log", "--format=%s", "main..HEAD"), "")
        self.assertFalse(self.calls)

    def test_review_then_ready(self):
        self.assertEqual(self.run_tool("publish", "SL-2", "open")[0], 0)
        with open(self.doc, "a") as handle:
            handle.write("\n## Close summary\n\n### What changed\n\n- Nothing.\n")
        code, out = self.run_tool("publish", "SL-2", "review")
        self.assertEqual(code, 0, out)
        self.assertEqual(self.git("log", "-1", "--format=%s"), "docs(slice): SL-2 close notes")
        self.assertIn(("pr", "edit", "12", "--body-file", "-"), self.calls)
        self.assertIn("What changed", self.inputs[-1])
        code, out = self.run_tool("publish", "SL-2", "ready", gate=1)
        self.assertEqual(code, 1)
        self.assertIn("the gate is red — SL-2 left open", out)
        self.assertEqual(self.fm()["state"], "open")
        code, out = self.run_tool("publish", "SL-2", "ready")
        self.assertEqual(code, 0, out)
        fm = self.fm()
        self.assertEqual((fm["state"], fm["closed"]), ("closed", datetime.date.today().isoformat()))
        self.assertEqual(self.git("log", "-1", "--format=%B").strip(), "docs(slice): SL-2 close summary\n\nSlice: SL-2")
        self.assertEqual(self.calls[-1], ("pr", "ready", "12"))
        self.assertEqual(self.git("rev-parse", "HEAD"), self.git("rev-parse", "origin/sl-2-b"))


class Proc(Base):
    """`proc` (CH-72): only the sections of a process file a skill needs."""

    TEXT = ("---\ntitle: P\naudience: 8\n---\n# P\n\nOpening rule.\n\n## Open — `/spry:x`\n\nopen body\n\n"
            "### Sub\n\nsub body\n\n## Close\n\nclose body\n")

    def test_the_opening_and_each_section_named_with_what_is_under_it(self):
        t = self.tree(**{"spry__process__p.md": self.TEXT})
        out = spry.proc(t.project(), "p", ["open"])
        self.assertEqual(out, "# P\n\nOpening rule.\n\n## Open — `/spry:x`\n\nopen body\n\n### Sub\n\nsub body\n")
        self.assertIn("close body", spry.proc(t.project(), "p.md", ["Clo"]), "a heading's first words match")
        self.assertEqual(spry.proc(t.project(), "p", [], listing=True), "Open · 8 lines\n  Sub · 4 lines\nClose · 4 lines\n")
        with self.assertRaises(SystemExit) as caught:
            spry.proc(t.project(), "p", ["Merge"])
        self.assertIn("its sections: Open, Close", str(caught.exception))

    def test_every_skill_names_sections_that_exist(self):
        import shlex
        plugin = os.path.join(REPO, "plugins", "spry")
        t = self.tree()
        shutil.copytree(os.path.join(plugin, "process"), os.path.join(t.root, "spry", "process"))
        seen = 0
        for name in os.listdir(os.path.join(plugin, "skills")):
            with open(os.path.join(plugin, "skills", name, "SKILL.md")) as handle:
                text = " ".join(handle.read().split())
            for call in re.findall(r"`python3 spry/tool/spry\.py proc ([^`]+)`", text):
                words = shlex.split(call.split(";")[0])
                if words[0] == "--for":
                    continue   # counted below
                spry.proc(t.project(), words[0], words[1:])
                seen += 1
            for extra in re.findall(r"adding `([^`]+)`", text):
                file = re.search(r"spry\.py proc (\w+)", text).group(1)
                spry.proc(t.project(), file, shlex.split(extra))
            for skill in re.findall(r"spry\.py (?:proc --for|brief SL-<n> --as) ([\w-]+)", text):
                self.assertEqual(skill, name, "a skill asks for its own reading")
                spry.proc_for(t.project(), skill)
                seen += 1
        self.assertGreaterEqual(seen, 9)

    def test_proc_for_prints_all_a_skill_reads_before_it_starts(self):
        """CH-82: one call, not one per file. CH-88: steps are in the sections themselves; a project
        whose `slicing.md` still has *Steps* apart gets it too."""
        t = self.tree()
        out = spry.proc_for(t.project(), "slice-close")
        for part in ("## Close — `/spry:slice-close [SL-n]`", "## When to stop and ask", "## While building",
                     "# Writing rules", "# Chat rules"):
            self.assertIn(part, out)
        self.assertNotIn("\n## Steps —", out)
        self.assertNotIn("\n## Plan —", out, "only the sections the skill runs")
        self.assertIn("`spry.py step SL-<n> --commit`", spry.proc_for(t.project(), "slice-build"))
        old = self.tree(**{"spry__process__slicing.md": "# Slicing\n\n## When to stop and ask\n\na\n\n## Build — x\n\nb\n\n"
                                                         "## While building\n\nc\n\n## Steps — `slices.mode: steps`\n\nd\n"})
        self.assertIn("## Steps — `slices.mode: steps`", spry.proc_for(old.project(), "slice-build"))
        p = t.project()
        self.assertIn("# Conflict check", spry.proc_for(p, "slice-plan"))
        self.assertIn("## Merge", spry.proc_for(p, "merge"))
        with self.assertRaises(SystemExit) as caught:
            spry.proc_for(p, "status")
        self.assertIn("proc --for takes: slice-open, slice-plan, slice-build, slice-close, merge, review-slice", str(caught.exception))
        self.assertIn("### b. Plan", spry.proc_for(p, "review-plan"))
        self.assertNotIn("### a. Slice", spry.proc_for(p, "review-plan"))
        self.assertIn("### c. Other", spry.proc_for(p, "review-other"))

    def test_a_brief_for_a_skill_ends_with_what_it_reads_first(self):
        """CH-82: `brief --as` carries the parent, the feature, `related` and the procedure, so a plan
        session asks for none of them one call at a time; without `--as` the brief is as it was."""
        t = self.tree(**{f"{S}__SL-2-b.md": slice_("SL-2", state="planned")})
        p = t.project()
        out = spry.brief(p, "SL-2", skill="slice-plan")
        self.assertIn(f"## Story — `{S}/README.md`", out)
        self.assertIn("| AC-1 | x | y | z |", out, "the parent, whole")
        self.assertNotIn("<!-- spry:proof -->", out, "generated blocks left out")
        self.assertIn(f"## Feature — `{F}/README.md`", out)
        self.assertIn("## Related — the conflict check starts here", out)
        self.assertIn("### Siblings", out)
        self.assertIn("## Procedure\n\n# Slicing", out)
        self.assertIn("## Plan — `/spry:slice-plan [SL-n]`", out)
        build = spry.brief(p, "SL-1", skill="slice-build")
        self.assertIn("## Build — `/spry:slice-build [SL-n]`", build)
        self.assertNotIn("## Story —", build, "the planning is not read again at the build")
        plain = spry.brief(p, "SL-1")
        self.assertNotIn("## Procedure", plain)
        review = spry.brief(p, "SL-1", diff=True, skill="slice-close")
        self.assertIn("## Procedure\n\n# Reviewing", review, "CH-85: a reviewer's checks come with its diff")
        self.assertIn("### a. Slice", review)
        self.assertNotIn("## 5. Post", review, "the rest is for the session that runs the review")
        self.assertNotIn("## Close —", review)


if __name__ == "__main__":
    unittest.main()
