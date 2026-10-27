import json
from datetime import datetime, timezone
from pathlib import Path

import osmnx as ox


BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / "data" / "raw"

# Approximate search center, not a surveyed reference point.
SEARCH_CENTER = (-22.874, -47.059)
SEARCH_DISTANCE_M = 1800


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    ox.settings.use_cache = True
    ox.settings.requests_timeout = 120

    print("Searching OpenStreetMap for water features near Taquaral...")

    features = ox.features.features_from_point(
        SEARCH_CENTER,
        tags={"natural": "water"},
        dist=SEARCH_DISTANCE_M,
    )

    polygons = features[
        features.geometry.geom_type.isin(["Polygon", "MultiPolygon"])
    ].copy()

    if polygons.empty:
        raise RuntimeError("No water polygons were found in the search area.")

    polygons = polygons.to_crs(epsg=4326).reset_index()

    # Keep a compact set of attributes for inspection and export.
    columns = [
        column
        for column in [
            "element", "id", "name", "natural", "water", "geometry"
        ]
        if column in polygons.columns
    ]
    polygons = polygons[columns]

    geojson_path = OUTPUT_DIR / "water_candidates.geojson"
    geojson_path.write_text(
        polygons.to_json(drop_id=True),
        encoding="utf-8",
    )

    metadata = {
        "source": "OpenStreetMap contributors",
        "license": "ODbL 1.0",
        "attribution_url": "https://www.openstreetmap.org/copyright",
        "downloaded_at_utc": datetime.now(timezone.utc).isoformat(),
        "search_center_lat_lon": list(SEARCH_CENTER),
        "search_distance_m": SEARCH_DISTANCE_M,
        "query_tags": {"natural": "water"},
        "coordinate_reference": "EPSG:4326",
        "polygon_count": len(polygons),
        "selection_status": "Candidates awaiting visual inspection",
    }

    (OUTPUT_DIR / "water_candidates_metadata.json").write_text(
        json.dumps(metadata, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print(f"\nFound {len(polygons)} water polygons.\n")

    for _, row in polygons.iterrows():
        name = row.get("name")
        if not isinstance(name, str) or not name.strip():
            name = "Unnamed water feature"

        print(
            f"OSM {row.get('element', 'unknown')}/{row.get('id', 'unknown')}"
            f" | Name: {name}"
            f" | Valid geometry: {row.geometry.is_valid}"
        )

    print(f"\nSaved to: {geojson_path}")
    print("Next step: inspect the polygons on the interactive map.")


if __name__ == "__main__":
    main()