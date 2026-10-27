"""Historical published results; no bathymetric surface is generated."""
import json
import csv
import io
from html import escape
from pathlib import Path

DATA_PATH = Path(__file__).resolve().parent / "data/references/historical_bathymetry.json"


def load_historical_bathymetry():
    return json.loads(DATA_PATH.read_text(encoding="utf-8"))


def render_historical_bathymetry(data):
    source, metrics = data["source"], data["metrics"]
    cards = "".join(
        '<article><span>' + escape(label) + '</span><strong>' + escape(value) + '</strong></article>'
        for label, value in [
            ("Published maximum depth", f'{metrics["maximum_depth_m"]:.1f} m'),
            ("Published mean depth", f'{metrics["mean_depth_m"]:.2f} m'),
            ("Published water volume", f'{metrics["volume_m3"]:,.0f} m³'),
            ("Published water area", f'{metrics["area_m2"]:,.2f} m²'),
            ("Published perimeter", f'{metrics["perimeter_m"]:,.2f} m'),
        ]
    )
    limitations = "".join('<li>' + escape(note) + '</li>' for note in data["limitations"])
    classes = "".join('<span class="band">' + escape(item["label"]) + '</span>' for item in data["published_depth_classes_m"])
    return """<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Historical Bathymetry — Published Data Explorer</title>
<style>
*{box-sizing:border-box}body{margin:0;padding:24px;background:#10202b;color:#edf5fa;font:16px/1.6 Arial,sans-serif}
h1{font-size:26px;margin:4px 0 12px}h2{font-size:20px;margin-top:28px}a{color:#66e5c4}
.notice{padding:18px;border-left:5px solid #5de0be;background:#192f3d;border-radius:8px}
.tag{color:#ffd087;font-weight:bold;font-size:13px;letter-spacing:1px}.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(205px,1fr));gap:14px;margin:24px 0}
article{background:#192f3d;border:1px solid #304b5c;border-radius:10px;padding:18px}article span{display:block;font-size:14px;color:#c1d5df}strong{display:block;font-size:27px;color:#5de0be;margin-top:8px}
.band{display:inline-block;padding:8px 14px;border:1px solid #7084ae;border-radius:6px;margin:4px;background:#23394d}
figure{margin:24px 0;padding:18px;background:#192f3d;border:1px solid #304b5c;border-radius:12px}figure img{display:block;width:100%;max-width:780px;height:auto;margin:16px auto;background:white;border-radius:4px}figcaption{max-width:900px;margin:auto;font-size:14px;color:#c1d5df}.figure-actions{display:flex;flex-wrap:wrap;gap:16px}.figure-actions a{padding:8px 12px;border:1px solid #5de0be;border-radius:6px}details{margin-top:18px}summary{cursor:pointer;color:#66e5c4}
small{color:#bdd0da}li{margin:8px 0}.citation{overflow-wrap:anywhere}table{border-collapse:collapse;width:100%;max-width:660px}td,th{text-align:left;border-bottom:1px solid #304b5c;padding:10px}
</style></head><body><div class="tag">V3 · PUBLISHED DATA EXPLORER</div>
<h1>Historical Bathymetry — Published Data Explorer</h1><p class="notice">__NOTICE__</p>
<p class="figure-actions" aria-label="Historical data downloads"><a href="/api/historical-bathymetry/export?format=csv">Download CSV</a><a href="/api/historical-bathymetry/export?format=json">Download JSON</a></p>
<p><small>Downloads include the source, page references, historical status and limitations. No new bathymetric measurements are generated.</small></p>
<div class="cards">__CARDS__</div>
<small>Transcribed published results — not recalculated from the current map. Printed page 20 / PDF page 43.</small>
<h2>Historical depth map — thesis Figure 3</h2>
<figure aria-labelledby="thesis-map-caption">
    <p class="figure-actions"><a href="/historical-bathymetry/figure" target="_blank" rel="noopener noreferrer">Open map at full size</a><a href="__URL__" target="_blank" rel="noopener noreferrer">Consult the original thesis</a></p>
    <img src="/historical-bathymetry/figure"
         alt="Historical map from thesis Figure 3 showing Taquaral Lake depth bands from less than 1 meter to 6–6.7 meters, two sampling stations, inflow and outflow."
         width="880" height="1346" loading="lazy">
    <figcaption id="thesis-map-caption">Source: __AUTHOR__ (2002), doctoral thesis, USP. Figure 3, printed page 22 / PDF page 45. Extracted from the published figure; page margins cropped. Original Portuguese labels and colors are preserved. Historical reference image — not a current survey or a georeferenced map layer.</figcaption>
</figure>
<details><summary>Read the map labels in English</summary><p>Gradiente de profundidade: depth gradient (m). Estação 1 / Estação 2: sampling station 1 / 2. Afluente: inflow. Efluente: outflow. Direção da corrente: flow direction. Barco: boat. Pedalinhos: pedal boats. Concha acústica: acoustic shell. Profundidade média: mean depth (wording printed on the original figure). Depth bands are listed below.</p></details>
<h2>Published depth classes</h2><p>__CLASSES__</p>
<p>Figure 3, printed page 22 / PDF page 45, shows seven depth classes and two sampling stations. These labels describe the published figure; this panel does not display a georeferenced depth layer.</p>
<h2>Method and dates</h2><p>__METHOD__</p>
<p>Thesis defended in 2002. Water sampling campaigns: March, May and August 2000. The bathymetric survey date remains unconfirmed.</p>
<h2>Source consistency check</h2>
<p>The abstract and the methods section report different station depths. The discrepancy remains unresolved.</p>
<table><thead><tr><th>Location</th><th>Abstract</th><th>Methods (p. 21)</th></tr></thead>
<tbody><tr><td>Near the outlet</td><td>5.70 m</td><td>5.50 m</td></tr><tr><td>Central region</td><td>3.50 m</td><td>3.70 m</td></tr></tbody></table>
<h2>Scope and limitations</h2><ul>__LIMITATIONS__</ul>
<h2>Source and attribution</h2><p class="citation">__AUTHOR__ (2002). <em>__TITLE__</em>. Doctoral thesis, __INSTITUTION__.</p>
<p><a href="__URL__" target="_blank" rel="noopener noreferrer">Consult the original thesis at USP</a> · <a href="/api/historical-bathymetry" target="_blank" rel="noopener noreferrer">View data and provenance (JSON)</a></p>
<p><small>Source reviewed on 27 October 2026. This explorer is developed based on the cited thesis. Reconstructing the underwater surface is outside this V3 release.</small></p>
</body></html>""".replace("__NOTICE__", escape(data["notice"])).replace("__CARDS__", cards).replace("__CLASSES__", classes).replace("__METHOD__", escape(data["method"])).replace("__LIMITATIONS__", limitations).replace("__AUTHOR__", escape(source["author"])).replace("__TITLE__", escape(source["title"])).replace("__INSTITUTION__", escape(source["institution"])).replace("__URL__", escape(source["url"], quote=True))


