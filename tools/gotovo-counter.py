# -*- coding: utf-8 -*-
"""gotovo-counter — считает, в скольких прогонах образ готового реально фиксировался.

Зачем. Правило «Образ готового» (Шаг 2.5в brief-architect + референс-гейт P0-13, введено
2026-08-31) закрывает корзину A разбора: 25% всех переделок снимались
одним вопросом на входе. Но стек уже трижды доказал, что записанное правило само по себе
не исполняется: `partial` 0 из 166, автопредложение `/harness-audit` 0 из 166,
brief-architect с формулировкой «ВСЕГДА» — 35-36%. Без замера через месяц нельзя отличить
«правило работает» от «правило тихо не исполняется», и разбор придётся повторять заново.

Как считает. Источник — frontmatter run-логов: поле `obraz_gotovogo`.

    obraz_gotovogo: filled   — образ зафиксирован (образец · получатель+канал+устройство ·
                               уровень готовности · чем проверим)
    obraz_gotovogo: skipped  — не зафиксирован, работа пошла без него
    obraz_gotovogo: n/a      — atomic-задача, образ не нужен («прочитай X», «сохрани Y»)

ОТСУТСТВИЕ ПОЛЯ СЧИТАЕТСЯ ЗА `skipped`, а не игнорируется. Это намеренно: пропуск поля —
это и есть основной способ, которым правило умирает молча. Если считать «нет поля = нет
данных», счётчик покажет красивую картину ровно в тот момент, когда правило перестанут
исполнять. Прогоны СТАРШЕ даты введения правила (2026-08-31) в знаменатель не берутся —
они закрывались, когда поля не существовало.

Запуск:
    py -3 ~/.claude/tools/gotovo-counter.py            # окно 30 дней, строка-сводка
    py -3 ~/.claude/tools/gotovo-counter.py --days 90  # другое окно
    py -3 ~/.claude/tools/gotovo-counter.py --list     # поимённо, кто пропустил
    py -3 ~/.claude/tools/gotovo-counter.py --selftest # проверка на подсаженных примерах

Код возврата: 0 — норма; 1 — доля `filled` ниже порога (правило проседает); 2 — ошибка запуска.
Порог: 60% при не менее чем 5 измеримых прогонах в окне. Ниже порога — правило чинят,
а не уговаривают исполнять.

Пути: корень vault — из переменной окружения VAULT_ROOT (по умолчанию ~/vault).
"""
import os, re, sys, glob, datetime, tempfile, shutil

sys.stdout.reconfigure(encoding="utf-8")

HOME = os.path.expanduser("~")
# Корень vault — из окружения (VAULT_ROOT), по умолчанию ~/vault.
VAULT = os.environ.get("VAULT_ROOT") or os.path.join(HOME, "vault")
ORCH = os.path.join(VAULT, "_orchestr")

RULE_START = datetime.date(2026, 8, 31)   # день введения правила; раньше поля не было
THRESHOLD = 0.60                          # доля filled, ниже которой правило считается проседающим
MIN_SAMPLE = 5                            # меньше — выборка не показательна, вердикт не выносим

DATE_IN_NAME = re.compile(r"run-.*?(\d{4})-(\d{2})-(\d{2})")
FIELD = re.compile(r"^obraz_gotovogo:\s*([a-z/]+)\s*$", re.M)
VALID = ("filled", "skipped", "n/a")


def run_date(path):
    """Дата прогона из имени файла. Префикс бывает не только run- (run-site-build-phase3-...),
    поэтому ищем первую дату в имени, а не фиксированную позицию."""
    m = DATE_IN_NAME.search(os.path.basename(path))
    if not m:
        return None
    try:
        return datetime.date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    except ValueError:
        return None


def scan(days, roots=None):
    today = datetime.date.today()
    edge = today - datetime.timedelta(days=days)
    floor = max(edge, RULE_START)
    roots = roots or [os.path.join(ORCH, "_ARCHIVE"), os.path.join(ORCH, "_ACTIVE")]

    stat = {"filled": [], "skipped": [], "n/a": [], "broken": []}
    for root in roots:
        for f in glob.glob(os.path.join(root, "run-*.md")):
            d = run_date(f)
            if d is None or d < floor:
                continue
            head = open(f, encoding="utf-8", errors="replace").read(4000)
            m = FIELD.search(head)
            val = m.group(1) if m else "skipped"
            if val not in VALID:
                stat["broken"].append((os.path.basename(f), val))
                val = "skipped"
            stat[val].append(os.path.basename(f))
    return stat, floor


