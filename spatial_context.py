"""V6: projected lake surroundings and DSM-derived surface gradients, not terrain hazards."""
import csv
import hashlib
import io
import json
import math
from functools import lru_cache
from pathlib import Path

import numpy as np
import rasterio
from fastapi import HTTPException
from pyproj import Transformer
from rasterio.features import geometry_mask
from rasterio.io import MemoryFile
from rasterio.transform import from_bounds
from rasterio.warp import calculate_default_transform, reproject, Resampling
from shapely.geometry import mapping, shape, box
from shapely.errors import ShapelyError
from pyproj.exceptions import ProjError
from shapely.ops import unary_union
from shapely import transform as transform_coordinates

BASE = Path(__file__).resolve().parent
RASTER_PATH = BASE / 'data/processed/taquaral_surface.tif'
WATER_PATH = BASE / 'data/raw/water_candidates.geojson'
RASTER_META = BASE / 'data/processed/taquaral_surface_metadata.json'
WATER_META = BASE / 'data/raw/water_candidates_metadata.json'
DISTANCES = (100, 250, 500)
TO_UTM = Transformer.from_crs(4326, 32723, always_xy=True).transform
TO_WGS = Transformer.from_crs(32723, 4326, always_xy=True).transform
TO_MERC = Transformer.from_crs(4326, 3857, always_xy=True).transform
LIMITATIONS = [
    'Educational spatial analysis of documented snapshots, not current conditions, a field survey or real-time monitoring.',
    'Copernicus GLO-30 is a Digital Surface Model: buildings and vegetation may affect elevations and derived surface slope. This is not bare-earth terrain slope.',
    'Approximately 30 m source sampling. Reprojection to a 30 m grid does not add source detail or establish positional/vertical accuracy.',
    'Buffers are distances from the mapped lake polygon, not park boundaries, legal protection zones, catchments or walking routes.',
    'All 11 available OSM water polygons are excluded from zones; this snapshot is not an exhaustive water inventory or independently surveyed shoreline.',
    'Elevation statistics select projected raster cell centers inside each zone. Cells near boundaries can straddle land and water; no subpixel shoreline precision is implied.',
    'Slope uses central differences and requires a full valid 3×3 neighborhood free of mapped water. Raster borders, water-adjacent cells and NoData neighborhoods are excluded, not zero-filled.',
    'Cumulative zones overlap and must not be summed. Disjoint rings are a separate selectable mode. NoData remains missing; coverage and valid-cell counts are reported.',
    'No drainage direction, flood risk, erosion probability, bathymetry, water depth or causal environmental inference is produced.',
    'LiDAR and land-use layers are not included. The USP thesis supplies other historical modules, not this DSM or the OSM boundary.',
]


def geometry_transform(function, geometry):
    return transform_coordinates(geometry, lambda xy: np.column_stack(function(xy[:, 0], xy[:, 1])))


def surface_slope(z, dx, dy, excluded):
    """Degrees; centered derivatives, full 3x3 stencil, no one-sided edges."""
    if dx <= 0 or dy <= 0 or z.ndim != 2 or z.shape != excluded.shape:
        raise ValueError('Invalid metric grid or mask.')
    result = np.full(z.shape, np.nan)
    if min(z.shape) < 3:
        return result
    valid = np.isfinite(z) & ~excluded
    stencil = np.ones((z.shape[0]-2, z.shape[1]-2), dtype=bool)
    for row in range(3):
        for col in range(3):
            stencil &= valid[row:row+z.shape[0]-2, col:col+z.shape[1]-2]
    dzdx = (z[1:-1, 2:] - z[1:-1, :-2])/(2*dx)
    dzdy = (z[2:, 1:-1] - z[:-2, 1:-1])/(2*dy)
    with np.errstate(invalid='ignore'):
        center = np.degrees(np.arctan(np.hypot(dzdx, dzdy)))
    result[1:-1, 1:-1] = np.where(stencil, center, np.nan)
    return result


def statistics(values, selected):
    valid = values[selected & np.isfinite(values)]
    count = int(valid.size)
    return {'selected_cell_count': int(selected.sum()), 'valid_cell_count': count,
            'missing_or_excluded_cell_count': int(selected.sum())-count,
            'minimum': float(valid.min()) if count else None,
            'maximum': float(valid.max()) if count else None,
            'median': float(np.median(valid)) if count else None}


