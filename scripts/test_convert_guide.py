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
        self.parts = []
        self.targets = []
        self.links = []
        self.images = []
        self.tables = 0
        self.feed(markup)

    def handle_data(self, data):
        self.parts.append(data)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if "id" in attrs:
            self.targets.append(attrs["id"])
        if tag == "a" and "href" in attrs:
            self.links.append(attrs["href"])
        if tag == "img":
            self.images.append(attrs["src"])
        if tag == "table":
            self.tables += 1

    def words(self):
        return re.sub(r"\s+", " ", " ".join(self.parts)).strip()


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
            {"index.md", "resources.md", *(f"chapter-{n:02d}.md" for n in range(1, 7))},
        )
        for name, content in self.files.items():
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
                    target = self.pages[url.path or name]
                    if url.fragment:
                        self.assertIn(unquote(url.fragment), target.targets)
                for image in page.images:
                    self.assertIn(image, self.media)

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
            converted = Page(render(content, "gfm-gfm_auto_identifiers"))
            with self.subTest(page=name):
                self.assertEqual(original.words(), converted.words())
                self.assertEqual(original.tables, converted.tables)
                self.assertEqual(
                    ["assets/" + image for image in original.images], converted.images
                )

    def test_generated_files_are_current(self):
        for name, content in self.files.items():
            self.assertEqual((CONVERTER.OUTPUT / name).read_text(encoding="utf-8"), content)
        for name, content in self.media.items():
            self.assertEqual((CONVERTER.OUTPUT / name).read_bytes(), content)


if __name__ == "__main__":
    unittest.main()
