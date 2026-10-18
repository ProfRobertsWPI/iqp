/* Search stays in the reader's browser; no query is sent to a service. */
(() => {
  function searchPages(pages, query) {
    const terms = [...new Set(query.toLocaleLowerCase().trim().split(/\s+/).filter(Boolean))];
    if (!terms.length) return [];
    return pages.map(page => {
      const title = page.title.toLocaleLowerCase();
      const text = page.text.toLocaleLowerCase();
      if (!terms.every(term => title.includes(term) || text.includes(term))) return null;
      const score = terms.reduce((total, term) => total + (title.includes(term) ? 10 : 1), 0);
      const position = Math.max(0, text.indexOf(terms[0]));
      const start = Math.max(0, position - 60);
      const excerpt = (start ? "..." : "") + page.text.slice(start, start + 200) +
        (start + 200 < page.text.length ? "..." : "");
      return { ...page, score, excerpt };
    }).filter(Boolean).sort((a, b) => b.score - a.score || a.title.localeCompare(b.title));
  }

  if (typeof module !== "undefined" && module.exports) {
    module.exports = { searchPages };
  }
  if (typeof document === "undefined") return;
  const search = document.querySelector(".guide-search");
  if (!search) return;
  const input = search.querySelector("input");
  const output = search.querySelector(".search-output");
  const status = search.querySelector(".search-status");
  const results = search.querySelector(".search-results");
  const close = search.querySelector(".search-close");
  let index;
  let revision = 0;

  function dismiss() {
    revision += 1;
    output.hidden = true;
    close.hidden = true;
    input.setAttribute("aria-expanded", "false");
  }

  async function update() {
    const current = ++revision;
    const query = input.value.trim();
    results.replaceChildren();
    if (!query) {
      dismiss();
      return;
    }
    output.hidden = false;
    close.hidden = false;
    input.setAttribute("aria-expanded", "true");
    status.textContent = "Searching...";
    try {
      if (!index) {
        index = fetch(search.dataset.indexUrl).then(response => {
          if (!response.ok) throw new Error(`Search index returned ${response.status}`);
          return response.json();
        }).then(pages => {
          if (!Array.isArray(pages) || !pages.length || pages.some(page =>
            typeof page.title !== "string" || typeof page.text !== "string" ||
            typeof page.url !== "string" ||
            new URL(page.url, window.location.href).origin !== window.location.origin
          )) throw new Error("Invalid search index");
          return pages;
        });
      }
      const pages = await index;
      if (current !== revision) return;
      const matches = searchPages(pages, query);
      status.textContent = matches.length ?
        `${matches.length} ${matches.length === 1 ? "page" : "pages"} found. Tab to a result to open it.` :
        "No matching pages. Try a different word or fewer words.";
      for (const match of matches) {
        const item = document.createElement("li");
        const link = document.createElement("a");
        link.href = match.url;
        const title = document.createElement("strong");
        title.textContent = match.title;
        const excerpt = document.createElement("span");
        excerpt.textContent = match.excerpt;
        link.append(title, excerpt);
        item.append(link);
        results.append(item);
      }
    } catch (error) {
      index = undefined;
      console.error("Guide search failed:", error);
      if (current !== revision) return;
      status.textContent = "Search is unavailable. Please use the chapter navigation or try again.";
    }
  }

  search.hidden = false;
  input.addEventListener("input", update);
  input.addEventListener("focus", () => { if (input.value.trim()) update(); });
  close.addEventListener("click", () => { input.focus(); dismiss(); });
  search.addEventListener("keydown", event => {
    if (event.key === "Escape") {
      input.focus();
      dismiss();
    }
  });
  document.addEventListener("click", event => {
    if (!search.contains(event.target)) dismiss();
  });
  search.addEventListener("focusout", event => {
    if (!search.contains(event.relatedTarget)) dismiss();
  });
})();
