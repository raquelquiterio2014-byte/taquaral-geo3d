import copy
import csv
import io
import itertools
import pytest
from fastapi.testclient import TestClient
import main
import campaign_comparison as cc

client = TestClient(main.app)


def test_known_arithmetic_and_directions():
    data=client.get('/api/historical-campaign-comparison').json()
    assert data['record_count']==8
    e1,e2=data['campaign_differences']
    assert e1['center_a']==pytest.approx(7.41)
    assert e1['center_b']==pytest.approx(10.985)
    assert e1['difference_b_minus_a']==pytest.approx(3.575)
    assert e2['difference_b_minus_a']==pytest.approx(3.5)
    assert all(s['n']==2 for s in data['summaries'])
    assert data['station_differences'][0]['difference_e2_minus_e1']==pytest.approx(-.22)
    assert data['within_campaign_changes'][0]['difference_last_minus_first']==pytest.approx(-.44)
    reverse=cc.compare_campaigns(campaign_a='august',campaign_b='march')
    assert reverse['campaign_differences'][0]['difference_b_minus_a']==pytest.approx(-3.575)


@pytest.mark.parametrize('parameter,a,b,station', list(itertools.product(
    ['dissolved_oxygen','water_temperature','ph','conductivity'],
    ['march','may','august'],['march','may','august'],[None,'E1','E2'])))
def test_every_selection(parameter,a,b,station):
    q={'parameter':parameter,'campaign_a':a,'campaign_b':b}
    if station:q['station']=station
    response=client.get('/api/historical-campaign-comparison',params=q)
    if a==b:
        assert response.status_code==422
        return
    assert response.status_code==200
    d=response.json()
    assert d['record_count']==(4 if station else 8)
    assert {r['depth_m'] for r in d['records']}=={0}
    assert all(r['date'].startswith('2000-') and r['source_year']==2002 for r in d['records'])
    assert len(d['station_differences'])==(0 if station else 4)
    assert {s['station'] for s in d['summaries']}==({station} if station else {'E1','E2'})
    assert len(d['summaries'])==(2 if station else 4)


def test_ph_uses_median_units_not_percentage_or_concentration_mean():
    d=cc.compare_campaigns('ph','march','may','E1')
    assert d['summaries'][0]['center_statistic']=='median_of_reported_pH'
    assert d['summaries'][0]['center']==pytest.approx(5.87)
    assert d['campaign_differences'][0]['difference_b_minus_a']==pytest.approx(1.27)
    assert d['campaign_differences'][0]['difference_unit']=='pH units'
    assert not any('percent' in key for key in d['campaign_differences'][0])
    assert 'not mean hydrogen-ion' in ' '.join(d['limitations'])


def test_all_exports_preserve_selection_source_and_scope():
    q={'parameter':'conductivity','campaign_a':'march','campaign_b':'may','station':'E2'}
    d=client.get('/api/historical-campaign-comparison',params=q).json()
    assert d['campaign_differences'][0]['difference_b_minus_a']==107
    response=client.get('/api/historical-campaign-comparison/export',params={**q,'format':'json'})
    assert response.json()==d
    for section,key in [('observations','records'),('summaries','summaries'),('campaign_differences','campaign_differences'),('within_campaign_changes','within_campaign_changes'),('station_differences','station_differences')]:
        response=client.get('/api/historical-campaign-comparison/export',params={**q,'format':'csv','section':section})
        assert response.status_code==200
        rows=list(csv.DictReader(io.StringIO(response.content.decode('utf-8-sig'))))
        assert len(rows)==len(d[key])
        assert all(r['analysis_source_year']=='2002' and '2000' in r['analysis_scope'] for r in rows)
        assert all(r['analysis_status']=='historical_descriptive_comparison' for r in rows)
        assert all(r['analysis_source_url']==d['source']['url'] for r in rows)


def test_invalid_filters_and_missing_rows_fail_closed(monkeypatch):
    for query in ['parameter=salinity','station=E3','campaign_a=september','campaign_b=invalid','format=pdf','section=bad']:
        route='/api/historical-campaign-comparison/export' if query.startswith(('format','section')) else '/api/historical-campaign-comparison'
        assert client.get(route+'?'+query).status_code==422
    records,metadata=cc.load_dataset()
    monkeypatch.setattr(cc,'load_dataset',lambda:(copy.deepcopy(records[1:]),metadata))
    response=client.get('/api/historical-campaign-comparison')
    assert response.status_code==503
    assert 'no missing values' in response.json()['detail']


def test_v5_integrated_without_changing_v4_scope():
    assert 'id="show-campaign"' in client.get('/').text
    assert client.get('/api/historical-water-quality').json()['record_count']==48
    html=client.get('/campaign-comparison').text
    assert 'not current water conditions' in html
    assert '0.0 m' in html
    assert 'Historical Campaign Comparison' in html
    script=client.get('/assets/campaign_comparison.js').text
    assert "mode:'markers'" in script
    assert 'current!==revision' in script
