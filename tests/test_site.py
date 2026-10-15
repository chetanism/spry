"""Checks for the docs site in site/: every page is in the navigation, every local link and
anchor resolves, and every page has the shell the script needs. Standard library only."""

import re
import unittest
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse

SITE = Path(__file__).resolve().parent.parent / "site"
NAV_JS = SITE / "assets" / "site.js"


def slug(text):
    # Same as slug() in site/assets/site.js — anchors are made from heading text in the browser.
    s = re.sub(r"[^\w\s-]", "", text.lower(), flags=re.ASCII).strip()
    s = re.sub(r"[\s_]+", "-", s)
    return re.sub(r"-+", "-", s)


class Page(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.links, self.ids, self.heads = [], set(), []
        self.title, self.scripts, self.in_title = "", [], False
        self.main = self.article = self.h1 = 0
        self._head = None

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if "id" in a:
            self.ids.add(a["id"])
        for key in ("href", "src"):
            if tag != "base" and key in a and a[key] is not None:
                self.links.append(a[key])
        if tag == "title":
            self.in_title = True
        elif tag == "script" and "src" in a:
            self.scripts.append(a["src"])
        elif tag == "main":
            self.main += 1
        elif tag == "article":
            self.article += 1
        elif tag == "h1":
            self.h1 += 1
        elif tag in ("h2", "h3"):
            self._head = [a.get("id"), ""]

    def handle_endtag(self, tag):
        if tag == "title":
            self.in_title = False
        elif tag in ("h2", "h3") and self._head is not None:
            self.heads.append(self._head)
            self._head = None

    def handle_data(self, data):
        if self.in_title:
            self.title += data
        if self._head is not None:
            self._head[1] += data

    def anchors(self):
        ids, seen = set(self.ids), set()
        for given, text in self.heads:
            if given:
                seen.add(given)
                continue
            base = slug(text)
            new, n = base, 2
            while new in seen:
                new, n = f"{base}-{n}", n + 1
            seen.add(new)
            ids.add(new)
        return ids


def parse(path):
    p = Page()
    p.feed(path.read_text(encoding="utf-8"))
    return p


def nav_paths():
    return re.findall(r'\[\s*"[^"]+",\s*"([^"]+\.html)"\s*\]', NAV_JS.read_text(encoding="utf-8"))


class SiteTest(unittest.TestCase):
    def test_nav_and_pages_match(self):
        listed = nav_paths()
        self.assertEqual(len(listed), len(set(listed)), "a page is listed twice in NAV")
        pages = {p.relative_to(SITE).as_posix() for p in SITE.rglob("*.html")} - {"404.html"}
        self.assertEqual(sorted(set(listed) - pages), [], "NAV lists pages that do not exist")
        self.assertEqual(sorted(pages - set(listed)), [], "pages missing from NAV in site.js")

    def test_every_page_has_the_shell(self):
        for path in SITE.rglob("*.html"):
            with self.subTest(page=path.relative_to(SITE).as_posix()):
                p = parse(path)
                self.assertTrue(p.title.strip(), "no <title>")
                self.assertEqual((p.main, p.article, p.h1), (1, 1, 1), "needs one <main>, <article>, <h1>")
                self.assertTrue(any(s.endswith("assets/site.js") for s in p.scripts), "site.js not loaded")

    def test_local_links_resolve(self):
        cache = {}
        for path in SITE.rglob("*.html"):
            page = parse(path)
            for link in page.links:
                u = urlparse(link)
                if u.scheme or link.startswith("//") or link.startswith("mailto:"):
                    continue
                target = (path.parent / u.path).resolve() if u.path else path
                with self.subTest(page=path.relative_to(SITE).as_posix(), link=link):
                    self.assertTrue(target.is_file(), "broken link")
                    if u.fragment and target.suffix == ".html":
                        if target not in cache:
                            cache[target] = parse(target).anchors()
                        self.assertIn(u.fragment, cache[target], "no such anchor")


if __name__ == "__main__":
    unittest.main()
