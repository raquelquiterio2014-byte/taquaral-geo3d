const test=require('node:test'),assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs'),path=require('node:path');
const code=fs.readFileSync(path.join(__dirname,'../assets/campaign_comparison.js'),'utf8');
const tick=()=>new Promise(r=>setImmediate(r));
function data(parameter='dissolved_oxygen',station=null){
 const ph=parameter==='ph';
 return {selection:{parameter,station},record_count:station?4:8,campaigns:{march:{label:'March'},august:{label:'August'}},parameter:{label:ph?'pH':'Dissolved oxygen',unit:ph?'dimensionless':'mg/L',source_table:ph?6:4,printed_page:ph?152:150,pdf_page:ph?175:173,row_excerpt:'/environmental-monitoring/source-row/'+(ph?6:4)},
 source:{author:'Esperanza Hernández Piedrahíta',year:2002,url:'https://teses.usp.br/'},grouping_provenance:'Captions of Tables 4–7',limitations:['Historical only'],
 records:[{date:'2000-03-13',station:'E1',depth_m:0,value:7.63,unit:'mg/L',value_raw:'7,63',source_table:4,source_printed_page:150,source_pdf_page:173,campaign_role:'A'}],
 summaries:[{role:'A',campaign:'march',station:'E1',n:2,minimum:7.19,maximum:7.63,center:7.41,unit:'mg/L'}],
 campaign_differences:[{station:'E1',center_a:7.41,center_b:10.985,difference_b_minus_a:3.575,difference_unit:'mg/L',n_a:2,n_b:2}],
 within_campaign_changes:[],station_differences:station?[]:[{date:'2000-03-13',e1:7.63,e2:7.41,difference_e2_minus_e1:-.22,difference_unit:'mg/L'}]};
}
function setup(fetcher){
 const nodes={},calls=[],draws=[];
 const make=()=>({value:'',hidden:false,children:[],handlers:{},append(x){this.children.push(x)},replaceChildren(){this.children=[]},addEventListener(k,fn){this.handlers[k]=fn}});
 const el=id=>nodes[id]??=make();
 for(const [id,value] of Object.entries({parameter:'dissolved_oxygen','campaign-a':'march','campaign-b':'august',station:''}))el(id).value=value;
 const parent={},location={origin:'http://localhost:8000'};
 vm.runInNewContext(code,{document:{getElementById:el,createElement:make},location,parent,window:{addEventListener(){}},URLSearchParams,
 requestAnimationFrame:fn=>fn(),Plotly:{async react(id,traces){draws.push(traces)},Plots:{resize(){}}},
 fetch:async url=>{calls.push(url);return fetcher?fetcher(url,calls.length):{ok:true,json:async()=>data()};}});
 return {el,calls,draws};
}
test('default UI renders source and signed comparison, exports matching filters',async()=>{
 const h=setup();await tick();await tick();
 assert.equal(h.el('results').hidden,false);assert.equal(h.el('record-count').textContent,8);
 assert.equal(h.el('statistic').textContent,'Arithmetic mean');
 assert.match(h.el('differences').children[0].children[3].textContent,/3.575/);
 assert.match(h.el('observations').href,/campaign_a=march&campaign_b=august/);
 assert.match(h.el('source-caption').textContent,/150 \/ PDF page 173/);
 assert.equal(h.draws[0][0].mode,'markers');
});
test('changing to pH and one station updates method, filters, and station note',async()=>{
 const h=setup(url=>{const q=new URL('http://localhost'+url).searchParams;return {ok:true,json:async()=>data(q.get('parameter'),q.get('station'))}});
 await tick();h.el('parameter').value='ph';h.el('station').value='E1';h.el('parameter').handlers.change();await tick();await tick();
 assert.equal(h.el('statistic').textContent,'Median of reported pH');
 assert.match(h.el('method').textContent,/never percentages/);assert.match(h.el('station-note').textContent,/Select both/);
 assert.match(h.el('json').href,/parameter=ph/);assert.match(h.el('json').href,/station=E1/);
});
test('failed selection hides old results and exports',async()=>{
 const h=setup((url,n)=>({ok:n===1,json:async()=>n===1?data():{detail:'Choose two different campaigns.'}}));
 await tick();h.el('campaign-b').value='march';h.el('campaign-b').handlers.change();await tick();
 assert.equal(h.el('results').hidden,true);assert.match(h.el('status').textContent,/different campaigns/);
});
test('late response from older filters cannot overwrite newer selection',async()=>{
 let release;
 const h=setup((url,n)=>n===1?new Promise(r=>release=r):{ok:true,json:async()=>data('ph')});
 h.el('parameter').value='ph';h.el('parameter').handlers.change();await tick();
 release({ok:true,json:async()=>data()});await tick();await tick();
 assert.equal(h.el('statistic').textContent,'Median of reported pH');assert.equal(h.draws.length,1);
});
