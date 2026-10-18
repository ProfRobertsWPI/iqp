const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const { test } = require("node:test");
const vm = require("node:vm");

const source = fs.readFileSync(path.join(__dirname, "..", "docs", "assets", "theme.js"), "utf8");

function setup({ saved = null, dark = false, query = "", blocked = false } = {}) {
  const root = new Map();
  const attributes = new Map();
  const handlers = {};
  const storage = new Map(saved === null ? [] : [["iqp-color-theme", saved]]);
  const warnings = [];
  const toggle = {
    hidden: true,
    setAttribute: (key, value) => attributes.set(key, value),
    addEventListener: (name, callback) => { handlers[name] = callback; },
  };
  const window = {
    location: { search: query, href: "https://example.test/iqp/chapter-02.html" + query },
    matchMedia: () => ({
      matches: dark,
      addEventListener: (name, callback) => { handlers.system = callback; },
    }),
    localStorage: {
      getItem(key) {
        if (blocked) throw new Error("Storage denied");
        return storage.get(key) ?? null;
      },
      setItem(key, value) {
        if (blocked) throw new Error("Storage denied");
        storage.set(key, value);
      },
    },
    history: {
      replaceState(_state, _unused, url) {
        window.location.search = url.search;
        window.location.href = url.href;
      },
    },
  };
  vm.runInNewContext(source, {
    window,
    URL,
    URLSearchParams,
    document: {
      documentElement: {
        setAttribute: (key, value) => root.set(key, value),
        getAttribute: key => root.get(key),
      },
      querySelector: () => toggle,
      addEventListener: (name, callback) => { handlers[name] = callback; },
    },
    console: { warn: (...args) => warnings.push(args) },
  });
  const initial = root.get("data-theme");
  handlers.DOMContentLoaded();
  return { root, attributes, handlers, storage, warnings, toggle, initial, window };
}

test("system theme is applied before the DOM loads and follows live changes", () => {
  const app = setup({ dark: true });
  assert.equal(app.initial, "dark");
  assert.equal(app.toggle.hidden, false);
  assert.equal(app.attributes.get("aria-pressed"), "true");
  app.handlers.system({ matches: false });
  assert.equal(app.root.get("data-theme"), "light");
  assert.equal(app.attributes.get("aria-pressed"), "false");
});

test("saved preferences override both initial and subsequent system changes", () => {
  const app = setup({ saved: "light", dark: true });
  assert.equal(app.initial, "light");
  app.handlers.system({ matches: true });
  assert.equal(app.root.get("data-theme"), "light");
});

test("toggle persists choice and updates its accessible state", () => {
  const app = setup();
  app.handlers.click();
  assert.equal(app.root.get("data-theme"), "dark");
  assert.equal(app.attributes.get("aria-pressed"), "true");
  assert.equal(app.storage.get("iqp-color-theme"), "dark");
  app.handlers.click();
  assert.equal(app.root.get("data-theme"), "light");
  assert.equal(app.attributes.get("aria-pressed"), "false");
  assert.equal(app.storage.get("iqp-color-theme"), "light");
});

test("explicit choice stops following system changes", () => {
  const app = setup({ dark: true });
  app.handlers.click();
  app.handlers.system({ matches: true });
  assert.equal(app.root.get("data-theme"), "light");
});

test("invalid stored and URL values do not become themes", () => {
  assert.equal(setup({ saved: "invalid", query: "?scoutTheme=invalid", dark: true }).initial, "dark");
  assert.equal(setup({ saved: "invalid" }).initial, "light");
});

test("URL theme accepts light and dark and updates when toggled", () => {
  for (const theme of ["light", "dark"]) {
    const app = setup({ saved: theme === "light" ? "dark" : "light", query: "?scoutTheme=" + theme });
    assert.equal(app.initial, theme);
    app.handlers.click();
    const next = theme === "light" ? "dark" : "light";
    assert.equal(app.window.location.search, "?scoutTheme=" + next);
    assert.equal(app.storage.get("iqp-color-theme"), next);
  }
});

test("blocked storage reports the issue without disabling the toggle", () => {
  const app = setup({ blocked: true });
  assert.equal(app.initial, "light");
  app.handlers.click();
  assert.equal(app.root.get("data-theme"), "dark");
  assert.equal(app.attributes.get("aria-pressed"), "true");
  assert.equal(app.warnings.length, 2);
});

test("layout loads theme before styles and provides a native accessible toggle", () => {
  const layout = fs.readFileSync(path.join(__dirname, "..", "docs", "_layouts", "default.html"), "utf8");
  assert.ok(layout.indexOf("/assets/theme.js") < layout.indexOf("/assets/site.css"));
  assert.match(layout, /<button class="theme-toggle" type="button" aria-pressed="false" hidden>/);
});
