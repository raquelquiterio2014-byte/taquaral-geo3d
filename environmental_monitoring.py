"""V4 initial slice: reviewed historical surface observations, not live monitoring."""
import csv
import io
import json
import math
from datetime import date
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATA_PATH = BASE_DIR / 'data/references/historical_water_quality.csv'
METADATA_PATH = BASE_DIR / 'data/references/historical_water_quality_metadata.json'


def validate_records(records, metadata):
    seen = set()
    parameters = metadata['parameters']
    for row in records:
        date.fromisoformat(row['date'])
        if row['date'] not in metadata['sample_dates']:
            raise ValueError('Date is outside the reviewed source columns.')
        if row['station'] not in metadata['stations'] or row['parameter'] not in parameters:
            raise ValueError('Unknown station or parameter.')
        specification = parameters[row['parameter']]
        if row['unit'] != specification['unit']:
            raise ValueError('Parameter unit does not match the reviewed source.')
        row['value'] = float(row['value'])
        row['depth_m'] = float(row['depth_m'])
        for key in ['source_year','source_table','source_printed_page','source_pdf_page','source_date_column']:
            row[key] = int(row[key])
        if not math.isfinite(row['value']) or row['depth_m'] != 0:
            raise ValueError('Expected a finite value from the reviewed surface row.')
        if float(row['value_raw'].replace(',','.')) != row['value']:
            raise ValueError('Normalized value differs from the printed-value transcription.')
        if row['source_table'] != specification['source_table'] or row['source_printed_page'] != specification['printed_page'] or row['source_pdf_page'] != specification['pdf_page']:
            raise ValueError('Source page/table mismatch.')
        if row['source_year'] != 2002 or row['status'] != 'historical_published_measurement' or row['review_status'] != 'visually_checked_against_pdf':
            raise ValueError('Missing historical status or review provenance.')
        if row['source_url'] != metadata['source']['url'] or row['source_author'] != metadata['source']['author']:
            raise ValueError('Source attribution mismatch.')
        key = (row['date'],row['station'],row['depth_m'],row['parameter'])
        if key in seen:
            raise ValueError('Duplicate station/date/depth/parameter observation.')
        seen.add(key)
    if len(records) != metadata['record_count']:
        raise ValueError('Reviewed dataset count mismatch.')
    return records


def load_dataset():
    metadata = json.loads(METADATA_PATH.read_text(encoding='utf-8'))
    with DATA_PATH.open(encoding='utf-8-sig',newline='') as stream:
        records = list(csv.DictReader(stream))
    return validate_records(records,metadata), metadata


def select_records(records, parameter=None, station=None, start=None, end=None):
    return [row for row in records if
        (parameter is None or row['parameter'] == parameter) and
        (station is None or row['station'] == station) and
        (start is None or row['date'] >= start.isoformat()) and
        (end is None or row['date'] <= end.isoformat())]


def csv_export(records, fieldnames):
    output = io.StringIO(newline='')
    writer = csv.DictWriter(output,fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(records)
    return output.getvalue().encode('utf-8-sig')
