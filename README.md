# IQP Writing Guide

The GitHub Pages edition of **IQP Writing Guide: From Proposal to Final Report**
is generated from `Prof Roberts_IQP Writing Guide_2026.docx`.

**Published guide:** <https://profrobertswpi.github.io/iqp/>

## Start here: maintaining the guide

**The author should make lasting content changes in the Word document,
not in the generated chapter Markdown files.** Running the converter replaces
those Markdown files. The Word document, worksheet files, converter, and
generated website files are all kept in this repository.

The normal update process is:

1. **Edit:** revise the Word document and save it under its existing filename.
2. **Upload/merge:** commit the revised document to `main`, or upload it on a
   branch and merge its pull request into `main`.
3. **Generate and publish automatically:** GitHub Actions converts Word to
   Markdown, checks the guide, builds the site, checks the built links,
   commits any regenerated files to `main`, and deploys the website.

**The author does not need to run the converter locally for routine updates.**
Updating the source Word document on `main` triggers conversion and publication.
Wait for the Actions run to succeed before assuming the changes are live.
The source retains its original filename, `Prof Roberts_IQP Writing Guide_2026.docx`;
references to that filename below identify the file, not an editing role.

### What to edit for each kind of change

| Change | Where to make it | What happens next |
| --- | --- | --- |
| Fix text, lists, captions, or existing table content | The source Word document | Merge to `main`; Actions regenerates and publishes. |
| Add or replace a guide image | Insert/embed it in the Word document | Merge to `main`; images are extracted to `docs/assets/media/`. |
| Replace the landing-page cover | Export the complete approved cover from Figma and replace `docs/assets/cover/iqp-writing-guide.png` | Keep the filename; it is a separately maintained site asset, not extracted from Word. |
| Add a section within an existing chapter | Add a Word heading, using the existing numbering and heading styles | Actions rebuilds chapter contents and sidebar links. Review links to renamed headings. |
| Replace an existing downloadable worksheet | Replace its file in `docs/assets/worksheets/`, keeping the exact filename | Commit and publish the replacement; no conversion is needed if nothing else changes. |
| Add or rename a worksheet, or change its associated table's header | Worksheet folder, Word table, and `WORKSHEETS` mapping in the converter | A technical maintainer must update the mapping, regenerate, and update affected tests. |
| Add an external website link | Use Word's **Insert > Link** on descriptive text | Regenerate and check the destination. |
| Add a link to another guide section | Use a Word hyperlink to an existing heading, or a supported numbered reference | Regenerate and check both Markdown and site destinations. |
| Add/remove a chapter, renumber sections, or rename mapped headings | Word document plus converter rules and tests | Coordinate with a technical maintainer; these are structural changes. |
| Change colors, fonts, theme behavior, or site layout | CSS, theme JavaScript, or shared layout under `docs/` | No Word conversion is needed; review and publish the site files. |

### Routine content edits, step by step

1. Get the latest repository files before editing. A technical maintainer can
   use Git/GitHub Desktop; avoid starting from an old downloaded copy.
2. Open `Prof Roberts_IQP Writing Guide_2026.docx` in Word, make changes, save,
   and close it. Keep that filename unless the converter's `SOURCE` setting
   is also updated.
3. Use Word's real heading styles and real bullet/numbered lists, rather than
   manually formatting ordinary paragraphs to look like headings or lists.
   Keep chapter titles in the form `Chapter 2 - Building Your Research Story`
   and numbered section headings in the form `2.1 Introduction`.
4. Upload/commit the revised document to the repository. In GitHub's web
   interface, use **Add file > Upload files** at the repository root and keep
   the exact filename so it replaces the existing source rather than adding
   a second copy. Commit directly to `main` if permitted, or create a branch
   and merge its pull request. Include any associated worksheet changes.
5. Follow the run in **Actions**, then review the published chapter pages,
   images, worksheet links, and navigation. Pull the latest `main` before the
   next local edit so the bot's regenerated files are included.

The author does not need Python or Ruby to edit Word or use automatic
publication. Local conversion remains available for previewing changes before
merging. For structural changes or a failed workflow, the author can provide
the revised Word document and any worksheets to the maintainer with a request
such as:

> Update the guide from the revised Word document. Regenerate the Markdown,
> images, and navigation, check links and worksheet downloads, and publish
> the changes to main.

