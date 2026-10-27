import json
import math
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import plotly.graph_objects as go
import rasterio
from pyproj import Transformer
from rasterio.windows import Window, from_bounds


BASE_DIR = Path(__file__).resolve().parent
RAW_DIR = BASE_DIR / "data" / "raw"
PROCESSED_DIR = BASE_DIR / "data" / "processed"
OUTPUT_DIR = BASE_DIR / "outputs"

TILE_NAME = "Copernicus_DSM_COG_10_S23_00_W048_00_DEM"
SOURCE_URL = (
    "https://copernicus-dem-30m.s3.amazonaws.com/"
    f"{TILE_NAME}/{TILE_NAME}.tif"
)

SOURCE_PATH = RAW_DIR / f"{TILE_NAME}.tif"
CROP_PATH = PROCESSED_DIR / "taquaral_surface.tif"
HTML_PATH = OUTPUT_DIR / "taquaral_surface_3d.html"

# Rectangular study area: west, south, east, north.
# This is a study extent, not the official park boundary.
STUDY_BOUNDS = (-47.075, -22.890, -47.035, -22.855)


def download_source():
    if SOURCE_PATH.exists():
        print("Using the previously downloaded elevation tile.")
        return

    temporary_path = SOURCE_PATH.with_suffix(".download")
    print("Downloading the elevation tile (approximately 41 MB)...")

    try:
        with urllib.request.urlopen(SOURCE_URL, timeout=120) as response:
            with temporary_path.open("wb") as output:
                while True:
                    chunk = response.read(1024 * 1024)
                    if not chunk:
                        break
                    output.write(chunk)

        temporary_path.replace(SOURCE_PATH)

    finally:
        if temporary_path.exists():
            temporary_path.unlink()

    print("Download complete.")


def main():
    for directory in (RAW_DIR, PROCESSED_DIR, OUTPUT_DIR):
        directory.mkdir(parents=True, exist_ok=True)

    download_source()

    with rasterio.open(SOURCE_PATH) as source:
        if source.crs is None or source.crs.to_epsg() != 4326:
            raise ValueError("Expected a WGS 84 geographic raster.")

        west, south, east, north = STUDY_BOUNDS

        if not (
            source.bounds.left <= west < east <= source.bounds.right
            and source.bounds.bottom <= south < north <= source.bounds.top
        ):
            raise ValueError("The study area is outside the source tile.")

        requested = from_bounds(
            west, south, east, north,
            transform=source.transform,
        )

        # Expand to whole pixels so the requested extent is fully covered.
        column_start = math.floor(requested.col_off)
        row_start = math.floor(requested.row_off)
        column_stop = math.ceil(requested.col_off + requested.width)
        row_stop = math.ceil(requested.row_off + requested.height)

        window = Window(
            column_start,
            row_start,
            column_stop - column_start,
            row_stop - row_start,
        )

        surface = source.read(1, window=window, masked=True)
        transform = source.window_transform(window)

        elevations = surface.astype("float64").filled(np.nan)
        elevations[~np.isfinite(elevations)] = np.nan

        if not np.isfinite(elevations).any():
            raise ValueError("No valid elevations were found.")

        profile = {
            "driver": "GTiff",
            "height": elevations.shape[0],
            "width": elevations.shape[1],
            "count": 1,
            "dtype": "float32",
            "crs": source.crs,
            "transform": transform,
            "nodata": -9999.0,
            "compress": "deflate",
        }

        with rasterio.open(CROP_PATH, "w", **profile) as destination:
            destination.write(
                np.where(
                    np.isfinite(elevations), elevations, -9999.0
                ).astype("float32"),
                1,
            )

    rows, columns = np.indices(elevations.shape)

    # Geographic coordinates of pixel centers.
    longitudes = (
        transform.c + (columns + 0.5) * transform.a
    )
    latitudes = (
        transform.f + (rows + 0.5) * transform.e
    )

    # UTM zone 23S provides horizontal coordinates in meters.
    to_utm = Transformer.from_crs(
        "EPSG:4326",
        "EPSG:32723",
        always_xy=True,
    )
    eastings, northings = to_utm.transform(longitudes, latitudes)

    center_lon = (west + east) / 2
    center_lat = (south + north) / 2
    origin_easting, origin_northing = to_utm.transform(
        center_lon, center_lat
    )

    figure = go.Figure(
        go.Surface(
            x=eastings - origin_easting,
            y=northings - origin_northing,
            z=elevations,
            colorscale="Earth",
            colorbar={"title": "Elevation (m)"},
            hovertemplate=(
                "East offset: %{x:.0f} m<br>"
                "North offset: %{y:.0f} m<br>"
                "Surface elevation: %{z:.1f} m"
                "<extra></extra>"
            ),
        )
    )

    figure.update_layout(
        title={
            "text": (
                "Taquaral Geo3D — Surface Exploration"
                "<br><sup>Copernicus GLO-30 · Approx. 30 m sampling"
                " · Surface model, not bathymetry</sup>"
            )
        },
        template="plotly_dark",
        paper_bgcolor="#10202b",
        margin={"l": 20, "r": 20, "t": 100, "b": 85},
        scene={
            "xaxis_title": "East offset (m)",
            "yaxis_title": "North offset (m)",
            "zaxis_title": "Surface elevation (m)",
            "aspectmode": "data",
            "camera": {"eye": {"x": 1.4, "y": -1.4, "z": 1.2}},
        },
        annotations=[
            {
                "text": (
                    "Source: Copernicus DEM / GLO-30 Public via AWS"
                    " · © DLR e.V. 2010–2014 and © Airbus Defence"
                    " and Space GmbH 2014–2018"
                    "<br>Vertical reference: EGM2008"
                    " · No vertical exaggeration · Not a field survey"
                ),
                "xref": "paper",
                "yref": "paper",
                "x": 0.5,
                "y": -0.08,
                "showarrow": False,
                "font": {"size": 11},
            }
        ],
    )

    figure.write_html(
        HTML_PATH,
        include_plotlyjs=True,
        full_html=True,
        config={"responsive": True, "displaylogo": False},
    )

    metadata = {
        "source": "Copernicus DEM GLO-30 Public",
        "source_url": SOURCE_URL,
        "prepared_at_utc": datetime.now(timezone.utc).isoformat(),
        "study_bounds_west_south_east_north": STUDY_BOUNDS,
        "horizontal_reference": "WGS 84 / UTM zone 23S",
        "vertical_reference": "EGM2008",
        "model_type": "Digital Surface Model",
        "nominal_sampling_m": 30,
        "vertical_exaggeration": 1,
        "valid_pixel_count": int(np.isfinite(elevations).sum()),
        "minimum_surface_elevation_m": float(np.nanmin(elevations)),
        "maximum_surface_elevation_m": float(np.nanmax(elevations)),
        "limitations": (
            "May include vegetation and buildings. "
            "Does not represent underwater depth or individual trees. "
            "The study rectangle is not the official park boundary."
        ),
        "dataset_information": "https://registry.opendata.aws/copernicus-dem/",
    }

    (PROCESSED_DIR / "taquaral_surface_metadata.json").write_text(
        json.dumps(metadata, indent=2),
        encoding="utf-8",
    )

    print(f"Surface grid: {elevations.shape}")
    print(f"Minimum elevation: {np.nanmin(elevations):.1f} m")
    print(f"Maximum elevation: {np.nanmax(elevations):.1f} m")
    print(f"\n3D viewer saved to:\n{HTML_PATH}")
    print("\nOpen the HTML file in your browser.")


if __name__ == "__main__":
    main()