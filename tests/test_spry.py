"""Tests for plugins/spry/tool/spry.py.  python3 tests/test_spry.py"""

import contextlib
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

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


def slice_(ident, state="closed", covers="[AC-1]", plan="", check=True):
    head = f"---\nid: {ident}\ntitle: Slice {ident}\nstate: {state}\nowner: A\naudience: 8\ncovers: {covers}\npr: 1\n---\n# {ident}\n\n"
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

    def test_bug_breaks_must_exist(self):
        bug = item("B-1", extra="breaks: [S-1/AC-4]\n", check=False)
        t = self.tree(**{f"{F}/bugs/B-1-x/README.md".replace("/", "__"): bug})
        self.assertProblem(t.problems(), "`breaks` names S-1/AC-4")


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
        path = spry.link_slice(t.project(), "SL-1", {"pr": "#42", "issue": "7", "branch": "sl-1-a"})
        with open(path) as handle:
            head = handle.read().split("\n---\n")[0]
        self.assertIn("pr: 42\n", head + "\n")
        self.assertIn("issue: 7", head)
        self.assertIn("branch: sl-1-a", head)
        self.assertEqual(head.count("pr:"), 1)
        with self.assertRaises(SystemExit):
            spry.link_slice(t.project(), "SL-1", {"pr": "next"})

    def test_covers_under_a_bug_says_what_to_do(self):
        bug = item("B-1").replace("state: ready", "state: ready")
        t = self.tree(**{f"{S}/bugs/B-1-x/README.md".replace("/", "__"): bug,
                         f"{S}/bugs/B-1-x/SL-1-a.md".replace("/", "__"): slice_("SL-1")})
        self.assertProblem(t.problems(), "B-1 is a bug, not a story — leave `covers: []`")



class Coverage(Base):
    PAGE = "---\ntitle: Coverage\naudience: 3\n---\n# Coverage\n\n<!-- spry:coverage -->\n<!-- /spry:coverage -->\n"

    def test_totals_when_everything_is_proven(self):
        out = spry.coverage_block(self.tree().project(), "spry/COVERAGE.md")
        self.assertIn("| Stories | 1 | 1 | 100% |", out)
        self.assertIn("| Acceptance criteria proven | 1 | 1 | 100% |", out)
        self.assertIn("| 1 of 1 | 1 of 1 | 0 |", out)
        self.assertEqual(out.count("_None._"), 2)

    def test_built_but_not_proven_and_cited_only_in_a_comment(self):
        t = self.tree(**{f"{S}/README.md".replace("/", "__"): story("S-1", acs=("AC-1", "AC-2")),
                         "src__b.test.ts": "// S-1/AC-2 covered below\ntest('x', () => {})\n"})
        out = spry.coverage_block(t.project(), os.path.join(t.root, "spry/COVERAGE.md"))
        self.assertIn("| Acceptance criteria proven | 1 | 2 | 50% |", out)
        self.assertIn("| [S-1 Title of S-1](plan/M-1-m/E-1-e/F-1-f/S-1-s/README.md) | AC-2 |", out)
        self.assertIn("| [S-1/AC-2](plan/M-1-m/E-1-e/F-1-f/S-1-s/README.md) Title of S-1 | `src/b.test.ts:1` |", out)

    def test_an_open_slice_is_not_built_and_dropped_work_is_not_defined(self):
        t = self.tree(**{f"{S}/SL-1-a.md".replace("/", "__"): slice_("SL-1", state="open"),
                         "src__a.test.ts": "nothing\n",
                         f"{F}/S-2-x/README.md".replace("/", "__"): story("S-2", state="dropped")})
        out = spry.coverage_block(t.project(), os.path.join(t.root, "spry/COVERAGE.md"))
        self.assertIn("| Stories | 0 | 1 | 0% |", out)
        self.assertIn("### Built, not proven", out)
        self.assertNotIn("| AC-1 |", out)

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

    def test_index_fills_the_page(self):
        t = self.tree(**{"spry__BACKLOG.md": self.PAGE})
        self.assertIn("spry/BACKLOG.md", spry.index(t.project(), dry=False))
        with open(os.path.join(t.root, "spry/BACKLOG.md")) as handle:
            self.assertIn("### Ready to build", handle.read())


