"""Convert the Word writing guide into chapter pages for GitHub Pages."""

import argparse
import copy
import html
import json
from pathlib import Path
import re
import shutil
import subprocess
from zipfile import ZipFile


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "Prof Roberts_IQP Writing Guide_2026.docx"
OUTPUT = ROOT / "docs"
CHAPTER = re.compile(r"^Chapter (\d+) - (.+)$")
SECTION = re.compile(r"^\d+\.\d+\s")


def walk(value):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk(child)


def text(value):
    return "".join(
        node["c"] if node["t"] == "Str" else " "
        for node in walk(value)
        if node.get("t") in {"Str", "Space", "SoftBreak", "LineBreak"}
    )


def pandoc(document):
    return subprocess.run(
        ["pandoc", "--from=json", "--to=gfm", "--wrap=none"],
        input=json.dumps(document),
        capture_output=True,
        encoding="utf-8",
        check=True,
    ).stdout.strip()


def html_block(document, block):
    markup = subprocess.run(
        ["pandoc", "--from=json", "--to=html"],
        input=json.dumps({**document, "blocks": [block]}),
        capture_output=True,
        encoding="utf-8",
        check=True,
    ).stdout.strip()
    return {"t": "RawBlock", "c": ["html", markup]}


def link(page, label=None):
    return f'[{label or page["title"]}]({page["slug"]}.html)'


def front_matter(title):
    return f"---\nlayout: default\ntitle: {json.dumps(title, ensure_ascii=False)}\n---\n\n"


def meaningful(block):
    return block["t"] != "Para" or text(block).strip() or any(
        node.get("t") == "Image" for node in walk(block)
    )


