# -*- coding: utf-8 -*-
import json, os, glob, subprocess, re, shutil

PB = os.environ.get("FFPROBE_BIN", "ffprobe")
HOME = os.environ["USERPROFILE"]
WORK = os.environ.get("VIDEO_WORK") or os.path.join(HOME, "video_work")
# your copy of skills/video-montage/remotion-template
PROJ = os.environ.get("REMOTION_PROJECT") or os.path.join(HOME, "remotion-project")

# locate source clips folder
src = None
roots = [HOME, os.path.join(HOME, "OneDrive")] + [d for d in glob.glob(os.path.join(HOME, "OneDrive", "*")) if os.path.isdir(d)]
for base in roots:
    for d in glob.glob(os.path.join(base, "*")):
        if os.path.isdir(d) and len(glob.glob(os.path.join(d, "*.MOV"))) > 3 and glob.glob(os.path.join(d, "*.ogg")):
            src = d; break
    if src: break
print("src:", src)

CLEAN = os.path.join(WORK, "clean_voice2.m4a")
# copy clean voice into source folder so Remotion --public-dir can serve it
shutil.copy(CLEAN, os.path.join(src, "clean_voice2.m4a"))

VOICE = float(subprocess.check_output([PB, "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", CLEAN]).decode().strip())

# clips from EDL, rescaled to voice length, mapped to real filenames
edl = json.load(open(os.path.join(WORK, "edl.json"), encoding="utf-8"))
total = sum(float(e.get("dur_seconds") or 0) for e in edl) or 1
scale = VOICE / total
clips = []
for e in edl:
    base = (e.get("clip") or "").strip()
    matches = [os.path.basename(m) for m in glob.glob(os.path.join(src, base + ".*")) if m.lower().endswith((".mov", ".mp4"))]
    if not matches:
        continue
    clips.append({"file": matches[0], "dur": round(max(1.3, float(e.get("dur_seconds") or 2.5) * scale), 3)})

# words from clean transcript (trans3), dedup consecutive
data3 = json.load(open(glob.glob(os.path.join(WORK, "trans3", "*.json"))[0], encoding="utf-8"))
def norm(s): return re.sub(r"\W+", "", s.lower(), flags=re.UNICODE)
raw = []
for seg in data3.get("segments", []):
    for w in seg.get("words", []):
        t = (w.get("word") or "").strip()
        if t and "start" in w and "end" in w:
            raw.append([float(w["start"]), float(w["end"]), t])
words = []
for w in raw:
    if words and norm(w[2]) and norm(w[2]) == norm(words[-1]["t"]):
        words[-1]["e"] = round(w[1], 3); continue
    words.append({"s": round(w[0], 3), "e": round(w[1], 3), "t": w[2]})

# keyword icon inserts (first occurrence)
# keyword -> icon; adapt to your narration (substring match on normalized word)
TRIGGERS = [("команда","👥"),("идея","💡"),("нейро","🧠"),("ночь","🌙"),
            ("город","🏙️"),("быстрее","🚀"),("стандарт","📋"),("рост","📈")]
inserts, used = [], set()
for wd in words:
    nt = norm(wd["t"])
    for trig, emo in TRIGGERS:
        if trig not in used and trig in nt:
            inserts.append({"t": wd["s"], "emoji": emo})
            used.add(trig); break

out = {
    "fps": 30, "w": 1080, "h": 1920,
    "audio": "clean_voice2.m4a",
    "voice": round(VOICE, 3),
    "introF": 102, "outroF": 90,
    # intro/outro card texts; edit per project
    "title": "ЗАГОЛОВОК", "subtitle": "подзаголовок ролика", "caption": "месяц · год", "outro": "спасибо за внимание",
    "clips": clips, "words": words, "inserts": inserts,
}
os.makedirs(os.path.join(PROJ, "src"), exist_ok=True)
json.dump(out, open(os.path.join(PROJ, "src", "data.json"), "w", encoding="utf-8"), ensure_ascii=False)
print("voice %.1fs | clips %d | words %d | inserts %d" % (VOICE, len(clips), len(words), len(inserts)))
