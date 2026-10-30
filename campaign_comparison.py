"""V5: descriptive comparison of reviewed historical surface observations."""
import csv
import io
import math
from statistics import median
from environmental_monitoring import load_dataset

CAMPAIGNS = {
    'march': {'label': 'March 2000 — rainy period', 'dates': ['2000-03-13', '2000-03-15']},
    'may': {'label': 'May 2000 — intermediate period', 'dates': ['2000-05-16', '2000-05-18']},
    'august': {'label': 'August 2000 — dry period', 'dates': ['2000-08-09', '2000-08-11']},
}
LIMITATIONS = [
    'Historical observations from 2000, not current conditions or real-time monitoring.',
    'Only reviewed surface rows (0.0 m), two dates per campaign and station. No station pooling.',
    'Period names reproduce the source-table captions; no new seasonal or climate classification is inferred.',
    'Descriptive comparisons only: no significance tests, causal attribution, long-term trends or regulatory classification.',
    'No interpolation, missing-value imputation, lake-wide spatial estimate or bathymetric change calculation.',
    'pH is logarithmic: the median summarizes reported pH values, not mean hydrogen-ion activity. Differences are pH units, never percentages.',
    'No percentage changes are calculated for any parameter. Signed differences retain the source units.',
    'AI-assisted transcription visually checked against the PDF; no independent second review or instrument revalidation.',
]


def compare_campaigns(parameter='dissolved_oxygen', campaign_a='march', campaign_b='august', station=None):
    records, metadata = load_dataset()
    if parameter not in metadata['parameters'] or campaign_a not in CAMPAIGNS or campaign_b not in CAMPAIGNS:
        raise ValueError('Unknown parameter or campaign.')
    if campaign_a == campaign_b:
        raise ValueError('Choose two different campaigns.')
    if station is not None and station not in metadata['stations']:
        raise ValueError('Unknown station.')
    stations = [station] if station else list(metadata['stations'])
    statistic = 'median_of_reported_pH' if parameter == 'ph' else 'arithmetic_mean'
    unit = metadata['parameters'][parameter]['unit']
    difference_unit = 'pH units' if parameter == 'ph' else unit
    selected, summaries, within = [], [], []
    for role, campaign in [('A', campaign_a), ('B', campaign_b)]:
        dates = CAMPAIGNS[campaign]['dates']
        for st in stations:
            rows = sorted((r for r in records if r['parameter'] == parameter and
                           r['station'] == st and r['date'] in dates and r['depth_m'] == 0), key=lambda r:r['date'])
            if [r['date'] for r in rows] != dates:
                raise ValueError('Incomplete reviewed campaign: comparisons are unavailable; no values are imputed.')
            values = [r['value'] for r in rows]
            center = median(values) if parameter == 'ph' else math.fsum(values)/len(values)
            summaries.append({'role': role, 'campaign': campaign, 'station': st, 'parameter': parameter,
                              'unit': unit, 'depth_m': 0.0, 'n': len(rows), 'dates': dates,
                              'minimum': min(values), 'maximum': max(values), 'center': center,
                              'center_statistic': statistic})
            within.append({'campaign': campaign, 'station': st, 'first_date': dates[0], 'last_date': dates[-1],
                           'first_value': values[0], 'last_value': values[-1],
                           'difference_last_minus_first': values[-1]-values[0], 'difference_unit': difference_unit})
            selected.extend({**r, 'campaign': campaign, 'campaign_role': role} for r in rows)
    differences = []
    for st in stations:
        a = next(s for s in summaries if s['station'] == st and s['role'] == 'A')
        b = next(s for s in summaries if s['station'] == st and s['role'] == 'B')
        differences.append({'station': st, 'center_a': a['center'], 'center_b': b['center'],
                            'difference_b_minus_a': b['center']-a['center'], 'difference_unit': difference_unit,
                            'center_statistic': statistic, 'n_a': a['n'], 'n_b': b['n']})
    station_differences = []
    if station is None:
        for campaign in [campaign_a, campaign_b]:
            for day in CAMPAIGNS[campaign]['dates']:
                e1 = next(r for r in selected if r['date'] == day and r['station'] == 'E1')
                e2 = next(r for r in selected if r['date'] == day and r['station'] == 'E2')
                station_differences.append({'campaign': campaign, 'date': day, 'e1': e1['value'], 'e2': e2['value'],
                                            'difference_e2_minus_e1': e2['value']-e1['value'], 'difference_unit': difference_unit})
    return {'version': 'V5', 'status': 'historical_descriptive_comparison',
            'selection': {'parameter': parameter, 'campaign_a': campaign_a, 'campaign_b': campaign_b, 'station': station},
            'campaigns': CAMPAIGNS, 'parameter': metadata['parameters'][parameter],
            'source': metadata['source'], 'review': metadata['review'],
            'grouping_provenance': 'Captions and date/station headings of annex Tables 4–7, printed pages 150–153 (PDF 173–176).',
            'record_count': len(selected), 'records': selected, 'summaries': summaries,
            'campaign_differences': differences, 'within_campaign_changes': within,
            'station_differences': station_differences, 'limitations': LIMITATIONS}


def export_csv(result, section='observations'):
    keys = {'observations': 'records', 'summaries': 'summaries', 'campaign_differences': 'campaign_differences',
            'within_campaign_changes': 'within_campaign_changes', 'station_differences': 'station_differences'}
    if section not in keys:
        raise ValueError('Unknown export section.')
    rows = result[keys[section]]
    # Preserve a usable header even when a single-station selection has no station pairs.
    fields = list(rows[0]) if rows else ['campaign', 'date', 'e1', 'e2', 'difference_e2_minus_e1', 'difference_unit']
    extra = ['analysis_parameter', 'baseline_campaign', 'comparison_campaign', 'analysis_status',
             'analysis_source_author', 'analysis_source_year', 'analysis_source_url', 'analysis_source_table',
             'analysis_printed_page', 'analysis_pdf_page', 'analysis_center_statistic', 'analysis_scope', 'analysis_note']
    output = io.StringIO(newline='')
    writer = csv.DictWriter(output, fieldnames=fields+extra)
    writer.writeheader()
    for row in rows:
        item = {k: (';'.join(v) if isinstance(v,list) else v) for k,v in row.items()}
        item.update(analysis_parameter=result['selection']['parameter'],
                    baseline_campaign=result['selection']['campaign_a'], comparison_campaign=result['selection']['campaign_b'],
                    analysis_status=result['status'], analysis_source_author=result['source']['author'],
                    analysis_source_year=result['source']['year'], analysis_source_url=result['source']['url'],
                    analysis_source_table=result['parameter']['source_table'], analysis_printed_page=result['parameter']['printed_page'],
                    analysis_pdf_page=result['parameter']['pdf_page'], analysis_center_statistic=result['summaries'][0]['center_statistic'],
                    analysis_scope='Surface only, 0.0 m; historical observations in 2000',
                    analysis_note='Descriptive only; not current conditions. '+result['limitations'][5])
        writer.writerow(item)
    return output.getvalue().encode('utf-8-sig')