def convert():
    if not shutil.which("pandoc"):
        raise RuntimeError("Pandoc is required. Install it from https://pandoc.org/installing.html")
    result = subprocess.run(
        ["pandoc", str(SOURCE), "--to=json"],
        capture_output=True,
        encoding="utf-8",
        check=True,
    )
    document = json.loads(result.stdout)
    pages = []
    first_chapter = None
    contents_start = None
    for index, block in enumerate(document["blocks"]):
        if block["t"] != "Header":
            continue
        title = text(block["c"][2]).strip()
        if title == "Table of Contents":
            contents_start = index
        match = CHAPTER.fullmatch(title)
        if match or title == "Resources":
            if first_chapter is None:
                first_chapter = index
            pages.append(
                {
                    "title": title,
                    "slug": f"chapter-{int(match[1]):02d}" if match else "resources",
                    "start": index,
                }
            )
    if [p["slug"] for p in pages] != [
        *(f"chapter-{n:02d}" for n in range(1, 7)),
        "resources",
    ]:
        raise ValueError("Expected six numbered chapters followed by Resources; review the source structure.")
    if contents_start is None or first_chapter is None:
        raise ValueError("The source must contain a table of contents and chapter headings.")

    targets = {}
    for index, page in enumerate(pages):
        end = pages[index + 1]["start"] if index + 1 < len(pages) else len(document["blocks"])
        page["blocks"] = copy.deepcopy(document["blocks"][page["start"]:end])
        heading_stack = []
        for block in page["blocks"]:
            if block["t"] != "Header":
                continue
            level, attributes, inlines = block["c"]
            title = text(inlines)
            if block is page["blocks"][0]:
                level = 1
            elif SECTION.match(title):
                level = 2
                heading_stack = []
            elif page["slug"] != "resources":
                source_level = level
                while heading_stack and heading_stack[-1] >= source_level:
                    heading_stack.pop()
                heading_stack.append(source_level)
                level = 2 + len(heading_stack)
            block["c"][0] = min(level, 6)
            anchor = attributes[0]
            if not anchor or anchor in targets:
                raise ValueError(f"Missing or duplicate heading anchor: {anchor!r}")
            targets[anchor] = page["slug"]

    for page in pages:
        for node in walk(page["blocks"]):
            if node.get("t") == "Link" and node["c"][2][0].startswith("#"):
                anchor = node["c"][2][0][1:]
                if anchor not in targets:
                    raise ValueError(f"Unresolved internal link: #{anchor}")
                prefix = "" if targets[anchor] == page["slug"] else targets[anchor] + ".html"
                node["c"][2][0] = prefix + "#" + anchor
            elif node.get("t") == "Image":
                node["c"][2][0] = "assets/" + node["c"][2][0]
                # Let the theme fit images to the viewport without distorting them.
                node["c"][0][2] = [
                    pair for pair in node["c"][0][2] if pair[0] not in {"width", "height"}
                ]

    files = {}
    preface = [block for block in document["blocks"][:contents_start] if meaningful(block)]
    home = [
        "# IQP Writing Guide",
        "*From Proposal to Final Report*",
        pandoc({**document, "blocks": preface}),
        "## Contents",
        "\n".join(f'- {link(page)}' for page in pages),
        "Each chapter includes a section contents list and links to the previous and next page.",
    ]
    files["index.md"] = front_matter("IQP Writing Guide") + "\n\n".join(home) + "\n"

    for index, page in enumerate(pages):
        blocks = []
        headings = []
        for block in page["blocks"]:
            if not meaningful(block):
                continue
            if block["t"] == "Header":
                level, attributes, inlines = block["c"]
                anchor = attributes[0]
                blocks.append(
                    {"t": "RawBlock", "c": ["html", f'<a id="{html.escape(anchor, quote=True)}"></a>']}
                )
                images = [inline for inline in inlines if inline["t"] == "Image"]
                if images:
                    blocks.append({"t": "Para", "c": images})
                    inlines[:] = [inline for inline in inlines if inline["t"] != "Image"]
                    if not text(inlines).strip():
                        continue
                if level == 2:
                    headings.append(f'- [{text(inlines)}](#{anchor})')
            # GFM cannot reliably round-trip underline or punctuation-only emphasis.
            if any(
                node.get("t") == "Underline"
                or (
                    node.get("t") in {"Strong", "Emph"}
                    and not any(character.isalnum() for character in text(node))
                )
                for node in walk(block)
            ):
                blocks.append(html_block(document, block))
            else:
                blocks.append(block)
            if block is page["blocks"][0]:
                # Insert the section contents after conversion, below the chapter title.
                blocks.append({"t": "RawBlock", "c": ["html", "<!-- chapter-contents -->"]})
        contents = "**On this page**\n\n" + "\n".join(headings) if headings else ""
        body = pandoc({**document, "blocks": blocks}).replace("<!-- chapter-contents -->", contents)
        navigation = ['[Contents](index.html)']
        if index:
            navigation.append(link(pages[index - 1], "Previous: " + pages[index - 1]["title"]))
        if index + 1 < len(pages):
            navigation.append(link(pages[index + 1], "Next: " + pages[index + 1]["title"]))
        files[page["slug"] + ".md"] = (
            front_matter(page["title"])
            + "[Contents](index.html)\n\n"
            + body
            + "\n\n---\n\n"
            + " | ".join(navigation)
            + "\n"
        )

    media = {}
    with ZipFile(SOURCE) as archive:
        for name in archive.namelist():
            if name.startswith("word/media/") and not name.endswith("/"):
                media["assets/media/" + Path(name).name] = archive.read(name)
    return files, media


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Check that committed pages match the Word source.")
    args = parser.parse_args()
    files, media = convert()
    if args.check:
        stale = [
            name for name, content in files.items()
            if not (OUTPUT / name).exists() or (OUTPUT / name).read_text(encoding="utf-8") != content
        ]
        stale += [
            name for name, content in media.items()
            if not (OUTPUT / name).exists() or (OUTPUT / name).read_bytes() != content
        ]
        if stale:
            raise SystemExit("Missing or outdated generated files: " + ", ".join(stale))
        print(f"Up to date: {len(files)} Markdown pages and {len(media)} images.")
        return
    OUTPUT.mkdir(exist_ok=True)
    for name, content in files.items():
        (OUTPUT / name).write_text(content, encoding="utf-8", newline="\n")
    for name, content in media.items():
        target = OUTPUT / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
    print(f"Generated {len(files)} Markdown pages and {len(media)} images in {OUTPUT}.")


if __name__ == "__main__":
    main()
