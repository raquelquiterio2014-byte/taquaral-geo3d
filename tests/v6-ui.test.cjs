const test=require('node:test'),assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs'),path=require('node:path');
const code=fs.readFileSync(path.join(__dirname,'../assets/spatial_context.js'),'utf8');
const tick=()=>new Promise(r=>setImmediate(r));
function fixture(mode='cumulative'){
 const stats={selected_cell_count:10,valid_cell_count:8,missing_or_excluded_cell_count:2,minimum:640,maximum:670,median:650};
 return {mode,zones:[100,250,500].map((v,i)=>({outer_distance_m:v,inner_distance_m:mode==='rings'?[0,100,250][i]:0,zone_area_m2:1000,crop_coverage_fraction:1,elevation_m:stats,surface_slope_degrees:{...stats,minimum:0,maximum:15,median:5}})),
 zone_geojson:{type:'FeatureCollection',features:[]},lake_geojson:{type:'Feature',geometry:{type:'Polygon',coordinates:[]}},raster_bounds_west_south_east_north:[-47.075,-22.89,-47.035,-22.855],
 legends:{elevation:{minimum:620,maximum:745,unit:'m (EGM2008)',colors:['#000000','#ffffff']},slope:{minimum:0,maximum:45,unit:'degrees',colors:['#000000','#ffffff']}},
 sources:{dsm:{name:'Copernicus',prepared_at_utc:'2026-10-26',attribution:'Source attribution'},water:{name:'OpenStreetMap',lake_reference:'relation/17154522',downloaded_at_utc:'2026-10-26',license:'ODbL 1.0',polygon_count:11,source_selection_status:'Candidates awaiting visual inspection'}},limitations:['Not current conditions']};
}
function setup({withMap=true,fetcher}={}){
 const nodes={},urls=[],maps=[],overlays=[];
 const make=()=>({value:'',hidden:false,style:{},children:[],options:[{},{},{}],handlers:{},append(x){this.children.push(x)},replaceChildren(){this.children=[]},addEventListener(k,fn){this.handlers[k]=fn}});
 const el=id=>nodes[id]??=make();for(const [id,value] of Object.entries({mode:'cumulative',layer:'elevation',distance:'500'}))el(id).value=value;
 const layer=()=>({addTo(){return this},getBounds(){return []},bringToFront(){},bindTooltip(){},on(k,fn){this[k]=fn;return this}});
 const L={map(){const m={createPane(){},getPane(){return {style:{}}},setView(){return this},removeLayer(){},invalidateSize(){},fitBounds(){}};maps.push(m);return m},tileLayer:layer,geoJSON:layer,imageOverlay(url){overlays.push(url);return layer()}};
 const context={document:{getElementById:el,createElement:make},URLSearchParams,location:{origin:'http://localhost'},parent:{},window:{addEventListener(){}},requestAnimationFrame:fn=>fn(),
 fetch:async url=>{urls.push(url);return fetcher?fetcher(url,urls.length):{ok:true,json:async()=>fixture(new URL('http://localhost'+url).searchParams.get('mode'))}}};
 if(withMap)context.L=L;
 vm.runInNewContext(code,context);
 return {el,urls,maps,overlays};
}
test('loads all zone rows, matching exports and geographic raster bounds',async()=>{
 const h=setup();await tick();
 assert.equal(h.el('results').hidden,false);assert.equal(h.el('rows').children.length,6);
 assert.match(h.el('csv').href,/mode=cumulative&format=csv/);
 assert.match(h.overlays[0],/distance=500&layer=elevation/);
 assert.match(h.el('mode-note').textContent,/Do not add/);
});
test('ring and slope controls update layer URL, labels and units',async()=>{
 const h=setup();await tick();h.el('mode').value='rings';h.el('layer').value='slope';h.el('mode').handlers.change();await tick();
 assert.match(h.overlays.at(-1),/mode=rings&distance=500&layer=slope/);
 assert.equal(h.el('distance').options[2].textContent,'250–500 m');
 assert.match(h.el('legend-title').textContent,/degrees/);assert.match(h.el('json').href,/mode=rings/);
});
test('missing map library keeps statistics and exports available with an error',async()=>{
 const h=setup({withMap:false});await tick();
 assert.equal(h.el('results').hidden,false);assert.equal(h.el('map-error').hidden,false);
 assert.match(h.el('map-error').textContent,/Tables and exports remain available/);assert.equal(h.el('rows').children.length,6);
});
test('an older response cannot replace a newer mode selection',async()=>{
 let release;
 const h=setup({fetcher:(url,n)=>n===1?new Promise(r=>release=r):{ok:true,json:async()=>fixture('rings')}});
 h.el('mode').value='rings';h.el('mode').handlers.change();await tick();release({ok:true,json:async()=>fixture()});await tick();
 assert.match(h.el('csv').href,/mode=rings/);assert.equal(h.overlays.length,1);
});
test('server error hides old results and provides actionable status',async()=>{
 const h=setup({fetcher:()=>({ok:false,json:async()=>({detail:'Restore the source data.'})})});await tick();
 assert.equal(h.el('results').hidden,true);assert.match(h.el('status').textContent,/Restore/);
});
