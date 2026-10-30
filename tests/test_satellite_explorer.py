import json
import numpy as np
import pytest
import rasterio
from fastapi.testclient import TestClient
from main import app
import satellite_explorer as se
client=TestClient(app)
def test_catalog_dates_and_products():
    r=client.get("/api/satellite/catalog");assert r.status_code==200
    d=r.json();assert len(d["scenes"])==3
    assert len({s["datetime"][:10] for s in d["scenes"]})==3
    assert "not quantitative reflectance" in d["limitations"][1]
    for s in d["scenes"]:
        assert s["native_rgb_resolution_m"]==10
        assert s["quality"]["scl_native_resolution_m"]==20
        assert s["quality"]["lake_pixel_centers"]["pixel_count"]>300
        assert 0<=s["scene_cloud_percent"]<=100
        assert 0<=s["quality"]["lake_pixel_centers"]["cloud_shadow_snow_percent"]<=100
        assert client.get(s["image"]).content[:8]==b"\x89PNG\r\n\x1a\n"
def test_source_resolution_and_png_geometry():
    from rasterio.warp import transform_bounds
    for s in se.catalog()["scenes"]:
        with rasterio.open(se.DATA/(s["id"]+".tif")) as src:
            assert src.count==3 and src.res==(10,10)
            assert src.width<300 and src.height<300
            assert src.read().max()>0
            b=transform_bounds(src.crs,4326,*src.bounds)
            assert b[0]<-47.05<b[2] and b[1]<-22.874<b[3]
        with rasterio.open(se.DATA/(s["id"]+"_scl.tif")) as src:
            assert src.res==(20,20)
            counts=s["quality"]["roi"]["class_counts"]
            assert sum(counts.values())==src.width*src.height
        assert s["bounds"][0][0]<-22.874<s["bounds"][1][0]
        assert s["bounds"][0][1]<-47.05<s["bounds"][1][1]
def test_missing_data_is_actionable(tmp_path,monkeypatch):
    monkeypatch.setattr(se,"DATA",tmp_path)
    r=client.get("/api/satellite/catalog");assert r.status_code==503
    assert "prepare_satellite.py" in r.json()["detail"]
def test_unknown_image_rejected():
    assert client.get("/api/satellite/image/not-a-scene").status_code==404
    assert client.get("/api/satellite/image/catalog.json").status_code==404
def test_dashboard_integration():
    html=client.get("/").text
    assert 'id="show-satellite"' in html and 'id="satellite-frame"' in html
    assert "taquaral:satellite-resize" in html
    h=client.get("/satellite-explorer");assert h.status_code==200
    assert 'id="date-a"' in h.text and 'id="date-b"' in h.text
    assert client.get("/assets/satellite_explorer.js").status_code==200
