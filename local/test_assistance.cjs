const assert=require('node:assert/strict');
let core;try{core=require('./static/assistance-core.js')}catch{}
assert.ok(core,'Assistance algorithms missing');
const layers=Array.from({length:3},(_,i)=>({label:['BASE','NAV','AJUSTES'][i],bindings:Array(38).fill('&none')}));
layers[0].bindings[9]='&kp P';layers[0].bindings[23]='&kp C';layers[0].bindings[33]='&kp LGUI';layers[0].bindings[36]='&mo 1';layers[0].bindings[37]='&kp LSHFT';layers[1].bindings[37]='&trans';layers[1].bindings[20]='&mo 2';layers[1].bindings[1]='&kp N2';layers[2].bindings[9]='&bt BT_CLR';
assert.deepEqual(core.resolve(layers,'limpar bluetooth','us')[0].positions,[36,20,9]);
assert.deepEqual(core.resolve(layers,'copiar','us')[0].positions,[33,23]);
assert.deepEqual(core.resolve(layers,'@','us')[0].positions,[36,37,1]);
assert.equal(core.resolve(layers,'@','unknown').length,0);
assert.equal(core.resolve(layers,'inexistente','us').length,0);
const stats={};core.observe(stats,'casa','','x');core.observe(stats,'casa','x','');core.observe(stats,'casa','','c');
assert.deepEqual(stats.c,{hits:1,misses:1});
core.observe(stats,'casa','c','cx');core.observe(stats,'casa','cx','cxy');assert.equal(stats.a.misses,1);
assert.ok(core.sequence({z:{hits:0,misses:5}}).includes('z'));
const report=core.diagnostics({telemetry:{sides:{left:{fresh:false,battery:0}}}});assert.ok(report.some(x=>x.includes('recentes')));
console.log('Assistance: nested layers, shortcuts, symbol map, correction accounting, adaptive practice and stale diagnostics passed');
const sparse=Array.from({length:3},()=>({label:'x',bindings:Array(38).fill('&none')}));
sparse[0].bindings[0]='&mo 2';sparse[0].bindings[1]='&kp A';sparse[1].bindings[1]='&kp B';sparse[2].bindings[1]='&trans';
assert.equal(core.resolve(sparse,'b').length,0,'Inactive lower layer must not leak into transparent bindings');
