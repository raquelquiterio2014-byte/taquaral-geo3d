import csv
import io
import json
import math
import numpy as np
import pytest
import rasterio
from fastapi.testclient import TestClient
from rasterio.io import MemoryFile
from shapely.geometry import Point, box, shape
import main
import spatial_context as sc

client=TestClient(main.app)


def test_planar_surface_has_analytical_slope_and_invalid_edges():
    yy,xx=np.indices((7,8));z=10+xx*3+yy*6
    slope=sc.surface_slope(z.astype(float),30,30,np.zeros(z.shape,dtype=bool))
    assert np.allclose(slope[1:-1,1:-1],math.degrees(math.atan(math.hypot(.1,.2))))
    assert np.isnan(slope[[0,-1],:]).all() and np.isnan(slope[:,[0,-1]]).all()
    flat=sc.surface_slope(np.full((5,5),650.),30,30,np.zeros((5,5),dtype=bool))
    assert np.all(flat[1:-1,1:-1]==0)


def test_water_and_nodata_remove_entire_neighborhood_without_zero_fill():
    z=np.arange(81,dtype=float).reshape(9,9)
    excluded=np.zeros(z.shape,dtype=bool);excluded[3,3]=True;z[6,6]=np.nan
    slope=sc.surface_slope(z,30,30,excluded)
    assert np.isnan(slope[2:5,2:5]).all()
    assert np.isnan(slope[5:8,5:8]).all()
    assert np.isfinite(slope[1,1])
    stats=sc.statistics(z,np.ones(z.shape,dtype=bool))
    assert stats['valid_cell_count']==80 and stats['missing_or_excluded_cell_count']==1
    empty=sc.statistics(np.full((2,2),np.nan),np.ones((2,2),dtype=bool))
    assert empty['median'] is None and empty['valid_cell_count']==0


def test_metric_buffers_rings_and_water_exclusions():
    lake=Point(300000,7470000).buffer(100,quad_segs=32)
    other=Point(300200,7470000).buffer(20)
    water=lake.union(other)
    cumulative=sc.make_zones(lake,water,'cumulative')
    rings=sc.make_zones(lake,water,'rings')
    assert cumulative[0][2].intersection(water).area<1e-6
    assert cumulative[-1][2].area==pytest.approx(sum(z.area for _,_,z in rings))
    assert rings[0][2].intersection(rings[1][2]).area<1e-6
    assert cumulative[0][2].difference(cumulative[1][2]).area<1e-6
    # Outer buffer extends the original radius by 100 projected meters.
    assert cumulative[0][2].bounds[0]==pytest.approx(299800,abs=.1)
    with pytest.raises(ValueError):sc.make_zones(lake,water,'unknown')


@pytest.mark.parametrize('mode',['cumulative','rings'])
def test_actual_analysis_geometry_counts_and_statistics(mode):
    response=client.get('/api/spatial-context',params={'mode':mode})
    assert response.status_code==200
    d=response.json();grid=sc.dataset()
    assert d['version']=='V6' and d['method']['vertical_reference']=='EGM2008'
    assert d['sources']['water']['polygon_count']==11
    assert [z['outer_distance_m'] for z in d['zones']]==[100,250,500]
    assert d['projected_grid']['resolution_m']==30
    for zone,feature in zip(d['zones'],d['zone_geojson']['features']):
        geom=sc.geometry_transform(sc.TO_UTM,shape(feature['geometry']))
        assert geom.intersection(grid['water']).area<1e-5
        assert geom.area==pytest.approx(zone['zone_area_m2'],rel=1e-8)
        assert zone['crop_coverage_fraction']==pytest.approx(1)
        assert zone['surface_slope_degrees']['valid_cell_count']<=zone['elevation_m']['valid_cell_count']
        for key in ['elevation_m','surface_slope_degrees']:
            s=zone[key]
            assert s['selected_cell_count']==s['valid_cell_count']+s['missing_or_excluded_cell_count']
            assert s['minimum']<=s['median']<=s['maximum']
        if mode=='cumulative':
            # Independently select cell centers in the vector zone and check the median.
            rows,cols=np.indices(grid['z'].shape)
            x=grid['transform'].c+(cols+.5)*30;y=grid['transform'].f-(rows+.5)*30
            from shapely import contains_xy
            mask=contains_xy(geom,x,y)
            assert zone['elevation_m']['median']==pytest.approx(float(np.nanmedian(grid['z'][mask])))
    assert 'LiDAR' in ' '.join(d['limitations'])


