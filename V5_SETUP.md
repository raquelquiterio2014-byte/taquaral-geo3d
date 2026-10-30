# V5 — Historical Campaign Comparison

V5 reuses the 48 reviewed V4 surface records without modifying their transcription. It adds descriptive comparisons of two selected campaigns, with E1 and E2 kept separate. No new measurements or additional depth rows are introduced.

## Source grouping checked

The captions and column headings in all four retained source excerpts (annex Tables 4–7) explicitly identify:

| Key | Source period description | Sampled dates in 2000 |
| --- | --- | --- |
| march | Rainy period (chuvoso) | March 13 and 15 |
| may | Intermediate period (intermediário) | May 16 and 18 |
| august | Dry period (seco) | August 9 and 11 |

These are labels in Esperanza Hernández Piedrahíta's USP doctoral thesis (2002), not new climate classifications. Source: printed pages 150–153 / PDF pages 173–176. The app shows the selected parameter's original caption, date/station headings and surface row. Station descriptions are from V4; no station coordinates are inferred.

## Comparisons

- Choose a parameter, baseline campaign A, comparison campaign B, and one or both stations.
- Individual values are shown as markers only, with no interpolation.
- Per station/campaign: n=2, minimum, maximum and a center. Dissolved oxygen, temperature and conductivity use an arithmetic mean. pH uses the median of the reported pH values; it is not mean hydrogen-ion activity.
- Between campaigns: center B minus center A, separately for each station. A is the selected baseline even when later in time than B.
- Within campaigns: last sampled date minus first sampled date.
- Between stations: E2 minus E1 on the exact same sampled date, available only when both stations are selected.
- No percentages are calculated for any parameter. pH differences are pH units; other differences keep their source units.
- Missing/incomplete or invalid source data blocks comparisons rather than filling or zeroing values.
- Display uses up to three decimals for readability, without claiming measurement accuracy. CSV/JSON preserve unrounded computations and provenance. JSON exports the full filtered analysis. Five CSV export sections retain source author/year/link/table/pages, parameter, campaigns, statistic and historical scope; the station-pair CSV is header-only for single-station selections.

Two dates per campaign do not establish representative seasonal means, statistical significance, causation, current conditions, long-term trends, regulatory status or recreational safety. No bathymetric change is calculated. The original transcription remains AI-assisted and visually checked, without independent second review or instrument revalidation.

## Install in the existing working project

1. Stop Uvicorn with Ctrl+C and back up the current project.
2. Copy the package contents (inside the folder containing main.py) over the existing project. Preserve the existing .venv and outputs folder, including outputs/taquaral_surface_3d.html. The generated V1 standalone HTML is not stored in GitHub.
3. This V5 uses the existing dependencies; no new dependency is needed for an up-to-date V4 environment.
4. Restart: `.\.venv\Scripts\python.exe -m uvicorn main:app --reload`
5. Open http://127.0.0.1:8000, press Ctrl+F5, and select **V5 · Campaign Comparison**.

Direct viewer: /campaign-comparison. API: /api/historical-campaign-comparison and /api/historical-campaign-comparison/export.

## Validation and manual acceptance

Validation result: **147 Python tests and 12 JavaScript tests passed** (JavaScript uses DOM/Plotly stubs, not a rendered browser). Automated coverage checks all parameter/campaign/station combinations, baseline reversal, hand-checked arithmetic, pH handling, invalid selections, incomplete-data refusal, exports and V4 preservation. Existing spatial tests now use an inside-lake segment, consistent with the previously introduced lake-only restriction. Raster NoData is tested independently from the HTTP polygon gate.

Manual Windows/browser checks remain pending: load all six dashboard tabs; compare March with August for each parameter; reverse A/B and confirm difference signs; select E1 alone; select identical campaigns and confirm an error with no stale results; download JSON and every CSV; compare source excerpts; check narrow-window layout. Python/API tests and DOM stubs do not establish browser rendering or scientific field accuracy.

Source: https://teses.usp.br/teses/disponiveis/18/18139/tde-01122016-130125/pt-br.html
DOI: 10.11606/T.18.2016.tde-01122016-130125
