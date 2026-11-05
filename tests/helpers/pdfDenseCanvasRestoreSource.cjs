// Test-only source adapter. Production authority remains in App/Page.
'use strict';
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),assert=require('node:assert/strict');
const ROOT=process.env.FIGURE_TEST_ROOT||path.resolve(__dirname,'../..');
const bytes=fs.readFileSync(path.join(__dirname,'../fixtures/pdf-dense-canvas-restore-app959.json'));
assert.equal(crypto.createHash('sha256').update(bytes).digest('hex'),'0d6139d6791b5071523ca36e9901087dc4e1e7cc1392a4d5251b1f7d5c65909c');
const baseline=JSON.parse(bytes);assert.equal(baseline.appSha256,'959c5c8171936fa04c843e20d661e2758e3a73c221fc656d44acf91e3ccc17c2');
for(const row of baseline.functions)assert.equal(crypto.createHash('sha256').update(row.source).digest('hex'),row.sha256);
const baselineSource=baseline.functions.map(row=>row.source).join('\n')+'\n  function __baselineEnd() {}';
const appSource=fs.readFileSync(process.env.FIGURE_APP_SOURCE||path.join(ROOT,'app/app.js'),'utf8');
const start=appSource.indexOf('  // Canvas restoration is local to an actual native target.');
const end=appSource.indexOf('  async function loadCanvasJson(',start);
assert.ok(start>=0&&end>start,'current canvas restore implementation');
// Load the real bounded content-metrics cache and its private production
// instance before restore helpers that clear it with the artifact store.
const metricsCacheBinding=/^  const artifactDataUrlMetricsCache = createArtifactDataUrlMetricsCache\(\);$/m.exec(appSource);
assert.ok(metricsCacheBinding,'actual private artifact metrics cache binding');
// Completion retires native text fonts. Fixtures without that optional engine
// take its production early return rather than substituting a stub.
const implementationHelpers=extract(appSource,'createArtifactDataUrlMetricsCache')+'\n'+metricsCacheBinding[0]+'\n'+extract(appSource,'retireUnusedPdfTextFonts')+'\n'+appSource.slice(start,end);
function extract(source,name){const m=new RegExp('^  (?:async )?function '+name+'[(]','m').exec(source);assert.ok(m,name);const e=new RegExp(String.fromCharCode(10)+'  (?:async )?function ').exec(source.slice(m.index+5));assert.ok(e,name);const body=source.slice(m.index,m.index+5+e.index);return name==='completeLoadedCanvasScene'?body.split(String.fromCharCode(10)+'  // Canvas restoration is local to an actual native target.')[0].trimEnd():body;}
module.exports={ROOT,appSource,baselineSource,implementationHelpers,extract};
