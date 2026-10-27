# V4 — Environmental Monitoring: initial historical water-quality dataset

This initial delivery is based on reviewed surface rows from the doctoral thesis by Esperanza Hernández Piedrahíta (USP, 2002). It is a historical-data explorer, not current monitoring.

## Reviewed scope

48 observations: four parameters × six dates × two stations. Only the depth row **0.0 m** is incorporated. Dates: 13/15 March, 16/18 May and 9/11 August **2000**. Publication/defense year 2002 is stored separately. Source sampling window: 09:00–10:30, timezone unspecified.

| Parameter | Unit | Annex table | Printed page | PDF page |
| --- | --- | --- | --- | --- |
| Dissolved oxygen | mg/L | 4 | 150 | 173 |
| Water temperature | °C | 5 | 151 | 174 |
| pH | dimensionless | 6 | 152 | 175 |
| Conductivity | µS/cm | 7 | 153 | 176 |

Each selected cell was visually checked against the rendered PDF, including column headings for date/station and units. Printed comma decimals are preserved in `value_raw`; machine-readable values use decimal points. Short attributed source-row excerpts are included for review. This was AI-assisted transcription, without independent second review or revalidation of original field measurements.

The remainder of the depth profiles and other tables are not transcribed or incorporated. Unreviewed/blank cells are not replaced by zero. No station coordinates, current conditions, regulatory class, forecast or safety assessment are inferred.

## Update the working PyCharm installation

1. Stop Uvicorn with Ctrl+C and keep a backup of the working project.
2. Copy `main.py` and `environmental_monitoring.py` into the project root.
3. Copy `assets/environmental_monitoring.html`, `assets/environmental_monitoring.js` and the four `assets/thesis_table_*_surface.png` files into the same relative locations.
4. Copy `data/references/historical_water_quality.csv` and `data/references/historical_water_quality_metadata.json` into the same relative locations. Do not edit the reviewed source files casually.
5. Keep all existing V1, V2 and V3 files. No new Python dependency is required for this V4 update.
6. Restart:

```powershell
.\.venv\Scripts\python.exe -m uvicorn main:app --reload
```

Open http://127.0.0.1:8000, refresh with Ctrl+F5 and select **V4 · Water Quality**.

## Use and manual checks

Choose a parameter, station and date range. Graphs display separate markers for each station, with no connecting/interpolated line. Table rows retain date, depth, original printed value and page numbers. Compare each selected parameter against the source-row excerpt. CSV/JSON downloads follow the current filters and preserve provenance. Source review does not imply instrument accuracy.

Check filter changes, chart rendering, exports, narrow-window layout, and that existing V1–V3 tabs continue to work. Browser visual verification is pending on the author's Windows installation.

## Data and API

- `data/references/historical_water_quality.csv`: the 48 reviewed observations with per-record provenance.
- `data/references/historical_water_quality_metadata.json`: scope, source PDF checksum, review method and limitations.
- `/environmental-monitoring`: English V4 viewer.
- `/api/historical-water-quality`: records and metadata; optional `parameter`, `station`, `start`, `end` filters.
- `/api/historical-water-quality/export?format=csv` or `format=json`: filtered downloads.
- `/environmental-monitoring/source-row/4` through `/7`: the relevant attributed source excerpts.

Automatic checks reject invalid units, missing provenance, nonfinite values, duplicate observation keys, source-table/page mismatches and raw/normalized-value inconsistencies. This read-only release does not yet provide user CSV upload, sensors, alerts or the complete thesis dataset.

## Publication boundaries

V2 covers connected spatial exploration and DSM elevation profiles. V3 covers historical bathymetry. V4 covers dated historical water-quality observations from selected thesis tables. Do not present V4 as real-time monitoring, current lake conditions, or the transcription of every thesis table.

Original source: https://teses.usp.br/teses/disponiveis/18/18139/tde-01122016-130125/pt-br.html