@pytest.mark.filterwarnings('ignore:Dataset has no geotransform:rasterio.errors.NotGeoreferencedWarning')
@pytest.mark.parametrize('distance',[100,250,500])
@pytest.mark.parametrize('mode',['cumulative','rings'])
@pytest.mark.parametrize('layer',['elevation','slope'])
def test_raster_overlay_is_rgba_with_transparent_missing_pixels(distance,mode,layer):
    response=client.get('/api/spatial-context/raster',params={'distance':distance,'mode':mode,'layer':layer})
    assert response.status_code==200 and response.content.startswith(b'\x89PNG')
    with MemoryFile(response.content) as mem,mem.open() as src:
        assert src.count==4 and (src.height,src.width)==sc.dataset()['native_shape']
        alpha=src.read(4)
        assert (alpha==0).any() and (alpha>0).any()


def test_exports_have_sources_methods_units_and_match_analysis():
    d=client.get('/api/spatial-context?mode=rings').json()
    assert client.get('/api/spatial-context/export?mode=rings&format=json').json()==d
    geo=client.get('/api/spatial-context/export?mode=rings&format=geojson').json()
    assert geo['features']==d['zone_geojson']['features'] and 'limitations' in geo
    assert geo['sources']['dsm']['sha256']==d['sources']['dsm']['sha256']
    response=client.get('/api/spatial-context/export?mode=rings&format=csv')
    rows=list(csv.DictReader(io.StringIO(response.content.decode('utf-8-sig'))))
    assert len(rows)==6
    assert all(r['analysis_crs']=='EPSG:32723' and r['mode']=='rings' for r in rows)
    assert all(r['dsm_sha256']==d['sources']['dsm']['sha256'] for r in rows)
    assert float(rows[0]['median'])==d['zones'][0]['elevation_m']['median']
    assert 'not current' in rows[0]['limitations']


def test_invalid_queries_and_missing_sources_are_actionable(tmp_path,monkeypatch):
    for path in ['/api/spatial-context?mode=unknown','/api/spatial-context/raster?distance=10','/api/spatial-context/raster?layer=depth','/api/spatial-context/export?format=pdf']:
        assert client.get(path).status_code==422
    monkeypatch.setattr(sc,'RASTER_PATH',tmp_path/'missing.tif')
    r=client.get('/api/spatial-context')
    assert r.status_code==503 and 'Restore' in r.json()['detail']


def test_no_valid_zone_cells_and_zero_crop_overlap_are_not_zero_filled(monkeypatch):
    grid=dict(sc.dataset())
    mask=sc.selection_mask(grid,sc.make_zones(grid['lake'],grid['water'],'cumulative')[-1][2])
    grid['z']=np.where(mask,np.nan,grid['z']);grid['slope']=np.where(mask,np.nan,grid['slope'])
    grid['footprint']=box(0,0,1,1)
    monkeypatch.setattr(sc,'dataset',lambda:grid)
    d=sc.analyze()
    for zone in d['zones']:
        assert zone['crop_coverage_fraction']==0
        assert zone['elevation_m']['median'] is None
        assert zone['surface_slope_degrees']['valid_cell_count']==0


def test_v6_dashboard_preserves_v4_and_v5():
    assert 'id="show-spatial"' in client.get('/').text
    assert 'Surface Analysis' in client.get('/spatial-context').text
    assert client.get('/assets/spatial_context.js').status_code==200
    assert client.get('/api/historical-water-quality').json()['record_count']==48
    assert client.get('/api/historical-campaign-comparison').json()['version']=='V5'


def test_crop_with_no_valid_elevation_fails_closed(tmp_path,monkeypatch):
    path=tmp_path/'nodata.tif'
    from rasterio.transform import from_origin
    with rasterio.open(path,'w',driver='GTiff',height=4,width=4,count=1,dtype='float32',crs='EPSG:4326',transform=from_origin(-47.055,-22.87,.001,.001),nodata=-9999) as src:
        src.write(np.full((4,4),-9999,dtype='float32'),1)
    monkeypatch.setattr(sc,'RASTER_PATH',path)
    assert client.get('/api/spatial-context').status_code==503
