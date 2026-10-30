"""Curated historical reading guide. Local references only; no live assertions."""
import csv
import io
import json
import re
from datetime import date
from html import escape
from pathlib import Path
from urllib.parse import urlencode, urlparse
from fastapi import HTTPException
BASE=Path(__file__).resolve().parent
DATA_PATH=BASE/"data/references/history_heritage.json"
CATEGORIES=("identity","culture","research","infrastructure")

def load_history():
    try:
        data=json.loads(DATA_PATH.read_text(encoding="utf-8"))
        sources=data["sources"]; events=data["events"]
        ids=[s["id"] for s in sources]
        if not ids or len(ids)!=len(set(ids)): raise ValueError("Source IDs must be unique")
        for s in sources:
            parsed=urlparse(s["url"])
            if parsed.scheme!="https" or not parsed.netloc or parsed.username or parsed.password: raise ValueError("Invalid source URL")
            date.fromisoformat(s["checked_on"])
            if not all(s.get(k) for k in ("title","publisher","locator","access_note")): raise ValueError("Source provenance missing")
        event_ids=set()
        for e in events:
            if e["id"] in event_ids: raise ValueError("Duplicate event")
            event_ids.add(e["id"])
            if e["category"] not in CATEGORIES or not e["source_ids"] or not set(e["source_ids"]).issubset(ids): raise ValueError("Unlinked event")
            if e["date_precision"]=="day": date.fromisoformat(e["date"])
            elif e["date_precision"]!="year" or len(e["date"])!=4: raise ValueError("Unsupported date precision")
            if str(e["year"])!=e["date"][:4]: raise ValueError("Year mismatch")
            if not all(e.get(k) for k in ("title","summary","notes","evidence_status")): raise ValueError("Event content missing")
        for note in data["uncertainties"]:
            if not set(note["source_ids"]).issubset(ids): raise ValueError("Unlinked uncertainty")
        return data
    except (OSError,ValueError,KeyError,TypeError) as exc:
        raise HTTPException(503,"History guide unavailable: restore data/references/history_heritage.json from the V8 package. No missing history is generated automatically.") from exc

def select_history(category=None,q="",start_year=None,end_year=None):
    if category is not None and category not in CATEGORIES: raise HTTPException(422,"Unknown history category")
    if start_year is not None and end_year is not None and start_year>end_year: raise HTTPException(422,"From year must not be later than To year")
    data=load_history()
    needle=q.strip().casefold()
    source_map={s["id"]:s for s in data["sources"]}
    selected=[]
    for e in data["events"]:
        if category and e["category"]!=category:continue
        if start_year is not None and e["year"]<start_year:continue
        if end_year is not None and e["year"]>end_year:continue
        text=" ".join([e["title"],e["summary"],e["notes"],e["date"],data["categories"][e["category"]]]+[source_map[s]["publisher"] for s in e["source_ids"]])
        if needle and needle not in text.casefold():continue
        selected.append(e)
    selected.sort(key=lambda e:(e["year"],e["date"],e["id"]))
    # Keep the full source catalog: uncertainty notes remain visible under every filter.
    return {**data,"events":selected,"event_count":len(selected),"total_event_count":len(data["events"]),"filters":{"category":category,"q":q.strip(),"start_year":start_year,"end_year":end_year}}

def export_csv(data):
    out=io.StringIO(newline="")
    columns=["id","date","date_precision","year","category","title","summary","notes","evidence_status","source_ids","source_urls","source_titles","source_publishers","source_locators","source_access_notes","reviewed_on","scope"]
    writer=csv.DictWriter(out,fieldnames=columns);writer.writeheader()
    sources={s["id"]:s for s in data["sources"]}
    for e in data["events"]:
        row={k:e[k] for k in columns if k in e}; refs=[sources[s] for s in e["source_ids"]]
        row["source_ids"]=" | ".join(e["source_ids"])
        for key,field in [("source_urls","url"),("source_titles","title"),("source_publishers","publisher"),("source_locators","locator"),("source_access_notes","access_note")]:row[key]=" | ".join(s[field] for s in refs)
        row.update(reviewed_on=data["reviewed_on"],scope=data["scope"])
        writer.writerow(row)
    return "\ufeff"+out.getvalue()

def render_history(data):
    esc=lambda v:escape(str(v),quote=True)
    refs={s["id"]:s for s in data["sources"]}
    def links(ids):return " ".join(f'<a href="{esc(refs[id]["url"])}" target="_blank" rel="noopener noreferrer">{esc(refs[id]["publisher"])} ↗</a>' for id in ids)
    selected=data["filters"]
    options='<option value="">All themes</option>'+''.join(f'<option value="{esc(k)}"'+(' selected' if selected["category"]==k else '')+f'>{esc(v)}</option>' for k,v in data["categories"].items())
    cards=[]
    for e in data["events"]:
        precision="Exact day reported" if e["date_precision"]=="day" else "Year only · day/month not established"
        cards.append(f'<article class="event"><div class="stamp"><time>{esc(e["date"])}</time><small>{precision}</small></div><div><div class="tag">{esc(data["categories"][e["category"]])}</div><h2>{esc(e["title"])}</h2><p>{esc(e["summary"])}</p><p class="note">{esc(e["notes"])}</p><div class="refs">{links(e["source_ids"])}</div></div></article>')
    if not cards:cards=['<p class="notice" role="status">No historical records match these filters. Clear filters to restore the timeline.</p>']
    sources=''.join(f'<article class="source"><h3>{esc(s["title"])}</h3><p>{esc(s["publisher"])} · Publication: {esc(s["published_date"] or "not established")} · Checked: {esc(s["checked_on"])}</p><p>{esc(s["locator"])}</p><p class="note">{esc(s["access_note"])}</p><a href="{esc(s["url"])}" target="_blank" rel="noopener noreferrer">Read source ↗</a></article>' for s in data["sources"])
    uncertainties=''.join(f'<article class="uncertainty"><h3>{esc(u["title"])}</h3><p>{esc(u["text"])}</p><div class="refs">{links(u["source_ids"])}</div></article>' for u in data["uncertainties"])
    params={k:v for k,v in selected.items() if v is not None and v!=""}
    export_url=lambda fmt:esc('/api/history-heritage/export?'+urlencode({**params,'format':fmt}))
    modules=''.join(f'<tr><th scope="row">{esc(m["version"])}</th><td>{esc(m["title"])}</td><td>{esc(m["status"])}</td></tr>' for m in data["project_closeout"]["modules"])
    limits=''.join(f'<li>{esc(x)}</li>' for x in data["project_closeout"]["limits"])
    template=(BASE/"assets/history_heritage.html").read_text(encoding='utf8')
    values={'overview':esc(data['overview']),'scope':esc(data['scope']),'count':str(data['event_count']),'total':str(data['total_event_count']),'source_count':str(len(data['sources'])),'reviewed':esc(data['reviewed_on']),'options':options,'query':esc(selected['q']),'start_year':esc(selected['start_year'] or ''),'end_year':esc(selected['end_year'] or ''),'cards':''.join(cards),'sources':sources,'uncertainties':uncertainties,'csv_url':export_url('csv'),'json_url':export_url('json'),'rights':esc(data['rights_note']),'modules':modules,'limits':limits}
    return re.sub(r'@@(\w+)@@', lambda match: values.get(match.group(1), match.group(0)), template)
