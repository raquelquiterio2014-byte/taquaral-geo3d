# V8 — History & Heritage · final educational edition

V8 adds a sourced historical reading guide and concludes the development series at V1–V8. It does not add live satellite services, LiDAR, current water-quality monitoring or new bathymetric measurements.

## Windows update

Stop Uvicorn with Ctrl+C. Make a backup outside the project folder. Copy the package contents into the working project, replacing matching source files. Keep the existing `.venv` and generated `outputs` files.

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m uvicorn main:app --reload
```

Open http://127.0.0.1:8000, press Ctrl+F5 and choose **V8 · History & Heritage**. The source catalog, timeline, filters and exports work locally without external scripts or online source retrieval. Source links require internet. Other map modules still require their existing map-library/basemap services.

## Historical scope

The guide contains 10 records, 5 sources and 4 uncertainty notes. A record means a curated claim documented by a cited source, not independently certified history. English summaries keep event dates separate from source publication dates. Year-only dates remain year-only; no day or month is invented.

- Names and park identity: 1950 naming instrument, 1972 inauguration, 2024 designation honoring an architect.
- Culture and science education: 1981 planetarium proposal, 1982 partnership and 1987 opening.
- Research: 2000 campaigns and 2002 doctoral defense; online publication occurred in 2016.
- Infrastructure: reported 2016 sediment removal and an August 2025 paving progress report.

The 1950 and 2024 laws are reported through municipal accounts; full original legal instruments were not independently inspected. The planetarium's exact opening day comes from its affiliated author's 2003 conference abstract and the month/year is corroborated by Unicamp. No visitor opening hours or current condition claims are included.

The thesis's 1968 lake-construction account and the earlier park-naming reference have not been reconciled. Land-transfer details and the separate lake-naming instrument remain outside verified scope. Dredged sediment volume is not water volume. Reported aims of paving are not measured environmental outcomes. No archival photograph rights are assumed: this module uses textual summaries and source links only.

## Browser acceptance checks

1. Open all nine dashboard tabs; V1–V7 should retain their existing functionality.
2. Open V8 and inspect the 10 timeline cards, especially year-only labels.
3. Filter Culture & science education from 1982 to 1987: two records should remain.
4. Search for planetarium. Then clear filters to restore all records.
5. Submit with empty year fields: the page should remain usable.
6. Check CSV and JSON use the same filters; CSV includes provenance. Empty results retain column headers.
7. Expand source catalog and open links. Some municipal portal pages may render differently; the local bibliography records the reviewed source and access limits.
8. Read uncertainty notes and the project-conclusion table. Check narrow-screen layout and scrolling in the parent iframe.

## API

- GET `/history-heritage`: HTML guide with GET form filters.
- GET `/api/history-heritage`: JSON guide with selected events.
- GET `/api/history-heritage/export?format=csv` or `format=json`: matching exports.
- Shared optional filters: `category` (`identity`, `culture`, `research`, `infrastructure`), `q` (maximum 120 characters), `start_year`, `end_year` (1500–2100). Empty form years mean no limit; inverted ranges and unknown categories return 422.

Missing/malformed references or unlinked source IDs return an actionable 503; no historical material is invented to fill a gap. Original source titles are retained for traceability. Full external texts and photographs are not redistributed.

## Closing the project

The series is concluded as an educational portfolio prototype. The status table describes delivered scopes without claiming all original V1 refinements or field validation. V7 remains a curated historical sample, not a live or automatically refreshed archive. LiDAR remains absent. See `PROJECT_CONCLUSION.md` for the module inventory and verification limits.

## Final automated verification

189 Python tests and 21 JavaScript tests passed. The V8 checks cover provenance integrity, date precision, matching filters/exports, empty form fields, invalid ranges, missing or broken reference data, escaped search text, empty results and tab integration. The V8 page needs no JavaScript. Browser layout and navigation remain subject to the manual acceptance checks above.
