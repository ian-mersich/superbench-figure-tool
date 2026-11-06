'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const fabric = require('../vendor/fabric/index.min.js');
const source = fs.readFileSync(require.resolve('../app/app.js'), 'utf8');

// These are native operands/pose and trusted scene input from SC7. This test
// has no QA-artifact, browser, renderer or generated-fixture dependency.
const SC7 = {
  path: [['M', 0, 64], ['C', 68, -54, 188, -36, 280, 48]],
  matrix: [1.1497566764465774, 0.2654422441257607, -0.1754618223882147,
    0.7600086505324836, 579.5668978243546, 189.03888325865688],
  offset: {x: 140, y: 22.124072312287943},
  pointer: {x: 561.845161982945, y: 153.86048970903673},
  delta: [36.160714285714334, -24.10714285714286]
};

function actual(name, context) {
  const start = source.indexOf(`  function ${name}(`);
  const end = source.indexOf('\n  function ', start + 1);
  assert.ok(start > 0 && end > start, `actual App function ${name}`);
  vm.runInContext(source.slice(start, end), context);
  return context[name];
}

function runtime() {
  const context = vm.createContext({fabricRef: fabric,
    isEditablePathObject: object => Array.isArray(object.path),
    isLineVectorObject: () => false});
  for (const name of ['clamp', 'roundPathCoord', 'pathPoint', 'lerpPoint', 'commandPoint',
    'pathEndpointIndices', 'pathCommandEndpoint', 'pathPointsCoincide', 'pathSegmentDescriptors',
    'cubicPointAt', 'quadraticPointAt', 'reflectedPreviousControl', 'segmentControls',
    'segmentPointAt', 'samplePathSegment', 'fabricPoint', 'pathRenderingOffset',
    'pathObjectSceneMatrix', 'pathLocalPointToCanvas', 'closestPointOnCanvasLine',
    'closestSegmentRawT', 'closestSegmentT', 'copyPathCommands', 'pathSegmentDragCommands']) {
    actual(name, context);
  }
  return context;
}

function objectFrom(record) {
  return {path: record.path.map(command => command.slice()), pathOffset: {...record.offset},
    calcTransformMatrix: () => record.matrix.slice()};
}

function world(object, point, vector = false) {
  const [a,b,c,d,e,f] = object.calcTransformMatrix();
  const x = point[0] - (vector ? 0 : object.pathOffset.x);
  const y = point[1] - (vector ? 0 : object.pathOffset.y);
  return [a*x+c*y+(vector ? 0 : e), b*x+d*y+(vector ? 0 : f)];
}

function polygon(object, commandIndex) {
  const command = object.path[commandIndex], previous = object.path[commandIndex-1];
  const start = previous.slice(-2), type = command[0];
  if (type === 'Q') return [start, command.slice(1,3), command.slice(3,5)];
  if (type === 'C') return [start, command.slice(1,3), command.slice(3,5), command.slice(5,7)];
  if (type === 'S') {
    const prior = previous[0] === 'C' ? previous.slice(3,5)
      : previous[0] === 'S' ? previous.slice(1,3) : start;
    return [start, [2*start[0]-prior[0], 2*start[1]-prior[1]], command.slice(1,3), command.slice(3,5)];
  }
  if (type === 'Z') {
    let first=commandIndex-1;
    while (first>=0 && object.path[first][0]!=='M') first--;
    return [start, object.path[first].slice(1,3)];
  }
  return [start, command.slice(-2)];
}

// Independent Bernstein polynomial/derivative; never call App interpolation.
function bernstein(points, t) {
  const u = 1-t, weights = points.length === 4 ? [u*u*u, 3*u*u*t, 3*u*t*t, t*t*t]
    : points.length === 3 ? [u*u, 2*u*t, t*t] : [u,t];
  return [0,1].map(axis => weights.reduce((sum,w,i) => sum+w*points[i][axis], 0));
}

function derivative(points, t) {
  const degree = points.length-1;
  const differences = points.slice(1).map((p,i) => p.map((v,axis) => degree*(v-points[i][axis])));
  if (differences.length === 1) return differences[0];
  return bernstein(differences, t);
}

function pointAt(object, points, t) { return world(object, bernstein(points,t)); }

function knownNormalPointer(object, points, t, distance = .37) {
  const point = pointAt(object, points, t), tangent = world(object, derivative(points,t), true);
  const length = Math.hypot(...tangent);
  return {x: point[0]-tangent[1]*distance/length, y: point[1]+tangent[0]*distance/length};
}

