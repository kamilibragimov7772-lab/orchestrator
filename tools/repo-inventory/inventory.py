#!/usr/bin/env python3
# Orchestrator stack for Claude Code. Author: @kamil_ibrgmv - https://instagram.com/kamil_ibrgmv
"""
repo-inventory — Слой 1 регламента ревью больших проектов.

Считает доступные файлы и строит индекс. Это инвентаризация, не семантическое ревью.
Внешние анализаторы запускаются только с --external-tools.

Запуск:
    python3 ~/.claude/tools/repo-inventory/inventory.py <путь-к-проекту> [--out DIR] [--external-tools]

Выход (в <out>/, по умолчанию <проект>/.inventory/):
    00_MAP.md          — карта проекта для человека и модели (главный вход)
    01_symbols.tsv     — индекс символов: файл, строка, вид, имя
    02_findings.json   — машинный реестр находок (дубли, мёртвый код, линт, сложность)
    03_hotspots.tsv    — горячие зоны по git churn x сложность
    04_todo.tsv        — TODO/FIXME/HACK/XXX с координатами
    raw/               — сырые выхлопы инструментов

Ничего не правит. Только читает и считает.
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
import tempfile
from collections import Counter, defaultdict

# ---------------------------------------------------------------- конфигурация

PRUNE_DIRS = {
    "node_modules", ".next", ".git", ".venv", "venv", "__pycache__", "dist",
    "build", ".pytest_cache", ".hypothesis", ".ruff_cache", ".mypy_cache",
    ".turbo", ".cache", "coverage", ".nyc_output", "vendor", "site-packages",
    ".svelte-kit", "target", ".gradle", ".idea", ".vscode", ".inventory",
}
# Каталоги-бэкапы ловим отдельно: они не мусор, а сигнал (задвоение проекта).
BACKUP_RE = re.compile(r"(\.bak[-.]|[-_]backup|[-_]old\d*$|[-_]copy\d*$|~$)", re.I)

GENERATED_FILES = {
    "package-lock.json", "yarn.lock", "pnpm-lock.yaml", "poetry.lock",
    "tsconfig.tsbuildinfo", "Cargo.lock", "composer.lock",
}

CODE_EXT = {
    ".ts": "ts", ".tsx": "ts", ".js": "js", ".jsx": "js", ".mjs": "js",
    ".cjs": "js", ".py": "py", ".go": "go", ".rs": "rs", ".rb": "rb",
    ".php": "php", ".java": "java", ".kt": "kt", ".sh": "sh", ".sql": "sql",
    ".css": "css", ".scss": "css", ".prisma": "prisma", ".vue": "vue",
    ".svelte": "svelte", ".ps1": "powershell", ".vbs": "vbscript", ".html": "html",
}
DOC_EXT = {".md", ".mdx", ".rst", ".txt", ".adoc"}
CONF_EXT = {".json", ".yml", ".yaml", ".toml", ".ini", ".cfg", ".env", ".xml"}
BIN_EXT = {
    ".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp", ".ico", ".woff",
    ".woff2", ".ttf", ".eot", ".pdf", ".zip", ".gz", ".mp4", ".mp3", ".db",
    ".sqlite", ".sqlite3", ".bin", ".so", ".dylib", ".dll", ".wasm",
}
LOG_EXT = {".log", ".err", ".out", ".jsonl"}

# Вендоренные библиотеки внутри репозитория — считаем, но из анализа выключаем.
VENDOR_HINT = re.compile(
    r"(^|/)(vendor|third[-_]?party|public/(maplibre|leaflet|chart|jquery)|"
    r"static/(lib|vendor)|assets/(lib|vendor))(/|$)", re.I
)
VENDOR_MIN_BYTES = 100_000  # одиночный файл крупнее — почти наверняка библиотека

CHARS_PER_TOKEN = 3.5  # эмпирическая оценка для кода; для прозы ~4.0

TODO_RE = re.compile(r"\b(TODO|FIXME|HACK|XXX|WTF|OPTIMIZE|DEPRECATED)\b[:\s]", re.I)

# Регулярки-экстракторы символов. Дешёвая замена ctags/tree-sitter: ловит
# определения верхнего уровня, чего достаточно для карты «где что живёт».
SYMBOL_RES = {
    "py": [
        (re.compile(r"^\s*class\s+([A-Za-z_]\w*)"), "class"),
        (re.compile(r"^\s*(?:async\s+)?def\s+([A-Za-z_]\w*)"), "func"),
        (re.compile(r"^([A-Z][A-Z0-9_]{2,})\s*[:=]"), "const"),
    ],
    "ts": [
        (re.compile(r"^\s*export\s+(?:default\s+)?(?:abstract\s+)?class\s+(\w+)"), "class"),
        (re.compile(r"^\s*export\s+(?:default\s+)?(?:async\s+)?function\s+(\w+)"), "func"),
        (re.compile(r"^\s*export\s+(?:const|let|var)\s+(\w+)"), "const"),
        (re.compile(r"^\s*export\s+(?:type|interface)\s+(\w+)"), "type"),
        (re.compile(r"^\s*(?:export\s+)?enum\s+(\w+)"), "enum"),
    ],
    "go": [
        (re.compile(r"^func\s+(?:\([^)]*\)\s*)?([A-Za-z_]\w*)"), "func"),
        (re.compile(r"^type\s+([A-Za-z_]\w*)"), "type"),
    ],
    "sql": [(re.compile(r"CREATE\s+(?:TABLE|VIEW|INDEX)\s+(?:IF NOT EXISTS\s+)?[`\"]?(\w+)", re.I), "table")],
    "prisma": [(re.compile(r"^\s*(?:model|enum)\s+(\w+)"), "model")],
}
SYMBOL_RES["js"] = SYMBOL_RES["ts"]


def run(cmd, cwd=None, timeout=900, env=None):
    """Запускает команду, возвращает (rc, stdout, stderr). Не падает."""
    try:
        p = subprocess.run(
            cmd, cwd=cwd, timeout=timeout, capture_output=True, text=True, encoding="utf-8", errors="replace",
            env=env or os.environ.copy(),
        )
        return p.returncode, p.stdout, p.stderr
    except FileNotFoundError:
        return 127, "", "not found"
    except subprocess.TimeoutExpired:
        return 124, "", "timeout"
    except Exception as e:  # noqa: BLE001
        return 1, "", str(e)


def have(tool):
    return shutil.which(tool) is not None


# ------------------------------------------------------------------ шаг 1: обход

def walk(root):
    """Возвращает список записей о файлах. Проходит всё, ничего не читая целиком."""
    entries = []
    for dp, dn, fn in os.walk(root):
        dn[:] = sorted(d for d in dn if d not in PRUNE_DIRS and not os.path.islink(os.path.join(dp, d)))
        rel_dir = os.path.relpath(dp, root)
        for f in sorted(fn):
            path = os.path.join(dp, f)
            if os.path.islink(path):
                continue  # do not read symlink targets outside the requested tree
            rel = os.path.relpath(path, root)
            ext = os.path.splitext(f)[1].lower()
            try:
                size = os.path.getsize(path)
                mtime = os.path.getmtime(path)
            except OSError:
                continue
            kind = (
                "bin" if ext in BIN_EXT else
                "log" if ext in LOG_EXT else
                "gen" if f in GENERATED_FILES else
                "doc" if ext in DOC_EXT else
                "conf" if ext in CONF_EXT else
                "code" if ext in CODE_EXT else "other"
            )
            vendor = bool(VENDOR_HINT.search(rel.replace(os.sep, "/"))) or (
                kind == "code" and size > VENDOR_MIN_BYTES
            )
            backup = bool(BACKUP_RE.search(rel_dir)) or bool(BACKUP_RE.search(f))
            entries.append({
                "rel": rel, "ext": ext, "size": size, "mtime": mtime,
                "kind": kind, "lang": CODE_EXT.get(ext), "vendor": vendor,
                "backup": backup, "abs": path,
            })
    return entries


def count_lines(entries):
    """Counts readable text. Reading bytes is not semantic or security review."""
    for e in entries:
        if e["kind"] in ("bin", "log") or e["size"] > 5_000_000:
            e["lines"] = 0
            e["sloc"] = 0
            continue
        try:
            with open(e["abs"], "rb") as fh:
                data = fh.read()
        except OSError:
            e["lines"] = e["sloc"] = 0
            e["read_error"] = True
            continue
        if b"\0" in data[:4096]:
            e["kind"] = "bin"
            e["lines"] = e["sloc"] = 0
            continue
        text = data.decode("utf-8", "replace")
        lines = text.splitlines()
        e["lines"] = len(lines)
        e["sloc"] = sum(1 for ln in lines if ln.strip() and not ln.strip().startswith(("#", "//", "*", "/*")))
        e["_text"] = text if e["kind"] == "code" and not e["vendor"] else None
    return entries


# --------------------------------------------------------- шаг 2: символы и TODO

def extract_symbols_and_todo(entries):
    symbols, todos = [], []
    for e in entries:
        text = e.get("_text")
        if text is None:
            continue
        res = SYMBOL_RES.get(e["lang"], [])
        for i, line in enumerate(text.splitlines(), 1):
            if len(line) > 400:
                continue
            for rx, kind in res:
                m = rx.match(line) or (rx.search(line) if e["lang"] == "sql" else None)
                if m:
                    symbols.append((e["rel"], i, kind, m.group(1)))
                    break
            if TODO_RE.search(line):
                todos.append((e["rel"], i, line.strip()[:200]))
    return symbols, todos


TEST_RE = re.compile(r"(^|/)(tests?|__tests__|spec|e2e)(/|$)|(^|/)(test_|conftest)", re.I)
NOISE_NAMES = {
    "main", "run", "setup", "test", "init", "handler", "GET", "POST", "PUT",
    "DELETE", "PATCH", "Page", "Layout", "default", "index", "toString",
    "render", "config", "metadata", "generateMetadata",
}


def find_duplicate_symbols(symbols, backup_files):
    """Одноимённые определения в разных файлах — кандидаты на задвоение логики.

    Шум режем сознательно: дандеры, тест-хелперы и копии из бэкап-каталогов
    дублями логики не считаются (бэкапы выносим отдельной строкой карты)."""
    by_name = defaultdict(list)
    for rel, ln, kind, name in symbols:
        if rel in backup_files:
            continue
        if TEST_RE.search(rel.replace(os.sep, "/")):
            continue
        if name.startswith("__") or name.startswith("_") and len(name) < 6:
            continue
        if kind in ("func", "class", "type") and len(name) > 3 and name not in NOISE_NAMES:
            by_name[(kind, name)].append(f"{rel}:{ln}")
    out = {}
    for k, v in by_name.items():
        files = {p.rsplit(":", 1)[0] for p in v}
        if len(files) > 1:  # только если в РАЗНЫХ файлах
            out[f"{k[0]} {k[1]}"] = sorted(v)
    return out


# --------------------------------------------------- шаг 3: внешние инструменты

def tool_jscpd(root, outdir, langs):
    """Дубли кода. Копипаста ≥50 токенов в ≥5 строк."""
    if not (langs & {"ts", "js", "py", "css"}):
        return None
    rep = tempfile.mkdtemp(prefix="jscpd-", dir=os.path.join(outdir, "raw"))
    ignore = (",".join(f"**/{d}/**" for d in sorted(PRUNE_DIRS))
              + ",**/*.bak*/**,**/*.min.js,**/data/**,**/logs/**,**/*.xml,"
                "**/_cache/**,**/*cache*/**,**/public/**,**/static/**")
    rc, out, err = run([
        "npx", "--yes", "jscpd@5", root,
        "--min-tokens", "50", "--min-lines", "5",
        "--reporters", "json", "--output", rep,
        "--ignore", ignore, "--silent",
    ], timeout=900)
    if rc != 0:
        return {"error": f"jscpd exited {rc}; result not accepted"}
    j = os.path.join(rep, "jscpd-report.json")
    if not os.path.exists(j):
        return {"error": err.strip()[:200] or f"rc={rc}"}
    try:
        with open(j, encoding="utf-8") as stream:
            data = json.load(stream)
    except Exception as e:  # noqa: BLE001
        return {"error": str(e)}
    st = data.get("statistics", {}).get("total", {})
    dups = []
    for d in data.get("duplicates", [])[:200]:
        dups.append({
            "lines": d.get("lines"),
            "tokens": d.get("tokens"),
            "a": f"{d['firstFile']['name']}:{d['firstFile']['start']}-{d['firstFile']['end']}",
            "b": f"{d['secondFile']['name']}:{d['secondFile']['start']}-{d['secondFile']['end']}",
        })
    dups.sort(key=lambda x: -(x["lines"] or 0))
    return {
        "percent": round(st.get("percentage", 0), 2),
        "cloned_lines": st.get("duplicatedLines", 0),
        "clones": st.get("clones", 0),
        "top": dups[:40],
    }


def tool_ruff(root, outdir):
    if not have("ruff"):
        return None
    rc, out, _ = run(["ruff", "check", root, "--output-format", "json",
                      "--select", "F,E,W,I,UP,B,SIM,ARG,ERA,PLR", "--exit-zero",
                      "--no-cache"], timeout=600)
    if rc != 0 or not out.strip():
        return {"error": f"ruff exited {rc} or returned no JSON"}
    try:
        items = json.loads(out)
    except Exception:
        return {"error": "parse"}
    open(os.path.join(outdir, "raw", "ruff.json"), "w", encoding="utf-8").write(out or "[]")
    codes = Counter(i.get("code") or "?" for i in items)
    fixable = sum(1 for i in items if i.get("fix"))
    return {"total": len(items), "fixable": fixable, "by_code": codes.most_common(25)}


def tool_vulture(root, outdir):
    if not have("vulture"):
        return None
    excl = ",".join(f"*/{d}/*" for d in sorted(PRUNE_DIRS)) + ",*.bak*"
    rc, out, _ = run(["vulture", root, "--min-confidence", "80", "--exclude", excl],
                     timeout=600)
    if rc not in (0, 3):
        return {"error": f"vulture exited {rc}; result not accepted"}
    open(os.path.join(outdir, "raw", "vulture.txt"), "w", encoding="utf-8").write(out or "")
    lines = [ln.replace(root + "/", "") for ln in (out or "").splitlines() if ln.strip()]
    src = [ln for ln in lines if not TEST_RE.search(ln.split(":")[0])]
    return {"total": len(lines), "in_src": len(src), "sample": src[:40] or lines[:40]}


def tool_knip(root, outdir):
    if not os.path.exists(os.path.join(root, "package.json")):
        return None
    rc, out, err = run(["npx", "--yes", "knip@5", "--reporter", "json",
                        "--no-exit-code"], cwd=root, timeout=900)
    if rc != 0:
        return {"error": f"knip exited {rc}; result not accepted"}
    body = out.strip()
    start = body.find("{")
    if start == -1:
        return {"error": (err or body)[-300:]}
    try:
        data = json.loads(body[start:])
    except Exception:
        return {"error": "parse"}
    open(os.path.join(outdir, "raw", "knip.json"), "w", encoding="utf-8").write(json.dumps(data)[:2_000_000])
    files = data.get("files", [])
    issues = data.get("issues", [])
    agg = Counter()
    for it in issues:
        for k in ("exports", "types", "dependencies", "devDependencies",
                  "unlisted", "unresolved", "duplicates", "enumMembers", "classMembers"):
            agg[k] += len(it.get(k) or [])
    return {"unused_files": len(files), "unused_files_sample": files[:40],
            "by_kind": agg.most_common()}


def tool_radon(root, outdir, langs):
    if "py" not in langs or not have("radon"):
        return None
    rc, out, _ = run(["radon", "cc", root, "-j", "--min", "C",
                      "-e", "*/.venv/*,*/node_modules/*,*.bak*/*"], timeout=600)
    if rc != 0 or not out.strip():
        return {"error": f"radon exited {rc} or returned no JSON"}
    try:
        data = json.loads(out)
    except Exception:
        return {"error": "parse"}
    open(os.path.join(outdir, "raw", "radon_cc.json"), "w", encoding="utf-8").write(out or "{}")
    worst = []
    for f, items in data.items():
        if not isinstance(items, list):
            continue
        for it in items:
            worst.append({"file": os.path.relpath(f, root), "line": it.get("lineno"),
                          "name": it.get("name"), "cc": it.get("complexity"),
                          "rank": it.get("rank")})
    worst.sort(key=lambda x: -(x["cc"] or 0))
    return {"functions_over_C": len(worst), "top": worst[:30]}


def tool_git_churn(root, outdir):
    if not os.path.exists(os.path.join(root, ".git")):
        return {"error": "не git-репозиторий"}
    rc, out, _ = run(["git", "log", "--since=12.months", "--pretty=format:%H",
                      "--numstat"], cwd=root, timeout=300)
    if rc != 0:
        return {"error": f"git log exited {rc}; result not accepted"}
    churn = Counter()
    commits = 0
    for ln in out.splitlines():
        if not ln.strip():
            continue
        parts = ln.split("\t")
        if len(parts) == 3:
            a, d, f = parts
            if a.isdigit():
                churn[f] += int(a) + int(d)
        else:
            commits += 1
    open(os.path.join(outdir, "raw", "git_churn.tsv"), "w", encoding="utf-8").write(
        "\n".join(f"{v}\t{k}" for k, v in churn.most_common())
    )
    return {"commits_12m": commits, "top": churn.most_common(30)}


# -------------------------------------------------------------------- шаг 4: вывод

def human(n):
    for u in ("Б", "КБ", "МБ", "ГБ"):
        if abs(n) < 1024:
            return f"{n:.0f} {u}" if u == "Б" else f"{n:.1f} {u}"
        n /= 1024
    return f"{n:.1f} ТБ"


def build_map(root, entries, symbols, dup_symbols, todos, findings, outdir, elapsed):
    code = [e for e in entries if e["kind"] == "code" and not e["vendor"] and not e["backup"]]
    vendor = [e for e in entries if e["vendor"]]
    backup = [e for e in entries if e["backup"]]
    docs = [e for e in entries if e["kind"] == "doc"]

    code_bytes = sum(e["size"] for e in code)
    all_text_bytes = sum(e["size"] for e in entries if e["kind"] in ("code", "doc", "conf"))

    by_lang = Counter()
    lines_by_lang = Counter()
    for e in code:
        by_lang[e["lang"]] += 1
        lines_by_lang[e["lang"]] += e["lines"]

    # Топ-каталоги по строкам кода
    dirs = Counter()
    for e in code:
        d = os.path.dirname(e["rel"]) or "."
        parts = d.split(os.sep)
        dirs[os.sep.join(parts[:2])] += e["lines"]

    L = []
    a = L.append
    a(f"# Карта проекта — {os.path.basename(os.path.abspath(root))}")
    a("")
    a(f"Собрано: {time.strftime('%Y-%m-%d %H:%M')} · за {elapsed:.0f} с · `repo-inventory`")
    a(f"Корень: `{os.path.abspath(root)}`")
    a("")
    a("## 1. Объём")
    a("")
    a("| Что | Значение |")
    a("|---|---|")
    a(f"| Файлов всего (без node_modules/.venv/.git/build) | {len(entries)} |")
    a(f"| Из них рабочего кода | {len(code)} файлов, {sum(e['lines'] for e in code):,} строк |")
    a(f"| Вендоренные библиотеки в репо | {len(vendor)} файлов, {human(sum(e['size'] for e in vendor))} |")
    a(f"| Копии/бэкапы внутри проекта | {len(backup)} файлов, {human(sum(e['size'] for e in backup))} |")
    a(f"| Документация (.md и пр.) | {len(docs)} файлов, {sum(e['lines'] for e in docs):,} строк |")
    a(f"| Байт рабочего кода | {code_bytes:,} ≈ **{int(code_bytes / CHARS_PER_TOKEN):,} токенов** |")
    a(f"| Байт всего текста (код+доки+конфиги) | {all_text_bytes:,} ≈ **{int(all_text_bytes / CHARS_PER_TOKEN):,} токенов** |")
    a("")
    if backup:
        bdirs = Counter()
        for e in backup:
            bdirs[e["rel"].split(os.sep)[0]] += e["lines"]
        a("> ⚠️ **Внутри проекта лежат копии.** Это не мусор в фоне — это код, "
          "который поиск, линтер и человек принимают за рабочий:")
        for d, n in bdirs.most_common(10):
            a(f"> - `{d}` — {n:,} строк")
        a("> Первое действие ревью: увести копии из рабочего дерева "
          "(в git-историю или в `_archive/` вне корня сборки).")
        a("")
    a("## 1а. Покрытие инвентаризации (не семантического ревью)")
    a("")
    a("Каждый файл дерева попал ровно в одну корзину. Сумма корзин = общему числу файлов —")
    a("Симлинки и каталоги из списка исключений не обходятся; ошибки чтения отмечаются отдельно.")
    a("")
    a("| Корзина | Файлов | Строк | Чем пройдено |")
    a("|---|---|---|---|")
    buckets = [
        ("тесты", [e for e in code if TEST_RE.search(e["rel"].replace(os.sep, "/"))], "счётчик строк + доступные регулярки символов"),
        ("рабочий код", [e for e in code], "счётчик строк + доступные регулярки символов"),
        ("копии/бэкапы", backup, "посчитаны, из анализа исключены (см. врезку)"),
        ("вендор-библиотеки", vendor, "посчитаны, из анализа исключены"),
        ("документация", docs, "счётчик строк; смысл и дубли текста не проверены"),
        ("конфиги", [e for e in entries if e["kind"] == "conf"], "счётчик строк, чтение по требованию"),
        ("логи и данные", [e for e in entries if e["kind"] == "log"], "только размер, содержимое не читается"),
        ("бинарники и медиа", [e for e in entries if e["kind"] == "bin"], "только размер"),
        ("сгенерированное", [e for e in entries if e["kind"] == "gen"], "исключено по имени файла"),
        ("прочее", [e for e in entries if e["kind"] == "other"], "счётчик строк"),
    ]
    seen = set()
    shown = 0
    for label, items, how in buckets:
        items = [e for e in items if id(e) not in seen]
        for e in items:
            seen.add(id(e))
        if not items:
            continue
        shown += len(items)
        a(f"| {label} | {len(items)} | {sum(e['lines'] for e in items):,} | {how} |")
    a(f"| **сумма** | **{shown}** | | сходится с «файлов всего» = {len(entries)} |")
    a("")
    if shown != len(entries):
        a(f"> ❌ РАСХОЖДЕНИЕ: {len(entries) - shown} файлов не попали ни в одну корзину. Чинить скрипт.")
        a("")
    a("Что скрипт вообще не обходит (вырезано на входе, список фиксированный): "
      + ", ".join(f"`{d}`" for d in sorted(PRUNE_DIRS)) + ".")
    a("")
    a("## 2. Языки")
    a("")
    a("| Язык | Файлов | Строк |")
    a("|---|---|---|")
    for lang, n in by_lang.most_common():
        a(f"| {lang} | {n} | {lines_by_lang[lang]:,} |")
    a("")
    a("## 3. Где живёт код (топ каталогов по строкам)")
    a("")
    for d, n in dirs.most_common(15):
        a(f"- `{d}/` — {n:,} строк")
    a("")
    a("## 4. Индекс символов")
    a("")
    kinds = Counter(k for _, _, k, _ in symbols)
    a(f"Всего определений: **{len(symbols)}** — {', '.join(f'{k}: {v}' for k, v in kinds.most_common())}")
    a("")
    a("Полный индекс: `01_symbols.tsv` (файл, строка, вид, имя). "
      "Ищи по нему grep'ом вместо чтения кода.")
    a("")
    if dup_symbols:
        a(f"### Одноимённые определения в разных файлах — {len(dup_symbols)} шт.")
        a("")
        a("Кандидаты на задвоение логики. Требует глазами: одно и то же или совпадение имён.")
        a("")
        for name, places in sorted(dup_symbols.items(), key=lambda x: -len(x[1]))[:25]:
            a(f"- `{name}` → {len(places)}× : {', '.join(places[:4])}{' …' if len(places) > 4 else ''}")
        a("")
    a("## 5. Находки инструментов")
    a("")
    a("| Инструмент | Фактический результат |")
    a("|---|---|")
    for name, result in findings.items():
        a(f"| {name} | {result.get('error', 'выполнен')} |")
    a("")
    a(f"Ошибок чтения: {sum(bool(e.get('read_error')) for e in entries)}")
    d = findings.get("duplicates")
    if d and "error" not in d:
        a(f"### Копипаста (jscpd, ≥50 токенов / ≥5 строк)")
        a(f"**{d['percent']}%** кодовой базы дублировано · {d['clones']} клонов · {d['cloned_lines']:,} строк")
        a("")
        for c in d["top"][:15]:
            a(f"- {c['lines']} строк — `{c['a']}` ≡ `{c['b']}`")
        a("")
    elif d:
        a(f"### Копипаста — не посчитана: {d['error']}\n")
    r = findings.get("ruff")
    if r and "error" not in r:
        a("### Линт Python (ruff)")
        a(f"Замечаний: **{r['total']}**, из них авто-исправимых: **{r['fixable']}**")
        a("")
        a("| Код | Шт. |")
        a("|---|---|")
        for code_, n in r["by_code"][:15]:
            a(f"| {code_} | {n} |")
        a("")
    v = findings.get("vulture")
    if v and "error" not in v:
        a("### Возможный мёртвый код Python (vulture, confidence ≥80)")
        a(f"Кандидатов: **{v['total']}**, из них вне тестов: **{v.get('in_src', '?')}**")
        a("")
        for ln in v["sample"][:20]:
            a(f"- `{ln}`")
        a("")
    k = findings.get("knip")
    if k and "error" not in k:
        a("### Неиспользуемое в JS/TS (knip)")
        a(f"Файлов ни на что не сосланных: **{k['unused_files']}**")
        if k["by_kind"]:
            a("")
            a("| Вид | Шт. |")
            a("|---|---|")
            for kk, n in k["by_kind"]:
                if n:
                    a(f"| {kk} | {n} |")
        a("")
        for f in k["unused_files_sample"][:20]:
            a(f"- `{f}`")
        a("")
    elif k:
        a(f"### knip — не отработал: {k['error']}\n")
    c = findings.get("radon")
    if c and "error" not in c:
        a("### Сложность (radon, цикломатическая ≥ C)")
        a(f"Функций сложнее порога: **{c['functions_over_C']}**")
        a("")
        for it in c["top"][:15]:
            a(f"- CC={it['cc']} ({it['rank']}) `{it['file']}:{it['line']}` — {it['name']}")
        a("")
    g = findings.get("git")
    if g and "error" not in g:
        a("### Горячие зоны (git churn за 12 мес)")
        a(f"Коммитов: {g['commits_12m']}")
        a("")
        for f, n in g["top"][:15]:
            a(f"- {n:,} изменённых строк — `{f}`")
        a("")
    elif g:
        a(f"### Горячие зоны — {g['error']}. **Без git самолечение запрещено** (нечем откатывать).\n")
    a("## 6. TODO и долги")
    a("")
    a(f"Меток TODO/FIXME/HACK/XXX: **{len(todos)}** — полный список в `04_todo.tsv`")
    a("")
    for rel, ln, txt in todos[:15]:
        a(f"- `{rel}:{ln}` — {txt[:120]}")
    a("")
    a("## 7. Что делать модели дальше")
    a("")
    a("Этот файл — вход. Код читать выборочно и только по адресам отсюда.")
    a("Порядок разбора: копипаста → одноимённые символы → мёртвый код → горячие зоны → сложность → TODO.")
    return "\n".join(L)


def main():
    ap = argparse.ArgumentParser()
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"): stream.reconfigure(encoding="utf-8")
    ap.add_argument("root")
    ap.add_argument("--external-tools", action="store_true", help="May download and run jscpd/knip through npx; review target configuration first")
    ap.add_argument("--out", default=None)
    ap.add_argument("--skip", default="", help="через запятую: jscpd,knip,ruff,vulture,radon,git")
    args = ap.parse_args()

    t0 = time.time()
    root = os.path.abspath(args.root)
    if not os.path.isdir(root):
        ap.error("root directory does not exist")
    outdir = os.path.abspath(args.out or os.path.join(root, ".inventory"))
    os.makedirs(os.path.join(outdir, "raw"), exist_ok=True)
    skip = {s.strip() for s in args.skip.split(",") if s.strip()}

    if "jscpd" in skip: skip.add("duplicates")

    print(f"[1/5] обход дерева {root} …", file=sys.stderr)
    entries = count_lines(walk(root))

    print("[2/5] символы, TODO …", file=sys.stderr)
    symbols, todos = extract_symbols_and_todo(entries)
    dup_symbols = find_duplicate_symbols(symbols, {e["rel"] for e in entries if e["backup"]})

    langs = {e["lang"] for e in entries if e["kind"] == "code" and not e["vendor"]}
    print(f"[3/5] инструменты (языки: {sorted(x for x in langs if x)}) …", file=sys.stderr)
    findings = {}
    for name, fn in [
        ("duplicates", lambda: tool_jscpd(root, outdir, langs)),
        ("ruff", lambda: tool_ruff(root, outdir)),
        ("vulture", lambda: tool_vulture(root, outdir)),
        ("knip", lambda: tool_knip(root, outdir)),
        ("radon", lambda: tool_radon(root, outdir, langs)),
        ("git", lambda: tool_git_churn(root, outdir)),
    ]:
        if name in skip or (name != "git" and not args.external_tools):
            findings[name] = {"error": "SKIP: not requested"}
            continue
        print(f"      · {name}", file=sys.stderr)
        res = fn()
        findings[name] = res if res is not None else {"error": "SKIP: unavailable or not applicable"}

    print("[4/5] запись среза …", file=sys.stderr)
    with open(os.path.join(outdir, "01_symbols.tsv"), "w", encoding="utf-8") as fh:
        fh.write("file\tline\tkind\tname\n")
        for rel, ln, kind, name in symbols:
            fh.write(f"{rel}\t{ln}\t{kind}\t{name}\n")
    with open(os.path.join(outdir, "04_todo.tsv"), "w", encoding="utf-8") as fh:
        fh.write("file\tline\ttext\n")
        for rel, ln, txt in todos:
            fh.write(f"{rel}\t{ln}\t{txt}\n")
    g = findings.get("git") or {}
    with open(os.path.join(outdir, "03_hotspots.tsv"), "w", encoding="utf-8") as fh:
        fh.write("churn_lines\tfile\n")
        for f, n in (g.get("top") or []):
            fh.write(f"{n}\t{f}\n")
    with open(os.path.join(outdir, "02_findings.json"), "w", encoding="utf-8") as fh:
        json.dump({
            "root": root,
            "generated": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "files": len(entries),
            "code_files": sum(1 for e in entries if e["kind"] == "code" and not e["vendor"] and not e["backup"]),
            "code_lines": sum(e["lines"] for e in entries if e["kind"] == "code" and not e["vendor"] and not e["backup"]),
            "backup_files": sum(1 for e in entries if e["backup"]),
            "symbols": len(symbols),
            "duplicate_symbol_names": dup_symbols,
            "todos": len(todos),
            "findings": findings,
        }, fh, ensure_ascii=False, indent=1)

    print("[5/5] карта …", file=sys.stderr)
    mp = build_map(root, entries, symbols, dup_symbols, todos, findings, outdir, time.time() - t0)
    open(os.path.join(outdir, "00_MAP.md"), "w", encoding="utf-8").write(mp)

    sizes = {f: os.path.getsize(os.path.join(outdir, f))
             for f in ("00_MAP.md", "01_symbols.tsv", "02_findings.json",
                       "03_hotspots.tsv", "04_todo.tsv")}
    print(f"\nГотово за {time.time() - t0:.0f} c → {outdir}", file=sys.stderr)
    for f, s in sizes.items():
        print(f"  {f:20} {s:>9,} Б  ≈{int(s / CHARS_PER_TOKEN):>7,} токенов", file=sys.stderr)
    print(f"  {'ИТОГО СРЕЗ':20} {sum(sizes.values()):>9,} Б  "
          f"≈{int(sum(sizes.values()) / CHARS_PER_TOKEN):>7,} токенов", file=sys.stderr)

    failed = any("error" in v and not v["error"].startswith("SKIP:") for v in findings.values())
    return int(failed or any(e.get("read_error") for e in entries))


if __name__ == "__main__":
    sys.exit(main())
