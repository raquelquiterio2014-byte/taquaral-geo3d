# Taquaral Geo3D — final educational edition

The development series concludes at **V8 — History & Heritage**. The package preserves all delivered V1–V7 modules. Closing the series is a scope decision, not a certification of scientific accuracy or production readiness.

| Version | Delivered scope | Source / period |
| --- | --- | --- |
| V1 · Parts 1–3 | Interactive map, geodesic measurements, integrated 3D surface viewer | OSM snapshot; Copernicus GLO-30 DSM |
| V2 | Connected 2D/3D A–B selection constrained to lake geometry; modeled surface profile | OSM geometry and Copernicus DSM |
| V3 | Published historical bathymetry metrics and original figure | USP thesis, defended 2002; survey date not established |
| V4 | Historical water-quality explorer | 48 reviewed surface records, six dates, two stations, campaigns in 2000 |
| V5 | Historical campaign comparison | Descriptive comparisons of the same reviewed V4 records |
| V6 | Buffer/ring elevation and surface-slope analysis | Copernicus DSM, approximately 30 m sampling; OSM water polygons |
| V7 | Historical satellite comparison | Three selected Sentinel-2 acquisitions from 2025; optional separate aerial reference |
| V8 | Historical timeline, reading notes, bibliography and matching CSV/JSON exports | Municipal, academic and institutional sources checked October 30, 2026 |

## What the final edition does not establish

- Current lake depth, updated water volume, underwater reconstruction or changes in bathymetry.
- Current water quality, pollution, safety or regulatory compliance.
- Detailed bare-earth terrain or a local LiDAR analysis. No LAS/LAZ point clouds are integrated.
- Live satellite video or automatic acquisition updates.
- Historically georeferenced shorelines, causal environmental attribution or independently verified legal/land-transfer history.

The original V1 ideas for extra POIs and other completion refinements were not fully implemented. They remain outside this final edition, not promised next releases. Source datasets retain their own rights. Historical public sources are not automatically public-domain content.

## Validation and practical limits

All existing Python and JavaScript checks plus the V8 source-linkage, date/filter/export and HTML-safety checks are run for the final package. Their final counts are recorded in `docs/V8_SETUP.md`. Automated checks verify application behavior and consistency, not independent historical truth or field accuracy.

Screenshots supplied by the author demonstrate prior modules running on Windows. The final V8 browser layout, links and navigation still require the manual checklist in `docs/V8_SETUP.md`. No successful browser interaction check is claimed from the build environment.

## Reproducibility

The ZIP preserves scripts, small public data snapshots, source excerpts and the generated V1 standalone 3D HTML in `outputs`. GitHub preserves source and small data; the large generated viewer is excluded there and can be regenerated with `build_surface_3d.py`. No virtual environment, IDE state, caches or backups are distributed.

The original source elevation tile is not bundled. Rebuilding the viewer from the public source may require an approximately 41 MB download. The included crop supports the current V2/V6 analyses. Map libraries/tiles, external source links and the optional aerial WMS need internet; the V8 guide and its exports do not.
