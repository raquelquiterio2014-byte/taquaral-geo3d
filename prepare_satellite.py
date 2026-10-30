"""Download bounded public Sentinel-2 TCI/SCL windows; no account or full granule required."""
import json, threading, urllib.request, urllib.parse, hashlib, time
from pathlib import Path
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from datetime import datetime, timezone
import numpy as np
import rasterio
from rasterio.windows import from_bounds
from rasterio.warp import transform_bounds, calculate_default_transform, reproject, Resampling
from rasterio.features import geometry_mask
from shapely.geometry import shape, mapping
from shapely.ops import transform as transform_geometry
from pyproj import Transformer
BASE = Path(__file__).resolve().parent
OUT = BASE / "data/satellite"
BBOX = (-47.060, -22.879, -47.043, -22.869)
IDS = ["S2B_23KKQ_20251005_0_L2A", "S2B_23KKQ_20251022_0_L2A", "S2A_23KKQ_20251228_0_L2A"]

def request(url, headers=None, method=None):
    for attempt in range(3):
        try:
            return urllib.request.urlopen(urllib.request.Request(url, headers=headers or {}, method=method), timeout=40)
        except Exception:
            if attempt == 2: raise
            time.sleep(attempt+1)

class Proxy(BaseHTTPRequestHandler):
    """Loopback bridge: urllib verifies remote TLS; GDAL performs bounded range reads."""
    def log_message(self, *args): pass
    def do_HEAD(self):
        try:
            with request(self.server.urls[self.path], method="HEAD") as r:
                self.send_response(200)
                self.send_header("Content-Length", r.headers["Content-Length"])
                self.send_header("Accept-Ranges", "bytes"); self.end_headers()
        except Exception: self.send_error(502)
    def do_GET(self):
        try:
            if self.path not in self.server.urls or not self.headers.get("Range"):
                self.send_error(400); return
            with request(self.server.urls[self.path], {"Range":self.headers["Range"]}) as r:
                if r.status != 206: raise ValueError("Server ignored bounded range request")
                data = r.read(16*1024*1024+1)
                if len(data)>16*1024*1024: raise ValueError("Range response too large")
                self.send_response(206)
                for key in ("Content-Length", "Content-Range", "Content-Type"):
                    if r.headers.get(key): self.send_header(key,r.headers[key])
                self.end_headers(); self.wfile.write(data)
        except Exception: self.send_error(502)

