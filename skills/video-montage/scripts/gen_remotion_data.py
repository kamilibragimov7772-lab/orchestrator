# -*- coding: utf-8 -*-
# Orchestrator stack for Claude Code. Author: @kamil_ibrgmv - https://instagram.com/kamil_ibrgmv
from video_config import required_dir, output_file, clip_files, validate_edl, scratch, one_file
import json, os, glob, subprocess, re, shutil

PB = os.environ.get("FFPROBE_BIN", "ffprobe")
WORK = required_dir("VIDEO_WORK", create=True)
# your copy of skills/video-montage/remotion-template
PROJ = required_dir("REMOTION_PROJECT")

# locate source clips folder
src = required_dir("VIDEO_SOURCE")

print("src:", src)

CLEAN = os.path.join(WORK, "clean_voice2.m4a")
# copy clean voice into source folder so Remotion --public-dir can serve it
audio_copy = os.path.join(src, "clean_voice2.m4a")
if os.path.exists(audio_copy): raise SystemExit("source audio target already exists; preserve it")
shutil.copy(CLEAN, audio_copy)

VOICE = float(subprocess.check_output([PB, "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", CLEAN]).decode().strip())

# clips from EDL, rescaled to voice length, mapped to real filenames
edl = validate_edl(json.load(open(os.path.join(WORK, "edl.json"), encoding="utf-8")), src)
total = sum(float(e.get("dur_seconds") or 0) for e in edl) or 1
scale = VOICE / total
clips = []
for e in edl:
    base = (e.get("clip") or "").strip()
    matches = [os.path.basename(m) for m in clip_files(src, base)]
    if not matches:
        continue
    clips.append({"file": matches[0], "dur": round(max(1.3, float(e.get("dur_seconds") or 2.5) * scale), 3)})

# words from clean transcript (trans3), dedup consecutive
data3 = json.load(open(one_file(os.path.join(WORK, "trans3"), ".json"), encoding="utf-8"))
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
