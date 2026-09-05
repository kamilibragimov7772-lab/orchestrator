# -*- coding: utf-8 -*-
import json, glob, re, os
WORK = os.environ.get("VIDEO_WORK") or os.path.join(os.environ["USERPROFILE"], "video_work")
data = json.load(open(glob.glob(os.path.join(WORK, "trans2", "*.json"))[0], encoding="utf-8"))
def norm(s): return re.sub(r"\W+", "", s.lower(), flags=re.UNICODE)
W = []
for seg in data.get("segments", []):
    for w in seg.get("words", []):
        t = (w.get("word") or "").strip()
        if t and "start" in w and "end" in w:
            W.append((float(w["start"]), float(w["end"]), t))
cuts = []
i = 0
n = len(W)
while i < n:
    found = False
    for k in range(5, 1, -1):  # prefer longest repeated run
        if i + 2*k <= n:
            a = [norm(W[i+j][2]) for j in range(k)]
            b = [norm(W[i+k+j][2]) for j in range(k)]
            if a == b and all(a):
                # cut the FIRST instance: [start of W[i], start of W[i+k])
                cuts.append((W[i][0], W[i+k][0], " ".join(W[i+j][2] for j in range(k))))
                i += k
                found = True
                break
    if not found:
        i += 1
for c in cuts:
    print("CUT %.2f -> %.2f   '%s'" % (c[0], c[1], c[2]))
print("ranges:", len(cuts))
json.dump([[c[0], c[1]] for c in cuts], open(os.path.join(WORK, "cuts.json"), "w", encoding="utf-8"))