### Adding or replacing images

Insert pictures into the Word document itself, preferably **in line with text**
in their own paragraphs, with descriptive alternative text and any caption
readers need. Do not link to an image that exists only on your computer.
Use common web formats such as PNG or JPEG; unusual Office drawing formats
need a maintainer's review for browser compatibility.

The converter extracts embedded images and writes Markdown image references.
Do not replace generated `image1.png`-style files by hand: the next conversion
can overwrite them, and Word can change media filenames after edits. Review
the image and its surrounding text after regeneration. Files no longer used
by Word are not automatically deleted from the asset folder; a maintainer
should remove obsolete files only after confirming no page references them.

### Adding or replacing worksheets

Worksheets are separate downloadable Word files, not substitutes for the
tables in the guide. Keep the associated planning table in the source document;
the converter inserts the download link directly below it.

For an existing worksheet, edit or replace the file under
`docs/assets/worksheets/` and keep its filename exactly, including spaces,
capitalization, and dash characters. Merely changing worksheet contents does
not require regeneration.

For a new worksheet, ask a technical maintainer to:

1. Add the `.docx` file under `docs/assets/worksheets/`.
2. Add or identify the associated planning table in the source Word document.
3. Add an entry to `WORKSHEETS` in `scripts/convert-guide.py`: the key is the
   exact concatenated header text produced by Pandoc, and the value contains
   the exact filename and reader-facing download label. Follow an existing
   entry; this is not a fuzzy match on the table's caption or nearby heading.
4. Regenerate and update worksheet-count/placement expectations in the tests.
   Confirm the table remains and the new download appears immediately below it.

Changing a mapped table's header can break its match even when the worksheet
file is unchanged. Renaming/removing a worksheet also requires updating/removing
its mapping and affected tests. The converter reports missing files, duplicate
matches, and configured worksheets with no matching table; do not publish
around those errors.

### Adding links and changing headings

For external resources, insert a normal Word hyperlink using a complete
`https://` address. Use descriptive labels rather than "click here." Avoid
local paths such as `C:\...`, which readers cannot access. WPI-only resources
may still require sign-in; conversion does not make them public.

For internal destinations, link to an existing Word heading using **Insert >
Link > Place in This Document**. A newly invented bookmark that is not a
recognized heading is not supported by the current converter. Plain-text
references such as `Chapter 3` and `Section 2.3` are also linked automatically
when their targets exist. Not every informal phrase or appendix mention is
automatically linked: some guide-specific phrases have explicit rules, and
examples about a student's own report intentionally remain unlinked.

Renaming a heading changes its automatic web/Markdown anchor. Regeneration
updates generated navigation and recognized references, but cannot repair old
bookmarks, links from other websites, or every custom reference rule. Ask a
maintainer to review the rules in `add_cross_references()` after heading or
numbering changes. In particular, the current converter expects exactly six
numbered chapters followed by `Resources`; adding a seventh chapter requires
code and test changes, not just a new Word heading.

If a maintainer works with Markdown links, use these forms (relative to a page
in `docs/`):

```markdown
[Another chapter](chapter-03.md)
[Introduction](chapter-02.md#21-introduction)
[A section on this page](#21-introduction)
![Descriptive image text](assets/media/image1.png)
[Download the introduction worksheet](assets/worksheets/Worksheet_Planning%20your%20introduction.docx)
[WPI](https://www.wpi.edu/)
```

Use `.md` page paths, not `.html`, `/iqp/` prefixes, or local filesystem paths.
Copy the actual heading anchor from the generated chapter contents rather
than guessing it. URL-encode spaces and punctuation in asset filenames; the
converter does this for worksheet links. These examples explain the generated
format, not an alternative to making durable edits in Word.

## Site structure

- `docs/index.md`: welcome, navigation guidance, chapter contents, and the
  original author's note / AI disclosure at the bottom.
- `docs/chapter-01.md` through `docs/chapter-06.md`: one page per chapter.
- `docs/resources.md`: resources and Appendices A-D.
- `docs/assets/media/`: the images embedded in the Word document.

Chapter pages include section contents and previous/next navigation. Tables,
lists, emphasis, hyperlinks, and images use native Markdown syntax. Table cells
containing multiple lines are flattened into single cells, and the merged
project-goal cell becomes a single entry with blank continuation cells.
Word-only underlining is removed rather than embedded as HTML. The printed table of contents and
its page numbers are replaced by web navigation. Inconsistent Word heading
levels are normalized for the web.

