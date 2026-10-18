(() => {
  const storageKey = "iqp-color-theme";
  const preference = window.matchMedia("(prefers-color-scheme: dark)");
  const validTheme = value => value === "light" || value === "dark";
  const queryTheme = new URLSearchParams(window.location.search).get("scoutTheme");
  let chosenTheme = validTheme(queryTheme) ? queryTheme : null;
  let toggle;

  if (!chosenTheme) {
    try {
      const savedTheme = window.localStorage.getItem(storageKey);
      chosenTheme = validTheme(savedTheme) ? savedTheme : null;
    } catch (error) {
      console.warn("Theme preference could not be read; using the system theme.", error);
    }
  }

  const applyTheme = theme => {
    document.documentElement.setAttribute("data-theme", theme);
    if (toggle) {
      toggle.setAttribute("aria-pressed", String(theme === "dark"));
    }
  };
  applyTheme(chosenTheme || (preference.matches ? "dark" : "light"));

  preference.addEventListener("change", event => {
    if (!chosenTheme) {
      applyTheme(event.matches ? "dark" : "light");
    }
  });

  document.addEventListener("DOMContentLoaded", () => {
    toggle = document.querySelector(".theme-toggle");
    toggle.hidden = false;
    applyTheme(document.documentElement.getAttribute("data-theme"));
    toggle.addEventListener("click", () => {
      chosenTheme = document.documentElement.getAttribute("data-theme") === "dark" ? "light" : "dark";
      applyTheme(chosenTheme);
      try {
        window.localStorage.setItem(storageKey, chosenTheme);
      } catch (error) {
        console.warn("Theme preference could not be saved; it applies to this page only.", error);
      }
      const url = new URL(window.location.href);
      if (url.searchParams.has("scoutTheme")) {
        url.searchParams.set("scoutTheme", chosenTheme);
        window.history.replaceState(null, "", url);
      }
    });
  });
})();
