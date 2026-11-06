const test = require("node:test");
const assert = require("node:assert/strict");
const ui = require("../app/scientific-asset-color-controls.js");

const regions = [
  { id: "cytoplasm", label: "Cytoplasm", default: "#7DD3C7" },
  { id: "nucleus", label: "Nucleus", default: "#B8B5FF" },
  { id: "outline", label: "Outline", default: "#26323D" }
];
const meta = { editableColorRegions: regions, colorOverrides: { nucleus: "#AA44CC" } };

test("Simple exposes named colors without per-part reset or specialist paint controls", () => {
  const markup = ui.render(meta, { prefix: "simple-asset", mode: "simple", paletteId: "pastel" });
  assert.match(markup, /data-scientific-asset-colors="simple"/);
  assert.match(markup, />Colors<\/strong>/);
  assert.match(markup, /value="pastel" selected>Pastel/);
  assert.equal((markup.match(/data-asset-color-region=/g) || []).length, 3);
  assert.equal((markup.match(/data-asset-colors-reset\b/g) || []).length, 1);
  assert.doesNotMatch(markup, /data-asset-color-reset=|>Fill<|>Stroke<|Original color|Edited from original/);
  assert.doesNotMatch(markup, /value="custom"|Your edited part colors/);
});

test("Every part has a visible associated label; prefixes keep two surfaces distinct", () => {
  const parts = [ui.render(meta, { prefix: "simple" }), ui.render(meta, { prefix: "advanced", mode: "advanced" })];
  const ids = [];
  for (const markup of parts) {
    ids.push(...[...markup.matchAll(/\bid="([^"]+)"/g)].map((match) => match[1]));
    const inputs = [...markup.matchAll(/<input type="color" id="([^"]+)"[^>]*aria-labelledby="([^"]+)"/g)];
    assert.equal(inputs.length, 3);
    for (const [, inputId, labelId] of inputs) {
      assert.match(markup, new RegExp(`<label[^>]*id="${labelId}" for="${inputId}">[^<]+</label>`));
    }
  }
  assert.equal(ids.length, new Set(ids).size);
  assert.equal((parts[1].match(/data-asset-color-reset=/g) || []).length, 3);
});

test("Advanced embeds palette and parts without duplicating its existing heading or reset button", () => {
  const markup = ui.render(meta, {
    prefix: "advanced-embedded", mode: "advanced", heading: false, resetAll: false, paletteId: "vivid"
  });
  assert.match(markup, /data-scientific-asset-colors="advanced" aria-label="Colors"/);
  assert.doesNotMatch(markup, /asset-color-header|>Colors<\/strong>|data-asset-colors-reset\b|advanced-embedded-heading/);
  assert.match(markup, /value="vivid" selected>Vivid/);
  assert.equal((markup.match(/data-asset-color-region=/g) || []).length, 3);
  assert.equal((markup.match(/data-asset-color-reset=/g) || []).length, 3);

  const headingOnly = ui.render(meta, { prefix: "heading-only", resetAll: false });
  assert.match(headingOnly, /aria-labelledby="heading-only-heading"/);
  assert.match(headingOnly, /<strong id="heading-only-heading">Colors<\/strong>/);
  assert.doesNotMatch(headingOnly, /data-asset-colors-reset\b/);
  const resetOnly = ui.render(meta, { prefix: "reset-only", heading: false });
  assert.match(resetOnly, /aria-label="Colors"/);
  assert.match(resetOnly, /data-asset-colors-reset\b/);
  assert.doesNotMatch(resetOnly, /reset-only-heading/);
});

test("Untrusted labels and malformed paints cannot inject markup or color values", () => {
  const markup = ui.render({ editableColorRegions: [
    { id: 'a" onfocus="bad', label: '<img src=x onerror=bad>&"', default: 'red" autofocus' },
    { id: "safe", label: "Medium", default: "#abcdef" }
  ], colorOverrides: { safe: "javascript:bad", 'a" onfocus="bad': "#12345678" } }, {
    prefix: 'bad" onclick="bad', palettes: [{ id: "original", name: '<svg onload="bad">' }]
  });
  assert.doesNotMatch(markup, /<img|<svg| onclick=| autofocus|value="javascript:|value="red/);
  assert.match(markup, /&lt;img src=x onerror=bad&gt;&amp;&quot;/);
  assert.match(markup, /value="#000000"/);
  assert.match(markup, /value="#ABCDEF"/);
  assert.equal((markup.match(/data-asset-color-region=/g) || []).length, 2);
});

test("Custom note requires real declared overrides while the base palette stays selected", () => {
  assert.match(ui.render(meta, { paletteId: "vivid", hasCustomColors: true }), /value="vivid" selected>Vivid/);
  assert.match(ui.render(meta, { paletteId: "vivid", hasCustomColors: true }), /Your edited part colors are kept\./);
  assert.doesNotMatch(ui.render({ editableColorRegions: regions, colorOverrides: { unrelated: "#123456" } }, {
    hasCustomColors: true, palettes: [{ id: "custom", name: "Custom" }]
  }), /Your edited part colors|value="custom"/);
  assert.doesNotMatch(ui.render(meta, { overrides: {}, hasCustomColors: true }), /Your edited part colors/);
});

test("Locked assets keep their labeled controls visible and disable all actions", () => {
  const markup = ui.render(meta, { prefix: "locked", locked: true, mode: "advanced", disabledReason: 'Unlock this asset to edit "part colors".' });
  const controls = [...markup.matchAll(/<(?:select|input|button)\b[^>]*>/g)].map((match) => match[0]);
  assert.equal(controls.length, 8);
  assert.ok(controls.every((control) => /\bdisabled\b/.test(control)));
  assert.match(markup, /title="Unlock this asset to edit &quot;part colors&quot;\."/);
  assert.equal(ui.render(null), "");
});

test("Palette-only colors enable the palette reset while every part reset stays disabled", () => {
  for (const overrides of [{}, { nucleus: "#CC4499", cytoplasm: "#11AABB" }]) {
    const markup = ui.render({ editableColorRegions: regions }, {
      mode: "advanced", paletteId: "pastel", overrides, customOverrides: {}, hasCustomColors: true
    });
    const resetAll = markup.match(/<button\b[^>]*data-asset-colors-reset\b[^>]*>/)[0];
    assert.doesNotMatch(resetAll, /\bdisabled\b/);
    assert.match(resetAll, /title="Reset palette and part colors; keep individual component edits"/);
    const partResets = [...markup.matchAll(/<button\b[^>]*data-asset-color-reset=[^>]*>/g)].map((match) => match[0]);
    assert.equal(partResets.length, 3);
    assert.ok(partResets.every((button) => /\bdisabled\b/.test(button)));
    assert.doesNotMatch(markup, /Your edited part colors/);
  }
  const original = ui.render({ editableColorRegions: regions }, { paletteId: "original", overrides: {}, customOverrides: {} });
  assert.match(original, /<button\b[^>]*data-asset-colors-reset\b[^>]* disabled>/);
});

test("Part reset and edited-colors hint use only valid declared custom overrides", () => {
  const paletteMeta = {
    editableColorRegions: regions, colorOverrides: { nucleus: "#CC4499", cytoplasm: "#11AABB" },
    customColorOverrides: { nucleus: "#AA44CC", unrelated: "#123456", cytoplasm: "red" }
  };
  const markup = ui.render(paletteMeta, { mode: "advanced", paletteId: "vivid", hasCustomColors: true });
  assert.match(markup, /Your edited part colors are kept\./);
  assert.doesNotMatch(markup.match(/<button\b[^>]*data-asset-color-reset="nucleus"[^>]*>/)[0], /\bdisabled\b/);
  assert.match(markup, /data-asset-color-reset="cytoplasm"[^>]* disabled>/);
  assert.match(markup, /data-asset-color-reset="outline"[^>]* disabled>/);
  const explicitEmpty = ui.render(paletteMeta, { mode: "advanced", customOverrides: {}, hasCustomColors: true });
  assert.doesNotMatch(explicitEmpty, /Your edited part colors/);
  assert.ok([...explicitEmpty.matchAll(/<button\b[^>]*data-asset-color-reset=[^>]*>/g)].every((match) => /\bdisabled\b/.test(match[0])));
  const metadataEmpty = ui.render({ ...paletteMeta, customColorOverrides: {} }, { mode: "advanced", hasCustomColors: true });
  assert.doesNotMatch(metadataEmpty, /Your edited part colors/);
});

// EventTarget exercises real listener addition/removal. The small target shim
// supplies DOM containment/closest facts; the app browser gate checks actual DOM.
function fixture() {
  const surface = new EventTarget();
  const children = new Set();
  surface.contains = (control) => children.has(control);
  const target = (selector, attributes = {}) => {
    const control = { disabled: false, dataset: {}, ...attributes };
    control.closest = (query) => query === selector ? control : null;
    children.add(control);
    return control;
  };
  const fire = (type, target) => {
    const event = new Event(type, { cancelable: true });
    Object.defineProperty(event, "target", { value: target });
    surface.dispatchEvent(event);
    return event;
  };
  return { surface, target, fire, children };
}

test("Delegated handlers deliver one committed change, reject invalid/disabled/foreign controls", () => {
  const f = fixture(), calls = [];
  ui.bind(f.surface, {
    onPalette: (id) => calls.push(["palette", id]),
    onPartColor: (id, color) => calls.push(["part", id, color]),
    onResetAll: () => calls.push(["reset-all"]),
    onResetPart: (id) => calls.push(["reset-part", id])
  });
  const palette = f.target("select[data-asset-palette]", { value: "pastel", options: [{ value: "pastel" }] });
  const color = f.target('input[type="color"][data-asset-color-region]', { value: "#abcDEF", dataset: { assetColorRegion: "nucleus" } });
  f.fire("input", color);
  assert.deepEqual(calls, []);
  f.fire("change", palette);
  f.fire("change", color);
  color.value = "red";
  f.fire("change", color);
  palette.value = "unexpected";
  f.fire("change", palette);
  color.value = "#123456"; color.disabled = true;
  f.fire("change", color);
  color.disabled = false; f.children.delete(color);
  f.fire("change", color);
  const resetAll = f.target("button[data-asset-colors-reset]");
  const resetPart = f.target("button[data-asset-color-reset]", { dataset: { assetColorReset: "nucleus" } });
  assert.equal(f.fire("click", resetAll).defaultPrevented, true);
  assert.equal(f.fire("click", resetPart).defaultPrevented, true);
  assert.deepEqual(calls, [["palette", "pastel"], ["part", "nucleus", "#ABCDEF"], ["reset-all"], ["reset-part", "nucleus"]]);
});

test("Rebinding and stale cleanup cannot leave duplicate or orphaned handlers", () => {
  const f = fixture(), old = [], current = [];
  const control = f.target('input[type="color"][data-asset-color-region]', { value: "#123456", dataset: { assetColorRegion: "cytoplasm" } });
  const cleanOld = ui.bind(f.surface, { onPartColor: (id) => old.push(id) });
  const cleanCurrent = ui.bind(f.surface, { onPartColor: (id) => current.push(id) });
  cleanOld(); cleanOld();
  f.fire("change", control);
  assert.deepEqual(old, []);
  assert.deepEqual(current, ["cytoplasm"]);
  cleanCurrent(); cleanCurrent();
  f.fire("change", control);
  assert.equal(current.length, 1);
});

test("Optional live part input is independent from committed changes and cleans up on rebind", () => {
  const f = fixture(), live = [], committed = [];
  const input = f.target('input[type="color"][data-asset-color-region]', {
    value: "#aBcDef", dataset: { assetColorRegion: "nucleus" }
  });
  const cleanup = ui.bind(f.surface, {
    onPartColorInput: (id, color) => live.push([id, color]),
    onPartColor: (id, color) => committed.push([id, color])
  });
  f.fire("input", input);
  assert.deepEqual(live, [["nucleus", "#ABCDEF"]]);
  assert.deepEqual(committed, []);
  f.fire("change", input);
  assert.deepEqual(committed, [["nucleus", "#ABCDEF"]]);
  for (const value of ["red", "#12345678", "#12345"]) {
    input.value = value; f.fire("input", input);
  }
  input.value = "#123456"; input.disabled = true; f.fire("input", input);
  input.disabled = false; f.children.delete(input); f.fire("input", input);
  assert.equal(live.length, 1);
  f.children.add(input);
  ui.bind(f.surface, { onPartColor: () => {} });
  cleanup();
  f.fire("input", input);
  assert.equal(live.length, 1);
});
