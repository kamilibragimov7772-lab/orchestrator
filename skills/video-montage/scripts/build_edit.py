# -*- coding: utf-8 -*-
import json, os, glob, subprocess

# ffmpeg/ffprobe: on PATH, or full paths via env FFMPEG_BIN / FFPROBE_BIN
FF = os.environ.get("FFMPEG_BIN", "ffmpeg")
PB = os.environ.get("FFPROBE_BIN", "ffprobe")
HOME = os.environ["USERPROFILE"]
# working folder for intermediates (edl.json, whisper json, subs, temp segments)
WORK = os.environ.get("VIDEO_WORK") or os.path.join(HOME, "video_work")

def ffpath(p):
    # path form accepted inside ffmpeg filter strings on Windows: C\:/dir/file
    return p.replace("\\", "/").replace(":", "\\:")
VOICE = 151.0
W, H, FPS = 1080, 1920, 30

# find source folder (with .ogg + many .MOV) without typing non-ascii path
src = None
roots = [HOME, os.path.join(HOME, "OneDrive")]
roots += [d for d in glob.glob(os.path.join(HOME, "OneDrive", "*")) if os.path.isdir(d)]
for base in roots:
    for d in glob.glob(os.path.join(base, "*")):
        if os.path.isdir(d) and glob.glob(os.path.join(d, "*.ogg")) and len(glob.glob(os.path.join(d, "*.MOV"))) > 3:
            src = d; break
    if src: break
if not src:
    raise SystemExit("source folder not found")
print("src:", src)
ogg = glob.glob(os.path.join(src, "*.ogg"))[0]

edl = json.load(open(os.path.join(WORK, "edl.json"), encoding="utf-8"))
total = sum(float(e.get("dur_seconds") or 0) for e in edl)
scale = VOICE / total if total > 0 else 1.0
print("edl clips:", len(edl), "raw total: %.1f" % total, "scale: %.3f" % scale)

tmp = os.path.join(WORK, "edit")
os.makedirs(tmp, exist_ok=True)
for f in glob.glob(os.path.join(tmp, "e_*.mp4")):
    os.remove(f)

vf = ("scale=%d:%d:force_original_aspect_ratio=increase,crop=%d:%d,"
      "fps=%d,format=yuv420p,setsar=1,fade=t=in:st=0:d=0.2" % (W, H, W, H, FPS))

lines, n = [], 0
for e in edl:
    clip = e.get("clip", "").strip()
    matches = [m for m in glob.glob(os.path.join(src, clip + ".*")) if m.lower().endswith((".mov", ".mp4"))]
    if not matches:
        print("  missing:", clip); continue
    dur = max(1.3, float(e.get("dur_seconds") or 2.5) * scale)
    n += 1
    seg = os.path.join(tmp, "e_%03d.mp4" % n)
    subprocess.run([FF, "-y", "-hide_banner", "-loglevel", "error", "-ss", "0", "-t", "%.3f" % dur,
                    "-i", matches[0], "-vf", vf, "-an", "-c:v", "libx264", "-preset", "veryfast",
                    "-crf", "20", seg], check=False)
    if os.path.exists(seg) and os.path.getsize(seg) > 0:
        lines.append("file '%s'" % seg.replace("\\", "/"))
        print("  [%d] %s %.1fs" % (n, clip, dur))

listpath = os.path.join(tmp, "list.txt")
open(listpath, "w", encoding="utf-8").write("\n".join(lines) + "\n")

silent = os.path.join(tmp, "silent.mp4")
subprocess.run([FF, "-y", "-hide_banner", "-loglevel", "error", "-f", "concat", "-safe", "0",
                "-i", listpath, "-c", "copy", silent], check=False)
vdur = float(subprocess.check_output([PB, "-v", "error", "-show_entries", "format=duration",
                                      "-of", "csv=p=0", silent]).decode().strip())
fst = max(0.0, vdur - 1.6)
print("body duration: %.1f s" % vdur)

out = os.path.join(HOME, "Videos", "reels_v3.mp4")
os.makedirs(os.path.dirname(out), exist_ok=True)
vfb = ("subtitles=filename='%s':fontsdir='C\\:/Windows/Fonts'," % ffpath(os.path.join(WORK, "subs.ass")) +
       "fade=t=out:st=%.2f:d=1.6,format=yuv420p" % fst)
subprocess.run([FF, "-y", "-hide_banner", "-loglevel", "error", "-i", silent, "-i", ogg,
                "-map", "0:v:0", "-map", "1:a:0", "-vf", vfb,
                "-af", "afade=t=out:st=%.2f:d=1.6" % fst,
                "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
                "-c:a", "aac", "-b:a", "192k", "-t", "%.2f" % min(vdur, VOICE + 1.0), out], check=False)
print("DONE:", out, "exists:", os.path.exists(out))
