# Taquaral Geo3D

An educational Python application for exploring Taquaral Lake and its surroundings
in Campinas, São Paulo, Brazil. It combines an interactive map, geodesic measurements
and a browser-based 3D surface viewer.

**Latest delivery: V3 — Historical Bathymetry — Published Data Explorer.**

V1 Parts 1–3 remain available. V1 completion tasks and V2 spatial synchronization remain pending; version numbers do not imply those tasks are finished.

## Implemented features

| V1 milestone | Delivered behavior |
| --- | --- |
| Part 1 — Interactive Mapping | Leaflet/OpenStreetMap basemap, navigation, coordinate inspection |
| Part 2 — Geospatial Measurements | Downloaded water polygons, highlighted lake boundary, area and outer boundary metrics, selectable points A–B and geodesic distance |
| Part 3 — Integrated 3D Surface Exploration | Copernicus GLO-30 processing, interactive Plotly surface, Map & Measurements and 3D Surface views in one FastAPI dashboard |

The application interface is in English. The thesis figure retains its original Portuguese labels, with English explanations provided alongside it. A map click is an approximate selection, not a
surveyed reference. Switching dashboard views preserves the measurement state.
The map and 3D view are not yet spatially synchronized.

## Run locally

Use Python 3.12 and a virtual environment. In Windows PowerShell:

```powershell
git clone https://github.com/raquelquiterio2014-byte/taquaral-geo3d.git
cd taquaral-geo3d
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe build_surface_3d.py
.\.venv\Scripts\python.exe -m uvicorn main:app --reload
```

Open **http://127.0.0.1:8000** and leave the server terminal running.
Use Ctrl+C to stop the server. The existing GeoJSON snapshot is included, so
the map measurements work without downloading OSM data again.

The first `build_surface_3d.py` run downloads an approximately 41 MB elevation tile,
clips the study area and creates `outputs/taquaral_surface_3d.html`. The dashboard's
3D tab requires this generated file. Without it, the route returns an explanatory
404. Source raster files, processed rasters and generated HTML are not committed;
the scripts regenerate them. An internet connection is required for dependency
installation, the initial elevation download, Leaflet and OpenStreetMap tiles.
Once generated, the standalone 3D HTML can also be opened without FastAPI or internet.

To refresh the water snapshot deliberately:

```powershell
.\.venv\Scripts\python.exe download_data.py
```

This replaces the local water snapshot and metadata. OSM edits may change the
number of candidates or numerical results. Identify and inspect the lake again.
`integrate_dashboard.py` is the original migration helper; integration is already
present in `main.py`, and the helper exits without changing an integrated file.

## API

| Method and route | Purpose |
| --- | --- |
| GET `/` | Integrated dashboard |
| GET `/api/water-features` | Local GeoJSON water snapshot |
| GET `/api/lake-metrics` | Area, outer/inner boundary lengths and method |
| GET `/api/distance?lat1=...&lon1=...&lat2=...&lon2=...` | WGS 84 geodesic distance in meters |
| GET `/surface-3d` | Generated 3D HTML viewer |
| GET `/historical-bathymetry` | V3 published historical data explorer |
| GET `/historical-bathymetry/figure` | Thesis Figure 3 with source attribution |
| GET `/api/historical-bathymetry` | Historical results, provenance and limitations |
| GET `/api/historical-bathymetry/export?format=csv` | CSV download with provenance per metric |
| GET `/api/historical-bathymetry/export?format=json` | Complete JSON download |
| GET `/docs` | FastAPI API documentation |

## Data, methods and limitations

- **Water geometry:** OpenStreetMap contributors, snapshot downloaded on 26 October
  2026. Eleven nearby water polygons are included. The target lake is OSM
  `relation/17154522`, named Lagoa Isaura Teles Alves de Lima in the snapshot.
- **Lake measurements:** PyProj geodesic calculations on the WGS 84 ellipsoid;
  water area subtracts interior rings, while the outer boundary excludes them.
  Snapshot results round to **150,766 m²**, **15.08 ha** and **2,772 m** of outer boundary.
  Zero interior rings in this polygon does not prove that physical islands are absent.
- **A–B distance:** shortest ellipsoidal surface distance, not a walking route or
  a terrain-following 3D distance. The displayed line is a visual connection.
- **3D surface:** Copernicus GLO-30 Public, approximately 30 m sampling. Geographic
  raster coordinates are converted to WGS 84 / UTM zone 23S (EPSG:32723) for
  horizontal offsets in meters. Elevations reference EGM2008. No vertical exaggeration.
