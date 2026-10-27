from fastapi.testclient import TestClient
import main

client = TestClient(main.app)


def test_historical_provenance_and_missing_survey_date_are_preserved():
    response = client.get('/api/historical-bathymetry')
    assert response.status_code == 200
    data = response.json()
    assert data['source']['defense_year'] == 2002
    assert data['source']['water_sampling_year'] == 2000
    assert data['source']['bathymetric_survey_date'] is None
    assert data['metrics']['maximum_depth_m'] == 6.7
    assert data['metrics']['volume_m3'] == 451739
    assert data['station_depth_discrepancy']['abstract_m'] != data['station_depth_discrepancy']['methods_section_m']


def test_panel_explicitly_attributes_thesis_and_historical_scope():
    response = client.get('/historical-bathymetry')
    assert response.status_code == 200
    assert 'not current measurements' in response.text
    assert 'Esperanza Hernández Piedrahíta' in response.text
    assert '451,739' in response.text
    assert 'unresolved' in response.text
    assert '__NOTICE__' not in response.text
    assert 'id="show-bathymetry"' in client.get('/').text


def test_thesis_figure_is_served_and_attributed():
    response = client.get('/historical-bathymetry/figure')
    assert response.status_code == 200
    assert response.headers['content-type'] == 'image/png'
    assert response.content.startswith(b'\x89PNG\r\n\x1a\n')
    panel = client.get('/historical-bathymetry').text
    assert 'src="/historical-bathymetry/figure"' in panel
    assert 'printed page 22 / PDF page 45' in panel
    assert 'Original Portuguese labels and colors are preserved' in panel


def test_exports_keep_historical_provenance():
    import csv
    import io
    response = client.get('/api/historical-bathymetry/export?format=csv')
    assert response.status_code == 200
    assert 'attachment;' in response.headers['content-disposition']
    rows = list(csv.DictReader(io.StringIO(response.content.decode('utf-8-sig'))))
    assert len(rows) == 5
    assert {r['unit'] for r in rows} == {'m', 'm2', 'm3'}
    for row in rows:
        assert row['bathymetric_survey_date'] == 'unconfirmed'
        assert row['thesis_defense_year'] == '2002'
        assert row['water_sampling_year'] == '2000'
        assert row['printed_page'] == '20'
        assert row['source_url'].startswith('https://teses.usp.br/')
        assert row['limitations']
        assert 'Unresolved' in row['station_depth_discrepancy']
    response = client.get('/api/historical-bathymetry/export?format=json')
    assert response.status_code == 200
    assert response.json() == client.get('/api/historical-bathymetry').json()
    assert response.json()['version'] == 'V3'
    assert 'filename="taquaral_v3_historical_bathymetry.json"' in response.headers['content-disposition']


def test_invalid_export_format_is_rejected():
    assert client.get('/api/historical-bathymetry/export?format=pdf').status_code == 422
