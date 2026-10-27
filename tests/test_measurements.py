import pytest
from fastapi.testclient import TestClient
from shapely.geometry import Polygon, mapping

import main


client = TestClient(main.app)


def test_dashboard_contains_both_views():
    response = client.get('/')
    assert response.status_code == 200
    assert 'id="show-map"' in response.text
    assert 'id="show-surface"' in response.text


def test_water_snapshot_identifies_one_lake():
    response = client.get('/api/water-features')
    assert response.status_code == 200
    data = response.json()
    assert len(data['features']) == 11
    assert main.get_lake_feature(data)['properties']['id'] == 17154522


def test_lake_metrics_match_documented_snapshot():
    response = client.get('/api/lake-metrics')
    assert response.status_code == 200
    result = response.json()
    assert round(result['water_area_m2']) == 150766
    assert round(result['outer_boundary_m']) == 2772
    assert result['water_area_ha'] == pytest.approx(result['water_area_m2'] / 10000)


def test_distance_is_zero_for_identical_points_and_symmetric():
    a = {'lat1': -22.875038, 'lon1': -47.057190,
         'lat2': -22.873220, 'lon2': -47.046676}
    distance = client.get('/api/distance', params=a).json()['distance_m']
    reverse = dict(lat1=a['lat2'], lon1=a['lon2'],
                   lat2=a['lat1'], lon2=a['lon1'])
    assert client.get('/api/distance', params=reverse).json()['distance_m'] == pytest.approx(distance)
    assert round(distance) == 1098
    a.update(lat2=a['lat1'], lon2=a['lon1'])
    assert client.get('/api/distance', params=a).json()['distance_m'] == 0


@pytest.mark.parametrize('value', [91, 'nan', 'inf'])
def test_distance_rejects_invalid_latitude(value):
    response = client.get('/api/distance', params={
        'lat1': value, 'lon1': -47.05, 'lat2': -22.87, 'lon2': -47.06,
    })
    assert response.status_code == 422


def test_hole_area_is_subtracted_without_changing_outer_boundary():
    outer = [(-47.06, -22.88), (-47.05, -22.88),
             (-47.05, -22.87), (-47.06, -22.87)]
    hole = [(-47.058, -22.878), (-47.052, -22.878),
            (-47.052, -22.872), (-47.058, -22.872)]
    def metrics(polygon):
        return main.calculate_lake_metrics({
            'geometry': mapping(polygon), 'properties': {},
        })
    full = metrics(Polygon(outer))
    cut = metrics(Polygon(outer, [hole]))
    removed = metrics(Polygon(hole))
    assert cut['water_area_m2'] == pytest.approx(full['water_area_m2'] - removed['water_area_m2'])
    assert cut['outer_boundary_m'] == pytest.approx(full['outer_boundary_m'])
    assert cut['interior_ring_count'] == 1


def test_missing_surface_has_actionable_response(tmp_path, monkeypatch):
    monkeypatch.setattr(main, '__file__', str(tmp_path / 'main.py'))
    response = client.get('/surface-3d')
    assert response.status_code == 404
    assert 'build_surface_3d.py' in response.json()['detail']
