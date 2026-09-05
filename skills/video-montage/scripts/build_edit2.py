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
W, H, FPS = 1080, 1920, 30
INTRO, OUTRO = 3.4, 3.0
CLEAN = os.path.join(WORK, "clean_voice.m4a")
SUBS = ffpath(os.path.join(WORK, "subs2.ass"))
FONT = "C\\:/Windows/Fonts/arialbd.ttf"
GFX  = ffpath(WORK)   # intro_title.txt / intro_sub1.txt / intro_sub2.txt / outro_title.txt live here

def dur(path):
    return float(subprocess.check_output([PB, "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path]).decode().strip())

# locate source clips folder
src = None
roots = [HOME, os.path.join(HOME, "OneDrive")] + [d for d in glob.glob(os.path.join(HOME, "OneDrive", "*")) if os.path.isdir(d)]
for base in roots:
    for d in glob.glob(os.path.join(base, "*")):
        if os.path.isdir(d) and len(glob.glob(os.path.join(d, "*.MOV"))) > 3 and glob.glob(os.path.join(d, "*.ogg")):
            src = d; break
    if src: break
if not src:
    raise SystemExit("source not found")
print("src:", src)

VOICE = dur(CLEAN)
print("clean voice: %.1f s" % VOICE)

edl = json.load(open(os.path.join(WORK, "edl.json"), encoding="utf-8"))
total = sum(float(e.get("dur_seconds") or 0) for e in edl)
scale = VOICE / total if total > 0 else 1.0

tmp = os.path.join(WORK, "edit2")
os.makedirs(tmp, exist_ok=True)
for f in glob.glob(os.path.join(tmp, "*.mp4")):
    os.remove(f)

vf = ("scale=%d:%d:force_original_aspect_ratio=increase,crop=%d:%d,fps=%d,format=yuv420p,setsar=1,fade=t=in:st=0:d=0.2" % (W, H, W, H, FPS))

# intro card (animated fade)
intro = os.path.join(tmp, "a_intro.mp4")
vf_intro = ("drawtext=fontfile='%s':textfile='%s/intro_title.txt':fontcolor=white:fontsize=140:x=(w-text_w)/2:y=h/2-220,"
            "drawtext=fontfile='%s':textfile='%s/intro_sub1.txt':fontcolor=0xCDD6F4:fontsize=54:x=(w-text_w)/2:y=h/2-20,"
            "drawtext=fontfile='%s':textfile='%s/intro_sub2.txt':fontcolor=0x8AA0C6:fontsize=42:x=(w-text_w)/2:y=h/2+60,"
            "fade=t=in:st=0:d=0.6,fade=t=out:st=3.0:d=0.4,format=yuv420p" % (FONT, GFX, FONT, GFX, FONT, GFX))
subprocess.run([FF, "-y", "-hide_banner", "-loglevel", "error", "-f", "lavfi", "-i",
                "color=c=0x0B1020:s=%dx%d:d=%.2f:r=%d" % (W, H, INTRO, FPS),
                "-vf", vf_intro, "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", intro], check=False)

# outro card
outro = os.path.join(tmp, "z_outro.mp4")
vf_outro = ("drawtext=fontfile='%s':textfile='%s/outro_title.txt':fontcolor=white:fontsize=92:x=(w-text_w)/2:y=(h-text_h)/2,"
            "fade=t=in:st=0:d=0.6,fade=t=out:st=2.5:d=0.5,format=yuv420p" % (FONT, GFX))
subprocess.run([FF, "-y", "-hide_banner", "-loglevel", "error", "-f", "lavfi", "-i",
                "color=c=0x111A2E:s=%dx%d:d=%.2f:r=%d" % (W, H, OUTRO, FPS),
                "-vf", vf_outro, "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", outro], check=False)

# body segments per EDL (rescaled to clean voice length)
lines = ["file '%s'" % intro.replace("\\", "/")]
n = 0
for e in edl:
    clip = e.get("clip", "").strip()
    matches = [m for m in glob.glob(os.path.join(src, clip + ".*")) if m.lower().endswith((".mov", ".mp4"))]
    if not matches:
        continue
    d = max(1.3, float(e.get("dur_seconds") or 2.5) * scale)
    n += 1
    seg = os.path.join(tmp, "e_%03d.mp4" % n)
    subprocess.run([FF, "-y", "-hide_banner", "-loglevel", "error", "-ss", "0", "-t", "%.3f" % d,
                    "-i", matches[0], "-vf", vf, "-an", "-c:v", "libx264", "-preset", "veryfast",
                    "-crf", "20", seg], check=False)
    if os.path.exists(seg) and os.path.getsize(seg) > 0:
        lines.append("file '%s'" % seg.replace("\\", "/"))
lines.append("file '%s'" % outro.replace("\\", "/"))
print("body segments:", n)

listpath = os.path.join(tmp, "list.txt")
open(listpath, "w", encoding="utf-8").write("\n".join(lines) + "\n")
silent = os.path.join(tmp, "silent.mp4")
subprocess.run([FF, "-y", "-hide_banner", "-loglevel", "error", "-f", "concat", "-safe", "0",
                "-i", listpath, "-c", "copy", silent], check=False)
vdur = dur(silent)
print("full video: %.1f s" % vdur)

# mux: voice delayed by intro, subtitles (already offset), fades
out = os.path.join(HOME, "Videos", "reels_v4.mp4")
fade_st = INTRO + VOICE - 1.2
vfb = "subtitles=filename='%s':fontsdir='C\\:/Windows/Fonts',format=yuv420p" % SUBS
af = "adelay=%d|%d,afade=t=out:st=%.2f:d=1.2" % (int(INTRO * 1000), int(INTRO * 1000), fade_st)
subprocess.run([FF, "-y", "-hide_banner", "-loglevel", "error", "-i", silent, "-i", CLEAN,
                "-map", "0:v:0", "-map", "1:a:0", "-vf", vfb, "-af", af,
                "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
                "-c:a", "aac", "-b:a", "192k", out], check=False)
print("DONE:", out, "exists:", os.path.exists(out))
