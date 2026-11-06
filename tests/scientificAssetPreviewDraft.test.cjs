const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");
const controls = require("../app/scientific-asset-color-controls.js");
const source = fs.readFileSync(require.resolve("../app/scientific-asset-preview.js"), "utf8");
const plain = (value) => JSON.parse(JSON.stringify(value));
const tick = () => new Promise((resolve) => setImmediate(resolve));
const deferred = () => {
  let resolve, reject;
  const promise = new Promise((yes, no) => { resolve = yes; reject = no; });
  return { promise, resolve, reject };
};

// EventTarget supplies real listener cleanup. This finite DOM shim parses only
// the color module's markup; browser QA owns layout, image decoding and focus UI.
class Element extends EventTarget {
  constructor(tag, document) {
    super(); this.tagName = tag.toUpperCase(); this.document = document;
    this.children = []; this.attributes = {}; this.dataset = {}; this.style = {};
    this.disabled = false; this.hidden = false; this.checked = false;
    this.value = ""; this.src = ""; this.textContent = ""; this.isConnected = true;
    this.rebuilds = 0;
  }
  setAttribute(name, value) {
    this.attributes[name] = String(value);
    if (name === "id") this.id = String(value);
    if (name === "class") this.className = String(value);
    if (name === "value") this.value = String(value);
    if (name === "disabled") this.disabled = true;
    if (name === "selected") this.selected = true;
    if (name.startsWith("data-")) this.dataset[name.slice(5).replace(/-([a-z])/g, (_, c) => c.toUpperCase())] = String(value);
  }
  getAttribute(name) { return name === "id" ? this.id : this.attributes[name]; }
  removeAttribute(name) { delete this.attributes[name]; if (name === "src") this.src = ""; }
  append(...nodes) { for (const n of nodes) { n.parentElement = this; this.children.push(n); } }
  replaceChildren(...nodes) { for (const n of this.children) n.parentElement = null; this.children = []; this.append(...nodes); }
  contains(node) { return node === this || this.children.some((n) => n.contains(node)); }
  matches(query) {
    return query.split(",").some((part) => {
      let q = part.trim();
      if (q.includes(":not(:disabled)")) { if (this.disabled) return false; q = q.replace(":not(:disabled)", ""); }
      const tag = q.match(/^[a-z]+/i)?.[0];
      if (tag && tag.toUpperCase() !== this.tagName) return false;
      const klass = q.match(/^\.([\w-]+)/)?.[1];
      if (klass && !(this.className || "").split(/\s+/).includes(klass)) return false;
      for (const [, name, value] of q.matchAll(/\[([\w-]+)(?:="([^"]*)")?\]/g)) {
        const found = this.getAttribute(name);
        if (found == null || value !== undefined && found !== value) return false;
      }
      return true;
    });
  }
  closest(query) { for (let n = this; n; n = n.parentElement) if (n.matches(query)) return n; return null; }
  querySelectorAll(query) {
    const descendants = this.children.flatMap((n) => [n, ...n.querySelectorAll("*")]);
    return query === "*" ? descendants : descendants.filter((n) => n.matches(query));
  }
  querySelector(query) { return this.querySelectorAll(query)[0] || null; }
  get options() { return this.children.filter((n) => n.tagName === "OPTION"); }
  focus() { this.document.activeElement = this; }
  getClientRects() { return this.hidden ? [] : [{}]; }
  showModal() { this.open = true; }
  close() { this.open = false; this.dispatchEvent(new Event("close")); }
  set innerHTML(markup) {
    this.rebuilds += 1; this.replaceChildren(); const stack = [this];
    for (const token of markup.matchAll(/<\/?[a-z][^>]*>/gi)) {
      const text = token[0];
      if (text.startsWith("</")) { stack.pop(); continue; }
      const tag = text.match(/^<([a-z]+)/i)[1]; const node = this.document.createElement(tag);
      for (const [, name, value] of text.slice(tag.length + 1, -1).matchAll(/([\w-]+)(?:="([^"]*)")?/g)) node.setAttribute(name, value ?? "");
      stack.at(-1).append(node);
      if (tag === "option" && node.selected) stack.at(-1).value = node.value;
      if (!["input", "img", "br"].includes(tag)) stack.push(node);
    }
  }
}

function fire(surface, type, target = surface, props = {}) {
  const event = new Event(type, { cancelable: true });
  Object.defineProperty(event, "target", { value: target });
  Object.assign(event, props); surface.dispatchEvent(event); return event;
}
const regions = [
  { id: "body", label: "Cell body", default: "#AABBCC" },
  { id: "nucleus", label: "Nucleus", default: "#DDEEFF" }
];
const palettes = [{ id: "original", name: "Original" }, { id: "pastel", name: "Pastel" }];
function preview(asset, draft) {
  const paletteOverrides = draft.paletteId === "pastel" ? { body: "#112233", nucleus: "#445566" } : {};
  return {
    svgText: `<svg data-asset="${asset.id}" data-palette="${draft.paletteId}" data-body="${draft.customColorOverrides.body || paletteOverrides.body || regions[0].default}"/>`,
    regions, paletteOverrides, colorOverrides: { ...paletteOverrides, ...draft.customColorOverrides },
    appearanceLabel: `${asset.id} / ${draft.paletteId}`
  };
}

function fixture(options = {}) {
  const ids = new Map();
  const document = {
    activeElement: null,
    getElementById: (id) => ids.get(id),
    querySelectorAll: () => [],
    createElement: (tag) => new Element(tag, document)
  };
  const suffixes = ["Dialog", "Title", "CloseBtn", "VariantSelect", "Image", "Appearance", "Description", "Limitations", "PartsHeading", "Parts", "EditHint", "Status", "ReplacementNote", "InsertBtn", "ReplaceSelectedBtn", "Eyebrow", "SearchField", "SearchInput", "ScopeField", "ScopeLabel", "IncludeCopies", "EditedField", "AllowEdited"];
  const els = {};
  for (const suffix of suffixes) {
    const tag = suffix === "Dialog" ? "dialog" : suffix === "Parts" ? options.partsTag || "div" : suffix.endsWith("Btn") ? "button" : suffix.endsWith("Select") ? "select" : suffix === "Image" ? "img" : suffix.endsWith("Input") || ["IncludeCopies", "AllowEdited"].includes(suffix) ? "input" : "div";
    const node = document.createElement(tag); node.id = "assetPreview" + suffix; ids.set(node.id, node); els[suffix] = node;
    if (suffix !== "Dialog") els.Dialog.append(node);
  }
  const origin = document.createElement("button"); origin.focus();
  const assets = new Map(["a", "b"].map((id) => [id, { id, name: "Drawing " + id, editable_color_regions: regions }]));
  const actions = []; const previews = []; let context = "document:page"; let closes = 0;
  els.Image.decode = options.decode || (() => Promise.resolve());
  const callbacks = {
    getAsset: (id) => assets.get(id), getVariants: () => [...assets.values()], getChoices: () => [...assets.values()],
    contextId: () => context, onCloseChange: () => { closes += 1; },
    loadPreview: (a) => preview(a, { paletteId: "original", customColorOverrides: {} }),
    onAction: (action, id, data) => { actions.push([action, id, plain(data)]); return true; },
    ...options.callbacks
  };
  if (options.draft !== false) {
    callbacks.createDraft ||= (a) => ({ assetId: a.id, artStyle: "soft-color", paletteId: "original", customColorOverrides: {} });
    callbacks.getPreview ||= (a, draft) => { previews.push(plain(draft)); return preview(a, draft); };
  }
  const contextObject = {
    document, module: { exports: {} }, getComputedStyle: () => ({ visibility: "visible" }),
    FigureStudioScientificAssetColorControls: controls,
    FigureStudioScientificAssetPalettes: { getPalettes: () => palettes }
  };
  vm.runInNewContext(source, contextObject);
  const api = contextObject.module.exports.create(callbacks);
  return { api, els, document, origin, assets, actions, previews, callbacks, state: () => plain(api.getState()),
    input: (id) => els.Parts.querySelector(`input[type="color"][data-asset-color-region="${id}"]`),
    part: (id, color, type = "input") => { const input = els.Parts.querySelector(`input[type="color"][data-asset-color-region="${id}"]`); input.value = color; fire(els.Parts, type, input); return input; },
    context: (value) => { context = value; }, closes: () => closes };
}

test("Legacy callbacks retain readonly UL/DIV rows, state and action options", async () => {
  for (const tag of ["ul", "div"]) {
    let argc;
    const f = fixture({ draft: false, partsTag: tag, callbacks: { loadPreview: function (a) { argc = arguments.length; return preview(a, { paletteId: "original", customColorOverrides: {} }); } } });
    assert.equal(await f.api.open("a", f.origin), true);
    assert.equal(argc, 1);
    assert.equal("draft" in f.state(), false);
    assert.equal(f.els.Parts.children[0].tagName, tag === "ul" ? "LI" : "DIV");
    fire(f.els.InsertBtn, "click"); await tick();
    assert.deepEqual(f.actions, [["insert", "a", { includeCopies: false, allowEdited: false }]]);
  }
});

test("Draft creation, preview, replacement and QA receive independent clones", async () => {
  const initial = { assetId: "a", artStyle: "soft-color", paletteId: "pastel", customColorOverrides: { body: "#aa44cc" } };
  const f = fixture({ callbacks: {
    createDraft: () => initial,
    getPreview: (a, draft) => { const value = preview(a, draft); draft.customColorOverrides.body = "#000000"; return value; },
    replacementInfo: (_a, draft) => { if (draft) draft.customColorOverrides.body = "#FFFFFF"; return {}; }
  } });
  await f.api.open("a", f.origin);
  initial.customColorOverrides.body = "#123456";
  const exposed = f.api.getState(); exposed.draft.customColorOverrides.body = "#112233";
  assert.equal(f.state().draft.customColorOverrides.body, "#AA44CC");
  assert.equal(f.state().displayedDraft.customColorOverrides.body, "#AA44CC");
  fire(f.els.InsertBtn, "click"); await tick();
  assert.equal(f.actions[0][2].appearanceDraft.customColorOverrides.body, "#AA44CC");
});

test("Live picker preserves its node/focus and commits only latest decoded image", async () => {
  const pending = [];
  const f = fixture({ callbacks: { getPreview: (a, draft) => {
    if (!draft.customColorOverrides.body) return preview(a, draft);
    const gate = deferred(); pending.push({ ...gate, a, draft: plain(draft) }); return gate.promise;
  } } });
  await f.api.open("a", f.origin);
  const input = f.input("body"); input.focus(); const rebuilds = f.els.Parts.rebuilds;
  f.part("body", "#FF0000"); f.part("body", "#00FF00");
  f.part("body", "#00FF00", "change");
  assert.equal(pending.length, 2);
  assert.equal(f.els.InsertBtn.disabled, true);
  fire(f.els.InsertBtn, "click"); await tick(); assert.equal(f.actions.length, 0);
  let value = input.value, writes = 0;
  Object.defineProperty(input, "value", { get: () => value, set: (next) => { value = next; writes += 1; } });
  pending[1].resolve(preview(pending[1].a, pending[1].draft)); await tick();
  assert.equal(f.els.InsertBtn.disabled, false);
  assert.equal(f.input("body"), input); assert.equal(f.document.activeElement, input);
  assert.equal(f.els.Parts.rebuilds, rebuilds);
  assert.equal(writes, 0);
  pending[0].resolve(preview(pending[0].a, pending[0].draft)); await tick();
  assert.equal(f.state().displayedDraft.customColorOverrides.body, "#00FF00");
  assert.match(decodeURIComponent(f.els.Image.src), /#00FF00/);
  fire(f.els.InsertBtn, "click"); await tick();
  assert.equal(f.actions[0][2].appearanceDraft.customColorOverrides.body, "#00FF00");
});

test("Image decode remains a commit gate after preview generation completes", async () => {
  let gate = null;
  const f = fixture({ decode: () => gate ? gate.promise : Promise.resolve() });
  await f.api.open("a", f.origin); gate = deferred();
  f.part("body", "#123456"); await tick();
  assert.equal(f.state().loading, true); assert.equal(f.els.InsertBtn.disabled, true);
  assert.deepEqual(f.state().displayedDraft.customColorOverrides, {});
  gate.resolve(); await tick();
  assert.equal(f.state().displayedDraft.customColorOverrides.body, "#123456");
});

test("Palette retains custom colors; part reset, baseline choice and all reset normalize draft", async () => {
  const f = fixture(); await f.api.open("a", f.origin);
  const input = f.part("body", "#FF0000"); await tick();
  const palette = f.els.Parts.querySelector("select[data-asset-palette]");
  palette.value = "pastel"; fire(f.els.Parts, "change", palette); await tick();
  assert.equal(f.state().draft.paletteId, "pastel");
  assert.equal(f.state().draft.customColorOverrides.body, "#FF0000");
  assert.equal(f.input("body"), input);
  fire(f.els.Parts, "click", f.els.Parts.querySelector('button[data-asset-color-reset="body"]')); await tick();
  assert.deepEqual(f.state().draft.customColorOverrides, {}); assert.equal(input.value, "#112233");
  f.part("body", "#FF0000"); await tick(); f.part("body", "#112233"); await tick();
  assert.deepEqual(f.state().draft.customColorOverrides, {});
  fire(f.els.Parts, "click", f.els.Parts.querySelector("button[data-asset-colors-reset]")); await tick();
  assert.equal(f.state().draft.paletteId, "original"); assert.equal(input.value, "#AABBCC");
});

test("App alone decides draft carry on biological variant changes", async () => {
  const previous = [];
  const f = fixture({ callbacks: { createDraft: (a, options) => {
    previous.push(plain(options));
    return { assetId: a.id, artStyle: "soft-color", paletteId: "original", customColorOverrides: {} };
  } } });
  await f.api.open("a", f.origin); f.part("body", "#123456"); await tick();
  f.els.VariantSelect.value = "b"; fire(f.els.VariantSelect, "change"); await tick();
  assert.equal(previous[1].previousDraft.customColorOverrides.body, "#123456");
  assert.equal(f.state().draft.assetId, "b"); assert.deepEqual(f.state().draft.customColorOverrides, {});
});

test("Escape discards draft, unbinds controls and rejects a late preview without actions", async () => {
  const pending = deferred();
  const f = fixture({ callbacks: { getPreview: (a, draft) => draft.customColorOverrides.body ? pending.promise : preview(a, draft) } });
  await f.api.open("a", f.origin); const input = f.part("body", "#123456");
  fire(f.els.Dialog, "cancel");
  assert.equal(f.state().open, false); assert.equal(f.state().draft, null);
  assert.equal(f.state().displayedDraft, null); assert.equal(f.els.Parts.children.length, 0);
  assert.equal(f.document.activeElement, f.origin);
  fire(f.els.Parts, "input", input);
  pending.resolve(preview(f.assets.get("a"), { paletteId: "pastel", customColorOverrides: {} })); await tick();
  assert.equal(f.els.Image.src, ""); assert.deepEqual(f.actions, []);
  await f.api.open("a", f.origin); assert.deepEqual(f.state().draft.customColorOverrides, {});
});

test("Document context change closes and clears an in-flight draft", async () => {
  const gate = deferred();
  const f = fixture({ callbacks: { getPreview: () => gate.promise } });
  const opened = f.api.open("a", f.origin, { mode: "change" });
  f.context("other-document"); f.api.refresh();
  gate.resolve(preview(f.assets.get("a"), { paletteId: "original", customColorOverrides: {} }));
  assert.equal(await opened, false); assert.equal(f.state().open, false);
  assert.equal(f.state().draft, null); assert.equal(f.closes(), 1); assert.deepEqual(f.actions, []);
});

test("Apply label retains selection/edited guards and action receives exact appearance and flags", async () => {
  const action = deferred(); let info = { selectedCount: 1, otherCount: 1, selectedDisabled: true, edited: false, actionLabel: "Apply colors" };
  const f = fixture({ callbacks: {
    replacementInfo: () => info,
    onAction: (kind, id, data) => {
      f.actions.push([kind, id, plain(data)]);
      data.appearanceDraft.customColorOverrides.body = "#000000";
      return action.promise;
    }
  } });
  await f.api.open("a", f.origin, { mode: "change" });
  assert.equal(f.els.ReplaceSelectedBtn.textContent, "Apply colors"); assert.equal(f.els.ReplaceSelectedBtn.disabled, true);
  info = { ...info, selectedDisabled: false, edited: true }; f.api.refresh();
  assert.equal(f.els.ReplaceSelectedBtn.disabled, true);
  f.els.AllowEdited.checked = true; fire(f.els.AllowEdited, "change");
  f.els.IncludeCopies.checked = true; fire(f.els.IncludeCopies, "change");
  f.part("body", "#123456"); await tick();
  const expected = f.state().displayedDraft;
  fire(f.els.ReplaceSelectedBtn, "click"); await tick();
  assert.equal(f.els.Status.textContent, "Applying colors…"); assert.equal(f.els.Parts.inert, true);
  assert.equal(f.api.close(), false); f.part("body", "#FFFFFF");
  assert.deepEqual(f.actions, [["change", "a", { includeCopies: true, allowEdited: true, appearanceDraft: expected }]]);
  action.resolve(false); await tick(); assert.equal(f.state().busy, false); assert.equal(f.els.Parts.inert, false);
  assert.equal(f.state().displayedDraft.customColorOverrides.body, "#123456");
});

test("Decode failure leaves commit disabled and retry of the same draft can recover", async () => {
  let fail = false;
  const f = fixture({ decode: () => fail ? Promise.reject(new Error("decode")) : Promise.resolve() });
  await f.api.open("a", f.origin); fail = true; f.part("body", "#123456"); await tick();
  assert.equal(f.state().displayedDraft, null); assert.equal(f.els.InsertBtn.disabled, true);
  assert.equal(f.els.Image.src, "");
  fail = false; f.part("body", "#123456"); await tick();
  assert.equal(f.els.InsertBtn.disabled, false); assert.equal(f.state().displayedDraft.customColorOverrides.body, "#123456");
});

test("An enabled draft requires a draft-aware renderer and cannot silently use global legacy colors", async () => {
  let legacyCalls = 0;
  const f = fixture({ callbacks: { loadPreview: () => { legacyCalls += 1; return preview({}, { paletteId: "original", customColorOverrides: {} }); } } });
  f.callbacks.getPreview = undefined;
  assert.equal(await f.api.open("a", f.origin), false);
  assert.equal(legacyCalls, 0); assert.equal(f.els.InsertBtn.disabled, true);
  assert.equal(f.state().displayedDraft, null);
});
