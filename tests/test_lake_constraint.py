import json
import sys
from pathlib import Path
import pytest
from fastapi import HTTPException
from shapely.geometry import shape
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import lake_constraint as lc

def test_actual_lake_and_outside_points():
    data=json.loads(lc.DATA.read_text())
    lake=shape(next(f['geometry'] for f in data['features'] if str(f['properties']['id'])=='17154522'))
    p=lake.representative_point()
    assert lc.require_lake_selection(p.y,p.x)['allowed']
    assert lc.require_lake_selection(p.y,p.x,p.y,p.x)['allowed']
    for lat,lon in [(-22.855278,-47.047778),(-22.871667,-47.041111)]:
        with pytest.raises(HTTPException, match='inside'):
            lc.require_lake_selection(lat,lon)

def fixture_lake(tmp_path,monkeypatch,geometry):
    p=tmp_path/'lake.geojson'
    p.write_text(json.dumps({'features':[{'properties':{'element':'relation','id':17154522},'geometry':geometry}]}))
    monkeypatch.setattr(lc,'DATA',p)

def test_hole_and_crossing(tmp_path,monkeypatch):
    fixture_lake(tmp_path,monkeypatch,{'type':'Polygon','coordinates':[
        [[0,0],[.01,0],[.01,.01],[0,.01],[0,0]],
        [[.004,.004],[.006,.004],[.006,.006],[.004,.006],[.004,.004]]]})
    assert lc.require_lake_selection(.002,.002,.002,.008)['allowed']
    with pytest.raises(HTTPException,match='inside'):
        lc.require_lake_selection(.005,.005)
    with pytest.raises(HTTPException,match='segment'):
        lc.require_lake_selection(.005,.002,.005,.008)
    assert lc.require_lake_selection(0,.005)['allowed']

def test_invalid_or_missing_boundary(tmp_path,monkeypatch):
    monkeypatch.setattr(lc,'DATA',tmp_path/'missing')
    with pytest.raises(HTTPException) as e: lc.require_lake_selection(0,0)
    assert e.value.status_code==503
    for args in [(float('nan'),0),(91,0),(0,0,0,None)]:
        with pytest.raises(HTTPException) as e: lc.require_lake_selection(*args)
        assert e.value.status_code==422

def test_installer_is_idempotent_and_fails_closed():
    from install_lake_limit import update
    main=Path(__file__).resolve().parents[1]/'main.py'
    current=main.read_text()
    assert update(current)==current
    assert 'require_lake_selection(lat2, lon2, lat1, lon1)' in current
    with pytest.raises(ValueError,match='No changes saved'):
        update('print("unsupported app")')
