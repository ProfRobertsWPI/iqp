"""Convert the Word writing guide into chapter pages for GitHub Pages."""

import argparse
import copy
import json
from pathlib import Path
import re
import shutil
import subprocess
from zipfile import ZipFile
from urllib.parse import quote


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "Prof Roberts_IQP Writing Guide_2026.docx"
OUTPUT = ROOT / "docs"
CHAPTER = re.compile(r"^Chapter (\d+) - (.+)$")
SECTION = re.compile(r"^\d+\.\d+\s")
WORKSHEETS = {
    "Introduction Move and Questions to Guide Your PlanningYour Ideas": (
        "Worksheet_Planning your introduction.docx",
        "Planning your Introduction",
    ),
    "Background SectionWhat is the purpose of this section?Why does this section appear in this order?": (
        "Worksheet_Planning your background chapter.docx",
        "Planning your Background Chapter",
    ),
    "Project GoalResearch ObjectiveResearch QuestionsWhat information do we need?Who or what can provide it?": (
        "WORKSHEET \u2013 Planning Your Goal, Objectives, and Research Questions.docx",
        "Planning Your Goal, Objectives, and Research Questions",
    ),
    "Research QuestionInformation NeededSource of InformationMethodHow will we collect it?Why does this method make sense?": (
        "WORKSHEET \u2013 Connect Research Questions to Methods.docx",
        "Connect Research Questions to Methods",
    ),
    "Research QuestionEvidence from Method/Source 1Evidence from Method/Source 2Evidence from Method/Source 3": (
        "WORKSHEET \u2013 Planning for Triangulation.docx",
        "Planning for Triangulation",
    ),
    "What did we find?What evidence supports this finding?What does the evidence mean?What limitations or alternative interpretations should readers understand?": (
        "WORKSHEET \u2013 Planning your Findings Chapter.docx",
        "Planning your Findings Chapter",
    ),
    "What did we find?What do we recommend?Who is the recommendation for?What would implementation require?": (
        "WORKSHEET \u2013 Planning your Recommendations.docx",
        "Planning your Recommendations",
    ),
}


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


def normalize_markdown(value):
    """Remove Word-only inline presentation and make table cells single-line."""
    if isinstance(value, list):
        result = []
        for child in value:
            child = normalize_markdown(child)
            if isinstance(child, dict) and child.get("t") == "Underline":
                result.extend(child["c"])
            elif isinstance(child, dict) and child.get("t") in {"Strong", "Emph"}:
                inlines = child["c"]
                leading = []
                trailing = []
                while inlines and inlines[0]["t"] in {"Space", "SoftBreak"}:
                    leading.append(inlines.pop(0))
                while inlines and inlines[-1]["t"] in {"Space", "SoftBreak"}:
                    trailing.insert(0, inlines.pop())
                result.extend(leading)
                if any(character.isalnum() for character in text(inlines)):
                    result.append(child)
                else:
                    result.extend(inlines)
                result.extend(trailing)
            else:
                result.append(child)
        portable = []
        for index, child in enumerate(result):
            following = result[index + 1] if index + 1 < len(result) else None
            if (
                isinstance(child, dict) and child.get("t") in {"Strong", "Emph"}
                and isinstance(following, dict) and following.get("t") == "Str"
                and following["c"][:1].isalnum()
            ):
                portable.extend(child["c"])
            else:
                portable.append(child)
        return portable
    if isinstance(value, dict):
        return {key: normalize_markdown(child) for key, child in value.items()}
    return value


def simplify_table(table):
    columns = len(table["c"][2])
    pending = {}
    sections = [table["c"][3][1]]
    sections.extend(rows for body in table["c"][4] for rows in (body[2], body[3]))
    sections.append(table["c"][5][1])
    for rows in sections:
        for row in rows:
            expanded = []
            cells = iter(row[1])
            for column in range(columns):
                if pending.get(column, 0):
                    pending[column] -= 1
                    cell = [["", [], []], {"t": "AlignDefault"}, 1, 1, []]
                else:
                    cell = next(cells)
                    if cell[3] != 1:
                        raise ValueError("Column-spanning tables need an explicit Markdown conversion.")
                    pending[column] = cell[2] - 1
                    cell[2] = 1
                flattened = []
                for block in cell[4]:
                    if block["t"] not in {"Para", "Plain"}:
                        raise ValueError(f"Unsupported table cell block: {block['t']}")
                    if flattened:
                        flattened.append({"t": "Space"})
                    flattened.extend(block["c"])
                for inline in walk(flattened):
                    if inline.get("t") in {"LineBreak", "SoftBreak"}:
                        inline.clear()
                        inline["t"] = "Space"
                cell[4] = [{"t": "Plain", "c": flattened}]
                expanded.append(cell)
            if next(cells, None) is not None:
                raise ValueError("Unexpected extra cells in table row.")
            row[1] = expanded
    for specification in table["c"][2]:
        specification[1] = {"t": "ColWidthDefault"}


