#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Детерминированное ядро приёмки. Часть «босса» — того, что принимает работу
после оркестратора.

Почему скриптом, а не агентом. Измерение на 259 прогонах (_orchestr_protocol
2.14.2): правило, попавшее в валидатор, держится на 76-100%; то же правило
текстом в промпте — на 0-39%. И разбор 48 доработок одного клиентского продукта: модель
точно называет ограничение и тут же его нарушает. Поэтому всё, что можно
проверить машиной, проверяет машина, а не модель.

Запуск:
    python3 checks.py <путь-к-run-логу.md> [--json]

Кросс-платформенный: только стандартная библиотека, никаких внешних пакетов.
Живёт в ~/.claude/tools/.

Пути: корень vault берётся из переменной окружения VAULT_ROOT (по умолчанию
~/vault), каталог стека — из CLAUDE_HOME (по умолчанию ~/.claude).
"""

import io
import json
import os
import re
import sys
import zipfile
import xml.etree.ElementTree as ET

# Корень vault и каталог стека — из окружения, с разумными умолчаниями.
VAULT = os.environ.get("VAULT_ROOT") or os.path.expanduser("~/vault")
STACK = os.environ.get("CLAUDE_HOME") or os.path.expanduser("~/.claude")

# ---------------------------------------------------------------- вердикты

OK = "ok"
FAIL = "fail"
SKIP = "skip"  # проверить нечем — не выдаём за успех


class Check:
    def __init__(self, name, status, detail=""):
        self.name = name
        self.status = status
        self.detail = detail

    def as_dict(self):
        return {"check": self.name, "status": self.status, "detail": self.detail}


# ---------------------------------------------------------- разбор run-лога


def read_text(path):
    with io.open(path, encoding="utf-8-sig") as fh:
        return fh.read()


def split_frontmatter(text):
    """Возвращает (сырой frontmatter, тело). Без внешнего YAML-парсера."""
    if not text.startswith("---\n"):
        return "", text
    end = re.search(r"(?m)^---[ \t]*$", text[4:])
    if end is None:
        return "", text
    pos = 4 + end.start()
    return text[4:pos], text[4 + end.end():]


def scalar(value):
    """Small documented YAML subset: quoted/unquoted strings, no YAML execution."""
    value = value.strip()
    if value.startswith('"'):
        try:
            decoded, end = json.JSONDecoder().raw_decode(value)
        except ValueError as exc:
            # Double quotes mean escape processing, in YAML as in JSON, so a raw
            # Windows path ("C:\Users\...") is genuinely invalid -- \U and \k are
            # not escapes. Keeping that strict is right; reporting it as a bare
            # JSONDecodeError is not, because the caller then says only "bundle
            # could not be built" and the author has nothing to fix. Name the
            # cause and the remedy instead.
            raise ValueError(
                'invalid double-quoted scalar (%s). Backslashes are escapes here: '
                "use single quotes ('C:\\path') or double them (\"C:\\\\path\")" % exc)
        tail = value[end:].strip()
        if not isinstance(decoded, str) or (tail and not tail.startswith('#')):
            raise ValueError('invalid quoted scalar')
        return decoded
    if value.startswith("'"):
        match = re.fullmatch(r"'((?:[^']|'')*)'[ \t]*(?:#.*)?", value)
        if not match:
            raise ValueError('invalid single-quoted scalar')
        return match.group(1).replace("''", "'")
    return re.split(r"[ \t]+#", value, maxsplit=1)[0].strip()


def fm_scalar(fm, key):
    """
    Значение скалярного ключа frontmatter, без хвостового YAML-комментария.

    Баг, найденный приёмщиком на одном из архивных прогонов: строка
    `status: done  # был `done-pending-rename`, приведён к словарю` целиком
    попадала в значение, `status != "done"`, и приёмка молча отвечала
    «не подлежит приёмке» — то есть «прогон ещё в работе» про закрытый
    прогон. Тихий отказ ровно того класса, ради которого гейт и строился;
    под него попадали 3 прогона в _ARCHIVE.

    Комментарий режем только по « #» с пробелом слева — чтобы не резать
    решётку внутри осмысленного значения.
    """
    matches = re.findall(r"^%s:[ \t]*(.*)$" % re.escape(key), fm, re.M)
    if not matches:
        return None
    if len(matches) != 1:
        raise ValueError('duplicate frontmatter key: ' + key)
    return scalar(matches[0])


def fm_list(fm, key):
    """Читает как inline-список [a, b], так и блочный список из дефисов."""
    if len(re.findall(r"^%s:" % re.escape(key), fm, re.M)) > 1:
        raise ValueError('duplicate list: ' + key)
    inline = re.search(r"^%s:[ \t]*\[(.*?)\][ \t]*(?:#.*)?$" % re.escape(key), fm, re.M)
    if inline:
        # Quoted paths may contain commas. Split only outside quoted strings.
        items, current, quote, escaped = [], '', None, False
        for c in inline.group(1):
            if escaped:
                current += c; escaped = False; continue
            if c == '\\' and quote == '"':
                current += c; escaped = True; continue
            if quote:
                current += c
                if c == quote: quote = None
            elif c in "\"'":
                quote = c; current += c
            elif c == ',':
                if not current.strip(): raise ValueError('empty artifact path')
                items.append(scalar(current)); current = ''
            else:
                current += c
        if quote: raise ValueError('unclosed quote in artifact list')
        if current.strip(): items.append(scalar(current))
        return items

    block = re.search(r"^%s:[ \t]*(?:#.*)?$" % re.escape(key), fm, re.M)
    if not block:
        return []
    items = []
    for line in fm[block.end() :].split("\n"):
        if re.match(r"^\s*-\s+", line):
            items.append(scalar(re.sub(r"^\s*-\s+", "", line)))
        elif line.strip() and not line.startswith(" "):
            break  # начался следующий ключ верхнего уровня
    return items


def expand(path, runlog=None):
    """
    Путь артефакта в вид, пригодный для проверки на диске.

    Второй баг того же разбора: относительные пути резолвились от текущего
    каталога процесса, поэтому 4 из 9 «провалов» на том же прогоне были
    ложными — файлы существовали. Скрипт врал в обе стороны, а ложный
    провал опаснее молчания: он заставляет чинить то, что не сломано.

    Для относительного пути перебираем осмысленные базы и берём первую,
    где файл реально есть. Не нашли — возвращаем кандидата от корня vault,
    чтобы в отчёте был предсказуемый путь, а не случайный cwd.
    """
    path = path.strip().strip("`")
    if not path or re.search(r"<[^>]*>|\$\w+|\$\{|%\w+%", path):
        raise ValueError('empty or unresolved artifact path')
    path = os.path.expanduser(os.path.expandvars(path))

    if os.path.isabs(path):
        return path, True

    vault = VAULT
    if not runlog:
        return os.path.abspath(path), True
    bases = [os.path.dirname(os.path.abspath(runlog)), vault, STACK]
    found = {os.path.normcase(os.path.realpath(os.path.join(base, path)))
             for base in bases if os.path.exists(os.path.join(base, path))}
    if len(found) > 1:
        raise ValueError('ambiguous artifact path; use an absolute path')
    return (next(iter(found)) if found else os.path.join(bases[0], path)), True


# ------------------------------------------------- открываемость артефактов


def artifact_opens(path):
    """
    Главное правило канона готовности: «Сдано = открыто тем путём, каким
    откроет получатель». Проверяем не «файл есть», а «файл разбирается тем
    форматом, который заявлен расширением».
    """
    ext = os.path.splitext(path)[1].lower()

    if os.path.isdir(path):
        return OK if os.listdir(path) else FAIL, "каталог пуст" if not os.listdir(path) else "каталог непустой"

    if not os.path.exists(path):
        return FAIL, "файла нет по указанному пути"

    size = os.path.getsize(path)
    if size == 0:
        return FAIL, "файл нулевого размера"

    try:
        if ext in (".docx", ".xlsx", ".pptx"):
            with zipfile.ZipFile(path) as z:
                if sum(x.file_size for x in z.infolist()) > 50 * 1024 * 1024:
                    return SKIP, "Office archive exceeds 50 MiB inspection budget"
                if z.testzip() is not None:
                    return FAIL, "битый архив office-формата"
                if '[Content_Types].xml' not in z.namelist():
                    return FAIL, "не office-документ внутри"
                ET.fromstring(z.read('[Content_Types].xml'))
                part = {'.docx': 'word/document.xml', '.xlsx': 'xl/workbook.xml', '.pptx': 'ppt/presentation.xml'}[ext]
                root = ET.fromstring(z.read(part))
                tag = {'.docx': 'document', '.xlsx': 'workbook', '.pptx': 'presentation'}[ext]
                if root.tag.rsplit('}', 1)[-1] != tag:
                    return FAIL, 'invalid Office main part'
            return OK, "структура Office разбирается; визуальная приёмка отдельно (%d Б)" % size

        if ext == ".pdf":
            with io.open(path, "rb") as fh:
                if fh.read(5) != b"%PDF-":
                    return FAIL, "нет сигнатуры %PDF-"
            return SKIP, "PDF signature only; render in a PDF viewer before acceptance (%d Б)" % size

        if ext == ".json":
            json.loads(read_text(path))
            return OK, "JSON парсится (%d Б)" % size

        if ext in (".html", ".htm"):
            head = read_text(path)[:4000].lower()
            if "<html" not in head and "<!doctype" not in head:
                return FAIL, "нет корневого html-тега"
            return OK, "HTML с корневым тегом (%d Б)" % size

        if ext in (".md", ".txt", ".csv", ".py", ".ts", ".js", ".sh", ".yml", ".yaml"):
            text = read_text(path)
            if not text.strip():
                return FAIL, "файл из одних пробелов"
            return OK, "текст читается, %d символов" % len(text)

        return SKIP, "тип %s не умею проверять — открой глазами" % (ext or "без расширения")

    except zipfile.BadZipFile:
        return FAIL, "битый архив"
    except json.JSONDecodeError as exc:
        return FAIL, "JSON не парсится: %s" % exc
    except Exception as exc:  # noqa: BLE001 — отчёт важнее типа исключения
        return FAIL, "не открылся: %s" % exc


# ------------------------------------------------- содержание образа готового

# Четыре поля канона готовности. Ключ — как поле названо в секции,
# значение — как о нём говорить в отчёте.
OBRAZ_FIELDS = (
    ("образец", "образец"),
    ("получател", "получатель, канал и устройство"),
    ("уровень", "уровень готовности"),
    ("провер", "чем проверим"),
)

# Маркеры незаполненности: явный вопрос, многоточие, прочерк, TODO.
UNFILLED = re.compile(r"(❓|\?{1,}\s*$|^\s*[-—–]\s*$|\bTODO\b|\bтбд\b|\bTBD\b)", re.I | re.M)


def check_obraz_section(body):
    """
    Флаг obraz_gotovogo: filled — заявка автора. Здесь проверяем факт:
    секция есть, все четыре поля присутствуют и ни одно не пустует.
    """
    # Заголовок часто несёт хвост вида «(Шаг 2.5в, референс-гейт P0-13)» —
    # привязка к концу строки давала ложное «секции нет».
    m = re.search(r"^##+\s*Образ готового\b.*$", body, re.M | re.I)
    if not m:
        return Check(
            "образ готового (содержание)",
            FAIL,
            "флаг filled стоит, а секции «## Образ готового» в логе нет",
        )

    # Секция — до следующего заголовка того же или более высокого уровня.
    rest = body[m.end() :]
    depth = len(re.match(r"#+", m.group(0)).group(0))
    nxt = re.search(r"^#{1,%d}\s+" % depth, rest, re.M)
    section = rest[: nxt.start()] if nxt else rest

    missing, empty = [], []
    for needle, human in OBRAZ_FIELDS:
        line = None
        for ln in section.split("\n"):
            if ':' in ln and needle.lower() in ln.split(':', 1)[0].lower():
                line = ln
                break
        if line is None:
            missing.append(human)
        elif UNFILLED.search(line.split(':', 1)[1]) or not re.sub(r"[^\w]", "", line.split(":", 1)[1]):
            empty.append(human)

    if missing or empty:
        parts = []
        if missing:
            parts.append("нет полей: " + ", ".join(missing))
        if empty:
            parts.append("не заполнены: " + ", ".join(empty))
        return Check("образ готового (содержание)", FAIL, "; ".join(parts))

    return Check("образ готового (содержание)", OK, "все четыре поля заполнены")


# ------------------------------------------------------------------ проверки


def run_checks(runlog_path):
    checks = []
    text = read_text(runlog_path)
    fm, body = split_frontmatter(text)

    run_id = fm_scalar(fm, "run_id") or os.path.basename(runlog_path)
    status = fm_scalar(fm, "status")

    # 1. Образ готового — поле введено в 2.14.1, без него приёмка беспредметна
    obraz = fm_scalar(fm, "obraz_gotovogo")
    if obraz is None:
        checks.append(Check("obraz_gotovogo", FAIL, "поля нет во frontmatter"))
    elif obraz in ("filled", "n/a"):
        # Флаг во frontmatter — заявка, а не факт. Первый боевой прогон
        # приёмщика (05.09) поймал ровно это: obraz_gotovogo: filled стоял,
        # а в самой секции поля «получатель, канал, устройство» и «уровень
        # готовности» были с «?». Проверка отметки без проверки содержания
        # декоративна, поэтому смотрим саму секцию.
        checks.append(Check("obraz_gotovogo (флаг)", OK, obraz))
        if obraz == "filled":
            checks.append(check_obraz_section(body))
    elif obraz == "skipped":
        # Не провал: пользователь сознательно пропустил образ готового. Но тогда у
        # приёмки нет мерила, и выдавать такой прогон за принятый нельзя.
        checks.append(Check("obraz_gotovogo", SKIP, "пропущен — приёмке нечем мерить результат"))
    else:
        checks.append(Check("obraz_gotovogo", FAIL, "значение %r вне словаря filled|skipped|n/a" % obraz))

    # 2. Обязательные секции run-лога
    for section in ("## Бюджеты", "## Trace"):
        present = bool(re.search(r'^' + re.escape(section) + r'[ \t]*$', body, re.M))
        checks.append(
            Check(
                "секция %s" % section,
                OK if present else FAIL,
                "на месте" if present else "секции нет — учёт не восстановить",
            )
        )

    # 3. Артефакты: заявлены и открываются
    artifacts = fm_list(fm, "artifacts")
    if not artifacts:
        checks.append(Check("артефакты", FAIL, "в frontmatter не заявлено ни одного"))
    else:
        for raw in artifacts:
            path, anchored = expand(raw, runlog_path)
            if not anchored:
                checks.append(Check(
                    "артефакт %s" % raw,
                    SKIP,
                    "относительный путь не привязан ни к одной базе "
                    "(cwd, каталог лога, VAULT_ROOT, ~, CLAUDE_HOME) — проверь глазами",
                ))
                continue
            st, detail = artifact_opens(path)
            checks.append(Check("артефакт %s" % raw, st, detail))

    # 4. Модели: факт перевода на fable виден только здесь
    budget = re.search(r'^## Бюджеты[ \t]*\n(.*?)(?=^## |\Z)', body, re.M | re.S)
    models = bool(budget and re.search(r'\b(?:Модель|model)\b', budget.group(1), re.I))
    checks.append(
        Check(
            "модели в ## Бюджеты",
            OK if models else SKIP,
            "budget model column present; verify actual usage separately" if models else "колонка Модель не заполнена",
        )
    )

    return run_id, status, checks


def main():
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, 'reconfigure'):
            stream.reconfigure(encoding='utf-8')
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    as_json = "--json" in sys.argv[1:]

    if not args:
        print("употребление: checks.py <run-лог.md> [--json]", file=sys.stderr)
        return 2
    path, _anchored = expand(args[0])
    if not os.path.exists(path):
        print("нет такого run-лога: %s" % path, file=sys.stderr)
        return 2

    try:
        run_id, status, checks = run_checks(path)
    except (OSError, ValueError, UnicodeError) as exc:
        payload = {'verdict_script': 'не принято', 'error': type(exc).__name__, 'detail': str(exc)}
        print(json.dumps(payload, ensure_ascii=False) if as_json else payload['detail'])
        return 2

    # Прогон в работе приёмке не подлежит: артефактов ещё нет по определению,
    # и «не принято» на нём — ложная тревога, а не находка. Гейт судит только
    # закрытые прогоны — это то же правило, по которому final-quality-gate
    # отказывается агрегировать неполный комплект отчётов.
    if status != "done":
        payload = {
            "run_id": run_id,
            "run_status": status,
            "verdict_script": "не подлежит приёмке",
            "detail": "status=%s, приёмка запускается только на status: done" % status,
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2) if as_json
              else "run: %s — не подлежит приёмке (status: %s)" % (run_id, status))
        return 4

    failed = [c for c in checks if c.status == FAIL]
    skipped = [c for c in checks if c.status == SKIP]

    # Вердикт скриптовой части. «не принято» — жёсткий: есть провалы.
    # «неполно» — провалов нет, но часть проверить нечем, и выдавать это
    # за приёмку нельзя.
    if failed:
        verdict = "не принято"
    elif skipped:
        verdict = "неполно"
    else:
        verdict = "принято"

    payload = {
        "run_id": run_id,
        "run_status": status,
        "verdict_script": verdict,
        "failed": len(failed),
        "skipped": len(skipped),
        "checks": [c.as_dict() for c in checks],
    }

    if as_json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print("run: %s (status: %s)" % (run_id, status))
        print("вердикт скрипта: %s" % verdict)
        for c in checks:
            mark = {OK: "  ok  ", FAIL: " FAIL ", SKIP: " skip "}[c.status]
            print("[%s] %s — %s" % (mark, c.name, c.detail))

    # Код возврата: 0 принято, 1 не принято, 3 неполно.
    return {"принято": 0, "не принято": 1, "неполно": 3}[verdict]


if __name__ == "__main__":
    sys.exit(main())
