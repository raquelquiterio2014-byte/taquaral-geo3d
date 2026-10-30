# V7 — Historical Satellite Explorer

V7 adds a new dashboard tab without replacing V1–V6. All interface text is English.

## Windows setup

1. Stop Uvicorn using Ctrl+C in its terminal.
2. Back up the working project outside the project folder.
3. Copy this package's contents into the existing project, replacing same-named source files. Keep your existing `.venv` and `outputs` directory. The V1 standalone surface HTML is generated, not included in GitHub.
4. From the project terminal:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m uvicorn main:app --reload
```

5. Open http://127.0.0.1:8000 and choose **V7 · Satellite Explorer**. If the previous page remains, press Ctrl+F5.

Three real Sentinel-2 acquisitions are bundled: 2025-10-05, 2025-10-22 and 2025-12-28, tile 23KKQ. No satellite account, API key or automatic download is required to view them. Internet is required for the Leaflet library and street basemap; if Leaflet fails, basic local previews remain available.

## What to test in the browser

- Check all eight tabs still open.
- Select different dates in A and B. Each caption must identify its image, UTC timestamp, satellite, scene cloud percentage and local SCL screening.
- Verify the cyan outline follows the same lake on both maps; it is a single OSM reference, not a historical shoreline estimate.
- Pan/zoom with synchronization checked and unchecked; fit the study area again.
- Toggle the outline. Switch tabs and return; maps should resize correctly.
- Choose the same date: the interface must say it is the same acquisition.
- Open source metadata and download the catalog JSON.
- Inspect at a narrow screen width: panels should stack.

## Data and processing

`prepare_satellite.py` uses public Earth Search item metadata and anonymous HTTPS range requests to crop the provider's TCI and SCL COG assets. The loopback HTTP bridge keeps remote TLS verification in urllib and prevents full-granule fallback. It is used only during preparation; no proxy runs in the dashboard.

The true-color product is the provider's 8-bit TCI, B04/B03/B02, native 10 m sampling. It is already rendered for display, not quantitative reflectance. Native-grid RGB and SCL crops, full source STAC records, display PNGs and processing metadata are in `data/satellite`. Display PNGs are reprojected to Web Mercator with nearest-neighbor sampling and bounds recorded for Leaflet. They do not improve the source resolution. The same display approach is used for every date; no local per-date histogram stretch or cloud removal is applied.

SCL is native 20 m. Classes 3,8,9,10,11 are flagged as shadow/cloud/cirrus/snow; 0/1 are invalid. Percentages are separately calculated over the rectangular crop and SCL pixel centers within the current OSM lake polygon. All pixel centers are the denominator, including invalid pixels; valid coverage is reported separately. Automated classifications are imperfect, especially at shorelines. Low scene cloud cover is not proof of a clear lake.

The included acquisitions were visually inspected as image crops. Browser interaction and overlay alignment still require the Windows manual checks above; automated API/geometry checks do not establish imagery accuracy.

To reproduce downloads (optional; internet and public services required):

```powershell
.\.venv\Scripts\python.exe prepare_satellite.py
```

The example list is a curated three-date sample, not a complete historical archive. Changing dates requires editing IDS and preparing/checking additional images. No free-form date query or automatic archive refresh is implemented.

## Historical interpretation

The thesis supports V3–V5 historical bathymetry and water-quality records. V7 uses separate Copernicus Sentinel observations from 2025, not images extracted from that thesis. No inference validates 2000 water-quality records with 2025 image color. No depth, pollution, water chemistry or causes of apparent change are inferred. The OSM polygon is common to all dates and cannot demonstrate shoreline changes.

## Sources and attribution

- Earth Search public STAC: https://earth-search.aws.element84.com/v1
- AWS Sentinel-2 L2A COG registry: https://registry.opendata.aws/sentinel-2-l2a-cogs/
- Sentinel-2 documentation: https://documentation.dataspace.copernicus.eu/Data/SentinelMissions/Sentinel2.html
- Contains modified Copernicus Sentinel data (2025). Individual item metadata and asset URLs are preserved with each crop.
- Lake outline and street basemap: © OpenStreetMap contributors, relation/17154522, ODbL. https://www.openstreetmap.org/copyright

An optional IGC / IDE-SP aerial preview is available on demand through a button below the satellite comparison. It is downloaded directly from the public WMS when clicked; it requires internet and service availability. It is not bundled as an offline image. It is labeled **aerial orthophoto — 2023/2024**, not satellite. The mosaic interval is not an exact acquisition day. Source GSD 0.25 m is not the resolution of this WMS preview. Its credits and request parameters are preserved; no LiDAR point cloud is included.

## Visual review decision

The 2025-11-21 candidate was excluded: a large bright saturated patch obscures the lake in its TCI, despite SCL flagging 0% cloud/shadow/snow in the lake mask. Its cause has not been established; it is not used as evidence of clear water, water quality or environmental change. This illustrates why SCL screening alone is insufficient.

## Verification

Automated suite: 174 Python tests and 21 JavaScript tests passed for V1–V7. These cover API behavior, source-grid resolution, scene IDs, local SCL counts, missing data, tab integration, date switching, map image pane ordering and library-failure fallback. Browser rendering, synchronized navigation and overlay alignment remain manual acceptance checks.
