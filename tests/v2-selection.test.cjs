const test=require('node:test'),assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs'),path=require('node:path');
const code=fs.readFileSync(path.join(__dirname,'../assets/connected_exploration.js'),'utf8');
const tick=()=>new Promise(r=>setImmediate(r));
async function setup(rejectBoundary=false){
 const elements={},sent=[],listeners={};
 const element=id=>elements[id]??={disabled:false,hidden:false,textContent:'',handlers:{},on(type,fn){this.handlers[type]=fn;}};
 const parent={postMessage(message){sent.push(message);}};
 const window={parent,location:{origin:'http://localhost:8000'},addEventListener(type,fn){listeners[type]=fn;}};
 const sample={latitude:-22.87,longitude:-47.05,east_offset_m:1,north_offset_m:2,elevation_m:650,distance_m:0};
 vm.runInNewContext(code,{window,document:{getElementById:element},URLSearchParams,console,requestAnimationFrame:fn=>fn(),
 Plotly:{async newPlot(){},async restyle(){},async react(){},Plots:{resize(){}}},
 fetch:async url=>({ok:!(rejectBoundary && url.startsWith('/api/lake-selection')),json:async()=>url.startsWith('/api/surface-scene')?{x:[],y:[],z:[],customdata:[],lake_line:{x:[],y:[],z:[]}}:
 url.startsWith('/api/lake-selection')?(rejectBoundary?{detail:'Choose a point inside the mapped Taquaral Lake outline.'}:{allowed:true}):url.startsWith('/api/surface-profile')?{distance_m:100,valid_sample_count:2,sample_count:2,sample_spacing_m:100,samples:[sample,{...sample,distance_m:100}]}:sample})});
 await tick();await tick();
 return {elements,sent,state(points,measuring=true){listeners.message({origin:window.location.origin,source:parent,data:{type:'taquaral:state',points,measuring}});},
 click(lat=-22.87,lng=-47.05){element('scene').handlers.plotly_click({points:[{curveNumber:0,customdata:[lat,lng]}]});},picks(){return sent.filter(m=>m.type==='taquaral:point');}};
}
test('duplicate click notifications before acknowledgement send only A once',async()=>{
 const h=await setup();h.state([]);await tick();h.click();h.click();await tick();assert.equal(h.picks().length,1);
});
test('B requires explicit arming after A acknowledgement',async()=>{
 const h=await setup();h.state([]);h.click();await tick();h.state([{lat:-22.87,lng:-47.05}]);await tick();
 h.click(-22.88,-47.06);await tick();assert.equal(h.picks().length,1);assert.equal(h.elements['select-b'].disabled,false);
 h.elements['select-b'].onclick();h.click(-22.88,-47.06);h.click(-22.88,-47.06);await tick();assert.equal(h.picks().length,2);
});
test('B at the same coordinate is rejected; another location is accepted',async()=>{
 const h=await setup();h.state([{lat:-22.87,lng:-47.05}]);h.elements['select-b'].onclick();h.click();
 assert.equal(h.picks().length,0);assert.match(h.elements.status.textContent,/different/i);h.click(-22.88,-47.06);await tick();assert.equal(h.picks().length,1);
});
test('stale unchanged state does not unlock an in-flight pick',async()=>{
 const h=await setup();h.state([]);h.click();h.state([]);h.click(-22.88,-47.06);await tick();assert.equal(h.picks().length,1);
});
test('start and clear block late events; another selection can start',async()=>{
 const h=await setup();h.state([{lat:-22.87,lng:-47.05},{lat:-22.88,lng:-47.06}],false);
 h.elements.start.onclick();h.click();assert.equal(h.picks().length,0);h.state([],false);h.state([],true);h.click();await tick();assert.equal(h.picks().length,1);
 h.elements.clear.onclick();h.click(-22.88,-47.06);await tick();assert.equal(h.picks().length,1);h.state([],false);h.elements.start.onclick();h.state([],true);h.click(-22.88,-47.06);await tick();assert.equal(h.picks().length,2);
});
test('A selected on the map can be continued in 3D; completion blocks further picks',async()=>{
 const h=await setup();h.state([{lat:-22.87,lng:-47.05}]);assert.equal(h.elements['select-b'].disabled,false);h.elements['select-b'].onclick();h.click(-22.88,-47.06);await tick();
 h.state([{lat:-22.87,lng:-47.05},{lat:-22.88,lng:-47.06}],false);await tick();assert.equal(h.elements['select-b'].disabled,true);h.click(-22.89,-47.07);assert.equal(h.picks().length,1);
});

test('outside pick is rejected without consuming A or posting a point',async()=>{
 const h=await setup(true);h.state([]);h.click();await tick();
 assert.equal(h.picks().length,0);assert.match(h.elements.status.textContent,/inside/);
 h.click();await tick();assert.equal(h.picks().length,0);
});
test('clear during boundary validation prevents a late point message',async()=>{
 const h=await setup();h.state([]);h.click();h.elements.clear.onclick();h.state([],false);
 await tick();assert.equal(h.picks().length,0);
});
