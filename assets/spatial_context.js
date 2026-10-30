'use strict';
(function(){
    const el=id=>document.getElementById(id);
    const number=v=>v===null?'No data':Number(v).toLocaleString('en-US',{maximumFractionDigits:2});
    let revision=0,map=null,zones=null,lake=null,raster=null,lastMode=null,lastData=null;
    function removeRaster(){if(raster&&map){map.removeLayer(raster);raster=null;}}
    function selectedStyle(feature){return {color:feature.properties.outer_distance_m===Number(el('distance').value)?'#ffce67':'#5de0be',weight:2,fillOpacity:0};}
    async function getJSON(url){const r=await fetch(url,{cache:'no-store'});const d=await r.json();if(!r.ok)throw Error(typeof d.detail==='string'?d.detail:'Could not load the analysis.');return d;}
    function renderRows(d){
        el('rows').replaceChildren();
        for(const zone of d.zones)for(const [key,label,unit] of [['elevation_m','DSM elevation','m'],['surface_slope_degrees','DSM surface slope','°']]){
            const s=zone[key],tr=document.createElement('tr');
            for(const v of [zone.inner_distance_m+'–'+zone.outer_distance_m,label,unit,number(s.minimum),number(s.maximum),number(s.median),s.valid_cell_count+' / '+s.selected_cell_count,s.missing_or_excluded_cell_count,number(zone.zone_area_m2),zone.crop_coverage_fraction===null?'No data':number(100*zone.crop_coverage_fraction)+'%']){
                const td=document.createElement('td');td.textContent=String(v);tr.append(td);
            }el('rows').append(tr);
        }
    }
    async function update(){
        const current=++revision,mode=el('mode').value,layer=el('layer').value,distance=Number(el('distance').value);
        el('results').hidden=true;el('status').className='';el('status').textContent='Loading spatial analysis…';removeRaster();
        el('map-error').hidden=true;
        try{
            const d=lastData&&lastMode===mode?lastData:await getJSON('/api/spatial-context?mode='+mode);
            if(current!==revision)return;
            lastData=d;const modeChanged=lastMode!==mode;lastMode=mode;
            renderRows(d);
            el('mode-note').textContent=mode==='cumulative'?'Cumulative zones overlap: each contains the surroundings from 0 m to its outer distance. Do not add these areas or counts.':'Disjoint rings separate the surroundings into 0–100 m, 100–250 m and 250–500 m intervals.';
            const labels=mode==='cumulative'?['0–100 m','0–250 m','0–500 m']:['0–100 m','100–250 m','250–500 m'];
            Array.from(el('distance').options).forEach((option,i)=>option.textContent=labels[i]);
            for(const format of ['csv','json','geojson'])el(format).href='/api/spatial-context/export?mode='+mode+'&format='+format;
            el('source-info').replaceChildren();
            for(const text of [d.sources.dsm.name+' · crop prepared '+d.sources.dsm.prepared_at_utc+' · elevations: EGM2008.',d.sources.dsm.attribution,d.sources.water.name+' · '+d.sources.water.lake_reference+' · OSM downloaded '+d.sources.water.downloaded_at_utc+' · '+d.sources.water.license+'.',d.sources.water.polygon_count+' water polygons excluded. Source selection metadata: '+d.sources.water.source_selection_status+'.','Buffer geometry: EPSG:32723. Grid: 30 m, nearest-cell reprojection. Slope: central differences with a full valid 3×3 neighborhood; all-touched mapped water and raster borders excluded. Display reprojection is separate from statistics.']){
                const p=document.createElement('p');p.textContent=text;el('source-info').append(p);
            }
            el('limits').replaceChildren();for(const text of d.limitations){const li=document.createElement('li');li.textContent=text;el('limits').append(li);}
            el('results').hidden=false;
            const legend=d.legends[layer];el('legend').hidden=layer==='none';
            if(legend){el('legend-title').textContent=layer==='elevation'?'DSM surface elevation — '+legend.unit:'DSM-derived surface slope — degrees';el('legend-low').textContent=number(legend.minimum);el('legend-high').textContent=number(legend.maximum)+(layer==='slope'?'°+':' m');el('ramp').style.background='linear-gradient(to right,'+legend.colors.join(',')+')';el('legend-note').textContent=layer==='elevation'?'Fixed full-crop elevation scale across zone selections. This is not lake depth.':'Fixed 0–45° display scale; values ≥45° use the top color. Summary statistics are not clipped.';}
            el('status').textContent='Three '+(mode==='rings'?'disjoint rings':'overlapping cumulative zones')+' analyzed · source sampling approximately 30 m · modeled surface, not surveyed terrain.';
            if(typeof L==='undefined'){el('map-error').hidden=false;el('map-error').textContent='The map library could not load. Tables and exports remain available. Check internet access to unpkg.com.';return;}
            if(!map){map=L.map('map').setView([-22.874,-47.052],15);map.createPane('v6-raster');map.getPane('v6-raster').style.zIndex=350;L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',{maxZoom:19,attribution:'© OpenStreetMap contributors'}).addTo(map);}
            if(zones)map.removeLayer(zones);if(lake)map.removeLayer(lake);
            zones=L.geoJSON(d.zone_geojson,{style:selectedStyle,onEachFeature:(f,l)=>l.bindTooltip(f.properties.inner_distance_m+'–'+f.properties.outer_distance_m+' m · '+mode)}).addTo(map);
            lake=L.geoJSON(d.lake_geojson,{style:{color:'#38cfff',weight:3,fillColor:'#38cfff',fillOpacity:.12}}).addTo(map);
            map.invalidateSize();if(modeChanged||!map._v6Fitted){map.fitBounds(zones.getBounds(),{padding:[15,15]});map._v6Fitted=true;}
            if(layer!=='none'){
                const b=d.raster_bounds_west_south_east_north;
                const url='/api/spatial-context/raster?mode='+mode+'&distance='+distance+'&layer='+layer;
                const overlay=L.imageOverlay(url,[[b[1],b[0]],[b[3],b[2]]],{interactive:false,opacity:.9,pane:'v6-raster'});
                overlay.on('error',()=>{if(current===revision){el('map-error').hidden=false;el('map-error').textContent='Raster overlay unavailable. Outlines, tables and exports remain available.';}});
                overlay.addTo(map);raster=overlay;zones.bringToFront();lake.bringToFront();
            }
        }catch(e){if(current===revision){el('results').hidden=true;el('status').textContent=e.message;el('status').className='error';}}
    }
    el('filters').addEventListener('submit',event=>event.preventDefault());
    for(const id of ['mode','distance','layer'])el(id).addEventListener('change',update);
    el('fit').onclick=()=>{if(map&&zones)map.fitBounds(zones.getBounds(),{padding:[15,15]});};
    window.addEventListener('message',event=>{if(event.origin===location.origin&&event.source===parent&&event.data?.type==='taquaral:spatial-resize'&&map)requestAnimationFrame(()=>map.invalidateSize());});
    update();
})();