def make_zones(lake, water, mode):
    if mode not in ('cumulative', 'rings'):
        raise ValueError('Choose cumulative buffers or disjoint rings.')
    zones = []
    previous = 0
    for distance in DISTANCES:
        inner = lake.buffer(previous, quad_segs=32) if mode == 'rings' and previous else lake
        zone = lake.buffer(distance, quad_segs=32).difference(inner).difference(water)
        zones.append((distance, previous if mode == 'rings' else 0, zone))
        previous = distance
    return zones


@lru_cache(maxsize=2)
def _load(paths_and_times):
    paths = [Path(p) for p,_ in paths_and_times]
    raster_path, water_path, raster_meta, water_meta = paths
    raster_metadata = json.loads(raster_meta.read_text(encoding='utf-8'))
    water_metadata = json.loads(water_meta.read_text(encoding='utf-8'))
    if raster_metadata.get('vertical_reference') != 'EGM2008':
        raise ValueError('Unknown vertical reference.')
    data = json.loads(water_path.read_text(encoding='utf-8'))
    if data.get('type') != 'FeatureCollection' or not data.get('features'):
        raise ValueError('Expected water FeatureCollection.')
    geometries, targets = [], []
    for feature in data['features']:
        if not isinstance(feature, dict) or not isinstance(feature.get('geometry'), dict):
            raise ValueError('Missing polygon geometry.')
        geometry = shape(feature['geometry'])
        if geometry.is_empty or not geometry.is_valid or geometry.geom_type not in ('Polygon', 'MultiPolygon'):
            raise ValueError('Invalid water polygon; no automatic geometry repair.')
        for polygon in ([geometry] if geometry.geom_type=='Polygon' else geometry.geoms):
            for ring in [polygon.exterior, *polygon.interiors]:
                if any(not math.isfinite(x) or not math.isfinite(y) or not -180<=x<=180 or not -90<=y<=90 for x,y,*_ in ring.coords):
                    raise ValueError('Invalid WGS 84 coordinate.')
        projected = geometry_transform(TO_UTM, geometry)
        geometries.append(projected)
        props = feature.get('properties') or {}
        if props.get('element')=='relation' and str(props.get('id'))=='17154522':
            targets.append(projected)
    if len(targets)!=1:
        raise ValueError('The target lake is not unique.')
    lake, water = targets[0], unary_union(geometries)
    with rasterio.open(raster_path) as src:
        if src.crs is None or src.crs.to_epsg()!=4326 or src.width*src.height>2_000_000:
            raise ValueError('Expected the small EPSG:4326 study crop.')
        if src.transform.b or src.transform.d or src.transform.a<=0 or src.transform.e>=0:
            raise ValueError('Expected north-up raster.')
        if src.scales[0] != 1 or src.offsets[0] != 0:
            raise ValueError('Expected the prepared unscaled DSM crop.')
        raw = src.read(1, masked=True).astype('float64').filled(np.nan)
        native_transform, native_shape, native_bounds = src.transform, raw.shape, src.bounds
        transform, width, height = calculate_default_transform(src.crs, 'EPSG:32723', src.width, src.height, *src.bounds, resolution=30)
        z = np.full((height, width), np.nan)
        reproject(raw, z, src_transform=src.transform, src_crs=src.crs, src_nodata=np.nan,
                  dst_transform=transform, dst_crs='EPSG:32723', dst_nodata=np.nan, resampling=Resampling.nearest)
    if not np.isfinite(z).any():
        raise ValueError('The DSM crop has no valid values.')
    # All-touched excludes even a partial water footprint from the slope stencil.
    water_touched = geometry_mask([mapping(water)], z.shape, transform, all_touched=True, invert=True)
    slope = surface_slope(z, abs(transform.a), abs(transform.e), water_touched)
    native_footprint = box(*native_bounds)
    # Densify before projecting the geographic rectangle to avoid straight-edge coverage assumptions.
    footprint = geometry_transform(TO_UTM, native_footprint.segmentize(.0001))
    return dict(z=z, slope=slope, transform=transform, lake=lake, water=water, footprint=footprint,
                native_transform=native_transform, native_shape=native_shape, native_bounds=list(native_bounds),
                raster_metadata=raster_metadata, water_metadata=water_metadata,
                raster_sha256=hashlib.sha256(raster_path.read_bytes()).hexdigest(),
                water_sha256=hashlib.sha256(water_path.read_bytes()).hexdigest(), polygon_count=len(geometries))