class Branch(Base):
    """Generated blocks on a branch: only CI on the main branch writes them."""

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
        self.assertEqual(written, [".spry/view/BACKLOG.md", ".spry/view/COVERAGE.md"])
        with open(os.path.join(self.t.root, ".spry/view/COVERAGE.md")) as handle:
            text = handle.read()
        self.assertIn("by `spry view`. Not committed.", text)
        self.assertIn("(../../spry/plan/M-1-m/README.md)", text)
        with open(os.path.join(self.t.root, "notes.txt"), "w") as handle:
            handle.write("x")
        self.run_git("add", "-A")
        self.run_git("commit", "-qm", "notes")
        self.assertEqual(spry.view(self.t.project(), since="HEAD~1"), [])
        self.assertEqual(len(spry.view(self.t.project(), since="HEAD~1~1~1")), 2)

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
        self.assertEqual(os.path.relpath(ext, t.root), "spry/knowledge/external/open-library/lookups-are-rate-limited.md")
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
        checks = "---\ntitle: c\naudience: 4\n---\n# c\n\n## Scenarios\n\n### AC-1 · fine\n\n### AC-5 · gone\n"
        t = self.tree(**{f"{S}/checks.md".replace("/", "__"): checks})
        problems = t.problems()
        self.assertTrue(any("scenario for AC-5" in p for p in problems), problems)
        self.assertFalse(any("AC-1" in p for p in problems), problems)

    def test_refuses_wrong_parent(self):
        t = self.tree_with_process()
        with self.assertRaises(SystemExit):
            spry.new_item(t.project(), "story", "M-1", "x")
        with self.assertRaises(SystemExit):
            spry.new_item(t.project(), "slice", "F-1", "x")

    def test_slug(self):
        self.assertEqual(spry.slugify("Lend a book — at the Desk!"), "lend-a-book-at-the-desk")
        self.assertLessEqual(len(spry.slugify("word " * 30)), 40)


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
RUNNER = "import runpy, sys\nfor f in sys.argv[1:]:\n    runpy.run_path(f)\n"
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
        before = os.stat(os.path.join(self.root, "src", "loans.py")).st_mtime_ns
        said = []
        results = spry.falsify_run(spry.Project(self.root), self.plan(self.both_guards()), say=said.append, jobs=2)
        self.assertEqual([r for _, r, _ in results], ["caught", "survived"])
        self.assertTrue(any(s.startswith("2 worktrees") for s in said), said)
        self.assertEqual(os.stat(os.path.join(self.root, "src", "loans.py")).st_mtime_ns, before)
        self.assertEqual(len(self.worktrees()), 1, "every worktree removed")

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

    def test_a_row_renamed_in_plain_words_still_counts(self):
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

    def test_gate_stops_at_the_first_failure(self):
        log = self.gate_config("echo f >> LOG && exit 3")
        code, said = self.gate()
        self.assertEqual(code, 1)
        self.assertEqual(self.ran(log), ["f"], "tests never ran after lint failed")
        self.assertIn("✗ lint", " ".join(said))
        code, _ = self.gate()
        self.assertEqual(self.ran(log), ["f", "f"], "a failure is never stamped green")

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
        self.write({"src/loans.py": "broken(\n"})
        code, said = self.gate()
        self.assertEqual(code, 1)
        self.assertFalse(any("quiet retry" in x for x in said), "an assertion or syntax error is not retried")

    def test_gate_refuses_a_placeholder(self):
        self.gate_config("<lint command>")
        with self.assertRaises(SystemExit):
            self.gate()

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


class Issues(Base):
    def test_an_open_slice_needs_an_issue_only_when_the_switch_is_on(self):
        doc = f"{S}/SL-1-a.md".replace("/", "__")
        t = self.tree(**{doc: slice_("SL-1", state="open")})
        self.assertFalse([p for p in t.problems() if "issue" in str(p)])
        on = json.dumps(dict(CONFIG, slices={"issue": True}))
        t = self.tree(**{doc: slice_("SL-1", state="open"), "spry__spry.config.json": on})
        self.assertProblem(t.problems(), "open without an `issue:` number")
        t = self.tree(**{doc: slice_("SL-1", state="open").replace("pr: 1\n", "pr: 1\nissue: 12\n"),
                         "spry__spry.config.json": on})
        self.assertFalse([p for p in t.problems() if "issue" in str(p)])
        t = self.tree(**{doc: slice_("SL-1"), "spry__spry.config.json": on})
        self.assertFalse([p for p in t.problems() if "issue" in str(p)], "a closed slice is history")

    def test_issue_body_is_the_frozen_work_order_and_the_close_summary(self):
        text = slice_("SL-1").replace("pr: 1\n", "pr: 1\nissue: 12\n") + "\n## Close summary\n\n### Summary\n\n- Lent.\n"
        p = self.tree(**{f"{S}/SL-1-a.md".replace("/", "__"): text}).project()
        opened = spry.issue_body(p, "SL-1")
        self.assertIn("never updated", opened.split("\n")[0])
        self.assertIn("## Work order", opened)
        self.assertNotIn("## Close summary", opened)
        closed = spry.issue_body(p, "SL-1", close=True)
        self.assertIn("- Lent.", closed)
        self.assertNotIn("## Work order", closed)
        self.assertTrue(spry.merge_message(p, "SL-1").rstrip().endswith("Closes #12"))
        self.assertIn("· issue #12", spry.pr_body(p, "SL-1").split("\n")[0])


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


if __name__ == "__main__":
    unittest.main()
