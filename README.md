# IQP Writing Guide

The GitHub Pages edition of **IQP Writing Guide: From Proposal to Final Report**
is generated from `Prof Roberts_IQP Writing Guide_2026.docx`.

## Site structure

- `docs/index.md`: contents and the original author's note / AI disclosure.
- `docs/chapter-01.md` through `docs/chapter-06.md`: one page per chapter.
- `docs/resources.md`: resources and Appendices A-D.
- `docs/assets/media/`: the images embedded in the Word document.

Chapter pages include section contents and previous/next navigation. Tables,
lists, emphasis, hyperlinks, and images are retained. Complex tables use HTML
inside Markdown to preserve their structure. The printed table of contents and
its page numbers are replaced by web navigation. Inconsistent Word heading
levels are normalized for the web.

## Publish on GitHub Pages

1. Merge these files into `main`.
2. In the repository's **Settings > Pages**, select **GitHub Actions** as the
   build and deployment source.
3. The **Deploy writing guide to GitHub Pages** workflow publishes changes to
   `docs/` on `main`. If needed, start it manually from the **Actions** tab.

The expected address is <https://profrobertswpi.github.io/iqp/>.
If you change the repository name or use a custom domain, update `url` and
`baseurl` in `docs/_config.yml`.

## Update from Word

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

## Local preview

With Ruby and Bundler installed:

```powershell
Set-Location docs
bundle install
bundle exec jekyll serve --baseurl /iqp
```

Open <http://localhost:4000/iqp/>. GitHub Actions builds the site without
requiring Ruby on your own machine.
