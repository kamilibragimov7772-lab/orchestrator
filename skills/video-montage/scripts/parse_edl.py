# -*- coding: utf-8 -*-
# Orchestrator stack for Claude Code. Author: @kamil_ibrgmv - https://instagram.com/kamil_ibrgmv
from video_config import required_dir, output_file, clip_files, validate_edl, scratch
# Extract the EDL (list of {clip, dur_seconds, covers_text}) from an agent's JSON answer
# and save it as <VIDEO_WORK>/edl.json for the build_edit*.py / gen_remotion_data.py scripts.
#   py parse_edl.py <path-to-agent-output.txt|json>
import json, os, sys
WORK = required_dir("VIDEO_WORK", create=True)
if len(sys.argv) < 2:
    raise SystemExit("usage: py parse_edl.py <agent-output-file>")
p = sys.argv[1]
txt = open(p, encoding="utf-8").read()
i = txt.find('{')
data = json.loads(txt[i:])
print("top keys:", list(data.keys()))

def find_edl(o):
    if isinstance(o, dict):
        if 'edl' in o and isinstance(o['edl'], list):
            return o['edl']
        for v in o.values():
            r = find_edl(v)
            if r:
                return r
    elif isinstance(o, list):
        for v in o:
            r = find_edl(v)
            if r:
                return r
    return None

edl = find_edl(data)
if not edl:
    print("NO EDL FOUND")
    raise SystemExit(1)
validate_edl(edl)
tot = 0.0
for e in edl:
    d = float(e.get("dur_seconds") or 0)
    tot += d
    print("%5.1f  %-10s  %s" % (d, e.get("clip",""), (e.get("covers_text") or e.get("reason") or "")[:46]))
print("TOTAL %.1f s | clips: %d" % (tot, len(edl)))
os.makedirs(WORK, exist_ok=True)
json.dump(edl, open(os.path.join(WORK, "edl.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=0)
