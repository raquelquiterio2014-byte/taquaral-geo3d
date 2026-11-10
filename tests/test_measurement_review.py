"""Regression cases suggested by public peer feedback; synthetic geometry is not a survey."""
import csv
import io
import json
import math
import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin
from shapely.geometry import Polygon, Point, mapping
from pyproj import Geod
from fastapi import HTTPException
from fastapi.testclient import TestClient
import main
import lake_constraint as lc
import connected_exploration as ce
from measurement_validation import compare_distances, build_report

client=TestClient(main.app)

def fixture(tmp_path,monkeypatch,polygon):
    path=tmp_path/'water.geojson'
    path.write_text(json.dumps({'features':[{'properties':{'element':'relation','id':17154522},'geometry':mapping(polygon)}]}))
    monkeypatch.setattr(lc,'DATA',path)

@pytest.mark.parametrize('point',[(0,0),(.005,0),(.01,.005)])
def test_covers_accepts_exact_boundary_where_contains_rejects(tmp_path,monkeypatch,point):
    lake=Polygon([(0,0),(.01,0),(.01,.01),(0,.01)])
    assert not lake.contains(Point(*point)) and lake.covers(Point(*point))
    fixture(tmp_path,monkeypatch,lake)
    assert lc.require_lake_selection(point[1],point[0])['allowed']

def test_concave_shore_both_endpoints_inside_but_crossing_rejected(tmp_path,monkeypatch):
    lake=Polygon([(0,0),(.01,0),(.01,.01),(.006,.01),(.006,.003),(.004,.003),(.004,.01),(0,.01)])
    assert lake.contains(Point(.002,.008)) and lake.contains(Point(.008,.008))
    fixture(tmp_path,monkeypatch,lake)
    with pytest.raises(HTTPException,match='segment'):lc.require_lake_selection(.008,.008,.008,.002)
    assert lc.require_lake_selection(.001,.008,.001,.002)['allowed']

def test_narrow_hole_between_vertices_is_not_missed(tmp_path,monkeypatch):
    # ~0.1 m wide hole: checking only sampled vertices could miss it.
    lake=Polygon([(0,0),(.001,0),(.001,.001),(0,.001)],holes=[[(.0005001,.0004),(.000501,.0004),(.000501,.0006),(.0005001,.0006)]])
    fixture(tmp_path,monkeypatch,lake)
    with pytest.raises(HTTPException,match='segment'):lc.require_lake_selection(.0005,.0009,.0005,.0001)

def test_http_distance_and_profile_reject_land_crossing(tmp_path,monkeypatch):
    lake=Polygon([(-47.06,-22.88),(-47.05,-22.88),(-47.05,-22.87),(-47.054,-22.87),(-47.054,-22.877),(-47.056,-22.877),(-47.056,-22.87),(-47.06,-22.87)])
    fixture(tmp_path,monkeypatch,lake)
    params=dict(lat1=-22.872,lon1=-47.058,lat2=-22.872,lon2=-47.052)
    for route in ['/api/distance','/api/surface-profile']:
        r=client.get(route,params=params);assert r.status_code==422 and 'segment' in r.json()['detail']

@pytest.mark.parametrize('values,nodata',[
    ([50,-9999,70],-9999),([50,float('nan'),70],None),([50,float('inf'),70],None),([50,-float('inf'),70],None)])
