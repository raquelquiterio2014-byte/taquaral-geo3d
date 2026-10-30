# V6 — Spatial Context & Surface Analysis

This initial V6 uses the existing public-data snapshots: the small Copernicus GLO-30 surface crop and the bundled OpenStreetMap water polygons. It adds no LiDAR, land-use classification, new field measurements or thesis-derived elevation data. The thesis remains the source for V3–V5 historical modules.

## Inputs and references

- `data/processed/taquaral_surface.tif` and its metadata: prepared 2026-10-26 from the public Copernicus DSM GLO-30 tile. Approximately 30 m source sampling; elevations reference EGM2008. Preparation/download dates are not acquisition dates. Attribution: © DLR e.V. 2010–2014 and © Airbus Defence and Space GmbH 2014–2018.
- `data/raw/water_candidates.geojson` and its metadata: 11 OSM water polygons, downloaded 2026-10-26. Target: relation/17154522. All mapped water features in this snapshot are excluded. The candidate-selection metadata is retained and visible; this is not a complete, independently surveyed water inventory.
- Input SHA-256 values and source links accompany JSON/GeoJSON and CSV exports.

## Method

1. Validate water polygons, source crop CRS, raster orientation and vertical-reference metadata. No automatic geometry repairs or missing-value filling.
2. Transform lake and water polygons from WGS 84 to **WGS 84 / UTM zone 23S (EPSG:32723)**.
3. Construct 100, 250 and 500 m planar buffers with 32 segments per quadrant, subtract the relevant inner buffer and all mapped water. The geometry follows mapped polygon boundaries, including any interior shorelines; it is not an official park/legal boundary.
4. **Cumulative** mode: 0–100, 0–250 and 0–500 m. Areas/counts overlap; never sum them. **Rings** mode: 0–100, 100–250 and 250–500 m, with no area overlap.
5. Reproject the native geographic DSM onto a 30×30 m UTM grid using nearest-cell sampling. This does not add source detail or improve accuracy.
6. Select cell centers inside each zone. Report elevation minimum, maximum, median, selected/valid counts and missing/excluded counts. Vector area uses projected geometry. Crop coverage is geometric overlap with the source crop, independently of valid-cell counts. It is not an accuracy measure.
7. Compute surface slope in degrees: `atan(hypot(dz/dx, dz/dy))`, using central differences across opposing neighbors. Require the **full 3×3 neighborhood** to be finite and free of mapped water. A conservative **all-touched** water mask excludes cells even partially intersecting water. Borders, water-adjacent neighborhoods and NoData are excluded, not converted to zero. The DSM can contain vegetation and buildings; this is not bare-earth terrain slope.
8. For map display only, warp selected elevation/slope cells to a Web Mercator display grid matching Leaflet. Transparent PNGs represent invalid/unselected pixels. The browser receives geographic corner bounds for placement. Statistics always use the UTM analysis grid. Display pixels can straddle boundaries; no subpixel shoreline precision is claimed.
9. Elevation colors use a fixed full-crop range. Slope colors cover 0–45°; higher values saturate visually but statistics remain unclipped.

The small crop covers the actual 500 m zones. Coverage and valid counts are calculated at runtime, not assumed. Empty zone statistics are null; a missing/invalid/all-NoData source crop produces an actionable 503 response.

## Dashboard

The **V6 · Spatial Context** tab offers zone construction, displayed distance and elevation/slope/outlines-only controls. Source dates, excluded-water count, methods and limitations are visible. Leaflet and OSM basemap tiles require internet access. If the external map library fails to load, tables and exports remain usable with a clear message. Raster-layer failures retain vector outlines and tabular results.

Exports use the selected construction mode and include **all three zones**, not only the currently displayed zone:

- Summary CSV: six rows (three zones × elevation/slope), units, counts, coverage, projected area, sources, dates, SHA-256 and limitations. Null values are blank, not zero.
- Full JSON: summaries, lake and zone geometry, method, source provenance, legends and limitations.
- GeoJSON: three zone features in WGS 84 longitude/latitude; construction CRS, distances, sources, method and limitations retained. Do not treat these as surveyed/legal boundaries.

## Install in the working project

Stop Uvicorn, back up the project and copy the package contents (inside the folder containing `main.py`) into the working project. Preserve the existing `.venv` and `outputs` folder, especially the previously generated V1 3D HTML. The latest code includes V1–V5 and the lake-only selection fixes.

No new application dependency is needed beyond the existing requirements. Restart:

```powershell
.\.venv\Scripts\python.exe -m uvicorn main:app --reload
```

Open http://127.0.0.1:8000, press Ctrl+F5 and select **V6 · Spatial Context**. A fresh installation should follow README.md; generate the standalone V1 viewer separately if required.

## API

- `/spatial-context`: viewer.
- `/api/spatial-context?mode=cumulative` or `mode=rings`: analysis.
- `/api/spatial-context/raster?mode=rings&distance=500&layer=slope`: display PNG. Distances: 100/250/500; layers: elevation/slope.
- `/api/spatial-context/export?mode=rings&format=geojson`: exports; formats json/csv/geojson.

## Validation and remaining browser checks

**169 Python tests and 17 JavaScript tests passed**, including existing V1–V5 coverage. V6 tests check analytical planar/flat slopes; water/NoData stencil exclusion; metric buffer distances; ring disjointness and area conservation; actual snapshot geometry/cell-center medians; all raster control combinations; transparent PNGs; source-preserving exports; invalid queries; unavailable/all-NoData data; partial coverage and empty zone statistics. JavaScript tests use DOM/Leaflet stubs and check controls, exports, stale-response protection and map-library failure behavior.

These checks do not constitute rendered browser verification or field validation. Chromium installation was unavailable in this environment; manual Windows/browser checks remain: all seven tabs, both zone modes, each distance/layer, map alignment and legends, zoom/fit, downloads, narrow-window layout and the existing A–B tool.

No drainage direction, flood risk, erosion probability, bathymetric inference, current-condition classification or legal protection assessment is produced.