- The elevation model is a **Digital Surface Model**, potentially influenced by
  vegetation and buildings. It is **not bathymetry**, individual-tree reconstruction
  or a bare-earth survey. The study rectangle is not the official park boundary.
- Source accuracy has not been independently established. Decimal display precision
  and passing software tests do not establish survey accuracy.

### Sources and attribution

- Map and vector data © [OpenStreetMap contributors](https://www.openstreetmap.org/copyright),
  available under ODbL. Keep the attribution and applicable database licence terms.
- [Copernicus DEM GLO-30 Public via AWS Open Data](https://registry.opendata.aws/copernicus-dem/).
  Check the dataset's licence and attribution terms when redistributing derived products.
  Copernicus DEM attribution: © DLR e.V. 2010–2014 and © Airbus Defence and Space GmbH 2014–2018.
- Dataset details: [Copernicus DEM documentation](https://copernicus-dem-30m.s3.amazonaws.com/readme.html).
- Local acquisition and processing metadata are retained beside the data.

## Verification

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest -q
```

At initial publication, **9 automated tests passed** on Python 3.12: dashboard view
presence, snapshot identification and metrics, distance symmetry and identical
points, invalid coordinates, interior-ring subtraction and a missing-viewer response.
All supplied Python files also passed syntax compilation. These are software checks,
not independent validation of geographic source accuracy. Browser execution on Windows
was demonstrated by the project author's screenshots; automated browser checks are not included.

The snapshot-specific tests intentionally detect changes to the reference data.
Review expected values when refreshing the dataset.

## Roadmap and publication numbering

Only **V1** has three publication parts. Subsequent post numbers match software versions.

| Version | Scope | Status |
| --- | --- | --- |
| V1 | Mapping, measurements and integrated 3D surface | Current prototype; POIs, export buttons, further validation and documentation refinements remain |
| V2 | Lake overlay on 3D, synchronized A–B points, elevation profile | Planned |
| V3 | Historical Bathymetry — Published Data Explorer | Delivered within this scope: thesis metrics, historical map, provenance and exports; underwater reconstruction excluded |
| V4 | Environmental Monitoring | Planned |
| V5 | Change Analysis | Planned; depends on comparable campaigns |
| V6 | Advanced Spatial Analysis | Planned; detailed datasets subject to availability |
| V7 | Satellite Monitoring | Planned; not implemented in this repository |
| V8 | History & Heritage | Research prepared separately; not installed in this dashboard |

## Project files

```text
main.py                         # FastAPI dashboard and measurements
download_data.py                # OSM water-data acquisition
build_surface_3d.py              # Elevation download, crop and Plotly viewer
integrate_dashboard.py          # Idempotent integration migration helper
data/raw/                       # Water snapshot and acquisition metadata
data/processed/                 # Surface processing metadata; generated raster
outputs/                        # Generated standalone 3D HTML
tests/                          # API and measurement checks
```

Developed by **Raquel Cruz** as a learning and portfolio project.


## V3 — Historical Bathymetry — Published Data Explorer

This work is being developed based on data published in the doctoral thesis by Esperanza Hernández Piedrahíta (USP, 2002). The Historical Bathymetry tab reports historical summary values and provenance, not current lake measurements or a reconstructed underwater surface. See [V3_SETUP.md](V3_SETUP.md) for source page numbers, unresolved station-depth discrepancies and update instructions.

The source data are in `data/references/historical_bathymetry.json`; `/api/historical-bathymetry` exposes them with their limitations. The specific bathymetric survey date is unconfirmed. V2 remains planned. Underwater surface reconstruction is outside the agreed V3 scope and requires a separate future data/method evaluation.


### V3 acceptance and attribution

- English historical-data panel with direct attribution to Esperanza Hernández Piedrahíta (USP, 2002).
- Five published summary metrics, exact source pages, and the Figure 3 reference image with a full-size link.
- Separate thesis defense year, water-sampling year, and unconfirmed bathymetric survey date.
- Explicit station-depth discrepancy, original map labels, and geometry/source limitations.
- CSV and JSON exports carry provenance and limitations; invalid export formats return 422.
- Existing OSM and geodesic functions remain available. Software tests do not validate historical survey accuracy.

The original thesis is available at https://teses.usp.br/teses/disponiveis/18/18139/tde-01122016-130125/pt-br.html . Figure 3 is an attributed excerpt for study and analysis; the full thesis is not bundled. Consult the source for reuse conditions. The historical map is not a georeferenced layer and is not evidence of current depths.

V3 verification: **14 automated tests passed** on Python 3.12, covering existing geodesic functions, historical attribution, figure serving, provenance-preserving exports and format validation. Automated browser review could not run in the build environment; visual confirmation on the author's Windows installation remains pending.