// Stationary roots of squared world distance, bracketed on a finite grid and
// bisected independently of the App's chord/ternary search. Endpoints compete.
function independentClosest(object, points, pointer) {
  const stationarity = t => {
    const p = pointAt(object,points,t), v = world(object,derivative(points,t),true);
    return (p[0]-pointer.x)*v[0] + (p[1]-pointer.y)*v[1];
  };
  const candidates = [0,1];
  let low = 0, previous = stationarity(0);
  for (let index=1; index<=2048; index++) {
    const high = index/2048, next = stationarity(high);
    if (previous === 0) candidates.push(low);
    if (previous*next < 0) {
      let left=low, right=high, a=previous;
      for (let step=0; step<55; step++) {
        const middle=(left+right)/2, b=stationarity(middle);
        if (a*b<=0) right=middle;
        else { left=middle; a=b; }
      }
      candidates.push((left+right)/2);
    }
    low=high;previous=next;
  }
  const distance = t => {
    const p=pointAt(object,points,t);
    return (p[0]-pointer.x)**2+(p[1]-pointer.y)**2;
  };
  return candidates.reduce((best,t) => distance(t)<distance(best) ? t : best,0);
}

function segment(context, object, index=1) {
  const found = context.pathSegmentDescriptors(object).find(row => row.endCommandIndex===index);
  assert.ok(found, `real segment descriptor ${index}`);
  return found;
}

function assertMinimumResponse(context, object, descriptor, pointer, expectedT, delta, tolerance=.005) {
  const raw = object.path.map(command => command.slice());
  const t = context.closestSegmentT(object,descriptor,pointer), u=1-expectedT;
  const weights = descriptor.type==='Q' ? [2*u*expectedT] : [3*u*u*expectedT,3*u*expectedT*expectedT];
  const denominator=weights.reduce((sum,w) => sum+w*w,0), index=descriptor.endCommandIndex;
  const commands=context.pathSegmentDragCommands({pathSnapshot:raw,segment:{endCommandIndex:index},t,
    inverseSceneMatrix:fabric.util.invertTransform(object.calcTransformMatrix())},...delta);
  for (let control=0; control<weights.length; control++) {
    const offset=1+2*control, old=world(object,raw[index].slice(offset,offset+2));
    const actual=world(object,Array.from(commands[index]).slice(offset,offset+2));
    for (let axis=0; axis<2; axis++) {
      const expected=old[axis]+delta[axis]*weights[control]/denominator;
      assert.ok(Math.abs(actual[axis]-expected)<=tolerance,
        `control ${control+1} axis ${axis}: ${actual[axis]-expected} world; tolerance ${tolerance}`);
    }
  }
  assert.deepEqual(JSON.parse(JSON.stringify(object.path)),raw,'nearest/reshape leaves captured input immutable');
  assert.deepEqual(Array.from(commands[index]).slice(-2),raw[index].slice(-2),'endpoint retained');
  for (let i=0;i<raw.length;i++) if(i!==index) assert.deepEqual(Array.from(commands[i]),raw[i]);
  const next={path:JSON.parse(JSON.stringify(commands)),pathOffset:object.pathOffset,
    calcTransformMatrix:()=>object.calcTransformMatrix()}, points=polygon(object,index);
  const original=pointAt(object,points,expectedT), moved=pointAt(next,polygon(next,index),expectedT);
  moved.forEach((v,axis) => assert.ok(Math.abs(v-original[axis]-delta[axis])<=tolerance,'material point follows delivered vector'));
}

test('captured SC7 nearest parameter and individual C minimum-response controls use the continuous painted curve', () => {
  const context=runtime(), object=objectFrom(SC7), points=polygon(object,1), descriptor=segment(context,object);
  const expected=independentClosest(object,points,SC7.pointer);
  assert.ok(Math.abs(expected-.45833523)<1e-7,'independent stationary-root oracle binds the captured scene');
  const actual=context.closestSegmentRawT(object,descriptor,SC7.pointer);
  assert.ok(Math.abs(actual-expected)<2e-7, `nearest t error ${actual-expected}`);
  assertMinimumResponse(context,object,descriptor,SC7.pointer,expected,SC7.delta);
});

test('captured SC7 control split has its own .005 world guard beyond material-point motion', () => {
  const context=runtime(),object=objectFrom(SC7),descriptor=segment(context,object);
  const expected=independentClosest(object,polygon(object,1),SC7.pointer);
  assertMinimumResponse(context,object,descriptor,SC7.pointer,expected,SC7.delta);
  assertMinimumResponse(context,object,descriptor,SC7.pointer,expected,[24.10714285714289,-17.07589285714286]);
});

