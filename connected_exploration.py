"""V2: connected Copernicus surface exploration, independent of V3 thesis data."""
import math
from functools import lru_cache
from pathlib import Path

import numpy as np
import rasterio
from fastapi import HTTPException
from pyproj import Geod, Transformer

BASE_DIR = Path(__file__).resolve().parent
RASTER_PATH = BASE_DIR / 'data/processed/taquaral_surface.tif'
GEOD = Geod(ellps='WGS84')
UTM = Transformer.from_crs(4326, 32723, always_xy=True)
SOURCE = {
    'source': 'Copernicus DEM GLO-30 Public',
    'source_url': 'https://registry.opendata.aws/copernicus-dem/',
    'horizontal_reference': 'WGS 84 / UTM zone 23S (EPSG:32723)',
    'vertical_reference': 'EGM2008',
    'nominal_sampling_m': 30,
    'sampling_method': 'Nearest native raster cell; no interpolated detail',
    'limitations': 'Digital Surface Model: vegetation and buildings may affect elevations. Elevations over mapped water are model values, not water depth or surveyed water level. No bathymetry, ground survey or walking route is inferred.',
    'attribution': '© DLR e.V. 2010–2014 and © Airbus Defence and Space GmbH 2014–2018',
}


@lru_cache(maxsize=2)
def _load_surface(path, modified):
    with rasterio.open(path) as src:
        if src.crs is None or src.crs.to_epsg() != 4326:
            raise HTTPException(503, 'Expected an EPSG:4326 surface crop. Rebuild with build_surface_3d.py.')
        values = src.read(1, masked=True).astype('float64').filled(np.nan)
        if not np.isfinite(values).any():
            raise HTTPException(503, 'The surface crop contains no valid elevations.')
        transform, bounds = src.transform, src.bounds
    if transform.b != 0 or transform.d != 0 or transform.a <= 0 or transform.e >= 0:
        raise HTTPException(503, 'Expected a north-up geographic surface crop.')
    rows, cols = np.indices(values.shape)
    lon = transform.c + (cols + .5) * transform.a
    lat = transform.f + (rows + .5) * transform.e
    # Match the original V1 viewer's documented study-center origin.
    origin = UTM.transform((-47.075 - 47.035) / 2, (-22.890 - 22.855) / 2)
    east, north = UTM.transform(lon, lat)
    return dict(z=values, lon=lon, lat=lat, x=east-origin[0], y=north-origin[1],
                transform=transform, bounds=bounds, origin=origin)


def surface():
    if not RASTER_PATH.is_file():
        raise HTTPException(503, 'Surface crop not found. Run python build_surface_3d.py, then reload V2.')
    return _load_surface(str(RASTER_PATH), RASTER_PATH.stat().st_mtime_ns)


def sample(lat, lon, grid=None):
    grid = surface() if grid is None else grid
    bounds = grid['bounds']
    if not (bounds.left <= lon < bounds.right and bounds.bottom < lat <= bounds.top):
        return None
    inverse = ~grid['transform']
    col = inverse.a * lon + inverse.b * lat + inverse.c
    row = inverse.d * lon + inverse.e * lat + inverse.f
    row, col = math.floor(row), math.floor(col)
    values = grid['z']
    if not (0 <= row < values.shape[0] and 0 <= col < values.shape[1]):
        return None
    value = float(values[row, col])
    return value if math.isfinite(value) else None


def point(lat, lon, grid=None):
    grid = surface() if grid is None else grid
    x, y = UTM.transform(lon, lat)
    return dict(latitude=lat, longitude=lon, east_offset_m=x-grid['origin'][0],
                north_offset_m=y-grid['origin'][1], elevation_m=sample(lat, lon, grid))


def profile(lat1, lon1, lat2, lon2):
    grid = surface()
    for lat, lon in [(lat1, lon1), (lat2, lon2)]:
        b = grid['bounds']
        if not (b.left <= lon < b.right and b.bottom < lat <= b.top):
            raise HTTPException(422, 'Both points must be within the Copernicus study extent. Select points near Taquaral.')
    azimuth, _, distance = GEOD.inv(lon1, lat1, lon2, lat2)
    intervals = max(1, math.ceil(distance / 30))
    samples = []
    for i in range(intervals + 1):
        along = distance * i / intervals
        lon, lat, _ = GEOD.fwd(lon1, lat1, azimuth, along)
        # Preserve exact user coordinates at both endpoints.
        if i == 0: lat, lon = lat1, lon1
        if i == intervals: lat, lon = lat2, lon2
        samples.append(dict(distance_m=along, **point(lat, lon, grid)))
    return dict(**SOURCE, distance_m=distance, sample_count=len(samples),
                sample_spacing_m=distance/intervals, samples=samples,
                valid_sample_count=sum(s['elevation_m'] is not None for s in samples))


def _lists(array):
    return np.where(np.isfinite(array), array, None).tolist()


def scene(lake):
    grid = surface()
    geometry = lake['geometry']
    polygons = [geometry['coordinates']] if geometry['type'] == 'Polygon' else geometry['coordinates']
    lake_line = dict(x=[], y=[], z=[])
    for polygon in polygons:
        for ring in polygon:
            densified = []
            for a, b in zip(ring, ring[1:]):
                distance = GEOD.inv(a[0], a[1], b[0], b[1])[2]
                count = max(0, math.ceil(distance/15)-1)
                densified.append(a)
                if count: densified.extend(GEOD.npts(a[0], a[1], b[0], b[1], count))
            densified.append(ring[-1])
            for lon, lat, *_ in densified:
                p = point(lat, lon, grid)
                lake_line['x'].append(p['east_offset_m'])
                lake_line['y'].append(p['north_offset_m'])
                # A display lift prevents z-fighting; it is not a measurement.
                lake_line['z'].append(None if p['elevation_m'] is None else p['elevation_m'] + 1)
            for values in lake_line.values(): values.append(None)
    b = grid['bounds']
    return dict(**SOURCE, x=grid['x'].tolist(), y=grid['y'].tolist(), z=_lists(grid['z']),
                customdata=np.stack([grid['lat'], grid['lon']], axis=-1).tolist(),
                bounds_west_south_east_north=[b.left,b.bottom,b.right,b.top],
                lake_line=lake_line, lake_source='OpenStreetMap contributors, relation/17154522',
                overlay_display_lift_m=1)