def dataset():
    paths = (RASTER_PATH, WATER_PATH, RASTER_META, WATER_META)
    try:
        return _load(tuple((str(p),p.stat().st_mtime_ns) for p in paths))
    except (OSError, ValueError, KeyError, TypeError, rasterio.errors.RasterioError, ShapelyError, ProjError) as exc:
        raise HTTPException(503, 'V6 source data unavailable or invalid. Restore the water GeoJSON, DSM crop and their metadata from the project package. No missing values are filled.') from exc


def selection_mask(grid, geometry):
    return geometry_mask([mapping(geometry)], grid['z'].shape, grid['transform'], all_touched=False, invert=True)


def provenance(grid):
    return {'dsm': {'name': 'Copernicus DEM GLO-30 Public', 'source_url': grid['raster_metadata'].get('source_url'),
                    'attribution': '© DLR e.V. 2010–2014 and © Airbus Defence and Space GmbH 2014–2018',
                    'prepared_at_utc': grid['raster_metadata'].get('prepared_at_utc'), 'sha256': grid['raster_sha256']},
            'water': {'name': 'OpenStreetMap contributors', 'lake_reference': 'relation/17154522', 'license': 'ODbL 1.0',
                      'url': 'https://www.openstreetmap.org/copyright', 'polygon_count': grid['polygon_count'],
                      'downloaded_at_utc': grid['water_metadata'].get('downloaded_at_utc'),
                      'source_selection_status': grid['water_metadata'].get('selection_status'), 'sha256': grid['water_sha256']}}


def analyze(mode='cumulative'):
    grid = dataset()
    summaries, features = [], []
    for distance, inner, zone in make_zones(grid['lake'], grid['water'], mode):
        selected = selection_mask(grid, zone)
        summary = {'outer_distance_m': distance, 'inner_distance_m': inner, 'mode': mode,
                   'zone_area_m2': zone.area, 'crop_coverage_fraction': min(1.0, zone.intersection(grid['footprint']).area/zone.area) if zone.area else None,
                   'elevation_m': statistics(grid['z'], selected), 'surface_slope_degrees': statistics(grid['slope'], selected)}
        summaries.append(summary)
        features.append({'type': 'Feature', 'properties': {'outer_distance_m': distance, 'inner_distance_m': inner,
                         'mode': mode, 'zone_area_m2': zone.area, 'status': 'educational_snapshot_analysis',
                         'construction_crs': 'EPSG:32723', 'excluded_water': 'All polygons in the bundled OSM snapshot',
                         'not_a_legal_or_park_boundary': True, 'source': 'OpenStreetMap contributors, ODbL 1.0'},
                         'geometry': mapping(geometry_transform(TO_WGS, zone))})
    finite = grid['z'][np.isfinite(grid['z'])]
    return {'version': 'V6', 'status': 'educational_snapshot_analysis', 'mode': mode, 'zones': summaries,
            'zone_geojson': {'type': 'FeatureCollection', 'features': features},
            'lake_geojson': {'type': 'Feature', 'properties': {'source':'OpenStreetMap contributors','reference':'relation/17154522'},
                             'geometry': mapping(geometry_transform(TO_WGS,grid['lake']))},
            'raster_bounds_west_south_east_north': grid['native_bounds'],
            'projected_grid': {'crs': 'EPSG:32723', 'resolution_m': 30, 'width': grid['z'].shape[1], 'height':grid['z'].shape[0]},
            'method': {'buffer_crs': 'WGS 84 / UTM zone 23S (EPSG:32723)', 'buffer_arc_segments_per_quadrant':32,
                       'grid_resampling': 'Nearest native cell onto a 30 m projected grid', 'zone_mask':'Projected cell centers inside zone',
                       'slope':'atan(hypot(centered dz/dx, centered dz/dy)) in degrees; full valid 3×3 neighborhood; all-touched mapped water excluded',
                       'display_projection':'EPSG:3857; display-only nearest-cell warp for Leaflet',
                       'vertical_reference':'EGM2008', 'statistics':'Minimum, maximum, median of valid cells; no imputation'},
            'legends': {'elevation': {'minimum':float(finite.min()), 'maximum':float(finite.max()), 'unit':'m (EGM2008)',
                                    'colors':['#264b96','#38a5a0','#d4da9a','#bc8b51','#795334']},
                        'slope': {'minimum':0, 'maximum':45, 'unit':'degrees; 45° or more uses the top color',
                                  'colors':['#eff7cf','#90cd89','#36a5a0','#4773a1','#663c83']}},
            'sources': provenance(grid), 'limitations':LIMITATIONS}


