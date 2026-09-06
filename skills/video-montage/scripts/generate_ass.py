# -*- coding: utf-8 -*-
from video_config import required_dir, output_file, clip_files, validate_edl, scratch
import json, os, glob, re

WORK = required_dir("VIDEO_WORK", create=True)
TRANS = os.path.join(WORK, "trans")
OUT   = os.path.join(WORK, "subs.ass")

js = glob.glob(os.path.join(TRANS, "*.json"))
if len(js) != 1:
    raise SystemExit("expected exactly one whisper JSON in " + TRANS)
data = json.load(open(js[0], encoding="utf-8"))

def ass_time(t):
    cs = int(round(t * 100)); h = cs//360000; m = (cs%360000)//6000; s = (cs%6000)//100; c = cs%100
    return "%d:%02d:%02d.%02d" % (h, m, s, c)

def norm(s):
    # \w is unicode-aware in py3 -> keeps Cyrillic letters and digits, drops punctuation/spaces
    return re.sub(r"\W+", "", s.lower(), flags=re.UNICODE)

raw = []
for seg in data.get("segments", []):
    for w in seg.get("words", []):
        t = (w.get("word") or "").strip()
        if t and "start" in w and "end" in w:
            raw.append([float(w["start"]), float(w["end"]), t])

# 1) drop consecutive duplicate words (Whisper stutter / repeats)
words = []
for w in raw:
    if words and norm(w[2]) and norm(w[2]) == norm(words[-1][2]):
        words[-1][1] = w[1]
        continue
    words.append(w)

# 2) drop a repeated 2-word pair right after itself
clean = []
i = 0
while i < len(words):
    if (i + 3 < len(words)
            and norm(words[i][2]) == norm(words[i+2][2])
            and norm(words[i+1][2]) == norm(words[i+3][2])):
        clean.append(words[i]); clean.append(words[i+1]); i += 4
    else:
        clean.append(words[i]); i += 1
words = clean

# chunk into short caption groups
chunks, cur = [], []
MAXW, MAXDUR = 5, 2.4
for w in words:
    if not cur:
        cur = [w]
    elif len(cur) >= MAXW or (w[1] - cur[0][0]) > MAXDUR:
        chunks.append(cur); cur = [w]
    else:
        cur.append(w)
if cur:
    chunks.append(cur)

header = """[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,90,&H0000E6FF,&H00FFFFFF,&H00101010,&H50000000,1,0,0,0,100,100,0,0,1,5,3,2,70,70,330,204

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

lines = [header.rstrip("\n")]
for ch in chunks:
    start, end = ch[0][0], ch[-1][1]
    if end <= start:
        end = start + 0.5
    parts = []
    for j, w in enumerate(ch):
        nxt = ch[j+1][0] if j+1 < len(ch) else w[1]
        dur = max(1, int(round((nxt - w[0]) * 100)))   # karaoke sweep timing per word
        parts.append("{\\kf%d}%s " % (dur, w[2]))
    text = "{\\fad(100,80)}" + "".join(parts).strip()
    lines.append("Dialogue: 0,%s,%s,Default,,0,0,0,,%s" % (ass_time(start), ass_time(end), text))

open(OUT, "w", encoding="utf-8").write("\n".join(lines) + "\n")
print("ASS:", OUT, "| chunks:", len(chunks), "| words:", len(words), "(raw:", len(raw), ")")
