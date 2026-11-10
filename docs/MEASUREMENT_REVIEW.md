# Measurement validation — peer-feedback review

Reviewed November 10, 2026. This is a validation supplement to the final educational V1–V8 edition, not V9, a new survey, or a claim of current environmental monitoring.

## Feedback supplied by the project author

> Two checks I would add: use covers instead of contains for the polygon test, since contains rejects points exactly on the boundary, and test the full A-B segment against the polygon, because a concave shoreline can have both endpoints inside while the line crosses land. Also compare your geodesic distance against a planar UTM distance on a few pairs as a sanity test, and check DEM nodata values along the profile.

> Fair point: agreement only validates the calculation, not the source geometry. For positional accuracy I’d compare the lake boundary against an independent reference, such as an authoritative survey layer, and measure the offset on a few control points. For the UTM check, within a single zone I’d expect agreement on the order of 0.1%; a larger gap points to a bug or a zone crossing.

The commenter identity and comment URL were not supplied for this record. The text is reproduced from the feedback supplied by the project author, not presented as a formal external certification.

## Assessment and implementation

| Suggestion | Assessment | Implementation / evidence |
| --- | --- | --- |
| Use `covers` for boundary-inclusive selection | Valid for the intended selection policy; a polygon does not `contain` a point exactly on its boundary | Already implemented in `lake_constraint.py`. New regression tests explicitly compare `contains` and `covers` for exact corners and edge points. |
| Check the full A–B path, not only endpoints | Valid; concave shores and interior holes can invalidate a connection | Already implemented: WGS 84 geodesic densified into chords no longer than 1 m, then the entire LineString is checked with `covers`. New concavity, narrow-hole and HTTP regressions added. |
| Compare geodesic and UTM planar distances | Useful local consistency check, not an independent test of source position | New `measurement_validation.py`, JSON/CSV report, six distinct diagnostic pairs derived from the lake polygon and endpoint API agreement tests. |
| Inspect missing DEM values along the profile | Valid; absence must not be converted to zero or silently interpolated | Existing masked raster read and finite-value sampling preserve nulls. New intermediate sentinel, NaN, ±infinity and all-invalid regressions. Valid numeric zero remains zero. Existing Plotly `connectgaps:false` is retained. |
| Compare the boundary with independent authoritative survey controls | Valid in principle, conditional on a suitable independent reference | NOT PERFORMED. The project supplies no independently verified survey layer and matched controls. The report explicitly records zero control points and `NOT_VALIDATED` positional accuracy. |
| Expect approximately 0.1% within one UTM zone | A reasonable loose diagnostic for short local pairs here, not a universal bound or error classifier | Both endpoints use EPSG:32723, never different UTM coordinate frames. The report includes local projection scale factors. Differences exceeding the diagnostic limit require investigation; they do not alone establish a bug or zone crossing. |

`covers` includes the boundary; this is a mathematical policy on the supplied geometry, not proof that the mapped shoreline is correct. A positive-distance path is tested as a continuous piecewise-linear geometry, not just a set of sampled points. The ellipsoidal curve is still numerically approximated in longitude/latitude; the 1 m chord length is not a claim of 1 m positional accuracy. Mapped holes are excluded from the interior; their boundaries remain admissible under `covers`.

## Reproduce

From the project folder, Windows PowerShell:

```powershell
.\.venv\Scripts\python.exe measurement_validation.py
.\.venv\Scripts\python.exe -m pytest -q
node --test tests/*.cjs
```

Install `requirements-dev.txt` before running Python tests. Node is needed only for the JavaScript tests. The report command writes `outputs/measurement_validation/report.json` and `pairs.csv`. The V2 **Source, method and limits** section links to `/api/measurement-validation` and its CSV export. The endpoint reads local files; it does not request a new survey.

The reviewed snapshot is preserved at `data/references/measurement_validation_review.json`, including source file hashes and runtime versions. New data or library versions can produce small differences. The live local endpoint recomputes when the GeoJSON or crop modification time changes.

## Observed results for this data snapshot

| Pair | Geodesic (m) | Raw UTM grid (m) | Relative difference (%) |
| --- | ---: | ---: | ---: |
| local-1 | 56.343 | 56.351 | 0.014817 |
| local-2 | 95.166 | 95.180 | 0.014497 |
| local-3 | 253.035 | 253.073 | 0.014891 |
| local-4 | 506.073 | 506.147 | 0.014715 |
| local-5 | 748.351 | 748.461 | 0.014701 |
| local-6 | 964.719 | 964.861 | 0.014730 |

All six paths pass the existing mapped-lake constraint. None of these particular profiles encounters a missing sample. The synthetic raster tests exercise missing-value behavior independently; absence of missing values on six paths does not prove completeness of the DSM. Actual numerical zero is not treated as absence.

The maximum relative difference is approximately **0.014891%**. Sampled local grid scale factors are approximately **1.0001448–1.0001498**, consistent with a small positive raw-grid distance difference. The script samples factors at 11 points along each short geodesic for interpretation; this is not a rigorous global error bound. Zero-length pairs have no relative-error percentage. The diagnostic rejects non-finite coordinates, coordinates outside EPSG:32723's area of use, and paths exceeding 2.5 km.

These are ellipsoidal surface versus projected-grid calculations, not measured terrain distances. Elevation-to-ground scale corrections are not applied. PyProj/PROJ supplies both methods, so this is a cross-method consistency check rather than an independent metrological validation.

**206 Python tests and 21 JavaScript tests passed**, including 17 new Python review cases. No new browser rendering verification or field validation is claimed.

## What positional validation would require

A future review would need an independently sourced, documented authoritative shoreline or survey reference with known CRS, datum, acquisition date and uncertainty. Independence includes checking lineage: imagery or geometry used to create the OSM outline cannot automatically be treated as an independent check.

Matched, identifiable locations must be selected across the boundary. Water level, acquisition epoch, shoreline movement, reference registration and matching uncertainty matter. Distances to a nearest edge alone may hide systematic matching problems; control-point offsets, directional residuals and a documented sampling strategy should be examined. A handful of offsets supports only a limited check, not a blanket positional-accuracy certification. No offsets or positional RMSE have been fabricated here.

## Documentation used

- Shapely `covers`: https://shapely.readthedocs.io/en/stable/reference/shapely.covers.html
- Shapely `contains`: https://shapely.readthedocs.io/en/stable/reference/shapely.contains.html
- PROJ UTM: https://proj.org/en/stable/operations/projections/utm.html
- PyProj `Proj.get_factors`: https://pyproj4.github.io/pyproj/stable/api/proj.html
- Rasterio masks: https://rasterio.readthedocs.io/en/stable/topics/masks.html
