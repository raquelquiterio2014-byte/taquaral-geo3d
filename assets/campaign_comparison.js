'use strict';
(function () {
    const el=id=>document.getElementById(id);
    const number=v=>Number(v).toLocaleString('en-US',{maximumFractionDigits:3});
    let revision=0, drawQueue=Promise.resolve();
    function fill(id, rows) {
        el(id).replaceChildren();
        for (const values of rows) {
            const tr=document.createElement('tr');
            for (const value of values) {const td=document.createElement('td');td.textContent=String(value);tr.append(td);}
            el(id).append(tr);
        }
    }
    async function update() {
        const current=++revision;
        el('results').hidden=true;
        el('status').className='';
        el('status').textContent='Loading historical comparisons…';
        const q=new URLSearchParams({parameter:el('parameter').value,campaign_a:el('campaign-a').value,campaign_b:el('campaign-b').value});
        if(el('station').value)q.set('station',el('station').value);
        try {
            const response=await fetch('/api/historical-campaign-comparison?'+q,{cache:'no-store'});
            const d=await response.json();
            if(current!==revision)return;
            if(!response.ok)throw Error(typeof d.detail==='string'?d.detail:'Invalid comparison selection.');
            el('record-count').textContent=d.record_count;
            const ph=d.selection.parameter==='ph';
            el('statistic').textContent=ph?'Median of reported pH':'Arithmetic mean';
            el('method').textContent=ph?'pH is logarithmic. The median summarizes the reported pH values, not mean hydrogen-ion activity. Differences are in pH units, never percentages.':'Each campaign center is the arithmetic mean of two observed values at one station. Minimum, maximum and sample count are shown alongside it.';
            fill('summaries',d.summaries.map(s=>[s.role,d.campaigns[s.campaign].label,s.station,s.n,number(s.minimum),number(s.maximum),number(s.center),s.unit]));
            fill('differences',d.campaign_differences.map(s=>[s.station,number(s.center_a),number(s.center_b),number(s.difference_b_minus_a),s.difference_unit,s.n_a+' / '+s.n_b]));
            fill('within',d.within_campaign_changes.map(s=>[d.campaigns[s.campaign].label,s.station,s.first_date,s.last_date,number(s.first_value),number(s.last_value),number(s.difference_last_minus_first),s.difference_unit]));
            fill('station-differences',d.station_differences.map(s=>[s.date,number(s.e1),number(s.e2),number(s.difference_e2_minus_e1),s.difference_unit]));
            el('station-note').textContent=d.station_differences.length?'Same-date station pairs only; no station locations or lake-wide averages are inferred.':'Select both stations to compare same-date E1 and E2 observations.';
            fill('records',d.records.map(s=>[s.date,s.station,s.depth_m.toFixed(1),s.value,s.unit,s.value_raw,s.source_table,s.source_printed_page+' / '+s.source_pdf_page]));
            for(const [id,section] of [['observations','observations'],['summary-csv','summaries'],['differences-csv','campaign_differences'],['within-csv','within_campaign_changes'],['station-csv','station_differences'],['json',null]]) {
                const eq=new URLSearchParams(q);eq.set('format',section?'csv':'json');if(section)eq.set('section',section);
                el(id).href='/api/historical-campaign-comparison/export?'+eq;
            }
            el('source-caption').textContent=d.source.author+' · USP doctoral thesis ('+d.source.year+'). Table '+d.parameter.source_table+', printed page '+d.parameter.printed_page+' / PDF page '+d.parameter.pdf_page+'. '+d.grouping_provenance;
            el('source-link').href=d.source.url;el('source-row').src=d.parameter.row_excerpt;
            el('limitations').replaceChildren();for(const text of d.limitations){const li=document.createElement('li');li.textContent=text;el('limitations').append(li);}
            el('results').hidden=false;
            el('status').textContent=d.record_count+' selected historical surface observations · two dates per campaign and station · 2000.';
            if(typeof Plotly==='undefined')throw Error('Tables and exports loaded. Plotly is unavailable; check the server dependency.');
            const traces=[];
            for(const [index,station] of ['E1','E2'].entries())for(const role of ['A','B']) {
                const rows=d.records.filter(r=>r.station===station&&r.campaign_role===role);
                if(!rows.length)continue;
                traces.push({type:'scatter',mode:'markers',name:station+' · Campaign '+role,x:rows.map(r=>r.date),y:rows.map(r=>r.value),
                    marker:{size:11,color:index?'#ffce67':'#5de0be',symbol:role==='A'?'circle':'diamond'},
                    customdata:rows.map(r=>[r.value_raw,r.source_table,r.source_printed_page]),
                    hovertemplate:'%{x}<br>Value: %{y}<br>Printed: %{customdata[0]}<br>Table %{customdata[1]}, p. %{customdata[2]}<extra>'+station+' · '+role+'</extra>'});
            }
            drawQueue=drawQueue.catch(()=>{}).then(()=>{
                if(current!==revision)return;
                return Plotly.react('chart',traces,{paper_bgcolor:'#10202b',plot_bgcolor:'#10202b',font:{color:'#edf5fa'},margin:{l:75,r:25,t:30,b:65},
                    xaxis:{type:'date',title:{text:'Sampled dates (2000)'}},yaxis:{title:{text:d.parameter.label+' ('+d.parameter.unit+')'}},legend:{orientation:'h'}},{responsive:true,displaylogo:false});
            });
            await drawQueue;
        } catch(error) {if(current===revision){el('status').textContent=error.message;el('status').className='error';}}
    }
    el('filters').addEventListener('submit',event=>event.preventDefault());
    for(const id of ['parameter','campaign-a','campaign-b','station'])el(id).addEventListener('change',update);
    window.addEventListener('message',event=>{
        if(event.origin===location.origin&&event.source===parent&&event.data?.type==='taquaral:campaign-resize'&&typeof Plotly!=='undefined'&&el('chart').data)
            requestAnimationFrame(()=>Plotly.Plots.resize(el('chart')));
    });
    update();
})();
