# Lake-only measurement selection

A and B must lie inside or on the mapped OpenStreetMap lake polygon (relation/17154522). The A–B ellipsoidal geodesic must remain inside that geometry. Interior rings are excluded. The server checks a geodesic polyline with chords at most 1 m long; this checking interval does not increase the accuracy of the OSM boundary or the approximately 30 m Copernicus DSM.

Both the 2D map and the connected 3D view reject invalid picks before committing them. A rejected B leaves A selected. No coordinate is snapped onto water. The `/api/distance`, `/api/surface-point`, and `/api/surface-profile` routes enforce the same boundary. All existing measurements using those routes are now lake-only. Clear old selections after updating.

The 3D scene still shows surrounding terrain for context. Zoom towards the cyan outline before selecting points. A click in 3D selects a native raster cell center; shoreline clicks may therefore be rejected. Use the 2D map for more precise coordinate selection. Missing DSM values remain gaps. A profile over the lake reports modeled surface elevations, not water depth or a surveyed water level.

Run `python install_lake_limit.py` in the project root after copying the update files. It modifies the existing main.py rather than replacing its tabs, checks all expected edit locations before writing, and saves main.before_lake_limit.py.bak. Re-running is idempotent.

Validation: 8 frontend tests (DOM/Plotly stubs), 4 Python tests including actual OSM geometry, the two outside coordinates from the screenshot, hole crossing, missing data and installer behavior. Browser verification on the user's Windows installation remains pending.