def markdown_anchors(document, pages):
    """Ask the GFM parser for the same automatic heading IDs used by GitHub."""
    anchors = {}
    for page in pages:
        headers = [
            block for block in page["blocks"]
            if block["t"] == "Header" and text(block["c"][2]).strip()
        ]
        parsed = json.loads(subprocess.run(
            ["pandoc", "--from=gfm", "--to=json"],
            input=pandoc({**document, "blocks": headers}),
            capture_output=True,
            encoding="utf-8",
            check=True,
        ).stdout)
        generated = [block for block in parsed["blocks"] if block["t"] == "Header"]
        if len(headers) != len(generated):
            raise ValueError("Markdown conversion changed the heading structure.")
        for original, converted in zip(headers, generated):
            old = original["c"][1][0]
            new = converted["c"][1][0]
            anchors[old] = new
            original["c"][1][0] = new
    return anchors


def link(page, label=None):
    return f'[{label or page["title"]}]({page["slug"]}.md)'


def front_matter(title):
    return f"---\nlayout: default\ntitle: {json.dumps(title, ensure_ascii=False)}\n---\n\n"


def meaningful(block):
    return block["t"] != "Para" or text(block).strip() or any(
        node.get("t") == "Image" for node in walk(block)
    )


def link_inlines(inlines, references):
    """Link plain-text runs without rewriting existing links or inline formatting."""
    pattern = re.compile(
        r"(?<!\w)(?:" + "|".join(re.escape(label) for label in sorted(references, key=len, reverse=True)) + r")(?!\w)"
    )
    result = []
    run = []

    def flush():
        value = text(run)
        position = 0

        def plain(value):
            return [
                {"t": "Space"} if part == " " else {"t": "Str", "c": part}
                for part in re.split("( )", value) if part
            ]

        for match in pattern.finditer(value):
            result.extend(plain(value[position:match.start()]))
            url, label = references[match[0]]
            result.append({"t": "Link", "c": [["", [], []], plain(label), [url, ""]]})
            position = match.end()
        result.extend(plain(value[position:]))
        run.clear()

    for inline in inlines:
        if inline["t"] in {"Str", "Space", "SoftBreak"}:
            run.append(inline)
            continue
        flush()
        if inline["t"] in {"Strong", "Emph", "Underline", "Strikeout", "Superscript", "Subscript"}:
            inline["c"] = link_inlines(inline["c"], references)
        result.append(inline)
    flush()
    return result