def crop(asset):
    server=ThreadingHTTPServer(("127.0.0.1",0),Proxy); server.urls={"/asset.tif":asset}
    threading.Thread(target=server.serve_forever,daemon=True).start()
    try:
        with rasterio.Env(GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR", CPL_VSIL_CURL_ALLOWED_EXTENSIONS=".tif", GDAL_HTTP_TIMEOUT="50"):
            with rasterio.open(f"http://127.0.0.1:{server.server_port}/asset.tif") as src:
                bounds=transform_bounds("EPSG:4326",src.crs,*BBOX)
                w=from_bounds(*bounds,src.transform).round_offsets().round_lengths()
                a=src.read(window=w)
                return a,src.window_transform(w),src.crs
    finally: server.shutdown(); server.server_close()

def save_tiff(path, a, transform, crs):
    with rasterio.open(path,"w",driver="GTiff",height=a.shape[1],width=a.shape[2],count=a.shape[0],dtype=a.dtype,crs=crs,transform=transform,compress="deflate") as dst: dst.write(a)

def display_png(path,a,trans,crs):
    b=rasterio.transform.array_bounds(a.shape[1],a.shape[2],trans)
    t,w,h=calculate_default_transform(crs,"EPSG:3857",a.shape[2],a.shape[1],*b)
    out=np.zeros((4,h,w),dtype="uint8")
    for i in range(3): reproject(a[i],out[i],src_transform=trans,src_crs=crs,dst_transform=t,dst_crs="EPSG:3857",resampling=Resampling.nearest)
    alpha=np.where(np.any(a>0,axis=0),255,0).astype("uint8")
    reproject(alpha,out[3],src_transform=trans,src_crs=crs,dst_transform=t,dst_crs="EPSG:3857",resampling=Resampling.nearest)
    with rasterio.open(path,"w",driver="PNG",height=h,width=w,count=4,dtype="uint8") as dst: dst.write(out)
    west,south,east,north=transform_bounds("EPSG:3857","EPSG:4326",*rasterio.transform.array_bounds(h,w,t))
    return [[south,west],[north,east]]

def quality(scl,trans,crs,lake):
    geom=transform_geometry(Transformer.from_crs(4326,crs,always_xy=True).transform,lake)
    mask=geometry_mask([mapping(geom)],out_shape=scl.shape,transform=trans,invert=True)
    def counts(values):
        n=values.size
        return {"pixel_count":int(n),"valid_percent":float(np.count_nonzero(~np.isin(values,[0,1]))/n*100) if n else None,
                "cloud_shadow_snow_percent":float(np.count_nonzero(np.isin(values,[3,8,9,10,11]))/n*100) if n else None,
                "class_counts":{str(i):int(np.count_nonzero(values==i)) for i in range(12)}}
    return {"scl_native_resolution_m":20,"roi":counts(scl.ravel()),"lake_pixel_centers":counts(scl[mask]),"method":"SCL classes 3,8,9,10,11 flag shadows, clouds, cirrus or snow; 0/1 invalid. Pixel centers within current OSM lake polygon; approximate screening, not independent cloud validation."}

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    water=json.loads((BASE/"data/raw/water_candidates.geojson").read_text())
    feature=next(f for f in water["features"] if str(f["properties"].get("id"))=="17154522" and f["properties"].get("element")=="relation")
    scenes=[]
    for id in IDS:
        print("Preparing",id,flush=True)
        url="https://earth-search.aws.element84.com/v1/collections/sentinel-2-l2a/items/"+id
        with request(url) as r: item=json.load(r)
        rgb_path=OUT/(id+".tif")
        scl_path=OUT/(id+"_scl.tif")
        if rgb_path.exists() and scl_path.exists():
            with rasterio.open(rgb_path) as src: a,t,c=src.read(),src.transform,src.crs
            with rasterio.open(scl_path) as src: scl,st,sc=src.read(),src.transform,src.crs
        else:
            a,t,c=crop(item["assets"]["visual"]["href"])
            scl,st,sc=crop(item["assets"]["scl"]["href"])
        if a.shape[0]!=3 or a.max()==0: raise ValueError("Missing RGB coverage")
        save_tiff(OUT/(id+".tif"),a,t,c);save_tiff(OUT/(id+"_scl.tif"),scl,st,sc)
        bounds=display_png(OUT/(id+".png"),a,t,c)
        (OUT/(id+"_stac.json")).write_text(json.dumps(item,indent=2)+"\n")
        scenes.append({"id":id,"datetime":item["properties"]["datetime"],"platform":item["properties"].get("platform"),"scene_cloud_percent":item["properties"].get("eo:cloud_cover"),"native_rgb_resolution_m":10,"bands":["B04","B03","B02"],"bounds":bounds,"image":"/api/satellite/image/"+id,"stac_url":url,"assets":{k:item["assets"][k]["href"] for k in ["visual","scl"]},"quality":quality(scl[0],st,sc,shape(feature["geometry"])),"rgb_sha256":hashlib.sha256((OUT/(id+".tif")).read_bytes()).hexdigest()})
        print(id,scenes[-1]["quality"],flush=True)
    data={"version":"V7","title":"Historical Satellite Explorer","prepared_utc":datetime.now(timezone.utc).isoformat(),"scenes":scenes,"lake":feature,"source":"Contains modified Copernicus Sentinel data (2025), accessed through Earth Search / AWS Sentinel-2 L2A COGs.","source_url":"https://registry.opendata.aws/sentinel-2-l2a-cogs/","method":"Provider true-color TCI (B04/B03/B02), 8-bit display product at native 10 m; bounded source-grid crops. PNG display reprojected to EPSG:3857 with nearest-neighbor sampling for Leaflet. No per-date custom stretch or cloud removal. SCL screening at 20 m.","limitations":["Historical educational imagery; not live monitoring.","TCI is a display product, not quantitative reflectance. Color differences may reflect atmosphere, lighting, processing or viewing conditions.","Scene-wide cloud percentage does not describe only the lake. SCL screening can miss thin cloud and mixes shoreline pixels.","10 m sampling limits visible detail. Zoom does not add spatial resolution.","The same OSM outline is shown on every date; it is not a date-specific shoreline measurement.","Images do not establish water depth, chemistry, pollution, vegetation species or causes of apparent change.","2025 imagery is separate from the thesis's 2000 field records; no temporal validation is implied."]}
    data["aerial_reference"] = {'type': 'aerial_orthophoto', 'mosaic_period': '2023/2024', 'local_acquisition_day': 'unconfirmed', 'source': 'IGC / IDE-SP', 'source_native_gsd_m': 0.25, 'preview_dimensions': [1024, 640], 'request_url': 'https://www.idesp.sp.gov.br/geoimage/idesp_raster/wms?SERVICE=WMS&VERSION=1.1.1&REQUEST=GetMap&SRS=EPSG%3A4326&LAYERS=ORTOFOTOS_SP_2023_2024&STYLES=&BBOX=-47.059%2C-22.878%2C-47.045%2C-22.870&WIDTH=1024&HEIGHT=640&FORMAT=image%2Fpng&TRANSPARENT=TRUE', 'source_metadata_url': 'https://www.idesp.sp.gov.br/geonetwork/srv/api/records/86bc2552-5c53-49e3-b8fe-7cb7cd0b9181/formatters/xml', 'note': 'Optional online WMS portrayal, coarser than native GSD; not a satellite image or LiDAR point cloud. Exact flight day and reuse terms are not established here.'}
    (OUT/"catalog.json").write_text(json.dumps(data,indent=2,ensure_ascii=False)+"\n")
if __name__=="__main__": main()
