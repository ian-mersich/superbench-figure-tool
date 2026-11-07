import assert from "node:assert/strict";
import { createRequire } from "node:module";
import { readFile, stat } from "node:fs/promises";
import test from "node:test";

const require = createRequire(import.meta.url);
const helpApi = require("../app/help/figure-studio-help-center.js");
const payload = JSON.parse(await readFile(new URL("../app/help/figure-studio-help.json", import.meta.url), "utf8"));
const version = JSON.parse(await readFile(new URL("../package.json", import.meta.url), "utf8")).version;
const help = helpApi.normalizeHelpCatalog(payload);

function tocIds(nodes) { return nodes.flatMap(node => [...node.articles, ...tocIds(node.children)]); }

test("Current Help keeps every topic once in a valid table of contents", () => {
  assert.equal(payload.version, version);
  assert.equal(help.articles.length, 35);
  assert.equal(new Set(help.articles.map(article => article.id)).size, 35);
  assert.deepEqual(new Set(tocIds(help.toc)), new Set(help.articles.map(article => article.id)));
  assert.equal(tocIds(help.toc).length, 35);
  for (const article of help.articles) {
    assert.ok(article.title && article.summary && article.blocks.length, article.id);
    for (const id of article.related) assert.ok(help.byId[id], `${article.id} related ${id}`);
    assert.match(article.updated, /^\d{4}-\d{2}-\d{2}$/);
    assert.equal(new Date(article.updated).toISOString().slice(0, 10), article.updated);
    assert.ok(article.updated <= payload.updated, `${article.id} is newer than the catalog date`);
  }
});

test("Context and feature coverage routes reference current articles", () => {
  for (const [area, id] of Object.entries(payload.context_routes)) assert.ok(help.byId[id], area);
  for (const [area, id] of Object.entries(payload.coverage)) assert.ok(help.byId[id], area);
  for (const area of ["save", "recovery", "figure-export", "presentation-export", "direct-selection", "paths-pen-nodes", "help-navigation", "limits"]) assert.ok(help.byId[help.coverage[area]], area);
  assert.equal(helpApi.resolveHelpContext(help, "tools.lines").id, "lines-arrows");
  assert.equal(helpApi.resolveHelpContext(help, "unknown-context").id, "getting-started");
});

test("Search finds visible task labels and all query terms", () => {
  for (const [query, id] of [["lines arrows", "lines-arrows"], ["PPTX", "pptx-compatibility"], ["Direct Selection", "paths-vectors"], ["Browser files", "save-save-as"]]) assert.ok(helpApi.searchHelpCatalog(help, query).some(article => article.id === id), query);
  assert.equal(helpApi.searchHelpCatalog(help, "unfindable-word-932111").length, 0);
  assert.equal(helpApi.searchHelpCatalog(help, "", {limit: 2}).length, 2);
  assert.deepEqual(helpApi.searchHelpCatalog(help, "", {articleIds: ["lines-arrows"]}).map(article => article.id), ["lines-arrows"]);
});

test("Deep links round trip and malformed percent escapes cannot break Help", () => {
  assert.deepEqual(helpApi.parseHelpDeepLink(helpApi.getHelpDeepLink("lines-arrows")), {id:"lines-arrows", slug:"lines-arrows"});
  assert.equal(helpApi.parseHelpDeepLink("#help/%oops"), null);
  assert.equal(helpApi.parseTutorialDeepLink("#tutorial/%oops"), null);
  assert.equal(helpApi.parseHelpDeepLink("#not-help/a"), null);
  assert.equal(helpApi.parseHelpDeepLink("https://example.test/app/#help/saving-recovery").id, "saving-recovery");
});

test("Retired course aliases lead only to existing reference articles", () => {
  for (const id of ["FIG-00", "FIG-01", "FIG-02", "FIG-03", "FIG-04", "FIG-05", "PRES-01", "PRES-02", "PRES-03", "SAFE-01", "first-figure", "pptx-interchange"]) assert.ok(help.byId[helpApi.retiredTopicAlias(id)], id);
  assert.equal(helpApi.retiredTopicAlias("unknown-course"), "getting-started");
  assert.equal(helpApi.normalizeTutorialCatalog, undefined);
  assert.equal(helpApi.normalizeTutorialProgress, undefined);
  assert.equal(payload.shared_help.tutorial_execution_enabled, false);
  assert.equal(payload.shared_help.document_mutation_enabled, false);
  assert.equal(payload.learn_routes, undefined);
});

