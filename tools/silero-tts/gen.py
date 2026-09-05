# -*- coding: utf-8 -*-
"""Локальная озвучка Silero v4_ru — родной русский, без акцента, без лимитов.
   Работает офлайн. Модель v4_ru.pt (40 МБ) в репозиторий не входит — скачай её из
   официального релиза Silero (https://models.silero.ai/models/tts/ru/v4_ru.pt,
   проект github.com/snakers4/silero-models) и положи рядом со скриптом, либо укажи
   путь в переменной окружения SILERO_MODEL.

   Режимы:
     py gen.py samples          — короткие образцы всех женских голосов
     py gen.py full <speaker>   — все реплики ролика из vo_continuous.json
"""
import io, json, os, sys, time
import torch
import soundfile as sf

ROOT = os.path.dirname(os.path.abspath(__file__))
MODEL = os.environ.get("SILERO_MODEL") or os.path.join(ROOT, "v4_ru.pt")
SR = 48000

DEV = torch.device("cuda" if torch.cuda.is_available() else "cpu")


def load():
    if not os.path.exists(MODEL):
        raise SystemExit("нет модели %s — скачай v4_ru.pt из официального релиза Silero "
                         "(https://models.silero.ai/models/tts/ru/v4_ru.pt) или задай SILERO_MODEL" % MODEL)
    m = torch.package.PackageImporter(MODEL).load_pickle("tts_models", "model")
    m.to(DEV)
    return m


def say(model, text, speaker):
    """Silero кладёт ударения и ё сам — это и даёт правильное русское звучание."""
    wav = model.apply_tts(text=text, speaker=speaker, sample_rate=SR,
                          put_accent=True, put_yo=True)
    return wav.cpu().numpy()


def samples():
    m = load()
    demo = ("Это образец голоса. Проверьте, как звучат ударения, буква ё "
            "и интонация вопроса. Подходит?")
    out = os.path.join(ROOT, "samples")
    os.makedirs(out, exist_ok=True)
    for sp in ["baya", "kseniya", "xenia"]:
        w = say(m, demo, sp)
        p = os.path.join(out, "%s.wav" % sp)
        sf.write(p, w, SR)
        print("%-8s %5.2f сек -> %s" % (sp, len(w) / SR, p))


def full(speaker):
    m = load()
    plan = json.load(io.open(os.path.join(ROOT, "vo_continuous.json"), encoding="utf-8"))
    out = os.path.join(ROOT, "out")
    os.makedirs(out, exist_ok=True)
    durs = {}
    t0 = time.time()
    for L in plan["lines"]:
        w = say(m, L["text"], speaker)
        p = os.path.join(out, "line-%02d.wav" % L["n"])
        sf.write(p, w, SR)
        durs[L["n"]] = round(len(w) / SR, 2)
        print("реплика %d: %5.2f сек" % (L["n"], durs[L["n"]]))
    io.open(os.path.join(out, "durs.json"), "w").write(json.dumps(durs))
    print("--- всего речи: %.1f сек, синтез занял %.1f с (%s)" %
          (sum(durs.values()), time.time() - t0, DEV))


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "samples":
        samples()
    elif len(sys.argv) > 2 and sys.argv[1] == "full":
        full(sys.argv[2])
    else:
        print(__doc__)
