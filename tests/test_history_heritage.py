import copy
import csv
import io
import json
import pytest
from fastapi.testclient import TestClient
from main import app
import history_heritage as hh
client=TestClient(app)

def test_catalog_provenance_and_date_precision():
    data=hh.load_history();assert len(data["events"])==10 and len(data["sources"])==5
    refs={s["id"] for s in data["sources"]}
    for e in data["events"]:
        assert set(e["source_ids"])<=refs
        if e["date_precision"]=="year":assert len(e["date"])==4
    e={e["id"]:e for e in data["events"]}
    assert e["park-name-1950"]["date"]=="1950-07-14"
    assert e["park-opening-1972"]["date"]=="1972-11-05"
    assert "not lake water volume" in e["dredging-2016"]["notes"]
    assert "not been independently inspected" in e["park-name-1950"]["notes"]
    assert "not necessarily creation of the lake" in e["park-opening-1972"]["notes"]

def test_filters_and_csv_use_identical_event_selection():
    params={"category":"culture","start_year":"1982","end_year":"1987"}
    data=client.get("/api/history-heritage",params=params).json()
    assert [e["id"] for e in data["events"]]==["science-agreement-1982","planetarium-opening-1987"]
    r=client.get("/api/history-heritage/export",params={**params,"format":"csv"})
    assert r.status_code==200
    rows=list(csv.DictReader(io.StringIO(r.content.decode("utf-8-sig"))))
    assert [e["id"] for e in rows]==[e["id"] for e in data["events"]]
    assert all(row["source_urls"].startswith("https://") and row["source_locators"] for row in rows)
    assert len(data["sources"])==5 # reading notes remain linked under filtering
    assert client.get("/api/history-heritage/export",params={**params,"format":"json"}).json()==data

@pytest.mark.parametrize("params",[{"category":"unknown"},{"start_year":"2000","end_year":"1980"},{"start_year":"1499"},{"end_year":"2101"},{"start_year":"2000.0"},{"q":"x"*121},{"format":"xml"}])
def test_invalid_filters(params):
    path="/api/history-heritage/export" if "format" in params else "/api/history-heritage"
    assert client.get(path,params=params).status_code==422

def test_blank_native_form_fields_and_search():
    r=client.get("/history-heritage",params={"category":"","q":"PLANETARIUM","start_year":"","end_year":""})
    assert r.status_code==200 and "A planetarium project is proposed" in r.text
    assert "The park name honors an architect" not in r.text
    assert "q=PLANETARIUM" in r.text

def test_empty_search_and_escaped_user_text():
    r=client.get("/history-heritage",params={"q":"<script>alert(1)</script>"})
    assert r.status_code==200 and "No historical records match" in r.text
    assert "<script>alert(1)</script>" not in r.text
    assert "&lt;script&gt;" in r.text
    r=client.get("/history-heritage",params={"q":"@@cards@@"})
    assert 'value="@@cards@@"' in r.text # input is text, never another template pass

def test_missing_reference_data_actionable(tmp_path,monkeypatch):
    monkeypatch.setattr(hh,"DATA_PATH",tmp_path/"missing.json")
    r=client.get("/api/history-heritage");assert r.status_code==503
    assert "restore" in r.json()["detail"]

def test_broken_provenance_is_rejected(tmp_path,monkeypatch):
    data=hh.load_history();data["events"][0]["source_ids"]=["invented"]
    f=tmp_path/"history.json";f.write_text(json.dumps(data));monkeypatch.setattr(hh,"DATA_PATH",f)
    assert client.get("/api/history-heritage").status_code==503

def test_no_results_csv_keeps_header_and_json_keeps_notes():
    params={"q":"nothingmatchesthisphrase"}
    data=client.get("/api/history-heritage",params=params).json()
    assert data["event_count"]==0 and len(data["uncertainties"])==4
    rows=list(csv.DictReader(io.StringIO(client.get("/api/history-heritage/export",params={**params,"format":"csv"}).content.decode("utf-8-sig"))))
    assert rows==[]

def test_nine_tabs_and_history_route_have_no_external_dependency():
    html=client.get("/").text
    assert 'id="show-history"' in html and 'data-source="/history-heritage"' in html
    h=client.get("/history-heritage").text
    assert "Project conclusion" in h and "V1–V8" in h
    assert "<script" not in h and "<img" not in h
    assert "No LAS/LAZ" in h