def raster_png(distance=100, mode='cumulative', layer='elevation'):
    if distance not in DISTANCES or layer not in ('elevation','slope'):
        raise ValueError('Invalid layer or buffer distance.')
    grid = dataset()
    zone = next(zone for outer,_,zone in make_zones(grid['lake'],grid['water'],mode) if outer==distance)
    values = grid['z'] if layer=='elevation' else grid['slope']
    values = np.where(selection_mask(grid,zone),values,np.nan)
    display = np.full(grid['native_shape'],np.nan)
    west,south,east,north = grid['native_bounds']
    left,bottom = TO_MERC(west,south);right,top = TO_MERC(east,north)
    display_transform = from_bounds(left,bottom,right,top,display.shape[1],display.shape[0])
    reproject(values,display,src_transform=grid['transform'],src_crs='EPSG:32723',src_nodata=np.nan,
              dst_transform=display_transform,dst_crs='EPSG:3857',dst_nodata=np.nan,resampling=Resampling.nearest)
    # This warp is display-only. Statistics always use the projected analysis grid.
    palette = analyze(mode)['legends'][layer]
    colors = np.array([tuple(bytes.fromhex(c[1:])) for c in palette['colors']])
    lo,hi = palette['minimum'],palette['maximum']
    valid = np.isfinite(display)
    fraction = np.zeros(display.shape)
    fraction[valid] = np.clip((display[valid]-lo)/(hi-lo) if hi>lo else 0,0,1)
    rgba=np.zeros((4,*display.shape),dtype='uint8')
    for band in range(3):
        rgba[band]=np.interp(fraction,np.linspace(0,1,len(colors)),colors[:,band]).astype('uint8')
    rgba[3]=np.where(valid,210,0).astype('uint8')
    with rasterio.Env(GDAL_PAM_ENABLED='NO'), MemoryFile() as mem:
        with mem.open(driver='PNG',width=display.shape[1],height=display.shape[0],count=4,dtype='uint8',
                      transform=display_transform) as image:
            image.write(rgba)
        return mem.read()


def export_csv(result):
    output=io.StringIO(newline='')
    fields=['mode','inner_distance_m','outer_distance_m','zone_area_m2','crop_coverage_fraction','metric','unit',
            'selected_cell_count','valid_cell_count','missing_or_excluded_cell_count','minimum','maximum','median',
            'analysis_crs','resolution_m','vertical_reference','dsm_sha256','water_sha256','source_dsm','source_water','source_dsm_url','source_water_url','dsm_prepared_at_utc','water_downloaded_at_utc','status','limitations']
    writer=csv.DictWriter(output,fieldnames=fields);writer.writeheader()
    for zone in result['zones']:
        for key,unit in [('elevation_m','m'),('surface_slope_degrees','degrees')]:
            writer.writerow({**{k:zone[k] for k in fields[:5]},'metric':key,'unit':unit,**zone[key],
                             'analysis_crs':'EPSG:32723','resolution_m':30,'vertical_reference':'EGM2008',
                             'dsm_sha256':result['sources']['dsm']['sha256'],'water_sha256':result['sources']['water']['sha256'],
                             'source_dsm':'Copernicus DEM GLO-30 Public','source_water':'OpenStreetMap contributors, relation/17154522, ODbL 1.0',
                             'source_dsm_url':result['sources']['dsm']['source_url'],'source_water_url':result['sources']['water']['url'],
                             'dsm_prepared_at_utc':result['sources']['dsm']['prepared_at_utc'],'water_downloaded_at_utc':result['sources']['water']['downloaded_at_utc'],
                             'status':result['status'],'limitations':' '.join(result['limitations'])})
    return output.getvalue().encode('utf-8-sig')
