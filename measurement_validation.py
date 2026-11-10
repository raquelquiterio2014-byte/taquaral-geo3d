"""Reproducible internal checks, explicitly separate from positional validation."""
import argparse
import csv
import hashlib
import io
import json
import math
import platform
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from itertools import combinations

import numpy as np
import pyproj
from pyproj import CRS, Geod, Proj, Transformer
from shapely.geometry import Point, shape
from fastapi import HTTPException
import connected_exploration as ce
import lake_constraint as lc

BASE=Path(__file__).resolve().parent
GEOD=Geod(ellps='WGS84')
CRS_UTM=CRS.from_epsg(32723)
UTM=Transformer.from_crs(4326,CRS_UTM,always_xy=True)
PROJECTION=Proj(CRS_UTM)
LIMIT_PERCENT=0.1
DISCLAIMER='Internal calculation consistency only; no independent source-geometry or positional accuracy validation.'

def compare_distances(lat1,lon1,lat2,lon2):
    """Project-local diagnostic; never transform endpoints into separate UTM zones."""
    for lat,lon in ((lat1,lon1),(lat2,lon2)):
        if not math.isfinite(lat) or not math.isfinite(lon): raise ValueError('Coordinates must be finite')
        if not (-48<=lon<=-42 and -80<=lat<=0):
            raise ValueError('Diagnostic requires the EPSG:32723 area of use, in one fixed CRS')
    az,_,geodesic=GEOD.inv(lon1,lat1,lon2,lat2)
    x1,y1=UTM.transform(lon1,lat1,errcheck=True)
    x2,y2=UTM.transform(lon2,lat2,errcheck=True)
    planar=math.hypot(x2-x1,y2-y1)
    # Local short-pair comparison, not a global 0.1% accuracy guarantee.
    if geodesic>2500: raise ValueError('Diagnostic is limited to project-local pairs <= 2500 m')
    factors=[]
    for fraction in np.linspace(0,1,11):
        lon,lat,_=GEOD.fwd(lon1,lat1,az,geodesic*float(fraction))
        f=PROJECTION.get_factors(lon,lat,errcheck=True)
        factors.extend((f.meridional_scale,f.parallel_scale))
    delta=planar-geodesic
    signed=None if geodesic==0 else delta/geodesic*100
    return {'point_a':{'latitude':lat1,'longitude':lon1},'point_b':{'latitude':lat2,'longitude':lon2},
            'geodesic_m':float(geodesic),'utm_grid_m':planar,'signed_difference_m':delta,
            'absolute_difference_m':abs(delta),'relative_difference_percent':signed,
            'diagnostic_limit_percent':LIMIT_PERCENT,'within_local_diagnostic_limit':None if signed is None else abs(signed)<=LIMIT_PERCENT,
            'sampled_scale_min':min(factors),'sampled_scale_max':max(factors),
            'zero_length_pair':geodesic==0,'interpretation':DISCLAIMER}

def _lake_and_pairs():
    data=json.loads(lc.DATA.read_text(encoding='utf8'))
    matches=[f for f in data['features'] if f.get('properties',{}).get('element')=='relation' and str(f['properties'].get('id'))=='17154522']
    if len(matches)!=1:raise ValueError('Lake not uniquely identified')
    lake=shape(matches[0]['geometry'])
    if not lake.is_valid or lake.is_empty or lake.geom_type not in {'Polygon','MultiPolygon'}:raise ValueError('Invalid lake')
    west,south,east,north=lake.bounds
    points=[(float(lon),float(lat)) for lon in np.linspace(west,east,21)[1:-1]
            for lat in np.linspace(south,north,11)[1:-1] if lake.covers(Point(lon,lat))]
    candidates=[(GEOD.inv(a[0],a[1],b[0],b[1])[2],a,b) for a,b in combinations(points,2)]
    selected=[]; used=set()
    for target in (50,100,250,500,750,1000):
        for distance,a,b in sorted(candidates,key=lambda item:abs(item[0]-target)):
            if (a,b) in used:continue
            try:lc.require_lake_selection(b[1],b[0],a[1],a[0])
            except HTTPException as exc:
                if exc.status_code==422:continue
                raise
            selected.append((a,b));used.add((a,b));break
        else:raise ValueError('Unable to derive six distinct in-lake test pairs')
    return selected