def export_historical_bathymetry_csv(data):
    """Export summary metrics with provenance on every row (UTF-8 BOM)."""
    output = io.StringIO(newline="")
    fields = ["metric", "value", "unit", "status", "author", "thesis_title", "institution",
              "thesis_defense_year", "water_sampling_year", "bathymetric_survey_date",
              "printed_page", "pdf_page", "source_url", "limitations",
              "station_depth_discrepancy"]
    writer = csv.DictWriter(output, fieldnames=fields)
    writer.writeheader()
    source = data["source"]
    for metric, unit in [("maximum_depth_m", "m"), ("mean_depth_m", "m"),
                         ("volume_m3", "m3"), ("area_m2", "m2"), ("perimeter_m", "m")]:
        writer.writerow({
            "metric": metric, "value": data["metrics"][metric], "unit": unit,
            "status": data["status"], "author": source["author"],
            "thesis_title": source["title"], "institution": source["institution"],
            "thesis_defense_year": source["defense_year"],
            "water_sampling_year": source["water_sampling_year"],
            "bathymetric_survey_date": source["bathymetric_survey_date"] or "unconfirmed",
            "printed_page": source["metrics_printed_page"],
            "pdf_page": source["metrics_pdf_page"], "source_url": source["url"],
            "limitations": " | ".join(data["limitations"]),
            "station_depth_discrepancy": json.dumps(data["station_depth_discrepancy"], ensure_ascii=False),
        })
    return output.getvalue().encode("utf-8-sig")
