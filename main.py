import json
import math
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse, Response
from pyproj import Geod
from shapely.geometry import shape
from historical_bathymetry import (load_historical_bathymetry, render_historical_bathymetry,
                                  export_historical_bathymetry_csv)


BASE_DIR = Path(__file__).resolve().parent
WATER_DATA_PATH = BASE_DIR / "data" / "raw" / "water_candidates.geojson"

LAKE_OSM_ID = "17154522"
GEOD = Geod(ellps="WGS84")

app = FastAPI(
    title="Taquaral Geo3D",
    description="Geospatial exploration of Taquaral Lake in Campinas, Brazil.",
)


def read_water_data():
    if not WATER_DATA_PATH.exists():
        raise HTTPException(
            status_code=404,
            detail="Water data not found. Run download_data.py first.",
        )

    try:
        data = json.loads(WATER_DATA_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise HTTPException(
            status_code=500,
            detail="Could not read the water data file.",
        ) from exc

    if (
        not isinstance(data, dict)
        or data.get("type") != "FeatureCollection"
        or not isinstance(data.get("features"), list)
    ):
        raise HTTPException(
            status_code=500,
            detail="Invalid GeoJSON FeatureCollection.",
        )

    return data


def get_lake_feature(data):
    matches = [
        feature
        for feature in data["features"]
        if (feature.get("properties") or {}).get("element") == "relation"
        and str((feature.get("properties") or {}).get("id")) == LAKE_OSM_ID
    ]

    if len(matches) != 1:
        raise HTTPException(
            status_code=422,
            detail="The target lake could not be uniquely identified.",
        )

    return matches[0]


def ring_metrics(ring):
    coordinates = list(ring.coords)

    for coordinate in coordinates:
        longitude, latitude = coordinate[:2]

        if (
            not math.isfinite(longitude)
            or not math.isfinite(latitude)
            or not -180 <= longitude <= 180
            or not -90 <= latitude <= 90
        ):
            raise ValueError("Invalid geographic coordinates.")

    area, perimeter = GEOD.polygon_area_perimeter(
        [coordinate[0] for coordinate in coordinates],
        [coordinate[1] for coordinate in coordinates],
    )

    if not math.isfinite(area) or not math.isfinite(perimeter):
        raise ValueError("Invalid geodesic result.")

    return abs(area), perimeter


def calculate_lake_metrics(feature):
    geometry = shape(feature["geometry"])

    if (
        geometry.is_empty
        or not geometry.is_valid
        or geometry.geom_type not in ("Polygon", "MultiPolygon")
    ):
        raise ValueError("A valid polygon geometry is required.")

    polygons = (
        [geometry]
        if geometry.geom_type == "Polygon"
        else list(geometry.geoms)
    )

    water_area = 0.0
    outer_boundary = 0.0
    inner_boundary = 0.0
    interior_ring_count = 0

    for polygon in polygons:
        area, length = ring_metrics(polygon.exterior)
        outer_boundary += length

        for interior in polygon.interiors:
            hole_area, hole_length = ring_metrics(interior)
            area -= hole_area
            inner_boundary += hole_length
            interior_ring_count += 1

        if area <= 0:
            raise ValueError("Water area must be positive.")

        water_area += area

    return {
        "name": (feature.get("properties") or {}).get("name") or "Taquaral Lake",
        "osm_reference": f"relation/{LAKE_OSM_ID}",
        "water_area_m2": water_area,
        "water_area_ha": water_area / 10000,
        "outer_boundary_m": outer_boundary,
        "inner_boundary_m": inner_boundary,
        "interior_ring_count": interior_ring_count,
        "method": "Geodesic calculation on the WGS 84 ellipsoid",
        "source": "OpenStreetMap contributors",
    }


@app.get("/api/water-features")
def water_features():
    return read_water_data()


@app.get("/api/lake-metrics")
def lake_metrics():
    feature = get_lake_feature(read_water_data())

    try:
        return calculate_lake_metrics(feature)
    except (ValueError, TypeError, KeyError) as exc:
        raise HTTPException(
            status_code=422,
            detail="Could not calculate metrics from the lake geometry.",
        ) from exc


@app.get("/api/distance")
def distance(
    lat1: float = Query(..., ge=-90, le=90),
    lon1: float = Query(..., ge=-180, le=180),
    lat2: float = Query(..., ge=-90, le=90),
    lon2: float = Query(..., ge=-180, le=180),
):
    if not all(math.isfinite(value) for value in (lat1, lon1, lat2, lon2)):
        raise HTTPException(
            status_code=422,
            detail="Coordinates must be finite numbers.",
        )

    # Geod expects longitude before latitude.
    _, _, distance_m = GEOD.inv(lon1, lat1, lon2, lat2)

    if not math.isfinite(distance_m):
        raise HTTPException(
            status_code=422,
            detail="Could not calculate the distance.",
        )

    return {
        "point_a": {"latitude": lat1, "longitude": lon1},
        "point_b": {"latitude": lat2, "longitude": lon2},
        "distance_m": distance_m,
        "method": "Shortest geodesic distance on the WGS 84 ellipsoid",
        "note": "Surface distance, not a walking route or a 3D terrain distance.",
    }


@app.get("/", response_class=HTMLResponse)
def home():
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Taquaral Geo3D</title>

        <link rel="stylesheet"
              href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css">

        <style>
            * { box-sizing: border-box; }

            body {
                margin: 0;
                font-family: Arial, sans-serif;
                background: #10202b;
                color: #edf5fa;
            }

            header {
                padding: 24px 30px;
                border-bottom: 1px solid #304453;
            }

            h1 { margin: 0 0 8px; }
            header p { margin: 0; color: #abc1cf; }

            main {
                display: grid;
                grid-template-columns: 320px minmax(0, 1fr);
                gap: 20px;
                padding: 20px;
                align-items: start;
            }

            aside {
                background: #192f3d;
                border-radius: 12px;
                padding: 22px;
            }

            h2 { font-size: 19px; margin-top: 25px; }
            aside h2:first-child { margin-top: 0; }

            p {
                line-height: 1.6;
                color: #c0d2de;
            }

            button {
                width: 100%;
                padding: 12px;
                margin: 5px 0;
                background: #5de0be;
                color: #10202b;
                border: 0;
                border-radius: 7px;
                cursor: pointer;
                font-weight: bold;
            }

            button:hover { background: #85ecd1; }

            button.secondary {
                background: #304b5c;
                color: #edf5fa;
            }

            button:focus-visible {
                outline: 3px solid white;
                outline-offset: 3px;
            }

            #map {
                height: 82vh;
                min-height: 450px;
                border-radius: 12px;
                background: #dce5e9;
                position: sticky;
                top: 20px;
            }

            .note { font-size: 13px; }

            .coordinate {
                font-family: monospace;
                overflow-wrap: anywhere;
                font-size: 12px;
            }

            .metric {
                padding: 15px;
                margin: 12px 0;
                background: #102632;
                border: 1px solid #304b5c;
                border-radius: 9px;
            }

            .metric-label, .metric-detail {
                font-size: 13px;
                color: #b4cad7;
            }

            .metric-value {
                margin: 7px 0;
                font-size: 25px;
                font-weight: bold;
                color: #66e5c4;
            }

            .distance-value { color: #ffce67; }

            .legend-item {
                display: flex;
                align-items: center;
                gap: 10px;
                margin: 12px 0;
                font-size: 14px;
            }

            .swatch {
                width: 20px;
                height: 14px;
                border-radius: 3px;
                flex-shrink: 0;
            }

            .lake-swatch {
                background: #38bdf8;
                border: 2px solid #0077b6;
            }

            .other-swatch {
                background: #94a3b8;
                border: 2px solid #64748b;
            }

            .leaflet-popup-content { line-height: 1.6; }

            @media (max-width: 750px) {
                main { grid-template-columns: 1fr; }
                header { padding: 20px; }

                #map {
                    height: 65vh;
                    min-height: 350px;
                    position: static;
                }
            }
        </style>
    </head>

    <body>
        <header>
            <h1>🌎 Taquaral Geo3D</h1>
            <p>Interactive exploration · Campinas, São Paulo, Brazil</p>
        </header>
        <style>
            [hidden] {
                display: none !important;
            }

            .dashboard-navigation {
                display: flex;
                flex-wrap: wrap;
                gap: 12px;
                padding: 18px 20px 0;
            }

            .dashboard-navigation button {
                width: auto;
                min-width: 180px;
                margin: 0;
                background: #304b5c;
                color: #edf5fa;
            }

            .dashboard-navigation button[aria-pressed="true"] {
                background: #5de0be;
                color: #10202b;
            }

            #surface-view, #bathymetry-view, #connected-view {
                padding: 20px;
            }

            .surface-panel {
                padding: 20px;
                background: #192f3d;
                border: 1px solid #304b5c;
                border-radius: 12px;
            }

            .surface-panel h2 {
                margin-top: 0;
            }

            .surface-panel a {
                color: #66e5c4;
            }

            #surface-frame, #bathymetry-frame, #connected-frame {
                display: block;
                width: 100%;
                height: 78vh;
                min-height: 500px;
                border: 0;
                border-radius: 8px;
                background: #10202b;
            }
        </style>

        <nav class="dashboard-navigation" aria-label="Dashboard views">
            <button id="show-map" type="button"
                    aria-controls="map-view" aria-pressed="true">
                Map &amp; Measurements
            </button>

            <button id="show-surface" type="button"
                    aria-controls="surface-view" aria-pressed="false">
                3D Surface
            </button>
            <button id="show-connected" type="button"
                    aria-controls="connected-view" aria-pressed="false">
                V2 · Connected Exploration
            </button>
            <button id="show-bathymetry" type="button"
                    aria-controls="bathymetry-view" aria-pressed="false">
                Historical Bathymetry
            </button>
        </nav>


        <main id="map-view">
            <aside>
                <h2>Distance measurement</h2>

                <button id="measure" type="button">
                    Measure distance
                </button>

                <button id="clear" class="secondary" type="button">
                    Clear measurement
                </button>

                <p id="distance-status" class="note" role="status">
                    Select Measure distance, then click point A and point B.
                </p>

                <div class="metric">
                    <div class="metric-label">Geodesic distance A–B</div>
                    <div id="distance-value"
                         class="metric-value distance-value">—</div>
                    <div class="metric-detail">WGS 84 ellipsoid · meters</div>
                </div>

                <p id="point-a" class="coordinate">Point A: —</p>
                <p id="point-b" class="coordinate">Point B: —</p>

                <p class="note">
                    Shortest surface distance between the selected coordinates.
                    Not a walking route or a 3D terrain distance.
                </p>

                <h2>Lake metrics</h2>

                <div class="metric">
                    <div class="metric-label">Mapped water area</div>
                    <div id="area-m2" class="metric-value">—</div>
                    <div id="area-ha" class="metric-detail">—</div>
                </div>

                <div class="metric">
                    <div class="metric-label">Outer boundary length</div>
                    <div id="outer-boundary" class="metric-value">—</div>
                    <div class="metric-detail">Excludes interior rings</div>
                </div>

                <p id="metrics-status" class="note" role="status">
                    Loading lake metrics…
                </p>

                <p class="note">
                    Geodesic calculation on the WGS 84 ellipsoid.
                    Water area excludes mapped interior rings.
                </p>

                <h2>Explore the area</h2>

                <button id="reset-view" type="button">
                    Return to Taquaral
                </button>

                <p id="coordinates" class="coordinate">
                    Click anywhere on the map.
                </p>

                <h2>Water boundaries</h2>

                <div class="legend-item">
                    <span class="swatch lake-swatch"></span>
                    <span>Taquaral Lake</span>
                </div>

                <div class="legend-item">
                    <span class="swatch other-swatch"></span>
                    <span>Other water features</span>
                </div>

                <p id="boundary-status" class="note" role="status">
                    Loading water boundaries…
                </p>

                <p id="map-status" class="note" role="status">
                    Loading basemap…
                </p>

                <h2>Data and scope</h2>
                <p class="note">
                    Source: OpenStreetMap contributors.
                    Lake metrics describe the downloaded mapped geometry.
                    Selected points are approximate map clicks.
                    Display precision does not establish positional accuracy.
                </p>

                <p class="note">
                    2D mapping and geodesic measurements are available.
                    3D surface exploration is available in the 3D Surface tab.
                    Published historical results are available in Historical Bathymetry.
                </p>
            </aside>

            <div id="map"
                 aria-label="Interactive map of the Taquaral area"></div>
        </main>
        <section id="surface-view" hidden aria-label="3D surface viewer">
            <div class="surface-panel">
                <h2>3D Surface Exploration</h2>

                <p class="note">
                    Rotate by dragging. Scroll to zoom.
                    Hover over the surface to inspect modeled elevations.
                </p>

                <p class="note">
                    Copernicus GLO-30 · Approximately 30 m sampling.
                    Surface model, not bathymetry.
                    Vertical reference: EGM2008.
                    No vertical exaggeration.
                </p>

                <p class="note">
                    <a href="/surface-3d" target="_blank"
                       rel="noopener noreferrer">
                        Open the 3D viewer in a separate tab
                    </a>
                </p>

                <iframe
                    id="surface-frame"
                    title="Taquaral interactive 3D surface"
                    data-source="/surface-3d">
                </iframe>
            </div>
        </section>


        <section id="connected-view" hidden aria-label="V2 connected spatial exploration">
            <iframe id="connected-frame" title="V2 — Connected Spatial Exploration"
                    data-source="/connected-exploration"></iframe>
        </section>
        <section id="bathymetry-view" hidden aria-label="Historical bathymetry from the USP thesis">
            <iframe id="bathymetry-frame" title="Historical bathymetry — USP thesis (2002)"
                    data-source="/historical-bathymetry"></iframe>
        </section>
        <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>

        <script>
            const byId = id => document.getElementById(id);
            // Single dashboard selection state shared with the same-origin V2 iframe.
            window.taquaralSelection = {points: [], measuring: false};
            function publishSelection(points, measuring) {
                window.taquaralSelection = {
                    points: points.map(p => ({lat: p.lat, lng: p.lng})),
                    measuring: measuring
                };
                const frame = document.getElementById("connected-frame");
                if (frame.contentWindow) {
                    frame.contentWindow.postMessage(
                        {type: "taquaral:state", ...window.taquaralSelection},
                        window.location.origin
                    );
                }
            }


            const numberFormat = new Intl.NumberFormat("en-US", {
                maximumFractionDigits: 0
            });

            const hectareFormat = new Intl.NumberFormat("en-US", {
                minimumFractionDigits: 2,
                maximumFractionDigits: 2
            });

            async function fetchData(url) {
                const response = await fetch(url, {cache: "no-store"});

                if (!response.ok) {
                    let message = "Request failed: " + response.status;

                    try {
                        const error = await response.json();
                        if (typeof error.detail === "string") {
                            message = error.detail;
                        }
                    } catch {
                        // Keep the HTTP status message.
                    }

                    throw new Error(message);
                }

                return response.json();
            }

            async function loadMetrics() {
                try {
                    const metrics = await fetchData("/api/lake-metrics");

                    byId("area-m2").textContent =
                        numberFormat.format(metrics.water_area_m2) + " m²";

                    byId("area-ha").textContent =
                        hectareFormat.format(metrics.water_area_ha) + " hectares";

                    byId("outer-boundary").textContent =
                        numberFormat.format(metrics.outer_boundary_m) + " m";

                    byId("metrics-status").textContent =
                        "OSM " + metrics.osm_reference +
                        ". Interior rings excluded from area: " +
                        metrics.interior_ring_count + ".";

                } catch (error) {
                    byId("metrics-status").textContent =
                        "Could not load metrics. " + error.message;
                }
            }

            loadMetrics();

            if (typeof L === "undefined") {
                byId("map-status").textContent =
                    "Map library could not load. Check your internet connection.";

                byId("boundary-status").textContent =
                    "Map unavailable.";

                byId("distance-status").textContent =
                    "Distance measurement requires the map.";

                byId("measure").disabled = true;
                byId("clear").disabled = true;
                byId("reset-view").disabled = true;
            } else {
                const initialCenter = [-22.874, -47.059];
                const map = L.map("map").setView(initialCenter, 16);
                const measurementLayer = L.layerGroup().addTo(map);

                let lakeBounds = null;
                let measuring = false;
                let points = [];
                let requestVersion = 0;
                let tileErrorOccurred = false;

                const tiles = L.tileLayer(
                    "https://tile.openstreetmap.org/{z}/{x}/{y}.png",
                    {
                        maxZoom: 19,
                        attribution:
                            '&copy; <a href="https://www.openstreetmap.org/copyright">' +
                            'OpenStreetMap contributors</a>'
                    }
                );

                tiles.on("loading", function () {
                    tileErrorOccurred = false;
                    byId("map-status").textContent = "Loading basemap…";
                });

                tiles.on("tileerror", function () {
                    tileErrorOccurred = true;
                    byId("map-status").textContent =
                        "Some map tiles could not load. Check your connection.";
                });

                tiles.on("load", function () {
                    if (!tileErrorOccurred) {
                        byId("map-status").textContent =
                            "Basemap loaded. Source: OpenStreetMap.";
                    }
                });

                tiles.addTo(map);

                function coordinateText(point) {
                    return point.lat.toFixed(6) + ", " + point.lng.toFixed(6);
                }

                function setMeasuring(active) {
                    measuring = active;
                    publishSelection(points, measuring);
                    byId("measure").setAttribute(
                        "aria-pressed",
                        String(active)
                    );

                    map.getContainer().style.cursor =
                        active ? "crosshair" : "";
                }

                function clearMeasurement() {
                    // Invalidate any pending distance response.
                    requestVersion += 1;

                    points = [];
                    measurementLayer.clearLayers();
                    map.closePopup();
                    setMeasuring(false);

                    byId("distance-value").textContent = "—";
                    byId("point-a").textContent = "Point A: —";
                    byId("point-b").textContent = "Point B: —";

                    byId("distance-status").textContent =
                        "Select Measure distance, then click point A and point B.";
                }

                byId("clear").addEventListener("click", clearMeasurement);

                byId("measure").addEventListener("click", function () {
                    clearMeasurement();
                    setMeasuring(true);

                    byId("distance-status").textContent =
                        "Click the map to select point A.";
                });

                async function calculateDistance() {
                    const currentVersion = requestVersion;
                    const [a, b] = points;

                    const query = new URLSearchParams({
                        lat1: a.lat,
                        lon1: a.lng,
                        lat2: b.lat,
                        lon2: b.lng
                    });

                    byId("distance-status").textContent =
                        "Calculating distance…";

                    try {
                        const result = await fetchData(
                            "/api/distance?" + query.toString()
                        );

                        // Ignore responses for a measurement that was cleared.
                        if (currentVersion !== requestVersion) {
                            return;
                        }

                        if (
                            typeof result.distance_m !== "number" ||
                            !Number.isFinite(result.distance_m)
                        ) {
                            throw new Error("Invalid distance result.");
                        }

                        const value = result.distance_m;

                        byId("distance-value").textContent =
                            value > 0 && value < 1
                                ? "< 1 m"
                                : numberFormat.format(value) + " m";

                        byId("distance-status").textContent =
                            "Measurement complete. Select Measure distance " +
                            "to choose another pair.";

                    } catch (error) {
                        if (currentVersion !== requestVersion) {
                            return;
                        }

                        byId("distance-status").textContent =
                            "Could not calculate distance. " + error.message +
                            " Select Measure distance to try again.";
                    }
                }

                function selectLocation(latlng) {
                    byId("coordinates").textContent =
                        "Latitude, longitude: " + coordinateText(latlng);

                    if (!measuring) {
                        return;
                    }

                    const point = L.latLng(latlng.lat, latlng.lng);
                    points.push(point);
                    publishSelection(points, measuring);

                    const label = points.length === 1 ? "A" : "B";

                    L.circleMarker(point, {
                        radius: 8,
                        color: "#10202b",
                        weight: 2,
                        fillColor: "#ffce67",
                        fillOpacity: 1,
                        interactive: false
                    })
                    .bindTooltip(label, {
                        permanent: true,
                        direction: "top"
                    })
                    .addTo(measurementLayer);

                    byId(label === "A" ? "point-a" : "point-b").textContent =
                        "Point " + label + ": " + coordinateText(point);

                    if (points.length === 1) {
                        byId("distance-status").textContent =
                            "Point A selected. Click the map to select point B.";
                        return;
                    }

                    setMeasuring(false);

                    // The line is a visual connection; the API computes distance.
                    L.polyline(points, {
                        color: "#e99f17",
                        weight: 4,
                        dashArray: "8, 6",
                        interactive: false
                    }).addTo(measurementLayer);

                    calculateDistance();
                }

                window.addEventListener("message", function (event) {
                    const frame = document.getElementById("connected-frame");
                    if (event.origin !== window.location.origin || event.source !== frame.contentWindow) return;
                    const message = event.data;
                    if (message?.type === "taquaral:ready") {
                        publishSelection(points, measuring);
                    } else if (message?.type === "taquaral:start") {
                        byId("measure").click();
                    } else if (message?.type === "taquaral:clear") {
                        clearMeasurement();
                    } else if (message?.type === "taquaral:point" && measuring) {
                        if (Number.isFinite(message.lat) && Number.isFinite(message.lng)
                            && Math.abs(message.lat) <= 90 && Math.abs(message.lng) <= 180) {
                            selectLocation(L.latLng(message.lat, message.lng));
                        }
                    }
                });

                map.on("click", function (event) {
                    selectLocation(event.latlng);
                });

                byId("reset-view").addEventListener("click", function () {
                    if (lakeBounds && lakeBounds.isValid()) {
                        map.fitBounds(lakeBounds, {padding: [35, 35]});
                    } else {
                        map.setView(initialCenter, 16);
                    }
                });

                function isTaquaral(feature) {
                    const properties = feature.properties || {};

                    return properties.element === "relation"
                        && String(properties.id) === "17154522";
                }

                async function loadWaterFeatures() {
                    try {
                        const data = await fetchData("/api/water-features");

                        if (
                            data.type !== "FeatureCollection" ||
                            !Array.isArray(data.features)
                        ) {
                            throw new Error("Invalid GeoJSON FeatureCollection.");
                        }

                        const waterLayer = L.geoJSON(data, {
                            bubblingMouseEvents: false,

                            style: function (feature) {
                                const selected = isTaquaral(feature);

                                return {
                                    color: selected ? "#0077b6" : "#64748b",
                                    weight: selected ? 3 : 1,
                                    fillColor: selected ? "#38bdf8" : "#94a3b8",
                                    fillOpacity: selected ? 0.35 : 0.15
                                };
                            },

                            onEachFeature: function (feature, layer) {
                                const properties = feature.properties || {};

                                layer.on("click", function (event) {
                                    const wasMeasuring = measuring;

                                    // Water polygons also accept points A and B.
                                    selectLocation(event.latlng);

                                    if (!wasMeasuring) {
                                        const popup = document.createElement("div");

                                        popup.textContent =
                                            (properties.name ||
                                                "Unnamed water feature") +
                                            " | OSM " +
                                            (properties.element || "unknown") +
                                            "/" + (properties.id || "unknown") +
                                            " | Source: OpenStreetMap contributors";

                                        L.popup()
                                            .setLatLng(event.latlng)
                                            .setContent(popup)
                                            .openOn(map);
                                    }
                                });
                            }
                        }).addTo(map);

                        const lakeLayers = waterLayer.getLayers().filter(
                            layer => isTaquaral(layer.feature)
                        );

                        if (lakeLayers.length === 1) {
                            const lake = lakeLayers[0];
                            lakeBounds = lake.getBounds();

                            lake.bringToFront();
                            map.fitBounds(lakeBounds, {padding: [35, 35]});

                            byId("boundary-status").textContent =
                                data.features.length +
                                " water polygons loaded. " +
                                "Taquaral Lake highlighted in blue.";
                        } else {
                            byId("boundary-status").textContent =
                                "Boundaries loaded, but the target lake " +
                                "could not be uniquely identified.";
                        }

                        L.control.layers(
                            null,
                            {
                                "Water boundaries": waterLayer,
                                "Distance measurement": measurementLayer
                            }
                        ).addTo(map);

                    } catch (error) {
                        byId("boundary-status").textContent =
                            "Could not load boundaries. " + error.message;
                    }
                }

                loadWaterFeatures();
            }
        </script>
    
        <script>
            (function () {
                const mapView = document.getElementById("map-view");
                const surfaceView = document.getElementById("surface-view");
                const mapButton = document.getElementById("show-map");
                const surfaceButton = document.getElementById("show-surface");
                const frame = document.getElementById("surface-frame");

                const bathymetryView = document.getElementById("bathymetry-view");
                const bathymetryButton = document.getElementById("show-bathymetry");
                const bathymetryFrame = document.getElementById("bathymetry-frame");
                const connectedView = document.getElementById("connected-view");
                const connectedButton = document.getElementById("show-connected");
                const connectedFrame = document.getElementById("connected-frame");
                const views = [mapView, surfaceView, connectedView, bathymetryView];
                const buttons = [mapButton, surfaceButton, connectedButton, bathymetryButton];
                function showView(index) {
                    views.forEach((view, i) => { view.hidden = i !== index; });
                    buttons.forEach((button, i) => {
                        button.setAttribute("aria-pressed", String(i === index));
                    });
                    if (index === 0) {
                        requestAnimationFrame(() => window.dispatchEvent(new Event("resize")));
                    } else {
                        const targetFrame = index === 1 ? frame : index === 2 ? connectedFrame : bathymetryFrame;
                        if (!targetFrame.hasAttribute("src")) {
                            targetFrame.src = targetFrame.dataset.source;
                        } else if (index === 2) {
                            requestAnimationFrame(() => connectedFrame.contentWindow.postMessage(
                                {type: "taquaral:resize"}, window.location.origin
                            ));
                        }
                    }
                }
                buttons.forEach((button, i) => {
                    button.addEventListener("click", () => showView(i));
                });
            })();
        </script>
