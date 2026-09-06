# -*- coding: utf-8 -*-
# Orchestrator stack for Claude Code. Author: @kamil_ibrgmv - https://instagram.com/kamil_ibrgmv
from video_config import required_dir, output_file, clip_files, validate_edl, scratch, one_file
import json, os, glob, subprocess

# ffmpeg/ffprobe: on PATH, or full paths via env FFMPEG_BIN / FFPROBE_BIN
FF = os.environ.get("FFMPEG_BIN", "ffmpeg")
PB = os.environ.get("FFPROBE_BIN", "ffprobe")
# working folder for intermediates (edl.json, whisper json, subs, temp segments)
WORK = required_dir("VIDEO_WORK", create=True)

def ffpath(p):
    # path form accepted inside ffmpeg filter strings on Windows: C\:/dir/file
    return p.replace("\\", "/").replace(":", "\\:")
W, H, FPS = 1080, 1920, 30

# find source folder (with .ogg + many .MOV) without typing non-ascii path
src = required_dir("VIDEO_SOURCE")

print("src:", src)
ogg = one_file(src, ".ogg")
VOICE = float(subprocess.check_output([PB, "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", ogg]).decode().strip())
out = output_file()

edl = validate_edl(json.load(open(os.path.join(WORK, "edl.json"), encoding="utf-8")), src)
total = sum(float(e.get("dur_seconds") or 0) for e in edl)
scale = VOICE / total if total > 0 else 1.0
print("edl clips:", len(edl), "raw total: %.1f" % total, "scale: %.3f" % scale)

tmp = scratch(WORK, "edit")

vf = ("scale=%d:%d:force_original_aspect_ratio=increase,crop=%d:%d,"
      "fps=%d,format=yuv420p,setsar=1,fade=t=in:st=0:d=0.2" % (W, H, W, H, FPS))

lines, n = [], 0
for e in edl:
    clip = e.get("clip", "").strip()
    matches = clip_files(src, clip)
    if not matches:
        print("  missing:", clip); continue
    dur = max(1.3, float(e.get("dur_seconds") or 2.5) * scale)
    n += 1
    seg = os.path.join(tmp, "e_%03d.mp4" % n)
    subprocess.run([FF, "-y", "-hide_banner", "-loglevel", "error", "-ss", "0", "-t", "%.3f" % dur,
                    "-i", matches[0], "-vf", vf, "-an", "-c:v", "libx264", "-preset", "veryfast",
                    "-crf", "20", seg], check=True)
    if os.path.exists(seg) and os.path.getsize(seg) > 0:
        lines.append("file '%s'" % seg.replace("\\", "/"))
        print("  [%d] %s %.1fs" % (n, clip, dur))

listpath = os.path.join(tmp, "list.txt")
open(listpath, "w", encoding="utf-8").write("\n".join(lines) + "\n")

silent = os.path.join(tmp, "silent.mp4")
subprocess.run([FF, "-y", "-hide_banner", "-loglevel", "error", "-f", "concat", "-safe", "0",
                "-i", listpath, "-c", "copy", silent], check=True)
vdur = float(subprocess.check_output([PB, "-v", "error", "-show_entries", "format=duration",
                                      "-of", "csv=p=0", silent]).decode().strip())
fst = max(0.0, vdur - 1.6)
print("body duration: %.1f s" % vdur)

os.makedirs(os.path.dirname(out), exist_ok=True)
vfb = ("subtitles=filename='%s':fontsdir='C\\:/Windows/Fonts'," % ffpath(os.path.join(WORK, "subs.ass")) +
       "fade=t=out:st=%.2f:d=1.6,format=yuv420p" % fst)
subprocess.run([FF, "-y", "-hide_banner", "-loglevel", "error", "-i", silent, "-i", ogg,
                "-map", "0:v:0", "-map", "1:a:0", "-vf", vfb,
                "-af", "afade=t=out:st=%.2f:d=1.6" % fst,
                "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
                "-c:a", "aac", "-b:a", "192k", "-t", "%.2f" % min(vdur, VOICE + 1.0), out], check=True)
print("DONE:", out, "exists:", os.path.exists(out))