@lru_cache(maxsize=2)
def _report(water_path,water_mtime,raster_path,raster_mtime):
    grid=ce.surface(); comparisons=[]
    for index,(a,b) in enumerate(_lake_and_pairs(),1):
        comparison=compare_distances(a[1],a[0],b[1],b[0])
        profile=ce.profile(a[1],a[0],b[1],b[0])
        comparison.update(pair_id=f'local-{index}',segment_covered_by_mapped_lake=True,
                          profile_sample_count=profile['sample_count'],valid_profile_samples=profile['valid_sample_count'],
                          missing_profile_samples=profile['sample_count']-profile['valid_sample_count'])
        comparisons.append(comparison)
    return {'title':'Measurement validation — peer-feedback review','reviewed_at_utc':datetime.now(timezone.utc).isoformat(),
            'scope':DISCLAIMER,'horizontal_crs':'WGS 84 / UTM zone 23S (EPSG:32723)',
            'reference_distance':'Shortest WGS 84 ellipsoidal geodesic; no terrain or elevation reduction',
            'grid_distance':'Euclidean distance between endpoints projected together into EPSG:32723; raw grid scale, not ground distance',
            'pair_source':'Six deterministic diagnostic pairs derived from the OSM polygon; not surveyed control points and not historical observations',
            'pairs':comparisons,'maximum_absolute_relative_difference_percent':max(abs(c['relative_difference_percent']) for c in comparisons),
            'all_local_pairs_within_diagnostic_limit':all(c['within_local_diagnostic_limit'] for c in comparisons),
            'boundary_rules':{'predicate':'covers (boundary included)','path_check':'Whole piecewise-linear representation of the geodesic, chords <= 1 m; exterior and mapped holes checked','limitation':'Numerical approximation in geographic coordinates, not proof of exact shoreline position or sub-meter field accuracy'},
            'raster':{'valid_cell_count':int(np.isfinite(grid['z']).sum()),'invalid_cell_count':int((~np.isfinite(grid['z'])).sum()),
                      'missing_value_behavior':'Raster validity masks and non-finite values become None/null samples; Plotly connectgaps:false; no zero filling or gap interpolation',
                      'nominal_sampling_m':30,'model_type':'DSM, not bathymetry'},
            'positional_accuracy':{'status':'NOT_VALIDATED','independent_reference_available':False,'control_points_tested':0,
                                   'reason':'No independently verified authoritative shoreline survey and matched control points are supplied with this project.',
                                   'requirements':['Reference provenance, lineage independence, CRS/datum, survey date and uncertainty','Matched identifiable boundary locations and comparable shoreline epoch/water level','Offsets and their distribution, with reference uncertainty and sampling method; calculation agreement alone is insufficient']},
            'threshold_note':'0.1% is a project-local diagnostic, not a universal same-zone bound. Expected raw-grid differences depend on projection scale and path. A larger difference prompts investigation; it is not proof of a bug or a zone crossing.',
            'sources':{'boundary_sha256':hashlib.sha256(Path(water_path).read_bytes()).hexdigest(),'dsm_sha256':hashlib.sha256(Path(raster_path).read_bytes()).hexdigest(),
                       'documentation':['https://shapely.readthedocs.io/en/stable/reference/shapely.covers.html','https://proj.org/en/stable/operations/projections/utm.html','https://pyproj4.github.io/pyproj/stable/api/proj.html','https://rasterio.readthedocs.io/en/stable/topics/masks.html']},
            'runtime':{'python':platform.python_version(),'pyproj':pyproj.__version__,'proj':pyproj.proj_version_str}}

def build_report():
    try:return _report(str(lc.DATA),lc.DATA.stat().st_mtime_ns,str(ce.RASTER_PATH),ce.RASTER_PATH.stat().st_mtime_ns)
    except (OSError,KeyError,ValueError,TypeError) as exc:
        raise HTTPException(503,'Measurement review unavailable: restore the lake GeoJSON and DSM crop.') from exc

def csv_report(data):
    out=io.StringIO(newline='')
    fields=['pair_id','latitude_a','longitude_a','latitude_b','longitude_b','geodesic_m','utm_grid_m','signed_difference_m','relative_difference_percent','sampled_scale_min','sampled_scale_max','valid_profile_samples','missing_profile_samples','scope']
    writer=csv.DictWriter(out,fieldnames=fields);writer.writeheader()
    for p in data['pairs']:
        row={k:p[k] for k in fields if k in p};row.update(latitude_a=p['point_a']['latitude'],longitude_a=p['point_a']['longitude'],latitude_b=p['point_b']['latitude'],longitude_b=p['point_b']['longitude'],scope=data['scope']);writer.writerow(row)
    return '\ufeff'+out.getvalue()

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,default=BASE/'outputs/measurement_validation');args=parser.parse_args()
    data=build_report();args.output.mkdir(parents=True,exist_ok=True)
    (args.output/'report.json').write_text(json.dumps(data,indent=2,allow_nan=False)+'\n',encoding='utf8')
    (args.output/'pairs.csv').write_text(csv_report(data),encoding='utf8')
    print(f"Pairs: {len(data['pairs'])}; max difference: {data['maximum_absolute_relative_difference_percent']:.6f}%")
    print('Positional accuracy: NOT_VALIDATED (independent survey and controls unavailable)')
    print(args.output)
if __name__=='__main__':main()