def report(stat, floor, days, show_list=False):
    filled, skipped, na = len(stat["filled"]), len(stat["skipped"]), len(stat["n/a"])
    measurable = filled + skipped
    print("Образ готового — замер за %d дн. (с %s, дня введения правила)" % (days, floor.isoformat()))
    print("  зафиксирован: %d · пропущен: %d · не требовался (atomic): %d" % (filled, skipped, na))

    if stat["broken"]:
        print("  ! неизвестное значение поля в %d прогонах — считаю как пропуск:" % len(stat["broken"]))
        for n, v in stat["broken"][:5]:
            print("      %s → %r" % (n, v))

    if show_list and stat["skipped"]:
        print("  пропустили:")
        for n in sorted(stat["skipped"]):
            print("      %s" % n)

    if measurable < MIN_SAMPLE:
        print("  вердикт: выборка мала (%d из %d нужных) — считаем дальше, не решаем"
              % (measurable, MIN_SAMPLE))
        return 0

    share = filled / measurable
    print("  доля: %.0f%% (%d из %d)" % (share * 100, filled, measurable))
    if share < THRESHOLD:
        print("  ВЕРДИКТ: правило проседает (порог %.0f%%). Чинить механизм, а не напоминать себе."
              % (THRESHOLD * 100))
        return 1
    print("  вердикт: правило держится")
    return 0


def selftest():
    """Мутационная проверка: счётчик обязан считать подсаженные случаи, а не показывать ноль.
    Три подсадки — заполнено, пропущено, поле отсутствует. Последняя обязана попасть
    в пропуски: именно так правило умирает молча, и слепота к этому случая обессмыслит счётчик."""
    tmp = tempfile.mkdtemp(prefix="gotovo-selftest-")
    try:
        d = datetime.date.today().isoformat()
        cases = [
            ("run-%s-0101-mut-filled.md" % d, "obraz_gotovogo: filled\n"),
            ("run-%s-0102-mut-skipped.md" % d, "obraz_gotovogo: skipped\n"),
            ("run-%s-0103-mut-nofield.md" % d, ""),
            ("run-%s-0104-mut-garbage.md" % d, "obraz_gotovogo: qwerty\n"),
            ("run-%s-0105-mut-old.md" % (RULE_START - datetime.timedelta(days=1)).isoformat(), ""),  # старше правила — вне знаменателя
        ]
        for name, extra in cases:
            with open(os.path.join(tmp, name), "w", encoding="utf-8") as fh:
                fh.write("---\nrun_id: x\nstatus: done\n%s---\n\nтело\n" % extra)

        stat, _ = scan(30, roots=[tmp])
        checks = [
            ("заполненный распознан", len(stat["filled"]) == 1),
            ("пропуск распознан", len(stat["skipped"]) == 3),     # skipped + без поля + мусор
            ("отсутствие поля учтено как пропуск", "run-%s-0103-mut-nofield.md" % d in stat["skipped"]),
            ("мусорное значение помечено", len(stat["broken"]) == 1),
            ("прогон старше правила не считается", all("mut-old" not in x for v in stat.values()
                                                       for x in (v if isinstance(v[0] if v else "", str) else []))),
        ]
        ok = True
        for label, res in checks:
            print("  %s — %s" % ("ПРОЙДЕНО" if res else "ПРОВАЛЕНО", label))
            ok = ok and res
        print("\nSELFTEST: %s" % ("ПРОЙДЕН" if ok else "ПРОВАЛЕН — счётчик не считает то, ради чего написан"))
        return 0 if ok else 1
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(selftest())
    days = 30
    if "--days" in sys.argv:
        try:
            days = int(sys.argv[sys.argv.index("--days") + 1])
        except (IndexError, ValueError):
            print("--days требует число"); sys.exit(2)
    if not os.path.isdir(ORCH):
        print("не найден каталог прогонов: %s" % ORCH); sys.exit(2)
    st, fl = scan(days)
    sys.exit(report(st, fl, days, show_list="--list" in sys.argv))
