import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { createRequire } from 'node:module';
import { pathToFileURL } from 'node:url';
import test from 'node:test';
const require=createRequire(import.meta.url);
const styles=require('../app/scientific-asset-art-styles.js');
const packsRoot=path.resolve(import.meta.dirname,'../assets/scientific-packs');
const registry=JSON.parse(fs.readFileSync(path.join(packsRoot,'library.json'),'utf8'));
const catalog=()=>registry.packs.flatMap(entry=>JSON.parse(fs.readFileSync(path.join(packsRoot,entry.path),'utf8')).assets);
const manifest=JSON.parse(fs.readFileSync(path.join(packsRoot,'style-4/manifest.json'),'utf8'));
const options={baseUrl:pathToFileURL(path.join(packsRoot,'style-4/manifest.json')).href,basePath:'assets/scientific-packs/style-4/'};

test('Style 4 maps all 486 existing identities to supplied vectors without changing the original catalog fields',()=>{
 const assets=catalog(),before=structuredClone(assets);
 styles.attachVariantManifest(assets,manifest,options);
 for(let i=0;i<assets.length;i++){
  const asset=assets[i];
  const {art_styles,...unchanged}=asset;
  assert.deepEqual(unchanged,before[i]);
  const variant=styles.assetForStyle(asset,'style-4');
  assert.equal(variant.id,asset.id);
  assert.equal(variant.concept_id,asset.concept_id);
  assert.equal(variant.art_style,'style-4');
  assert.equal(variant.art_style_source_sha256,art_styles['style-4'].sha256);
  assert.equal(variant.file,'assets/scientific-packs/style-4/'+art_styles['style-4'].file);
  assert.equal(variant._packAssetPath,'');
  const expectedUrl=new URL(art_styles['style-4'].file,options.baseUrl);expectedUrl.searchParams.set('v',art_styles['style-4'].sha256);
  assert.equal(variant._svgUrl,expectedUrl.href);
  assert.deepEqual(variant.editable_color_regions,art_styles['style-4'].editable_color_regions);
  const source=fs.readFileSync(new URL(variant._svgUrl),'utf8');
  assert.equal(styles.transformSvg(source,'style-4'),source,'supplied multicolor paint must remain exact');
  assert.deepEqual(styles.assetForStyle(asset,'soft-color'),asset);
  for(const legacy of ['cut-paper','technical-ink']) assert.deepEqual(styles.assetForStyle(asset,legacy).editable_color_regions,styles.transformRegions(asset.editable_color_regions,legacy));
 }
 assert.equal(assets.length,486);
});

test('Incomplete, duplicate, unsafe and mismatched Style 4 mappings fail atomically',()=>{
 const samples=[
  m=>m.assets.pop(),
  m=>m.assets.push(m.assets[0]),
  m=>m.assets[0].asset_id='unknown',
  m=>m.assets[0].editable_color_regions=[],
  m=>m.assets[0].sha256='wrong',
  ...['../other.svg','/other.svg','https://example.com/x.svg','svg/x.svg?x=1','svg\\x.svg'].map(file=>m=>m.assets[0].file=file)
 ];
 for(const mutate of samples){const assets=catalog(),m=structuredClone(manifest);mutate(m);assert.throws(()=>styles.attachVariantManifest(assets,m,options));assert.ok(assets.every(a=>!a.art_styles));}
 assert.throws(()=>styles.assetForStyle(catalog()[0],'style-4'),/unavailable/);
});

test('Selecting Style 4 keeps shade lists and faithful reset defaults rather than recoloring the original SVG',()=>{
 const assets=catalog();styles.attachVariantManifest(assets,manifest,options);
 const variant=assets.flatMap(a=>a.art_styles['style-4'].editable_color_regions).find(r=>new Set(r.default_paints.map(p=>p.color)).size>1);
 assert.ok(variant,'the supplied set includes multicolor editable regions');
 const transformed=styles.transformRegions([variant],'style-4');assert.deepEqual(transformed,[variant]);assert.notEqual(transformed[0],variant);
 assert.equal(styles.normalizeStyle('style-4'),'style-4');assert.equal(styles.normalizeStyle('future-unknown'),'soft-color');
});
