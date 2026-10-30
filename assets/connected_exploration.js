'use strict';
(async function () {
    const el = id => document.getElementById(id);
    const origin = window.location.origin;
    const embedded = window.parent !== window;
    let ready = false, revision = 0;
    let state = {points: [], measuring: false};
    // Lock each 3D pick before postMessage, and explicitly arm B after A.
    // No clock-based debounce: delayed/repeated Plotly events remain blocked.
    const selection = {
        phase: 'idle', pendingCount: null,
        begin() { this.phase = 'waiting_reset'; this.pendingCount = null; },
        clear() { this.phase = 'waiting_clear'; this.pendingCount = null; },
        accept(points, measuring) {
            if (this.phase === 'waiting_reset') {
                if (points.length || !measuring) return;
            } else if (this.phase === 'waiting_clear') {
                if (points.length || measuring) return;
            } else if (this.pendingCount !== null && measuring && points.length <= this.pendingCount) {
                return; // A delayed, unchanged parent state is not an acknowledgement.
            }
            const previous = this.phase;
            this.pendingCount = null;
            state = {points, measuring};
            this.phase = !measuring ? (points.length === 2 ? 'complete' : 'idle') :
                points.length === 0 ? 'a' : points.length === 1 ? (previous === 'b' ? 'b' : 'await_b') : 'complete';
        },
        armB() {
            if (this.phase === 'await_b' && state.measuring && state.points.length === 1) this.phase = 'b';
        },
        pick(lat, lng) {
            if (!state.measuring || !['a', 'b'].includes(this.phase)) return false;
            if (!Number.isFinite(lat) || !Number.isFinite(lng) || Math.abs(lat)>90 || Math.abs(lng)>180) return false;
            const count = this.phase === 'a' ? 0 : 1;
            if (state.points.length !== count) return false;
            if (count && Math.abs(lat-state.points[0].lat)<1e-9 && Math.abs(lng-state.points[0].lng)<1e-9) {
                el('status').textContent = 'Choose point B at a different surface location from point A.';
                return false;
            }
            this.pendingCount = count;
            this.phase = 'pending'; // Synchronous lock precedes the parent message.
            send('taquaral:point', {lat, lng});
            instructions();
            return true;
        }
    };
    const chartOptions = {responsive: true, displaylogo: false};
    const layout = {template: 'plotly_dark', paper_bgcolor: '#10202b', plot_bgcolor: '#10202b',
        font: {color: '#edf5fa'}, margin: {l: 45, r: 35, t: 35, b: 50}};
    async function fetchJSON(url) {
        const r = await fetch(url, {cache: 'no-store'});
        if (!r.ok) { let d; try { d = await r.json(); } catch {} throw new Error(typeof d?.detail === 'string' ? d.detail : 'Request failed: ' + r.status); }
        return r.json();
    }
    function send(type, extra = {}) { if (embedded) window.parent.postMessage({type, ...extra}, origin); }
    function instructions() {
        el('selected').textContent = ['A','B'].map((label,i) => label + ': ' + (state.points[i] ? state.points[i].lat.toFixed(6) + ', ' + state.points[i].lng.toFixed(6) : '—')).join(' · ');
        el('select-b').disabled = !embedded || !ready || selection.phase !== 'await_b';
        el('start').disabled = !embedded || !ready;
        el('clear').disabled = !embedded || !ready;
        el('status').textContent = !embedded ? 'Open this view from the dashboard to share point selections.' :
            selection.phase === 'waiting_reset' ? 'Starting a new selection…' :
            selection.phase === 'waiting_clear' ? 'Clearing selection…' :
            selection.phase === 'pending' ? 'Registering the selected point…' :
            selection.phase === 'a' ? 'Click the surface once to select point A.' :
            selection.phase === 'await_b' ? 'Point A selected. Select the Select point B button before choosing B on the surface, or choose B on the 2D map.' :
            selection.phase === 'b' ? 'Click a different surface location once to select point B.' :
            state.points.length === 2 ? 'A–B selected. The map and V2 share these coordinates.' :
            'Choose Select point A to start. Rotate by dragging; scroll to zoom.';
    }
    async function updateSelection() {
        if (!ready) return;
        const current = ++revision;
        const pts = state.points.map(p => ({...p}));
        instructions();
        el('profile-section').hidden = true;
        // Clear the previous trace immediately, including during a pending request.
        await Plotly.restyle('scene', {x:[[]], y:[[]], z:[[]], text:[[]]}, [2]);
        if (current !== revision || !pts.length) return;
        try {
            let samples;
            if (pts.length === 1) {
                const q = new URLSearchParams({lat:pts[0].lat, lon:pts[0].lng});
                samples = [await fetchJSON('/api/surface-point?' + q)];
            } else {
                const q = new URLSearchParams({lat1:pts[0].lat, lon1:pts[0].lng, lat2:pts[1].lat, lon2:pts[1].lng});
                const data = await fetchJSON('/api/surface-profile?' + q);
                if (current !== revision) return;
                samples = data.samples;
                el('profile-section').hidden = false;
                el('distance').textContent = data.distance_m.toLocaleString('en-US', {maximumFractionDigits:0}) + ' m';
                const showZ = z => z === null ? 'No data' : z.toFixed(1) + ' m';
                el('elevation-a').textContent = showZ(samples[0].elevation_m);
                el('elevation-b').textContent = showZ(samples[samples.length-1].elevation_m);
                el('profile-status').textContent = data.valid_sample_count + '/' + data.sample_count + ' valid samples · spacing ' + data.sample_spacing_m.toFixed(1) + ' m · nearest native cell. EGM2008 surface elevations, not lake depth.';
                await Plotly.react('profile', [{type:'scatter', mode:'lines+markers', x:samples.map(s=>s.distance_m),
                    y:samples.map(s=>s.elevation_m), connectgaps:false, line:{color:'#5de0be'}, marker:{size:3},
                    hovertemplate:'Distance: %{x:.1f} m<br>Modeled surface: %{y:.1f} m<extra></extra>'}],
                    {...layout, xaxis:{title:{text:'Distance from A (m)'}}, yaxis:{title:{text:'DSM elevation — EGM2008 (m)'}}}, chartOptions);
            }
            if (current !== revision) return;
            const labels = samples.map((_,i)=>i===0?'A':i===samples.length-1 && pts.length===2?'B':'');
            await Plotly.restyle('scene', {x:[samples.map(s=>s.east_offset_m)], y:[samples.map(s=>s.north_offset_m)],
                z:[samples.map(s=>s.elevation_m === null ? null : s.elevation_m+1)], text:[labels]}, [2]);
        } catch (e) {
            if (current === revision) el('status').textContent = 'Surface selection unavailable: ' + e.message + ' The 2D geodesic measurement remains available.';
        }
    }
    window.addEventListener('message', event => {
        if (event.origin !== origin || event.source !== window.parent) return;
        if (event.data?.type === 'taquaral:resize') {
            if (ready) requestAnimationFrame(() => {
                Plotly.Plots.resize(el('scene'));
                if (!el('profile-section').hidden) Plotly.Plots.resize(el('profile'));
            });
            return;
        }
        if (event.data?.type !== 'taquaral:state') return;
        const points = event.data.points;
        if (!Array.isArray(points) || points.length>2 || points.some(p=>!Number.isFinite(p.lat)||!Number.isFinite(p.lng)||Math.abs(p.lat)>90||Math.abs(p.lng)>180)) return;
        selection.accept(points, !!event.data.measuring);
        updateSelection();
    });
    el('start').onclick = () => { selection.begin(); instructions(); send('taquaral:start'); };
    el('select-b').onclick = () => { selection.armB(); instructions(); };
    el('clear').onclick = () => { selection.clear(); instructions(); send('taquaral:clear'); };
    instructions();
    try {
        if (typeof Plotly === 'undefined') throw new Error('Plotly could not load. Check the server dependencies.');
        const d = await fetchJSON('/api/surface-scene');
        await Plotly.newPlot('scene', [
            {type:'surface',x:d.x,y:d.y,z:d.z,customdata:d.customdata,colorscale:'Earth', colorbar:{title:{text:'DSM elevation (m)'}},
                hovertemplate:'East offset: %{x:.0f} m<br>North offset: %{y:.0f} m<br>Surface elevation: %{z:.1f} m<extra></extra>'},
            {type:'scatter3d',mode:'lines',name:'Mapped lake outline (display lift +1 m)',...d.lake_line,line:{color:'#38cfff',width:5},connectgaps:false,hoverinfo:'skip'},
            {type:'scatter3d',mode:'lines+markers+text',name:'Shared A–B',x:[],y:[],z:[],text:[],textposition:'top center',connectgaps:false,line:{color:'#ffce67',width:5},marker:{size:4,color:'#ffce67'},hoverinfo:'skip'}
        ], {...layout, uirevision:'v2-camera', scene:{aspectmode:'data', xaxis:{title:{text:'East offset (m)'}},yaxis:{title:{text:'North offset (m)'}},zaxis:{title:{text:'DSM elevation (m)'}},camera:{eye:{x:1.4,y:-1.4,z:1.2}}}}, chartOptions);
        el('scene').on('plotly_click', event => {
            if (!state.measuring) return;
            const p=event.points.find(p=>p.curveNumber===0);
            if (p && Array.isArray(p.customdata)) selection.pick(p.customdata[0], p.customdata[1]);
        });
        ready = true;
        await updateSelection();
        send('taquaral:ready');
    } catch(e) { el('status').textContent = 'Could not load V2: ' + e.message; }
})();
