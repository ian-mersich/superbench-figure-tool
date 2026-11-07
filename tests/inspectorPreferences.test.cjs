const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const { test } = require('node:test');

const root = process.env.FIGURE_UI_SOURCE_ROOT || path.resolve(__dirname, '..');
const app = fs.readFileSync(path.join(root, 'app/app.js'), 'utf8');
function source(name) {
  const start = app.indexOf(`  function ${name}(`);
  assert.ok(start >= 0, `${name} exists`);
  const next = app.slice(start + 3).search(/^  (?:async )?function /m);
  return app.slice(start, next < 0 ? undefined : start + 3 + next);
}
function context() {
  return vm.createContext({
    normalizeRailLayoutSide: value => JSON.parse(JSON.stringify(value)),
    cloneFigureLayoutValue: value => JSON.parse(JSON.stringify(value)),
    createDefaultRailLayout: () => ({ left: { dock: 'left' }, right: { dock: 'right' } }),
    normalizePresentationPane: value => value === 'assets' ? 'assets' : 'slides',
  });
}

test('legacy Style, Colors and Selection routes migrate without adding a fourth view', () => {
  const ctx = context();
  vm.runInContext(source('normalizeInspectorTab'), ctx);
  for (const [old, expected] of Object.entries({ style: 'appearance', swatches: 'appearance', selection: 'properties', appearance: 'appearance', properties: 'properties', layers: 'layers', unknown: 'properties' })) {
    assert.equal(ctx.normalizeInspectorTab(old), expected);
  }
});

test('saved legacy colors view opens Appearance colors and preserves both rail records', () => {
  const ctx = context();
  vm.runInContext(source('normalizeInspectorTab') + source('defaultFigureLayoutProfile') + source('normalizeFigureLayoutProfile'), ctx);
  const rails = {
    workspace: 'custom',
    left: { dock: 'left', mode: 'docked', visible: false, width: 257, floating: null, collapsed: false },
    right: { dock: 'right', mode: 'floating', visible: true, width: 293, floating: { left: 876, top: 112, width: 260, height: 320 }, collapsed: false },
  };
  for (const mode of ['simple', 'advanced', 'presentation']) {
    const input = { rails, palette: { position: 'right', visible: false }, sidebarTab: 'tools', inspectorTab: 'swatches', presentationPane: 'assets' };
    const before = JSON.stringify(input);
    const migrated = JSON.parse(JSON.stringify(ctx.normalizeFigureLayoutProfile(input, mode)));
    assert.deepEqual(migrated.rails, rails);
    assert.deepEqual(migrated.palette, input.palette);
    assert.equal(migrated.inspectorTab, 'appearance');
    assert.equal(migrated.savedColorsOpen, true);
    assert.equal(JSON.stringify(input), before, 'migration does not mutate the saved record');
    assert.deepEqual(JSON.parse(JSON.stringify(ctx.normalizeFigureLayoutProfile(migrated, mode))), migrated, 'normalization is stable on the next startup');
  }
});

test('ordinary legacy Style retains geometry with saved colors closed', () => {
  const ctx = context();
  vm.runInContext(source('normalizeInspectorTab') + source('defaultFigureLayoutProfile') + source('normalizeFigureLayoutProfile'), ctx);
  const profile = ctx.normalizeFigureLayoutProfile({ rails: { left: { dock: 'left' }, right: { dock: 'right', mode: 'floating', floating: { width: 410, height: 550 } } }, inspectorTab: 'style' }, 'advanced');
  assert.equal(profile.inspectorTab, 'appearance');
  assert.equal(profile.savedColorsOpen, false);
  assert.equal(profile.rails.right.floating.width, 410);
});

test('inline asset reset preserves part controls, escaped labels and existing binding actions', () => {
  const controls = require(path.join(root, 'app/scientific-asset-color-controls.js'));
  const meta = { editableColorRegions: [{ id: 'matrix', label: 'Matrix <fill>', default: '#FFDD00' }] };
  const html = controls.render(meta, { prefix: 'inspector-test', mode: 'advanced', heading: false, resetAll: true, inlineReset: true, overrides: { matrix: '#125B8A' }, customOverrides: { matrix: '#125B8A' }, hasCustomColors: true });
  assert.equal((html.match(/data-asset-colors-reset/g) || []).length, 1);
  assert.match(html, /asset-palette-row/);
  assert.match(html, /Edited colors kept/);
  assert.match(html, /Matrix &lt;fill&gt;/);
  assert.match(html, /value="#125B8A" data-asset-color-region="matrix"/);
  assert.match(html, /data-asset-color-reset="matrix"/);
  const legacy = controls.render(meta, { prefix: 'legacy-test', resetAll: true });
  assert.doesNotMatch(legacy, /asset-palette-row/);
  assert.equal((legacy.match(/data-asset-colors-reset/g) || []).length, 1);
});
