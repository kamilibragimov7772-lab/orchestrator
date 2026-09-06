# -*- coding: utf-8 -*-
# Orchestrator stack for Claude Code. Author: @kamil_ibrgmv - https://instagram.com/kamil_ibrgmv
from video_config import required_dir, output_file, clip_files, validate_edl, scratch
import json, os, glob, re

WORK = required_dir("VIDEO_WORK", create=True)
TRANS = os.path.join(WORK, "trans3")
OUT   = os.path.join(WORK, "subs3.ass")
OFFSET = 3.4

js = glob.glob(os.path.join(TRANS, "*.json"))
if len(js) != 1:
    raise SystemExit("expected exactly one whisper JSON in " + TRANS)
data = json.load(open(js[0], encoding="utf-8"))

def at(t):
    t = t + OFFSET
    cs = int(round(t * 100)); h = cs//360000; m = (cs%360000)//6000; s = (cs%6000)//100; c = cs%100
    return "%d:%02d:%02d.%02d" % (h, m, s, c)

def norm(s):
    return re.sub(r"\W+", "", s.lower(), flags=re.UNICODE)

raw = []
for seg in data.get("segments", []):
    for w in seg.get("words", []):
        t = (w.get("word") or "").strip()
        if t and "start" in w and "end" in w:
            raw.append([float(w["start"]), float(w["end"]), t])

# dedup consecutive
words = []
for w in raw:
    if words and norm(w[2]) and norm(w[2]) == norm(words[-1][2]):
        words[-1][1] = w[1]; continue
    words.append(w)

# karaoke chunks
chunks, cur = [], []
for w in words:
    if not cur: cur = [w]
    elif len(cur) >= 5 or (w[1]-cur[0][0]) > 2.4: chunks.append(cur); cur = [w]
    else: cur.append(w)
if cur: chunks.append(cur)

# animated keyword inserts: first occurrence of each trigger
# keyword -> icon; adapt to your narration (substring match on normalized word)
TRIGGERS = [
    ("команда", "👥"),
    ("идея", "💡"),
    ("нейро", "🧠"),
    ("ночь", "🌙"),
    ("город", "🏙"),
    ("быстрее", "🚀"),
    ("стандарт", "📋"),
    ("рост", "📈"),
]
inserts = []
used = set()
for st, en, t in words:
    nt = norm(t)
    for trig, disp in TRIGGERS:
        if trig in used:
            continue
        if trig in nt:
            inserts.append((st, disp))
            used.add(trig)
            break

header = """[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,90,&H0000E6FF,&H00FFFFFF,&H00101010,&H50000000,1,0,0,0,100,100,0,0,1,5,3,2,70,70,330,204
Style: Insert,Segoe UI Emoji,165,&H00FFFFFF,&H000000FF,&H00101010,&H00000000,0,0,0,0,100,100,0,0,1,5,3,8,40,40,410,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

lines = [header.rstrip("\n")]
# karaoke (bottom)
for ch in chunks:
    start, end = ch[0][0], ch[-1][1]
    if end <= start: end = start + 0.5
    parts = []
    for j, w in enumerate(ch):
        nxt = ch[j+1][0] if j+1 < len(ch) else w[1]
        dur = max(1, int(round((nxt - w[0]) * 100)))
        parts.append("{\\kf%d}%s " % (dur, w[2]))
    text = "{\\fad(100,80)}" + "".join(parts).strip()
    lines.append("Dialogue: 0,%s,%s,Default,,0,0,0,,%s" % (at(start), at(end), text))
# animated keyword inserts (top, pop-in)
for st, disp in inserts:
    anim = "{\\fad(120,140)\\fscx30\\fscy30\\t(0,200,\\fscx115\\fscy115)\\t(200,360,\\fscx100\\fscy100)}"
    lines.append("Dialogue: 1,%s,%s,Insert,,0,0,0,,%s%s" % (at(st), at(st + 1.8), anim, disp))

open(OUT, "w", encoding="utf-8").write("\n".join(lines) + "\n")
print("subs3:", OUT, "| karaoke:", len(chunks), "| inserts:", len(inserts))