</body>
    </html>
    """

# TAQUARAL_3D_DASHBOARD_INTEGRATION
@app.get("/surface-3d", include_in_schema=False)
def surface_3d_viewer():
    from fastapi.responses import FileResponse

    surface_path = (
        Path(__file__).resolve().parent
        / "outputs"
        / "taquaral_surface_3d.html"
    )

    if not surface_path.is_file():
        raise HTTPException(
            status_code=404,
            detail="3D viewer not found. Run build_surface_3d.py first.",
        )

    return FileResponse(
        path=surface_path,
        media_type="text/html",
        headers={"Cache-Control": "no-cache"},
    )


@app.get("/api/historical-bathymetry")
def historical_bathymetry_data():
    return load_historical_bathymetry()


@app.get("/historical-bathymetry", response_class=HTMLResponse)
def historical_bathymetry_view():
    return render_historical_bathymetry(load_historical_bathymetry())


@app.get("/historical-bathymetry/figure", include_in_schema=False)
def historical_bathymetry_figure():
    from fastapi.responses import FileResponse

    figure_path = BASE_DIR / "assets" / "thesis_2002_figure_3.png"
    if not figure_path.is_file():
        raise HTTPException(status_code=404, detail="Thesis figure not found. Copy the assets folder from the V3 update package.")
    return FileResponse(figure_path, media_type="image/png")


@app.get("/api/historical-bathymetry/export")
def historical_bathymetry_export(format: str = Query("json", pattern="^(json|csv)$")):
    data = load_historical_bathymetry()
    if format == "csv":
        content = export_historical_bathymetry_csv(data)
        media_type = "text/csv"
    else:
        content = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
        media_type = "application/json"
    return Response(content=content, media_type=media_type,
                    headers={"Content-Disposition": f'attachment; filename="taquaral_v3_historical_bathymetry.{format}"'})


@app.get("/connected-exploration", response_class=HTMLResponse)
def connected_exploration_view():
    return (BASE_DIR / "assets/connected_exploration.html").read_text(encoding="utf-8")


@app.get("/assets/connected_exploration.js", include_in_schema=False)
def connected_exploration_script():
    from fastapi.responses import FileResponse
    return FileResponse(BASE_DIR / "assets/connected_exploration.js", media_type="text/javascript")


@app.get("/assets/plotly.min.js", include_in_schema=False)
def local_plotly_library():
    from plotly.offline import get_plotlyjs
    return Response(get_plotlyjs(), media_type="text/javascript",
                    headers={"Cache-Control": "public, max-age=3600"})


@app.get("/api/surface-scene")
def connected_surface_scene():
    from connected_exploration import scene
    return scene(get_lake_feature(read_water_data()))


@app.get("/api/surface-point")
def connected_surface_point(
    lat: float = Query(..., ge=-90, le=90, allow_inf_nan=False),
    lon: float = Query(..., ge=-180, le=180, allow_inf_nan=False),
):
    from connected_exploration import point
    return point(lat, lon)


@app.get("/api/surface-profile")
def connected_surface_profile(
    lat1: float = Query(..., ge=-90, le=90, allow_inf_nan=False),
    lon1: float = Query(..., ge=-180, le=180, allow_inf_nan=False),
    lat2: float = Query(..., ge=-90, le=90, allow_inf_nan=False),
    lon2: float = Query(..., ge=-180, le=180, allow_inf_nan=False),
):
    from connected_exploration import profile
    return profile(lat1, lon1, lat2, lon2)
