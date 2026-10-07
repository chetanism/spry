"""Tests for plugins/spry/tool/spry.py.  python3 tests/test_spry.py"""

import contextlib
import io
import json
import os
import shutil
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

    def test_guide_left_in_ready_but_not_draft(self):
        guided = item("F-1", body="<!-- guide: fill me -->\n- <thing>\n")
        self.assertProblem(self.tree(**{f"{F}/README.md".replace("/", "__"): guided}).problems(), "template guide left")
        draft = item("F-1", state="draft", body="<!-- guide: fill me -->\n- <thing>\n")
        self.assertEqual(self.tree(**{f"{F}/README.md".replace("/", "__"): draft}).problems(), [])

    def test_placeholder(self):
        t = self.tree(**{f"{F}/README.md".replace("/", "__"): item("F-1", body="- Lent to <member>\n")})
        self.assertProblem(t.problems(), "placeholder `<member>`")

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

    def test_status_prints_tree(self):
        out = spry.status(self.tree().project(), None)
        self.assertIn("M-1 Title of M-1", out)
        self.assertIn("slice SL-1", out)


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
