"""Local-only serving of reviewed historical satellite products; no runtime downloads."""
import json
from pathlib import Path
from fastapi import HTTPException
BASE=Path(__file__).resolve().parent
DATA=BASE/"data/satellite"
def catalog():
    try:
        data=json.loads((DATA/"catalog.json").read_text(encoding="utf8"))
        scenes=data["scenes"]
        if len(scenes)<2 or len({s["id"] for s in scenes})!=len(scenes): raise ValueError("Invalid scene list")
        for s in scenes:
            if s["native_rgb_resolution_m"]!=10 or not (DATA/(s["id"]+".png")).is_file(): raise ValueError("Missing scene")
        return data
    except (OSError,ValueError,KeyError,TypeError) as exc:
        raise HTTPException(503,"Satellite images unavailable. Restore data/satellite from the V7 package or run prepare_satellite.py with internet access.") from exc

def image_path(scene_id):
    if scene_id not in {s["id"] for s in catalog()["scenes"]}: raise HTTPException(404,"Unknown satellite scene")
    return DATA/(scene_id+".png")
