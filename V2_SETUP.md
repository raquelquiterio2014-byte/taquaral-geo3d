# V2 — Connected Spatial Exploration

V2 connects the existing 2D measurements to a Copernicus Digital Surface Model. It is independent of the historical thesis-based V3 explorer.

## Update the working PyCharm project

1. Stop the server with Ctrl+C and keep a backup copy of the working project.
2. Copy `main.py` and `connected_exploration.py` into the project root.
3. Copy `assets/connected_exploration.html` and `assets/connected_exploration.js` into `assets`.
4. Copy the supplied `data/processed/taquaral_surface.tif` into the same relative path. This small crop is sufficient; the 41 MB source tile is not needed at runtime. Keep the existing surface metadata. Alternatively, regenerate with `python build_surface_3d.py`.
5. Install or update the existing dependencies:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m uvicorn main:app --reload
```

6. Open http://127.0.0.1:8000 and refresh with Ctrl+F5.

The ZIP also contains the existing V3 files and the generated V1 3D HTML viewer. If installing into a fresh folder, copy all files and create a new virtual environment as documented in README.md. No `.venv` is included.

## Use and manual verification

- Select Measure distance on the 2D map and choose A and B. Open **V2 · Connected Exploration**: the same coordinates should appear with the A–B surface trace, endpoint elevations and profile.
- In V2, select **Select A–B**, click two surface grid locations, then return to **Map & Measurements**: the A–B markers and distance should match the shared coordinates. Surface selections snap to pixel centers; map clicks retain their selected coordinates.
- **Clear selection** clears both views and hides the profile. Changing tabs preserves selections and the 3D camera.
- A point outside the cropped study area keeps the 2D geodesic result and shows an actionable V2 message. Missing/no-data cells appear as gaps, not zero elevations.
- Check the layout and chart resize in a narrow browser window. The title and sources remain visible in the iframe.
- Historical Bathymetry should still show the independent V3 thesis-based panel and its CSV/JSON downloads.

These manual visual checks remain pending on the author's Windows installation; browser rendering was not validated in the build environment.

## Source and interpretation

The crop is derived from Copernicus DEM GLO-30 Public, prepared on 26 October 2026. It is a Digital Surface Model, approximately 30 m nominal sampling, with EGM2008 elevations. Horizontal offsets use WGS 84 / UTM zone 23S (EPSG:32723), with the same study-center origin as V1.

The profile follows the WGS 84 ellipsoidal geodesic with sample intervals at most 30 m and nearest-cell extraction. More samples do not add source detail. The chart has independent axes, while the 3D scene uses equal spatial scaling. No route distance, ground survey or underwater surface is inferred.

The OSM lake outline and selected points/path are displayed 1 m above the sampled DSM to remain visible. This display lift never changes the reported elevations. Over-water DSM values are model values, not water depth or surveyed water level. Source geometry and DEM resolution differ, so the outline and apparent surface features may not align precisely.

## API

- `/connected-exploration`: dashboard V2 view (shared state requires opening from the dashboard).
- `/api/surface-scene`: DSM grid and sampled OSM lake outline.
- `/api/surface-point?lat=...&lon=...`: point elevation and UTM offsets (null elevation for missing/outside cells).
- `/api/surface-profile?lat1=...&lon1=...&lat2=...&lon2=...`: geodesic sampled profile with source/method.

## Publication boundaries

- **V1 Part 3:** first integrated browser 3D surface viewer.
- **V2:** connected selection between 2D and 3D, draped OSM outline and modeled surface elevation profile.
- **V3:** historical bathymetry from Hernández Piedrahíta's thesis, source figure and published metrics. V2 does not use thesis depths to build its surface.

Post numbers follow version numbers; V1 alone has Parts 1–3. Do not describe V2 as a measured bathymetric reconstruction or reuse the V3 historical depths as V2 results.
