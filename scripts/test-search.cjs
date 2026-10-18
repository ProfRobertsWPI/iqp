const assert = require("node:assert/strict");
const { test } = require("node:test");
const { searchPages } = require("../docs/assets/search.js");

const pages = [
  { title: "Chapter 2 - Research Story", url: "/iqp/chapter-02.html", text: "Plan interviews and triangulation with your team." },
  { title: "Chapter 3 - Findings", url: "/iqp/chapter-03.html", text: "Use the research story to communicate findings." },
];

test("search is case-insensitive and matches full chapter content", () => {
  assert.equal(searchPages(pages, "TRIANGULATION")[0].url, "/iqp/chapter-02.html");
});
test("multiple words must all match and title matches rank first", () => {
  assert.equal(searchPages(pages, "research story")[0].title, pages[0].title);
  assert.equal(searchPages(pages, "interviews findings").length, 0);
});
test("empty and unmatched queries return no results", () => {
  assert.deepEqual(searchPages(pages, "  "), []);
  assert.deepEqual(searchPages(pages, "zzzzzz"), []);
});
test("snippets include the match and stay bounded", () => {
  const text = "a".repeat(400) + "triangulation" + "b".repeat(400);
  const result = searchPages([{ ...pages[0], text }], "triangulation")[0];
  assert.ok(result.excerpt.includes("triangulation"));
  assert.ok(result.excerpt.length <= 206);
});