def test_nodata_in_middle_of_profile_becomes_json_null(tmp_path,monkeypatch,values,nodata):
    path=tmp_path/'profile.tif'
    with rasterio.open(path,'w',driver='GTiff',height=1,width=3,count=1,dtype='float32',crs='EPSG:4326',transform=from_origin(-47.06,-22.87,.0001,.0001),nodata=nodata) as dst:
        dst.write(np.array([values],dtype='float32'),1)
    monkeypatch.setattr(ce,'RASTER_PATH',path)
    data=ce.profile(-22.87005,-47.05995,-22.87005,-47.05975)
    assert data['sample_count']==2 # short path; add an explicit center sample below
    assert ce.sample(-22.87005,-47.05985) is None
    # Repeat long enough at latitude sampling <=30 m to hit an interior masked cell.
    with rasterio.open(path,'w',driver='GTiff',height=1,width=3,count=1,dtype='float32',crs='EPSG:4326',transform=from_origin(-47.06,-22.87,.001,.001),nodata=nodata) as dst:
        dst.write(np.array([values],dtype='float32'),1)
    ce._load_surface.cache_clear()
    data=ce.profile(-22.8705,-47.0595,-22.8705,-47.0575)
    missing=[s for s in data['samples'][1:-1] if s['elevation_m'] is None]
    assert missing and data['samples'][0]['elevation_m']==50 and data['samples'][-1]['elevation_m']==70
    assert data['valid_sample_count']==sum(s['elevation_m'] is not None for s in data['samples'])
    assert 'NaN' not in json.dumps(data,allow_nan=False)


def test_all_nodata_rejected_and_zero_preserved(tmp_path,monkeypatch):
    path=tmp_path/'all.tif'
    with rasterio.open(path,'w',driver='GTiff',height=1,width=2,count=1,dtype='float32',crs='EPSG:4326',transform=from_origin(-47.06,-22.87,.001,.001),nodata=-9999) as dst:
        dst.write(np.array([[-9999,-9999]],dtype='float32'),1)
    monkeypatch.setattr(ce,'RASTER_PATH',path)
    with pytest.raises(HTTPException,match='no valid'):ce.surface()
    with rasterio.open(path,'r+') as dst:dst.write(np.array([[0,-9999]],dtype='float32'),1)
    ce._load_surface.cache_clear()
    assert ce.sample(-22.8705,-47.0595)==0


def test_utm_comparison_reports_projection_scale_and_degenerate_pair():
    d=compare_distances(-22.8744274,-47.0488455,-22.8744274,-47.0478455)
    assert d['within_local_diagnostic_limit'] and 0<abs(d['relative_difference_percent'])<.1
    ratio=d['utm_grid_m']/d['geodesic_m']
    assert d['sampled_scale_min']-1e-7<=ratio<=d['sampled_scale_max']+1e-7
    zero=compare_distances(-22.874,-47.05,-22.874,-47.05)
    assert zero['relative_difference_percent'] is None and zero['zero_length_pair']

@pytest.mark.parametrize('args',[(0,0,0,.001),(-22,-47,-22,-41),(-22,-47,-22,-46),(float('nan'),-47,-22,-47)])
def test_out_of_scope_coordinates_fail_closed(args):
    with pytest.raises(ValueError):compare_distances(*args)


def test_actual_report_api_provenance_and_distance_agreement():
    r=client.get('/api/measurement-validation');assert r.status_code==200
    data=r.json();assert len(data['pairs'])==6
    assert data['positional_accuracy']['status']=='NOT_VALIDATED'
    assert data['positional_accuracy']['control_points_tested']==0
    assert data['all_local_pairs_within_diagnostic_limit']
    assert 'not proof' in data['threshold_note']
    for p in data['pairs']:
        assert p['segment_covered_by_mapped_lake']
        a,b=p['point_a'],p['point_b']
        api=client.get('/api/distance',params=dict(lat1=a['latitude'],lon1=a['longitude'],lat2=b['latitude'],lon2=b['longitude'])).json()
        assert p['geodesic_m']==pytest.approx(api['distance_m'],abs=1e-8)
        assert p['profile_sample_count']==p['valid_profile_samples']+p['missing_profile_samples']
    rows=list(csv.DictReader(io.StringIO(client.get('/api/measurement-validation?format=csv').content.decode('utf-8-sig'))))
    assert len(rows)==6 and 'no independent' in rows[0]['scope']
    assert client.get('/api/measurement-validation?format=xml').status_code==422
    assert '/api/measurement-validation' in client.get('/connected-exploration').text
