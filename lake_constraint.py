"""Restrict selections to the documented OSM lake polygon; no snapping."""
import json
import math
from pathlib import Path
from fastapi import HTTPException
from pyproj import Geod
from shapely.geometry import Point, LineString, shape

GEOD = Geod(ellps="WGS84")
DATA = Path(__file__).resolve().parent / "data/raw/water_candidates.geojson"

def require_lake_selection(lat, lon, lat1=None, lon1=None):
    values = [lat, lon] + ([] if lat1 is None and lon1 is None else [lat1, lon1])
    if any(v is None or not math.isfinite(v) for v in values):
        raise HTTPException(422, "Coordinates must be finite numbers.")
    if abs(lat)>90 or abs(lon)>180 or (lat1 is not None and (abs(lat1)>90 or abs(lon1)>180)):
        raise HTTPException(422, "Invalid geographic coordinates.")
    try:
        data = json.loads(DATA.read_text(encoding="utf-8"))
        matches = [f for f in data["features"] if
                   (f.get("properties") or {}).get("element") == "relation" and
                   str((f.get("properties") or {}).get("id")) == "17154522"]
        if len(matches) != 1:
            raise ValueError("Ambiguous lake")
        lake = shape(matches[0]["geometry"])
        if lake.is_empty or not lake.is_valid or lake.geom_type not in {"Polygon", "MultiPolygon"}:
            raise ValueError("Invalid lake")
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise HTTPException(503, "Lake boundary unavailable. Restore data/raw/water_candidates.geojson.") from exc
    if not lake.covers(Point(lon, lat)) or (lat1 is not None and not lake.covers(Point(lon1, lat1))):
        raise HTTPException(422, "Choose a point inside the mapped Taquaral Lake outline. No point was moved or accepted outside it.")
    if lat1 is not None:
        _, _, distance = GEOD.inv(lon1, lat1, lon, lat)
        if distance > 0:
            # Approximate the ellipsoidal geodesic with chords no longer than 1 m.
            count = max(0, math.ceil(distance) - 1)
            middle = GEOD.npts(lon1, lat1, lon, lat, count) if count else []
            if not lake.covers(LineString([(lon1, lat1), *middle, (lon, lat)])):
                raise HTTPException(422, "The A–B segment leaves the mapped lake or crosses an interior ring. Choose another point B.")
    return {"allowed": True, "boundary": "OSM relation/17154522", "scope": "Mapped lake only"}