test("Help loads its catalog alone and never touches stored course progress", async () => {
  const priorDocument = globalThis.document;
  globalThis.document = {addEventListener(){}, removeEventListener(){}};
  const requested = [];
  try {
    const controller = helpApi.create({
      fetch: async url => { requested.push(url); return {ok:true, json:async () => payload}; },
      storage: {getItem(){throw Error("Storage must stay untouched");}, setItem(){throw Error("Storage must stay untouched");}},
      listenForDeepLinks:false, openDeepLinkOnCreate:false
    });
    await Promise.all([controller.load(), controller.load()]);
    assert.deepEqual(requested, ["app/help/figure-studio-help.json"]);
    assert.equal(controller.getState().tutorialCount, 0);
    assert.equal(controller.getState().view, "help");
    controller.destroy();
  } finally { globalThis.document = priorDocument; }
});

test("An unavailable Help catalog can be retried without recreating the editor", async () => {
  const priorDocument = globalThis.document;
  globalThis.document = {addEventListener(){}, removeEventListener(){}};
  let attempts = 0;
  try {
    const controller = helpApi.create({fetch: async () => (++attempts === 1 ? {ok:false,status:503} : {ok:true,json:async () => payload}), listenForDeepLinks:false, openDeepLinkOnCreate:false});
    await assert.rejects(controller.load(), /503/);
    await controller.load();
    assert.equal(controller.getState().articleCount, 35);
    assert.equal(attempts, 2);
    controller.destroy();
  } finally { globalThis.document = priorDocument; }
});

test("Article rendering escapes prose, captions, and attribute markup", () => {
  assert.equal(helpApi.renderHelpBlock({type:"paragraph",text:"<script>bad()</script>"}), "<p>&lt;script&gt;bad()&lt;/script&gt;</p>");
  const image = helpApi.renderHelpBlock({type:"image",src:"media/sample.png",alt:'\" onerror=\"bad()',caption:"<img>"});
  assert.ok(image.includes("&quot; onerror=&quot;bad()"));
  assert.ok(image.includes("&lt;img&gt;"));
});

test("Media loads only packaged paths and never accepts remote or executable URLs", () => {
  for (const src of ["https://example.test/tracker.png", "//example.test/tracker.png", "javascript:bad()", "media/../secret.png", "media/x.svg", "media/x.png?token=a", "media/x.png#fragment"]) {
    assert.equal(helpApi.helpMediaPath(src), "", src);
    assert.equal(helpApi.renderHelpBlock({type:"image",src}), "", src);
  }
  assert.equal(helpApi.helpMediaPath("media/lines-picker.png"), "media/lines-picker.png");
});

test("Silent clips have native playback controls and no automatic motion", () => {
  const video = helpApi.renderHelpBlock({type:"video",src:"media/demo.webm",poster:"media/demo.png",alt:"Draw a line",caption:"Drag across the artboard."}, {mediaUrl:path => `/nested/app/help/${path}`});
  assert.match(video, /controls playsinline preload="none"/);
  assert.match(video, /poster="\/nested\/app\/help\/media\/demo.png"/);
  assert.doesNotMatch(video, /autoplay|loop/);
  assert.match(video, /Drag across the artboard/);
});

test("Every published media block has a local file and a written explanation", async () => {
  const media = help.articles.flatMap(article => article.blocks.filter(block => ["image","video"].includes(block.type)));
  assert.ok(media.length >= 5, "real instructional media must accompany current tasks");
  for (const block of media) {
    assert.ok(block.alt && block.caption, block.src);
    assert.ok(helpApi.helpMediaPath(block.src), block.src);
    assert.ok((await stat(new URL(`../app/help/${block.src}`, import.meta.url))).size > 0, block.src);
    if (block.type === "video") assert.ok((await stat(new URL(`../app/help/${block.poster}`, import.meta.url))).size > 0, block.poster);
  }
});
