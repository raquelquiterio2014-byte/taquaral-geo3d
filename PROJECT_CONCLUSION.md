# Taquaral Geo3D — final educational edition

## Project conclusion — V8 educational edition

Taquaral Geo3D concludes its planned educational development series at **V8 — History & Heritage**. The repository integrates the delivered scopes of V1 Parts 1–3 and V2–V8.

**Implementation status:** V1–V8 are implemented within the scope recorded in the version status table. This does not mean that every original roadmap idea was delivered.

**Local acceptance status:** manual browser acceptance remains pending as documented in the version setup files. Earlier author-supplied Windows screenshots demonstrate selected views, but do not establish complete acceptance of the final integrated edition.

**Series status:** closed at V8. Remaining acceptance checks concern the delivered edition; they do not imply a planned V9 or a commitment to implement omitted features.

Extra V1 POIs and completion refinements, additional V4 depth records and user CSV upload are not included in the final edition. They are outside its committed scope unless a separate future extension is explicitly approved and documented.

Closing the series does not certify geographic accuracy, historical truth, current environmental conditions or production readiness.

## Version status

The authoritative V1–V8 implementation and local acceptance table is maintained in [README.md — Version status and publication numbering](README.md#version-status-and-publication-numbering). This conclusion uses the same status definitions; it does not maintain a separate roadmap.

## Limitations and validation status

### Data and interpretation

- **Different periods and sources:** OSM download dates, DSM preparation dates, satellite acquisition dates, historical sampling dates and source publication dates are distinct. The modules do not form a contemporaneous environmental survey.
- **V1–V2:** geodesic distances are not walking routes or terrain-following distances. Copernicus GLO-30 is a Digital Surface Model with approximately 30 m sampling and EGM2008 elevations; it may include vegetation and buildings. Over-water model elevations are not lake depths.
- **V3:** published bathymetry summaries and Figure 3 are historical reference material. The bathymetric survey date is unconfirmed, station-depth discrepancies remain documented, and the figure is not georeferenced. Historical depth must not be combined with the OSM area to claim a measured current volume.
- **V4–V5:** the dataset contains 48 reviewed surface observations from 2000. Transcription was AI-assisted and visually checked, without an independent second review or revalidation of field instruments. Two dates per campaign do not establish representative seasonal means, significance, causation or long-term trends.
- **V6:** buffers and rings are analytical geometries, not legal boundaries. DSM-derived surface slope is not bare-earth terrain slope, drainage direction or flood risk. Cumulative zones overlap and must not be summed. Missing or excluded cells are not zero values.
- **V7:** three curated acquisitions from 2025 are a historical sample, not a live feed or complete archive. RGB sampling is 10 m and SCL sampling is 20 m. Cloud screening is imperfect. The shared OSM outline does not establish historical shoreline change. Image color does not establish depth, pollution or water chemistry.
- **V8:** timeline entries are attributed summaries, not independently certified history. Unresolved legal, naming, chronology and land-transfer questions remain explicit. Reported infrastructure objectives are not measured environmental outcomes.

No module establishes current lake safety, water quality, regulatory compliance or survey-grade accuracy. Source materials retain their own reuse and attribution conditions.

### Software verification and local acceptance

The [V8 setup](docs/V8_SETUP.md) records **189 passing Python tests and 21 passing JavaScript tests** for its delivery snapshot. Earlier counts belong to earlier delivery snapshots and must not be added together or presented as fresh verification of a later revision.

Automated checks establish tested application behavior and internal consistency. JavaScript tests using DOM or library stubs do not establish rendered browser behavior. They do not independently validate geographic accuracy, historical claims or original field measurements.

Manual acceptance remains pending under the version setup checklists. For the final edition, review all nine dashboard tabs, shared A–B behavior, maps and overlays, filters, errors, exports, source links and narrow-screen layouts. Record the tested commit, environment, date and outcome before changing an acceptance status to confirmed.

### Local runtime requirements

A fresh GitHub installation must generate `outputs/taquaral_surface_3d.html` with `build_surface_3d.py`; the generated viewer is excluded from GitHub. Rebuilding may require the approximately 41 MB source elevation download.

The included DSM crop supports V2/V6, and the curated satellite crops support V7. Internet remains necessary for external map libraries, basemap tiles, source links and the optional aerial WMS. The V8 guide and its exports use local reference data.

## Reproducibility

The ZIP preserves scripts, small public data snapshots, source excerpts and the generated V1 standalone 3D HTML in `outputs`. GitHub preserves source and small data; the large generated viewer is excluded there and can be regenerated with `build_surface_3d.py`. No virtual environment, IDE state, caches or backups are distributed.

The original source elevation tile is not bundled. Rebuilding the viewer from the public source may require an approximately 41 MB download. The included crop supports the current V2/V6 analyses. Map libraries/tiles, external source links and the optional aerial WMS need internet; the V8 guide and its exports do not.

## Peer-feedback validation supplement · November 10, 2026

The educational series remains concluded at V8. A post-series review adds reproducible internal distance diagnostics and regression tests without adding a new product version. Read `docs/MEASUREMENT_REVIEW.md` for the supplied comments and assessment. Six local UTM/geodesic comparisons passed the project's 0.1% diagnostic (maximum approximately 0.014891%). Independent positional validation of the source shoreline remains **NOT_VALIDATED**; no authoritative survey/control-point offsets are available. Updated automated suite: 206 Python and 21 JavaScript checks passed.
