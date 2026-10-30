"""Run from the project root; preserves installed V2/V3/V4 tabs."""
from pathlib import Path
import ast
import shutil

MARKER = '# TAQUARAL_LAKE_ONLY_SELECTION'

def update(source):
    if MARKER in source:
        return source
    changes = [
        ('from shapely.geometry import shape', 'from shapely.geometry import shape\nfrom lake_constraint import require_lake_selection'),
        ('    # Geod expects longitude before latitude.', '    require_lake_selection(lat2, lon2, lat1, lon1)\n\n    # Geod expects longitude before latitude.'),
        ('                function selectLocation(latlng) {', '''                let lakeCheckPending = false;
                async function selectLocation(latlng) {'''),
        ('                    const point = L.latLng(latlng.lat, latlng.lng);', '''                    if (lakeCheckPending) return;
                    lakeCheckPending = true;
                    const checkVersion = requestVersion;
                    try {
                        const q = new URLSearchParams({lat:latlng.lat, lon:latlng.lng});
                        if (points.length) { q.set("lat1",points[0].lat); q.set("lon1",points[0].lng); }
                        await fetchData("/api/lake-selection?" + q);
                    } catch (error) {
                        if (checkVersion === requestVersion) {
                            byId("distance-status").textContent = error.message;
                            document.getElementById("connected-frame").contentWindow.postMessage(
                                {type:"taquaral:rejected", detail:error.message}, window.location.origin);
                        }
                        return;
                    } finally { lakeCheckPending = false; }
                    if (checkVersion !== requestVersion || !measuring) return;
                    const point = L.latLng(latlng.lat, latlng.lng);'''),
        ('    return point(lat, lon)', '    require_lake_selection(lat, lon)\n    return point(lat, lon)'),
        ('    return profile(lat1, lon1, lat2, lon2)', '    require_lake_selection(lat2, lon2, lat1, lon1)\n    return profile(lat1, lon1, lat2, lon2)'),
    ]
    for old, new in changes:
        if source.count(old) != 1:
            raise ValueError('Unexpected main.py structure. No changes saved: ' + old[:70])
        source = source.replace(old, new, 1)
    source += '''

# TAQUARAL_LAKE_ONLY_SELECTION
@app.get("/api/lake-selection")
def lake_selection(
    lat: float = Query(..., ge=-90, le=90, allow_inf_nan=False),
    lon: float = Query(..., ge=-180, le=180, allow_inf_nan=False),
    lat1: float | None = Query(None, ge=-90, le=90, allow_inf_nan=False),
    lon1: float | None = Query(None, ge=-180, le=180, allow_inf_nan=False),
):
    return require_lake_selection(lat, lon, lat1, lon1)
'''
    ast.parse(source)
    return source

if __name__ == '__main__':
    root = Path(__file__).resolve().parent
    target = root / 'main.py'
    original = target.read_text(encoding='utf-8-sig')
    result = update(original)
    if result == original:
        print('Lake-only selection is already installed.')
    else:
        backup = root / 'main.before_lake_limit.py.bak'
        if not backup.exists():
            shutil.copy2(target, backup)
        target.write_text(result, encoding='utf-8')
        print('Lake-only selection installed. Restart uvicorn, then press Ctrl+F5.')