Every page also has a left sidebar with expandable chapter menus and direct
links to numbered sections and resource appendices. The current chapter opens
automatically; the selected section is highlighted when following an anchor
link. On small screens the navigation becomes a collapsible menu above the
content. Navigation data in `docs/_data/navigation.json` is regenerated from the
Word headings along with the chapter pages. The shared layout and responsive
styles live in `docs/_layouts/default.html` and `docs/assets/site.css`.

The shared top header includes the guide title, light/dark toggle, and
**Search the guide** and stays visible while scrolling. Its measured height
offsets the desktop sidebar and section-link targets so headings are not
hidden behind it, including when the header wraps on small screens.
Search matches words across all eight guide pages,
prioritizes page-title matches, and shows links with text snippets. Multiple
search words must all occur on a page. Tab moves through result links; Escape
or **Close** dismisses results. Search runs in the browser without sending
queries to an external service. It requires JavaScript; chapter navigation
still works without it. Worksheet file contents are not indexed.

Jekyll builds `docs/search.json` from pages using the shared `default` layout,
so the index updates on every publication, including Word-triggered updates.
Search behavior lives in `docs/assets/search.js`; run its checks with
`node --test scripts\test-search.cjs`. Welcome/navigation text is maintained
in the converter's `home` list, while the author's original note remains
sourced from Word. The reference site's header/search pattern is adapted to
the cover-inspired theme rather than replacing the site's generator or sidebar.

The seven planning tables in Chapters 2 and 3 remain in the guide, with a
download link immediately below each one for its matching Word worksheet in
`docs/assets/worksheets/`. The converter matches table headers to the worksheet
mapping in `scripts/convert-guide.py` and reports missing files or unmatched
tables instead of generating broken download links.

Explicit references to this guide's chapters, numbered sections, and appendix
examples link directly to the relevant heading. Related Guidance entries link
to the most specific matching topic. Examples referring to appendices in a
student's own report remain plain text. These links are generated by
`scripts/convert-guide.py`, not maintained by hand in the Markdown.
The web edition also corrects three stale source references: "Part II" points
to Chapter 2, data-collection tools to Section 2.3, and appendices/supplemental
materials to Section 4.3 rather than Section 5.4.

## Markdown and published-site links

Page links use relative `.md` paths, so they work when browsing the repository
on GitHub or in a GitHub-flavored Markdown preview. Images and worksheets also
use relative asset paths, with spaces and punctuation URL-encoded in worksheet
filenames.

GitHub Pages uses `jekyll-relative-links` to rewrite `.md` page links to the
published `.html` URLs, including the `/iqp` base path. Section links use
GitHub-style automatic heading anchors, including section numbers and
per-page suffixes for duplicate headings. The site's GFM parser generates the
same anchors. No HTML anchors, links, lists, images, or tables are embedded in
the generated Markdown. Custom HTML remains only in the site's shared layout.
Markdown viewers must support GFM tables and automatic heading anchors.

The site adds the download attribute to worksheet links in the shared layout;
in Markdown views, the same links open the Word file for download using the
viewer's normal file controls.

## Cover art, site colors, and themes

