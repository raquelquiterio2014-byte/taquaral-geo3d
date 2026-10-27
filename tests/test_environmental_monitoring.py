import copy
import csv
import io

import pytest
from fastapi.testclient import TestClient
import main
import environmental_monitoring as em

client=TestClient(main.app)


def test_reviewed_subset_has_source_units_dates_and_surface_depth():
    data=client.get('/api/historical-water-quality').json()
    assert data['record_count']==48
    assert data['metadata']['record_count']==48
    assert len({r['date'] for r in data['records']})==6
    assert {r['station'] for r in data['records']}=={'E1','E2'}
    assert {r['depth_m'] for r in data['records']}=={0}
    assert all(r['date'].startswith('2000-') and r['source_year']==2002 for r in data['records'])
    assert all(r['review_status']=='visually_checked_against_pdf' for r in data['records'])
    assert all(r['source_url']==data['metadata']['source']['url'] for r in data['records'])


def test_source_column_alignment_and_printed_values():
    records=client.get('/api/historical-water-quality').json()['records']
    cells={(r['parameter'],r['date'],r['station']):r for r in records}
    oxygen=cells['dissolved_oxygen','2000-03-15','E1']
    assert oxygen['value']==7.19 and oxygen['value_raw']=='7,19'
    assert oxygen['source_table']==4 and oxygen['source_pdf_page']==173
    ph=cells['ph','2000-05-16','E2']
    assert ph['value']==8.19 and ph['unit']=='dimensionless'
    assert cells['conductivity','2000-03-15','E2']['value']==31
    assert cells['water_temperature','2000-08-11','E1']['value']==18.8


def test_filters_and_downloads_use_identical_selection():
    query='parameter=conductivity&station=E2&start=2000-05-01&end=2000-05-31'
    data=client.get('/api/historical-water-quality?'+query).json()
    assert data['record_count']==2
    assert [r['value'] for r in data['records']]==[150,153]
    assert client.get('/api/historical-water-quality/export?format=json&'+query).json()==data
    response=client.get('/api/historical-water-quality/export?format=csv&'+query)
    assert 'attachment' in response.headers['content-disposition']
    rows=list(csv.DictReader(io.StringIO(response.content.decode('utf-8-sig'))))
    assert len(rows)==2
    assert all(r['source_year']=='2002' and r['status']=='historical_published_measurement' and r['source_pdf_page']=='176' for r in rows)
    assert all('not describe current' in r['interpretation'] for r in rows)


def test_invalid_filters_and_empty_selection():
    for query in ['parameter=unknown','station=E3','start=invalid','start=2001-01-01&end=2000-01-01']:
        assert client.get('/api/historical-water-quality?'+query).status_code==422
    empty=client.get('/api/historical-water-quality?start=2026-01-01').json()
    assert empty['record_count']==0 and empty['records']==[]
    assert client.get('/api/historical-water-quality/export?format=pdf').status_code==422


@pytest.mark.parametrize('mutation',['unit','nan','duplicate','raw'])
def test_validation_rejects_corrupted_records(mutation):
    records,meta=em.load_dataset()
    records=copy.deepcopy(records)
    if mutation=='unit':records[0]['unit']='µg/L'
    if mutation=='nan':records[0]['value']='nan'
    if mutation=='duplicate':records[1]=copy.deepcopy(records[0])
    if mutation=='raw':records[0]['value_raw']='99,99'
    with pytest.raises(ValueError):em.validate_records(records,meta)


def test_source_excerpts_dashboard_and_plot_are_historical():
    for table in [4,5,6,7]:
        r=client.get(f'/environmental-monitoring/source-row/{table}')
        assert r.status_code==200 and r.content.startswith(b'\x89PNG')
    assert client.get('/environmental-monitoring/source-row/8').status_code==404
    assert 'id="show-environment"' in client.get('/').text
    html=client.get('/environmental-monitoring').text
    assert 'do not indicate current conditions or real-time monitoring' in html
    assert '48 surface observations' in html
    assert "mode:'markers'" in client.get('/assets/environmental_monitoring.js').text
