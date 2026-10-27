'use strict';
(function () {
    const el=id=>document.getElementById(id);
    let revision=0;
    function query() {
        const q=new URLSearchParams({parameter:el('parameter').value});
        for (const k of ['station','start','end']) if (el(k).value) q.set(k,el(k).value);
        return q;
    }
    async function update() {
        const current=++revision;
        el('status').className='';
        el('status').textContent='Loading selected historical records…';
        el('rows').replaceChildren();
        el('source-figure').hidden=true;
        for (const f of ['csv','json']) el(f).hidden=true;
        if(typeof Plotly!=='undefined') Plotly.purge('chart');
        try {
            const q=query();
            const response=await fetch('/api/historical-water-quality?'+q,{cache:'no-store'});
            const data=await response.json();
            if(!response.ok) throw Error(typeof data.detail==='string'?data.detail:'Invalid filter or request.');
            if(current!==revision)return;
            const records=data.records;
            const meta=data.metadata;
            const spec=meta.parameters[el('parameter').value];
            for(const f of ['csv','json']){
                const exportQuery=new URLSearchParams(q);exportQuery.set('format',f);
                el(f).href='/api/historical-water-quality/export?'+exportQuery;
                el(f).hidden=false;
            }
            el('status').textContent=records.length+' of '+meta.record_count+' reviewed records selected · depth 0.0 m · historical observations from 2000.';
            for(const r of records){
                const tr=document.createElement('tr');
                for(const value of [r.date,r.station,r.depth_m.toFixed(1),r.value,r.unit,r.value_raw,r.source_table,r.source_printed_page+' / '+r.source_pdf_page]){
                    const td=document.createElement('td');td.textContent=String(value);tr.append(td);
                }
                el('rows').append(tr);
            }
            el('source-caption').textContent='Table '+spec.source_table+', printed page '+spec.printed_page+' / PDF page '+spec.pdf_page+'. The excerpt below preserves the selected surface row and its column headings.';
            el('source-row').src=spec.row_excerpt;
            el('source-figure').hidden=false;
            if(typeof Plotly==='undefined') throw Error('Table loaded, but the chart library is unavailable. Check Plotly installation.');
            const traces=['E1','E2'].map((station,i)=>{
                const rows=records.filter(r=>r.station===station).sort((a,b)=>a.date.localeCompare(b.date));
                return {type:'scatter',mode:'markers',name:station,x:rows.map(r=>r.date),y:rows.map(r=>r.value),
                    customdata:rows.map(r=>[r.value_raw,r.source_table,r.source_printed_page]),marker:{size:10,color:i?'#ffce67':'#5de0be',symbol:i?'diamond':'circle'},
                    hovertemplate:'Date: %{x}<br>Value: %{y}<br>Printed: %{customdata[0]}<br>Table %{customdata[1]}, p. %{customdata[2]}<extra>'+station+'</extra>'};
            }).filter(t=>t.x.length);
            await Plotly.newPlot('chart',traces,{paper_bgcolor:'#10202b',plot_bgcolor:'#10202b',font:{color:'#edf5fa'},margin:{l:70,r:25,t:30,b:55},
                xaxis:{title:{text:'Sampling date (2000)'},type:'date'},yaxis:{title:{text:spec.label+' ('+spec.unit+')'}},legend:{orientation:'h'},
                annotations:records.length?[]:[{text:'No observations match the filters.',xref:'paper',yref:'paper',x:.5,y:.5,showarrow:false}]},{responsive:true,displaylogo:false});
        } catch(e) {if(current===revision){el('status').textContent=e.message;el('status').className='error';}}
    }
    for(const k of ['parameter','station','start','end'])el(k).addEventListener('change',update);
    window.addEventListener('message',event=>{
        if(event.origin===location.origin && event.source===parent && event.data?.type==='taquaral:environment-resize' && typeof Plotly!=='undefined'){
            requestAnimationFrame(()=>{if(el('chart').data)Plotly.Plots.resize(el('chart'));});
        }
    });
    update();
})();
