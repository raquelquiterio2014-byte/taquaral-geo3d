import numpy as np
import pytest
import rasterio
from fastapi.testclient import TestClient
from rasterio.transform import from_origin

import main
import connected_exploration as ce

client = TestClient(main.app)
PAIR = {'lat1': -22.875038, 'lon1': -47.057190, 'lat2': -22.873220, 'lon2': -47.046676}


def test_profile_preserves_endpoints_and_geodesic_distance():
    r = client.get('/api/surface-profile', params=PAIR)
    assert r.status_code == 200
    p = r.json()
    assert p['distance_m'] == pytest.approx(client.get('/api/distance', params=PAIR).json()['distance_m'])
    assert round(p['distance_m']) == 1098
    assert 0 < p['sample_spacing_m'] <= 30
    assert p['samples'][0]['latitude'] == PAIR['lat1']
    assert p['samples'][-1]['longitude'] == PAIR['lon2']
    assert p['samples'][0]['distance_m'] == 0
    assert p['samples'][-1]['distance_m'] == p['distance_m']
    assert all(a['distance_m'] < b['distance_m'] for a,b in zip(p['samples'],p['samples'][1:]))
    assert p['vertical_reference'] == 'EGM2008'
    assert 'not water depth' in p['limitations']
    assert p['samples'][0]['elevation_m'] == client.get('/api/surface-point', params={'lat':PAIR['lat1'],'lon':PAIR['lon1']}).json()['elevation_m']


def test_identical_points_are_supported():
    p = client.get('/api/surface-profile', params={**PAIR, 'lat2': PAIR['lat1'], 'lon2': PAIR['lon1']}).json()
    assert p['distance_m'] == 0
    assert p['sample_count'] == 2
    assert p['samples'][0]['elevation_m'] == p['samples'][1]['elevation_m']


def test_scene_dimensions_overlay_and_native_pixels():
    data = client.get('/api/surface-scene').json()
    z = np.array(data['z'], dtype=float)
    assert z.shape == np.shape(data['x']) == np.shape(data['y'])
    assert np.shape(data['customdata']) == (*z.shape, 2)
    assert data['overlay_display_lift_m'] == 1
    assert data['lake_source'].startswith('OpenStreetMap')
    assert any(v is not None for v in data['lake_line']['z'])
    lat, lon = data['customdata'][20][30]
    p = ce.point(lat, lon)
    assert p['elevation_m'] == z[20,30]
    assert p['east_offset_m'] == pytest.approx(data['x'][20][30])
    assert p['north_offset_m'] == pytest.approx(data['y'][20][30])
    assert np.isfinite(z).any()


def test_invalid_and_outside_profiles_are_rejected():
    assert client.get('/api/surface-profile', params={**PAIR, 'lat1': 'nan'}).status_code == 422
    assert client.get('/api/surface-profile', params={**PAIR, 'lat1': 0}).status_code == 422


def test_missing_crop_is_actionable(tmp_path, monkeypatch):
    monkeypatch.setattr(ce, 'RASTER_PATH', tmp_path/'missing.tif')
    r = client.get('/api/surface-profile', params=PAIR)
    assert r.status_code == 503
    assert 'build_surface_3d.py' in r.json()['detail']


def test_nearest_cell_nodata_and_bounds(tmp_path, monkeypatch):
    path = tmp_path/'crop.tif'
    values = np.array([[10,-9999],[30,40]], dtype='float32')
    with rasterio.open(path,'w',driver='GTiff',height=2,width=2,count=1,dtype='float32',
                       crs='EPSG:4326',transform=from_origin(-47.06,-22.87,.001,.001),nodata=-9999) as dst:
        dst.write(values,1)
    monkeypatch.setattr(ce,'RASTER_PATH',path)
    assert ce.sample(-22.8705,-47.0595) == 10
    assert ce.sample(-22.8705,-47.0585) is None
    assert ce.sample(-22.872,-47.0595) is None
    assert ce.sample(-22.8705,-47.058) is None
    r = client.get('/api/surface-profile',params={'lat1':-22.8705,'lon1':-47.0595,'lat2':-22.8705,'lon2':-47.0585})
    assert r.status_code == 200
    assert r.json()['samples'][-1]['elevation_m'] is None


def test_v2_assets_and_v3_are_separate():
    assert 'id="show-connected"' in client.get('/').text
    html = client.get('/connected-exploration').text
    assert 'Connected Spatial Exploration' in html
    assert 'thesis' not in html.lower()
    script = client.get('/assets/connected_exploration.js').text
    assert 'event.origin !== origin' in script
    assert '/api/surface-profile' in script
    assert '/api/historical-bathymetry' not in script
    assert client.get('/api/historical-bathymetry').json()['version'] == 'V3'