def add_cross_references(pages, targets):
    numbered = {}
    for page in pages:
        for block in page["blocks"]:
            if block["t"] == "Header":
                title = text(block["c"][2])
                if SECTION.match(title):
                    numbered[title.split()[0]] = (title, block["c"][1][0])

    for page in pages:
        def url(anchor):
            if anchor not in targets:
                raise ValueError(f"Unknown cross-reference target: {anchor}")
            prefix = "" if targets[anchor] == page["slug"] else targets[anchor] + ".md"
            return prefix + "#" + anchor

        references = {}
        for number, (title, anchor) in numbered.items():
            for label in (title, "Section " + number, "section " + number):
                references[label] = (url(anchor), label)
        for chapter in pages:
            if chapter["slug"].startswith("chapter-"):
                label = "Chapter " + str(int(chapter["slug"].split("-")[1]))
                references[label] = (url(chapter["blocks"][0]["c"][1][0]), label)

        for block in page["blocks"]:
            for node in walk(block):
                if node.get("t") not in {"Para", "Plain"}:
                    continue
                value = text(node["c"])
                local = dict(references)
                # These are references to the guide, not example appendices in a student's report.
                if "See Appendix A and B for examples" in value:
                    for label, anchor in (
                        ("Appendix A", "appendix-a-cover-page-examples"),
                        ("B", "appendix-b-required-wpi-title-page-for-final-report"),
                    ):
                        local[label] = (url(anchor), label)
                if "See Appendix D for examples" in value:
                    local["Appendix D"] = (url("appendix-d-example-meet-the-team-pages"), "Appendix D")
                if "Section 5.2 and 5.3" in value:
                    local["5.3"] = (url("formatting-and-document-mechanics"), "5.3")
                if "As discussed in Part II" in value:
                    local["Part II"] = (
                        url("chapter-2---building-your-research-story"), "Chapter 2"
                    )
                if "As discussed earlier in this guide" in value:
                    local["earlier in this guide"] = (url("writing-as-a-team"), "earlier in this guide")
                if "Authorship Statement (below)" in value:
                    local["Authorship Statement"] = (url("authorship-statement"), "Authorship Statement")
                guidance = {
                    "Quoting, Paraphrasing, and Summarizing: Section 5.4": (
                        "quoting-paraphrasing-and-summarizing", None
                    ),
                    "Using AI in Research and Writing: Section 5.4": ("ai-generated-content-and-sources", None),
                    "Data Collection Tools and Supporting Materials: Section 5.4": (
                        "data-collection-tools-and-supporting-materials",
                        "Data Collection Tools and Supporting Materials: Section 2.3",
                    ),
                    "Appendices and Supplemental Materials: Section 5.4": (
                        "appendices-and-supplemental-materials",
                        "Appendices and Supplemental Materials: Section 4.3",
                    ),
                }
                if value in guidance:
                    anchor, corrected = guidance[value]
                    local[value] = (url(anchor), corrected or value)
                if "Authorship Table as described in section 4.2" in value:
                    local["Authorship Table"] = (url("authorship-table"), "Authorship Table")
                node["c"] = link_inlines(node["c"], local)


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
                prefix = "" if targets[anchor] == page["slug"] else targets[anchor] + ".md"
                node["c"][2][0] = prefix + "#" + anchor
            elif node.get("t") == "Image":
                node["c"][2][0] = "assets/" + node["c"][2][0]
                # Let the theme fit images to the viewport without distorting them.
                node["c"][0][2] = [
                    pair for pair in node["c"][0][2] if pair[0] not in {"width", "height"}
                ]

    add_cross_references(pages, targets)

    for page in pages:
        page["blocks"] = normalize_markdown(page["blocks"])
        for block in page["blocks"]:
            if block["t"] == "Header":
                images = [inline for inline in block["c"][2] if inline["t"] == "Image"]
                block["heading_images"] = images
                block["c"][2] = [inline for inline in block["c"][2] if inline["t"] != "Image"]
    anchors = markdown_anchors(document, pages)
    for page in pages:
        for node in walk(page["blocks"]):
            if node.get("t") == "Link":
                destination = node["c"][2][0]
                if "#" in destination and not re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*:", destination):
                    path, anchor = destination.split("#", 1)
                    node["c"][2][0] = path + "#" + anchors[anchor]

    files = {}
    sidebar = [
        {
            "title": page["title"],
            "url": "/" + page["slug"] + ".html",
            "sections": [
                {"title": text(block["c"][2]), "anchor": block["c"][1][0]}
                for block in page["blocks"]
                if block["t"] == "Header" and block["c"][0] == 2
            ],
        }
        for page in pages
    ]
    preface = normalize_markdown([block for block in document["blocks"][:contents_start] if meaningful(block)])
    home = [
        "# IQP Writing Guide",
        "*From Proposal to Final Report*",
        "[![IQP Writing Guide cover: a winding path connects research, collaboration, and writing "
        "on a cream, navy, and teal background.](assets/cover/iqp-writing-guide.png)]"
        "(assets/cover/iqp-writing-guide.png)",
        "[View the cover full-size](assets/cover/iqp-writing-guide.png)",
        "## Welcome",
        "Welcome to the Interactive Qualifying Project (IQP) Writing Guide. "
        "This guide supports you as you write your ID2050 research proposal and "
        "IQP final report, from planning your research story to assembling and sharing your completed report.",
        "## How to use this guide",
        "Read the chapters in order or jump to the topic you need using the chapter links below. "
        "On the website, the **Chapters and sections** sidebar lets you explore each chapter's sections; "
        "on smaller screens, open the menu above the page. Use **Search the guide** in the header to find "
        "topics across the guide, and **Dark mode** to choose a comfortable reading theme.",
        "Each chapter includes an **On this page** section list and previous/next links. "
        "Follow linked chapter and section references for related guidance. "
        "Planning tables stay in the guide, with links below them to download editable Word worksheets. "
        "Resources and Appendices A-D are collected on the Resources page.",
        "## Contents",
        "\n".join(f'- {link(page)}' for page in pages),
        "---",
        pandoc({**document, "blocks": preface}),
    ]
    files["index.md"] = front_matter("IQP Writing Guide") + "\n\n".join(home) + "\n"

    linked_worksheets = set()
    for index, page in enumerate(pages):
        blocks = []
        headings = []
        for block in page["blocks"]:
            if not meaningful(block):
                continue
            if block["t"] == "Header":
                level, attributes, inlines = block["c"]
                anchor = attributes[0]
                images = block.pop("heading_images", [])
                if images:
                    blocks.append({"t": "Para", "c": images})
                    if not text(inlines).strip():
                        continue
                if level == 2:
                    headings.append(f'- [{text(inlines)}](#{anchor})')
            header = text(block["c"][3]) if block["t"] == "Table" else None
            if block["t"] == "Table":
                simplify_table(block)
            blocks.append(block)
            if block["t"] == "Table":
                if header in WORKSHEETS:
                    filename, label = WORKSHEETS[header]
                    if filename in linked_worksheets:
                        raise ValueError(f"Worksheet matched more than one table: {filename}")
                    worksheet = OUTPUT / "assets" / "worksheets" / filename
                    if not worksheet.is_file():
                        raise FileNotFoundError(f"Missing worksheet: {worksheet}")
                    linked_worksheets.add(filename)
                    url = "assets/worksheets/" + quote(filename, safe="")
                    blocks.append({"t": "Para", "c": [{
                        "t": "Link",
                        "c": [["", [], []], [{"t": "Str", "c": f"Download worksheet: {label} (Word .docx)"}], [url, ""]],
                    }]})
            if block is page["blocks"][0]:
                # Insert the section contents after conversion, below the chapter title.
                blocks.append({"t": "Para", "c": [{"t": "Str", "c": "CHAPTER_CONTENTS_PLACEHOLDER"}]})
        contents = "**On this page**\n\n" + "\n".join(headings) if headings else ""
        body = pandoc({**document, "blocks": blocks}).replace("CHAPTER_CONTENTS_PLACEHOLDER", contents)
        navigation = ['[Contents](index.md)']
        if index:
            navigation.append(link(pages[index - 1], "Previous: " + pages[index - 1]["title"]))
        if index + 1 < len(pages):
            navigation.append(link(pages[index + 1], "Next: " + pages[index + 1]["title"]))
        files[page["slug"] + ".md"] = (
            front_matter(page["title"])
            + "[Contents](index.md)\n\n"
            + body
            + "\n\n---\n\n"
            + "\n".join("- " + item for item in navigation)
            + "\n"
        )

    missing = {filename for filename, _ in WORKSHEETS.values()} - linked_worksheets
    if missing:
        raise ValueError("No matching table found for worksheets: " + ", ".join(sorted(missing)))

    media = {}
    with ZipFile(SOURCE) as archive:
        for name in archive.namelist():
            if name.startswith("word/media/") and not name.endswith("/"):
                media["assets/media/" + Path(name).name] = archive.read(name)
    files["_data/navigation.json"] = json.dumps(sidebar, ensure_ascii=False, indent=2) + "\n"
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
        print(f"Up to date: {len(files) - 1} Markdown pages, sidebar navigation, and {len(media)} images.")
        return
    OUTPUT.mkdir(exist_ok=True)
    for name, content in files.items():
        target = OUTPUT / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8", newline="\n")
    for name, content in media.items():
        target = OUTPUT / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
    print(f"Generated {len(files) - 1} Markdown pages, sidebar navigation, and {len(media)} images in {OUTPUT}.")


if __name__ == "__main__":
    main()
