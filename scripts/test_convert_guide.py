"""Check document fidelity and local links in the generated site."""

from html.parser import HTMLParser
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import unittest
from urllib.parse import unquote, urlsplit


SPEC = importlib.util.spec_from_file_location("convert_guide", Path(__file__).with_name("convert-guide.py"))
CONVERTER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CONVERTER)


class Page(HTMLParser):
    def __init__(self, markup):
        super().__init__()
        self.markup = markup
        self.parts = []
        self.targets = []
        self.links = []
        self.images = []
        self.tables = 0
        self.downloads = []
        self.feed(markup)

    def handle_data(self, data):
        self.parts.append(data)

    def handle_starttag(self, tag, attrs):
        if tag in {"p", "li", "th", "td", "tr", "br", "h1", "h2", "h3", "h4", "h5", "h6"}:
            self.parts.append(" ")
        attrs = dict(attrs)
        if "id" in attrs:
            self.targets.append(attrs["id"])
        if tag == "a" and "href" in attrs:
            self.links.append(attrs["href"])
            if attrs["href"].startswith("assets/worksheets/"):
                self.downloads.append(attrs["href"])
        if tag == "img":
            self.images.append(attrs["src"])
        if tag == "table":
            self.tables += 1

    def handle_endtag(self, tag):
        if tag in {"p", "li", "th", "td", "tr", "h1", "h2", "h3", "h4", "h5", "h6"}:
            self.parts.append(" ")

    def words(self):
        return re.sub(r"\s+", " ", "".join(self.parts)).strip()


def render(content, source):
    return subprocess.run(
        ["pandoc", "--from=" + source, "--to=html"],
        input=content,
        capture_output=True,
        encoding="utf-8",
        check=True,
    ).stdout


class GuideTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.files, cls.media = CONVERTER.convert()
        cls.pages = {
            name: Page(render(content.split("---\n", 2)[2], "gfm"))
            for name, content in cls.files.items()
            if name.endswith(".md")
        }
        cls.source = json.loads(subprocess.run(
            ["pandoc", str(CONVERTER.SOURCE), "--to=json"],
            capture_output=True,
            encoding="utf-8",
            check=True,
        ).stdout)

    def test_page_structure(self):
        self.assertEqual(
            set(self.files),
            {"index.md", "resources.md", "_data/navigation.json", *(f"chapter-{n:02d}.md" for n in range(1, 7))},
        )
        for name, content in self.files.items():
            if not name.endswith(".md"):
                continue
            with self.subTest(page=name):
                self.assertEqual(len(re.findall(r"^# ", content, re.M)), 1)
                self.assertNotIn("<!-- chapter-contents -->", content)
                self.assertNotRegex(content, r"^#{1,6} !\[")
                self.assertNotRegex(content, r"</?[a-zA-Z][a-zA-Z0-9]*(?:\s[^>]*|/?)>")
                self.assertNotRegex(content, r"\]\([^)]*\.html(?:#|\))")

    def test_home_welcomes_readers_before_author_note(self):
        home = self.files["index.md"]
        self.assertLess(home.index("## Welcome"), home.index("## How to use this guide"))
        self.assertLess(home.index("## Contents"), home.index("Author"))
        contents_start = next(
            i for i, block in enumerate(self.source["blocks"])
            if block["t"] == "Header" and CONVERTER.text(block["c"][2]) == "Table of Contents"
        )
        preface = CONVERTER.normalize_markdown([
            block for block in self.source["blocks"][:contents_start]
            if CONVERTER.meaningful(block)
        ])
        self.assertTrue(home.rstrip().endswith(CONVERTER.pandoc({**self.source, "blocks": preface})))

    @unittest.skipUnless(os.environ.get("IQP_SITE_BUILD"), "Set IQP_SITE_BUILD to a Jekyll build directory.")
    def test_jekyll_build_matches_markdown_links_and_anchors(self):
        destination = Path(os.environ["IQP_SITE_BUILD"])
        search_index = json.loads((destination / "search.json").read_text(encoding="utf-8"))
        self.assertEqual(len(search_index), len(self.pages))
        self.assertEqual({page["url"] for page in search_index}, {
            "/iqp/" if name == "index.md" else "/iqp/" + name.removesuffix(".md") + ".html"
            for name in self.pages
        })
        for entry in search_index:
            self.assertTrue(entry["title"])
            self.assertTrue(entry["text"])
            self.assertNotIn("<h1", entry["text"])
        built_pages = {
            name.removesuffix(".md") + ".html": Page(
                (destination / (name.removesuffix(".md") + ".html")).read_text(encoding="utf-8")
            )
            for name in self.pages
        }
        for name, markdown in self.pages.items():
            site_name = name.removesuffix(".md") + ".html"
            built = built_pages[site_name]
            with self.subTest(page=name):
                self.assertEqual(len(built.targets), len(set(built.targets)))
                for anchor in markdown.targets:
                    self.assertIn(anchor, built.targets)
                for href in built.links:
                    url = urlsplit(href)
                    if url.scheme or url.netloc:
                        continue
                    self.assertFalse(url.path.endswith(".md"), href)
                    local = unquote(url.path).removeprefix("/iqp/")
                    if not local:
                        local = "index.html" if url.path else site_name
                    if local.endswith(".html"):
                        target = built_pages[local]
                        if url.fragment:
                            self.assertIn(unquote(url.fragment), target.targets, href)
                    else:
                        self.assertTrue((destination / local).is_file(), href)
                for image in built.images:
                    self.assertTrue((destination / unquote(image).removeprefix("/iqp/")).is_file(), image)
                self.assertEqual(markdown.tables, built.tables)
                self.assertEqual(len(markdown.images), len(built.images))
                for href in markdown.links:
                    url = urlsplit(href)
                    if url.path.endswith(".md") and not url.scheme and not url.netloc:
                        expected = "/iqp/" + url.path.removesuffix(".md") + ".html"
                        if url.path == "index.md":
                            expected = "/iqp/"
                        if url.fragment:
                            expected += "#" + url.fragment
                        self.assertIn(expected, built.links)

    def test_local_links_and_images(self):
        for name, page in self.pages.items():
            with self.subTest(page=name):
                self.assertEqual(len(page.targets), len(set(page.targets)))
                for href in page.links:
                    url = urlsplit(href)
                    if url.scheme or url.netloc:
                        continue
                    if url.path.startswith("assets/"):
                        self.assertTrue((CONVERTER.OUTPUT / unquote(url.path)).is_file(), href)
                        continue
                    target = self.pages[url.path or name]
                    if url.fragment:
                        self.assertIn(unquote(url.fragment), target.targets)
                for image in page.images:
                    self.assertIn(image, self.media)

    def test_sidebar_covers_chapters_and_sections(self):
        navigation = json.loads(self.files["_data/navigation.json"])
        self.assertEqual(len(navigation), 7)
        for chapter in navigation:
            page = self.pages[chapter["url"].removeprefix("/").replace(".html", ".md")]
            self.assertTrue(chapter["sections"])
            for section in chapter["sections"]:
                self.assertIn(section["anchor"], page.targets)
                self.assertIn(section["title"], page.words())
        layout = (CONVERTER.OUTPUT / "_layouts" / "default.html").read_text(encoding="utf-8")
        self.assertIn("site.data.navigation", layout)
        self.assertIn("chapter.url | relative_url", layout)
        self.assertIn('aria-current="page"', layout)
        self.assertIn('href="#main-content"', layout)

    def test_worksheet_downloads_follow_matching_tables(self):
        downloads = []
        expected_chapters = {"chapter-02.md": 5, "chapter-03.md": 2}
        for name, page in self.pages.items():
            self.assertEqual(len(page.downloads), expected_chapters.get(name, 0))
            downloads.extend(unquote(url).removeprefix("assets/worksheets/") for url in page.downloads)
            matches = re.findall(
                r'</table>\s*<p><a\s+href="([^"]+)">Download\s+worksheet:',
                page.markup,
            )
            self.assertEqual(matches, page.downloads)
        expected = [
            CONVERTER.WORKSHEETS[CONVERTER.text(block["c"][3])][0]
            for block in self.source["blocks"]
            if block["t"] == "Table" and CONVERTER.text(block["c"][3]) in CONVERTER.WORKSHEETS
        ]
        self.assertEqual(downloads, expected)
        self.assertEqual(set(downloads), {
            path.name for path in (CONVERTER.OUTPUT / "assets" / "worksheets").glob("*.docx")
        })

    def test_document_content_is_preserved(self):
        blocks = self.source["blocks"]
        starts = [
            i for i, block in enumerate(blocks)
            if block["t"] == "Header" and (
                CONVERTER.CHAPTER.fullmatch(CONVERTER.text(block["c"][2]).strip())
                or CONVERTER.text(block["c"][2]).strip() == "Resources"
            )
        ]
        for index, start in enumerate(starts):
            end = starts[index + 1] if index + 1 < len(starts) else len(blocks)
            name = f"chapter-{index + 1:02d}.md" if index < 6 else "resources.md"
            original = Page(render(json.dumps({**self.source, "blocks": blocks[start:end]}), "json"))
            content = self.files[name].split("---\n", 2)[2]
            content = content.removeprefix("\n[Contents](index.md)\n\n")
            content = content.rsplit("\n\n---\n\n", 1)[0]
            content = re.sub(r"\*\*On this page\*\*\n\n(?:- .+\n)+", "", content)
            content = re.sub(r"^\[Download worksheet:.*$", "", content, flags=re.M)
            converted = Page(render(content, "gfm"))
            with self.subTest(page=name):
                expected = original.words()
                for old, new in (
                    ("As discussed in Part II", "As discussed in Chapter 2"),
                    (
                        "Data Collection Tools and Supporting Materials: Section 5.4",
                        "Data Collection Tools and Supporting Materials: Section 2.3",
                    ),
                    (
                        "Appendices and Supplemental Materials: Section 5.4",
                        "Appendices and Supplemental Materials: Section 4.3",
                    ),
                ):
                    expected = expected.replace(old, new)
                self.assertEqual(expected, converted.words())
                self.assertEqual(original.tables, converted.tables)
                self.assertEqual(
                    ["assets/" + image for image in original.images], converted.images
                )

    def test_explicit_cross_references_are_linked(self):
        chapter2 = self.files["chapter-02.md"]
        chapter3 = self.files["chapter-03.md"]
        chapter4 = self.files["chapter-04.md"]
        self.assertIn(
            "[5.2 Figures, Tables, and Data Visualization](chapter-05.md#52-figures-tables-and-data-visualization)",
            chapter3,
        )
        for label, destination in (
            ("Section 5.1", "chapter-05.md#51-designing-for-your-reader"),
            ("Section 5.2", "chapter-05.md#52-figures-tables-and-data-visualization"),
            ("Section 5.3", "chapter-05.md#53-formatting-and-document-mechanics"),
            ("Section 5.4", "chapter-05.md#54-citations-and-references"),
            ("Appendix A", "resources.md#appendix-a-cover-page-examples"),
            ("B", "resources.md#appendix-b-required-wpi-title-page-for-final-report"),
            ("Appendix D", "resources.md#appendix-d-example-meet-the-team-pages"),
            ("Authorship Statement", "#authorship-statement"),
            ("earlier in this guide", "chapter-01.md#13-writing-as-a-team"),
        ):
            self.assertIn(f"[{label}]({destination})", chapter4)
        self.assertIn(
            "[section 4.2](chapter-04.md#42-completing-your-id2050-research-proposal)",
            self.files["resources.md"],
        )
        self.assertIn(
            "[Data Collection Tools and Supporting Materials: Section 2.3](#data-collection-tools-and-supporting-materials)",
            chapter2,
        )
        self.assertIn(
            "[Appendices and Supplemental Materials: Section 4.3](chapter-04.md#appendices-and-supplemental-materials)",
            chapter2,
        )
        self.assertIn("*See Appendix A for our interview questions.*", chapter2)
        self.assertIn("- Appendix A: Interview Protocol", chapter4)
        self.assertIn("- Appendix B: Survey Instrument", chapter4)
        for name, content in self.files.items():
            if name.endswith(".md"):
                self.assertNotRegex(content, r"(?<!\[)[Ss]ection 5\.[1-4](?!\d|\])")

    def test_cross_reference_linking_preserves_existing_links_and_formatting(self):
        existing = {
            "t": "Link",
            "c": [["", [], []], [{"t": "Str", "c": "Section 5.4"}], ["https://example.com", ""]],
        }
        inlines = [
            existing,
            {"t": "Space"},
            {"t": "Strong", "c": [
                {"t": "Str", "c": "Section"}, {"t": "Space"}, {"t": "Str", "c": "5.4"},
            ]},
        ]
        result = CONVERTER.link_inlines(inlines, {"Section 5.4": ("chapter-05.html#citations-and-references", "Section 5.4")})
        self.assertEqual(result[0], existing)
        self.assertEqual(result[2]["t"], "Strong")
        self.assertEqual(result[2]["c"][0]["t"], "Link")
        self.assertEqual(result[2]["c"][0]["c"][2][0], "chapter-05.html#citations-and-references")

    def test_generated_files_are_current(self):
        for name, content in self.files.items():
            self.assertEqual((CONVERTER.OUTPUT / name).read_text(encoding="utf-8"), content)
        for name, content in self.media.items():
            self.assertEqual((CONVERTER.OUTPUT / name).read_bytes(), content)


if __name__ == "__main__":
    unittest.main()
