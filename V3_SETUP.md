# V3 — Historical Bathymetry — Published Data Explorer

This work is being developed based on data published in the doctoral thesis by Esperanza Hernández Piedrahíta (USP, 2002).

This delivery adds a Historical Bathymetry tab and source/provenance endpoints. The agreed V3 scope is delivered: historical metrics, source map, provenance, consistency notes and CSV/JSON exports. Underwater surface reconstruction is outside this release.

## Update the working PyCharm project

1. Stop Uvicorn with Ctrl+C.
2. Keep a copy of the working project in a separate backup folder.
3. Copy `main.py`, `historical_bathymetry.py` and the `data/references` and `assets` folders from this package into the working project, preserving their paths. Optional tests and documentation can also be copied. Do not replace the virtual environment.
4. Start the server from the project root:

```powershell
.\.venv\Scripts\python.exe -m uvicorn main:app --reload
```

5. Open http://127.0.0.1:8000 and select Historical Bathymetry. Refresh with Ctrl+F5 if needed.

The archive includes the original map data and generated 3D HTML viewer, so it can also be extracted into a separate project folder. A new folder needs its own Python environment and the dependencies in requirements.txt. The large source elevation tile is omitted; build_surface_3d.py can download it again.

## Routes

- `/historical-bathymetry`: English historical results panel.
- `/api/historical-bathymetry`: historical results, provenance, unresolved discrepancies and limitations.

## Evidence

Original source: https://teses.usp.br/teses/disponiveis/18/18139/tde-01122016-130125/pt-br.html

Printed page 20 (PDF page 43): method and morphometric summary. Printed page 22 (PDF page 45): Figure 3 depth classes. Printed page 21 (PDF page 44): station depths in methods, differing from the abstract. Water sampling occurred in 2000; the specific bathymetric survey date is unconfirmed.

Summary values are transcribed, not recalculated from the OSM polygon. Do not combine the historical mean depth with the current OSM area to claim a measured water volume or infer change by comparing unrelated geometries. No station coordinates have been invented. Figure 3 is included with attribution for source-based study and analysis; the complete thesis PDF is not redistributed. The original Portuguese labels and colors are preserved, with English explanations alongside the image. The figure is not georeferenced and is not overlaid on OpenStreetMap.

## Figure update

Copy the complete `assets` folder as well as the updated Python and reference files. The panel now displays Figure 3 with a full-size image link and English label explanations. No new Python dependencies are required.

## Exports

Use Download CSV or Download JSON at the top of the V3 panel. Both files contain historical status, source attribution and limitations. CSV uses a UTF-8 BOM for Excel compatibility. No new dependencies are needed when updating an existing working V3 installation.