for (const command of [['Q',31.123456,-28.987654,80.234567,10.345678],
  ['C',17.123456,-24.987654,62.456789,35.234567,80.234567,10.345678]]) {
  test(`raw ${command[0]} known world-normal closest points retain fractional coordinates through nested reflected/skewed affine groups`, () => {
    const context=runtime(),object=new fabric.Path([['M',.123456,10.654321],command,['L',120.123456,20.654321]],
      {left:80,top:90,angle:23,skewX:11,flipY:true});
    const inner=new fabric.Group([object],{angle:-17,scaleX:.87,scaleY:1.13});
    const outer=new fabric.Group([inner],{angle:31,skewY:7,scaleX:1.21,scaleY:.76,flipX:true});
    const descriptor=segment(context,object),points=polygon(object,1),before=JSON.stringify(object.path);
    assert.equal(object.group,inner);assert.equal(inner.group,outer);
    for (const t of [.17,5.5/12,.83]) {
      const pointer=knownNormalPointer(object,points,t),independent=independentClosest(object,points,pointer);
      assert.ok(Math.abs(independent-t)<1e-10,'analytic normal has the known nearest parameter');
      const got=context.closestSegmentRawT(object,descriptor,pointer);
      assert.ok(Math.abs(got-t)<2e-7,`known t ${t}, actual ${got}`);
      assertMinimumResponse(context,object,descriptor,pointer,t,[17.123456,-9.876543]);
    }
    assert.equal(JSON.stringify(object.path),before);
  });
}

test('raw near-end parameters remain distinct from the existing insertion/reshape inset band', () => {
  const context=runtime(),object=objectFrom({path:[['M',.123456,.654321],['Q',50.123456,.654321,100.123456,.654321]],
    matrix:[1.2,.3,-.4,.8,37,-21],offset:{x:50.123456,y:.654321}});
  const descriptor=segment(context,object),points=polygon(object,1);
  for (const [t,inset] of [[.01,.03],[.99,.97]]) {
    const pointer=knownNormalPointer(object,points,t,.2),raw=context.closestSegmentRawT(object,descriptor,pointer);
    assert.ok(Math.abs(raw-t)<2e-7,`raw ${t} must not be moved to insertion safety band`);
    assert.equal(context.closestSegmentT(object,descriptor,pointer),inset);
    assert.ok(raw<=.03||raw>=.97,'raw cut guard can still reject the endpoint safety band');
  }
});

for (const previous of [['C',10.123456,20.234567,30.345678,-18.456789,48.567891,4.678912],
  ['S',30.345678,-18.456789,48.567891,4.678912],['L',48.567891,4.678912]]) {
  test(`raw S nearest geometry reflects only a prior C/S control (${previous[0]})`, () => {
    const context=runtime(),object=objectFrom({path:[['M',.123456,.654321],previous,['S',68.123456,27.234567,94.345678,2.456789]],
      matrix:[1.15,.27,-.19,.78,127,83],offset:{x:46.234567,y:6.345678}});
    const descriptor=segment(context,object,2),points=polygon(object,2);
    for (const t of [.23,.62]) {
      const pointer=knownNormalPointer(object,points,t,.1);
      assert.ok(Math.abs(independentClosest(object,points,pointer)-t)<1e-10);
      assert.ok(Math.abs(context.closestSegmentRawT(object,descriptor,pointer)-t)<2e-7,'unrounded reflected S curve');
    }
  });
}

for (const secondContour of [false,true]) test(`raw Z nearest geometry closes to its correct fractional subpath start (second contour: ${secondContour})`, () => {
  const commands=[['M',.123456,.654321],['L',80.234567,20.345678],['L',65.456789,72.567891],['Z']];
  if (secondContour) commands.push(['M',220.123456,28.654321],['L',301.234567,39.345678],['L',284.456789,91.567891],['Z']);
  const context=runtime(),object=objectFrom({path:commands,
    matrix:[.91,-.21,.17,1.13,53,87],offset:{x:40.123456,y:36.234567}});
  const index=secondContour?7:3,descriptor=segment(context,object,index),points=polygon(object,index);
  assert.equal(descriptor.subpathStartCommandIndex,secondContour?4:0);
  for (const t of [.19,.71]) {
    const pointer=knownNormalPointer(object,points,t,.1);
    assert.ok(Math.abs(context.closestSegmentRawT(object,descriptor,pointer)-t)<2e-7,'unrounded closing line');
  }
});
