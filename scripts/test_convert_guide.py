"""Check document fidelity and local links in the generated site."""

from html.parser import HTMLParser
import importlib.util
import json
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
            if "download" in attrs:
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
            name.removesuffix(".md") + ".html": Page(render(content, "gfm-gfm_auto_identifiers"))
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
            page = self.pages[chapter["url"].removeprefix("/")]
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
        expected_chapters = {"chapter-02.html": 5, "chapter-03.html": 2}
        for name, page in self.pages.items():
            self.assertEqual(len(page.downloads), expected_chapters.get(name, 0))
            downloads.extend(unquote(url).removeprefix("assets/worksheets/") for url in page.downloads)
            matches = re.findall(
                r'</table>\s*<p class="worksheet-download"><a href="([^"]+)" download>',
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
            content = content.removeprefix("\n[Contents](index.html)\n\n")
            content = content.rsplit("\n\n---\n\n", 1)[0]
            content = re.sub(r"\*\*On this page\*\*\n\n(?:- .+\n)+", "", content)
            content = re.sub(r'<p class="worksheet-download">.*?</p>', "", content)
            converted = Page(render(content, "gfm-gfm_auto_identifiers"))
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
            "[5.2 Figures, Tables, and Data Visualization](chapter-05.html#figures-tables-and-data-visualization)",
            chapter3,
        )
        for label, destination in (
            ("Section 5.1", "chapter-05.html#designing-for-your-reader"),
            ("Section 5.2", "chapter-05.html#figures-tables-and-data-visualization"),
            ("Section 5.3", "chapter-05.html#formatting-and-document-mechanics"),
            ("Section 5.4", "chapter-05.html#citations-and-references"),
            ("Appendix A", "resources.html#appendix-a-cover-page-examples"),
            ("B", "resources.html#appendix-b-required-wpi-title-page-for-final-report"),
            ("Appendix D", "resources.html#appendix-d-example-meet-the-team-pages"),
            ("Authorship Statement", "#authorship-statement"),
            ("earlier in this guide", "chapter-01.html#writing-as-a-team"),
        ):
            self.assertIn(f"[{label}]({destination})", chapter4)
        self.assertIn(
            "[section 4.2](chapter-04.html#completing-your-id2050-research-proposal)",
            self.files["resources.md"],
        )
        self.assertIn(
            "[Data Collection Tools and Supporting Materials: Section 2.3](#data-collection-tools-and-supporting-materials)",
            chapter2,
        )
        self.assertIn(
            "[Appendices and Supplemental Materials: Section 4.3](chapter-04.html#appendices-and-supplemental-materials)",
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