The author selected the [Figma cover design](https://www.figma.com/design/gBEn5y4tMGH2LACd53AM1T)
(frame `1:2`, **IQP Writing Guide Cover**) as the visual direction. The complete
cover is exported to `docs/assets/cover/iqp-writing-guide.png` and displayed
on the right of the landing page alongside the welcome text, without a
full-size link. On small screens it stacks above the welcome text. It is stored locally so
readers do not need Figma access and the site does not depend on expiring export
URLs. The cover's title, subtitle, and author credit are retained as artwork;
page titles and navigation remain accessible text outside the image.

To replace it, export the complete frame (including its text layers) from
Figma and replace that PNG under the same filename. Do not place it in
`assets/media/`, which is reserved for images extracted from Word. The
converter generates the landing-page image/link but never overwrites this
separate cover asset. If the artwork or filename changes, update its
descriptive alternative text and references in the converter, plus affected
tests, before regenerating.

At the author's request, the earlier WPI crimson/gray branding was replaced
by a palette inspired by the cover:

| Role | Light theme | Dark theme |
| --- | --- | --- |
| Reading background | Cream `#F5EFDC` | Deep navy `#152735` |
| Main text | Navy `#142F40` | Cream `#F5EFDC` |
| Links and active navigation | Teal `#28676B` | Light sage/teal `#A4CCC3` |
| Header | Navy `#142F40` with cream text | Same navy and cream |

The cover's gold informs highlight accents, not small body text. Colors are
maintained as semantic `--cp-*` variables in `docs/assets/site.css`; dark-mode
colors are readability adaptations rather than exact samples from the image.
This is a cover-inspired site palette, not an official WPI brand treatment.
Headings use Georgia and body text uses Verdana with system fallbacks; no
licensed fonts or recreated WPI logos are distributed.

The **Dark mode** toggle in the header switches light/dark themes and saves
the preference in the reader's browser across pages and visits. Before a choice
is saved, the site follows the system color scheme, including live changes.
If browser storage is blocked, switching still works on the current page.
Printing uses a light palette regardless of the screen theme. Theme behavior
lives in `docs/assets/theme.js` and runs before the stylesheet to avoid a flash
of the wrong theme.

Run theme behavior checks with `node --test scripts\test-theme.cjs`.

## Publish on GitHub Pages

### Normal publication

1. Edit the Word source and/or worksheet files. Local regeneration is optional
   for a preview; Actions always regenerates before publishing.
2. Commit all relevant source changes together: the changed Word document,
   any worksheet files, and any converter or test updates needed for structural
   changes. If you regenerated locally, include those outputs too. Review the
   diff to avoid including unrelated files.
3. Push a working branch and open a pull request targeting `main`. Review and
   merge it. A maintainer with permission may instead push the reviewed commit
   directly to `main`; that was the publication method used during initial
   setup. Do not overwrite newer changes on `main`.
4. Open the repository's **Actions** tab and select **Deploy writing guide to
   GitHub Pages**. Confirm the run for the new commit completes successfully
   for both **build** and **deploy**. A successful push alone does not mean
   the website has finished publishing.
5. Open the published guide and check the changed pages, sidebar/section links,
   images, and worksheet downloads. Refresh if the browser shows old content.

The workflow in `.github/workflows/pages.yml` runs when a push to `main`
changes the source Word document, `scripts/convert-guide.py`,
`scripts/test_convert_guide.py`, `scripts/test-theme.cjs`,
`scripts/test-search.cjs`, `docs/**`, or the
workflow itself. It can also be started manually from
**Actions > Deploy writing guide to GitHub Pages > Run workflow**, selecting
`main`. Manual runs also regenerate, check, commit, and publish. Runs on other
branches are skipped. A README-only commit does not trigger publication.

The workflow uses Python 3.11 and Pandoc 3.12, matching the converter's
development versions. It checks the generated content and theme, builds Jekyll,
and checks built-site links before committing generated files and deploying.
When conversion changes files in `docs/`, it creates a
`Regenerate writing guide from Word source` commit as `github-actions[bot]`.
If generated output is unchanged, no extra commit is created. The bot commit
uses the repository's built-in `GITHUB_TOKEN`; it does not trigger another
workflow run. The original run continues through deployment, so no personal
access token or second publication run is needed.

### One-time configuration and recovery

In **Settings > Pages**, the build and deployment source must be **GitHub
Actions**. This is already configured for this repository; it is not a setting
to change for every publication.

The build job requests `contents: write` so its token can commit generated
files. Repository/organization policy and branch rules must allow that bot
push to `main`. If branch protection requires all changes through pull
requests or disallows bot pushes, a maintainer must arrange an approved
exception or redesign the generation step to open a pull request instead.
Do not disable protections blindly. A rejected push fails the run before
deployment rather than publishing files that were not saved to the repository.

The expected address is <https://profrobertswpi.github.io/iqp/>.
If you change the repository name or use a custom domain, update `url` and
`baseurl` in `docs/_config.yml`.

If publication fails, inspect the failed step's log in **Actions**, correct
the cause, and push the fix or rerun the workflow as appropriate. Do not
assume the live site includes a failed deployment. To undo a bad published
change, have a maintainer revert its commit on `main` and let Pages deploy
again; avoid force-pushing history. Revert the source change as well as its
generated output when undoing content changes; reverting only generated
Markdown will be undone by the next conversion.

Runs are serialized, and each build checks out the latest `main`. If `main`
changes again before the bot can push, Git rejects the non-fast-forward push;
the workflow never force-pushes. Let the queued run process the latest source
or manually rerun on `main`. A conversion/test failure also stops publication;
inspect it for a changed heading, worksheet mapping, or structural expectation.

## Update from Word

These commands are optional for local preview or troubleshooting; Actions
runs conversion automatically on `main`.

Install Python 3.11 or later and [Pandoc](https://pandoc.org/installing.html).
The conversion uses only the Python standard library and Pandoc; this edition
was generated with Pandoc 3.12.

From the repository root:

```powershell
python scripts\convert-guide.py
python scripts\convert-guide.py --check
python -m unittest discover -s scripts -p "test_*.py"
```

Commit the regenerated pages and images along with changes to the Word source.
The converter overwrites generated Markdown pages, so make durable content
changes in Word rather than editing those pages directly. External resource
links are preserved as supplied; some point to WPI sign-in-protected resources.

`--check` reports whether generated files match the source without writing
them. The Python tests check source-text fidelity, page structure, native
Markdown, local links/images, sidebar destinations, and worksheet placement.
Without `IQP_SITE_BUILD`, the additional built-site parity test is skipped;
use [Local preview](#local-preview) for that check. The publication workflow
runs both the Python and theme checks, including built-site parity after
building Jekyll.

For changes to theme behavior, also run:

```powershell
node --test scripts\test-theme.cjs
```

Some tests intentionally encode the current guide's structure and content.
When deliberately changing it, review and update only the relevant
expectations; do not remove checks merely to make a failed conversion pass.

## Design decisions and maintenance boundaries

These decisions were made while creating and refining this edition:

| Decision | Reason and maintenance consequence |
| --- | --- |
| Keep Word as the content source of truth | The author can continue editing in Word. Markdown, extracted images, and navigation are generated outputs, not a second independently maintained edition. The converter does not write changes back to Word. |
| One page per chapter, plus home and Resources/Appendices | Matches the guide's organization without a long single-page site. Current structure checks require six chapters and Resources. |
| Generate chapter contents, previous/next links, and sidebar | Navigation stays aligned with recognized Word headings. Do not hand-edit `docs/_data/navigation.json`. |
| Keep guide tables and offer separate worksheet downloads | Readers retain the examples while receiving editable planning tools. Table-header mappings make worksheet association explicit. |
| Use native GitHub-flavored Markdown | Pages remain readable in the repository as well as on the website. Merged cells and multiline cell layout are simplified; Word-only underlining is removed. Complex new tables may require converter work. |
| Use `.md` links and automatic heading IDs | Repository links work without a site build; Jekyll's relative-link plugin rewrites them for the published site. Heading changes can change public anchors. |
| Link guide references, not every mention of a chapter/appendix | References describing students' own reports are not necessarily destinations in this guide. Specific phrases and three stale source references have explicit conversion rules, described above. |
| Keep site presentation outside chapter content | Cover-inspired colors, responsive navigation, worksheet download behavior, and light/dark mode live in the shared layout/CSS/JavaScript. The author chose the cover palette over the initial WPI branding. No licensed fonts or recreated WPI logos are distributed. |
| Automatically regenerate and publish from `main` | Initially conversion was local; the workflow now converts Word, validates, commits generated output, and deploys in one run. The repository's Markdown stays in sync with the site. Local Python/Pandoc and Ruby are optional preview tools. |

The conversion-time reference corrections do not modify the original Word
document. If those passages are corrected in Word later, review the matching
converter rules and fidelity-test expectations together.

## Local preview

With Ruby and Bundler installed:

```powershell
Set-Location docs
bundle install
bundle exec jekyll serve --baseurl /iqp
```

Open <http://localhost:4000/iqp/>. GitHub Actions builds the site without
requiring Ruby on your own machine.

To check a Jekyll build against the Markdown pages (including every local page,
section, image, worksheet link, and sidebar anchor):

```powershell
$env:BUNDLE_GEMFILE = (Resolve-Path docs\Gemfile).Path
bundle exec jekyll build --source docs --destination docs\_site
$env:IQP_SITE_BUILD = (Resolve-Path docs\_site).Path
python -m unittest discover -s scripts -p "test_*.py"
```
