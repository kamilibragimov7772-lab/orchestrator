# -*- coding: utf-8 -*-
"""agent-lint — проверка определений субагентов на исполнимость.

Зачем. Аудит 40 карточек (2026-08-21) показал: главные дефекты стека не стилистические,
а структурные — обязанность без инструмента, ссылка на несуществующий файл, отсутствие
приёмки, самопротиворечие frontmatter против тела. Все они молчаливые: агент не падает,
а выдаёт правдоподобный результат. Линтер делает их громкими.

История версий:
  v1 (2026-08-21) — 9 правил. Ворота нашли, что v1 слеп ровно к тем трём классам путей,
     которые были сломаны в том же прогоне: путь с нераскрытой переменной ($), путь
     с двойным корнем (<abs path>/~/...) и путь без корня (_shared/...). Все три
     отбрасывались фильтрами PLACEHOLDER / LOOKS_LOCAL до всякой проверки, поэтому
     «0 ошибок» было получено на выборке, из которой исключено свежесломанное.
     Плюс правило Write обессмыслилось: вставленный во все 40 карточек блок DoD
     содержит слово expected_path, то есть триггер срабатывал всегда и везде.
  v2 (2026-08-21) — правила путей переписаны на проверку скелета; общие вставленные
     блоки вырезаются перед проверкой обязанностей; добавлены проверки согласованности
     статусов и рекурсивный обход _shared/. Появился режим --selftest.

Запуск:
    py -3 ~/.claude/tools/agent-lint.py             # все карточки + _shared
    py -3 ~/.claude/tools/agent-lint.py --quiet     # только ошибки
    py -3 ~/.claude/tools/agent-lint.py --selftest  # синтетические негативные регрессии, без приватных бэкапов
    py -3 ~/.claude/tools/agent-lint.py <файл>...

Код возврата: 0 — чисто; 1 — есть ОШИБКИ. Предупреждения код возврата не меняют.

Пути: каталог стека — из переменной окружения CLAUDE_HOME (по умолчанию корень checkout),
корень vault — из VAULT_ROOT (по умолчанию ~/vault).
"""
import os, re, sys, glob, collections, subprocess

sys.stdout.reconfigure(encoding="utf-8")

HOME = os.path.expanduser("~")
STACK = os.path.abspath(os.environ.get("CLAUDE_HOME") or os.path.dirname(os.path.dirname(__file__)))
AG = os.path.join(STACK, "agents")

# Vault на разных машинах лежит по-разному, а его копия может быть неполной. Жёстко
# зашитый путь давал на второй машине десятки ошибок на ровном месте — то есть хук
# заблокировал бы там любой коммит. Поэтому корень берётся из окружения, с умолчанием ~/vault.
VAULT = os.environ.get("VAULT_ROOT") or os.path.join(HOME, "vault")

# Существование ФАЙЛОВ ВНЕ СТЕКА машинно-зависимо (vault неполон на сервере, виндовых путей
# там нет вовсе) — такие промахи идут предупреждением. Структурные дефекты пути (нераскрытая
# переменная, двойной корень, бескорневая ссылка на канон) машинно-независимы и остаются
# ошибкой на обеих машинах.
_CANON_ROOTS = [os.path.join(STACK, d)
                for d in ("agents", "commands", "skills", "tools", "githooks", "hooks")]
# Внутри ~/.claude есть машинно-зависимое: projects/ (сессии, имя кодирует виндовый путь),
# plugins/ (маркетплейс ставится отдельно), cache/, backups/, chrome/. Их отсутствие
# на второй машине — норма, а не дефект карточки. Канон моста — только список выше.


def in_stack(resolved):
    r = os.path.normcase(os.path.abspath(resolved))
    return r == os.path.normcase(STACK) or any(
        r == os.path.normcase(x) or r.startswith(os.path.normcase(x) + os.sep)
        for x in _CANON_ROOTS)

QUIET = "--quiet" in sys.argv
SELFTEST = "--selftest" in sys.argv
targets = [a for a in sys.argv[1:] if not a.startswith("--")]

if SELFTEST:
    test = os.path.join(STACK, "tests", "test_agent_lint.py")
    if not os.path.isfile(test):
        print("SELFTEST unavailable: install tests/test_agent_lint.py", file=sys.stderr)
        sys.exit(2)
    sys.exit(subprocess.call([sys.executable, test]))
files = targets or (sorted(glob.glob(os.path.join(AG, "*.md")))
                    + sorted(glob.glob(os.path.join(AG, "_shared", "**", "*.md"), recursive=True)))
if not files or any(not os.path.isfile(f) for f in files):
    print("agent-lint: no cards or missing input file; NOT CHECKED", file=sys.stderr)
    sys.exit(2)

KNOWN = {os.path.basename(f)[:-3] for f in glob.glob(os.path.join(AG, "*.md"))}

# ── обязанность → требуемый инструмент ────────────────────────────────────────
DUTY = [
    ("Write", r"Сохрани|Путь по умолчанию|expected_path|запиши файл|создай файл|сохрани отчёт"),
    # «посчита» без уточнения ловило пассив («N посчитан неверно») — это не приказ считать,
    # а описание ошибки. Нужны повелительные и инфинитивные формы плюс явные шелл-вызовы.
    ("Bash", r"\bnpx\b|\bcurl\b|lighthouse|axe-core|npm audit|посчитай\b|посчитать\b"
             r"|`ls |`du |`wc |chrome-launcher"),
]
CAPS = [
    ("браузер (Playwright/CDP)", r"[Оо]ткрой (страницу )?в Chrome|нажми Tab|VoiceOver|NVDA",
     r"mcp__playwright|mcp__chrome-devtools|browser_navigate"),
]

# Общие блоки, вставленные во ВСЕ карточки, вырезаются перед проверкой обязанностей:
# иначе их собственный текст («expected_path», «tool_unavailable») делает правила вечно
# истинными и обессмысливает проверку. Это ровно тот дефект, который нашли ворота у v1.
SHARED_BLOCKS = [
    re.compile(r"## Валидация входа \(обязательно.*?(?=\n#{1,3} |\Z)", re.S),
    re.compile(r"## Definition of Done\n.*?(?=\n#{1,3} |\Z)", re.S),
]

PATH_IN_TICKS = re.compile(r"`([^`\n]{3,200})`")
PLACEHOLDER = re.compile(r"<[^>]{1,40}>|\{[^}]{1,40}\}|YYYY|ГГГГ|\bN\b|\.\.\.")
SUFFIX = ("-architect", "-researcher", "-analyst", "-reviewer", "-auditor", "-engineer",
          "-designer", "-compiler", "-curator", "-hunter", "-narrator", "-checker",
          "-optimizer", "-writer", "-author", "-editor", "-discoverer", "-strategist")
INVENTORY = re.compile(
    r"(?<![\d\-–—<>≤≥])\b(\d{1,4})\s+(HTML-файл\w*|состояни\w*|раздел\w* vault|канонических\w*)\b"
    r"|A-запись\s+\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}"
    r"|Chromium\s+\d{3,4}", re.I)

CANON_DIRS = ("_shared/", "site-build/")


# Закрытые списки читаются ИЗ канона, а не дублируются здесь: второй экземпляр списка —
# это ровно тот дубль правила, за которым ходили ворота.
def _canon_enum(pat):
    try:
        cc = open(os.path.join(AG, "_shared", "communication_contract.md"), encoding="utf-8").read()
        m = re.search(pat, cc)
        return set(x.strip() for x in m.group(1).split("|")) if m else set()
    except Exception:
        return set()


CANON_META = _canon_enum(r"type: <(brief\|[^>]*)>")
if not CANON_META:
    print("agent-lint: communication contract missing or invalid; NOT CHECKED", file=sys.stderr)
    sys.exit(2)

# Структурные шаблоны поломки пути. Ищутся по ВСЕМУ тексту файла, включая код-блоки,
# и не зависят от того, сумели ли мы распознать строку как путь.
# Только склейка «плейсхолдер-корень + второй корень». Первая редакция имела вторую
# альтернативу «любой ~/.claude после непробела» — она ловила каждый путь в обратных
# кавычках и дала 326 ложных ошибок на живом дереве. Шумное правило хуже отсутствующего.
STRUCT_DOUBLE_ROOT = re.compile(r"<[^>\n]{0,40}>/(?:~/|[A-Za-z]:\\)|[A-Za-z]:\\[^\s`]*[A-Za-z]:\\")
STRUCT_UNEXPANDED = re.compile(r"(?:~|[A-Za-z]:\\|/)[\w./\\-]*\$\{?\w+[\w./\\-]*\.(?:md|json|ya?ml|txt|html)")


def strip_shared(body):
    for pat in SHARED_BLOCKS:
        body = pat.sub("", body)
    return body


def resolve(p):
    q = p.strip().rstrip(".,;:)»`")
    q = q.replace("~/vault", VAULT)
    if q == "~/.claude" or q.startswith("~/.claude/"):
        q = os.path.join(STACK, q[len("~/.claude"):].lstrip("/"))
    if q.startswith("~/"):
        q = os.path.join(HOME, q[2:])
    return q.replace("/", os.sep)


def check_path(s, add_err, add_warn):
    """Проверка пути.

    Порядок важен: СНАЧАЛА решаем, путь ли это вообще, и только потом применяем правила.
    Первая редакция делала наоборот и ловила ключи W3C Design Tokens ($type, $value) и
    шелл-команды (echo $HTTP_PROXY) как «нераскрытые переменные в пути».

    Плейсхолдеры не повод пропустить путь целиком: вырезаем их и проверяем неизменяемый хвост —
    иначе `<abs path>/~/.claude/...` (двойной корень) проходит незамеченным.
    """
    raw = s.strip()

    # Путь ли это? Однотокенная строка, начинающаяся с корня, точки или каталога канона.
    if " " in raw:
        return
    is_canon_rel = any(raw.startswith(d) for d in CANON_DIRS)
    if not (re.match(r"^(~/|[A-Za-z]:\\|\./|\.\./)", raw) or is_canon_rel):
        return

    # 1. ссылка на канон без корня — агент не найдёт файл
    if is_canon_rel:
        if raw.rstrip("/").count("/") == 0:
            add_warn("упоминание каталога канона без корня: %s" % raw[:70])
        else:
            add_err("ссылка на канон без корня (агент не найдёт): %s" % raw[:70])
        return
    if raw.startswith(("./", "../")):
        add_err("относительный путь без корня: %s" % raw[:70])
        return

    # 2. нераскрытая переменная шелла в пути
    if re.search(r"\$\w+|\$\{", raw):
        add_err("нераскрытая переменная в пути: %s" % raw[:70])
        return

    # 3. второй корень в середине пути
    if re.search(r"[^\s]\~/|[A-Za-z]:\\.*[A-Za-z]:\\", raw):
        add_err("двойной корень в пути: %s" % raw[:70])
        return

    # 4. глоб — проверяем каталог, а не литеральный путь
    if "*" in raw or "?" in raw:
        d = os.path.dirname(resolve(raw.split("*")[0].split("?")[0]))
        if d and not os.path.exists(d):
            (add_err if in_stack(d) else add_warn)(
                "каталог глоба не существует%s: %s (из %s)"
                % ("" if in_stack(d) else " на этой машине", d[-52:], raw[:40]))
        return

    # 5. шаблонный путь — проверяем неизменяемый КАТАЛОГ до первого плейсхолдера.
    #    Именно каталог, а не любой префикс: в «~/vault/_orchestr/_ACTIVE/run-<run_id>.md»
    #    префикс обрывается на «run-», и проверка существования такого «каталога»
    #    давала ложную ошибку.
    if PLACEHOLDER.search(raw):
        head = PLACEHOLDER.split(raw)[0]
        head = head[:head.rfind("/") + 1] if "/" in head else ""
        head = head.rstrip("/")
        if head.count("/") >= 2:
            r = resolve(head)
            if not os.path.exists(r):
                (add_err if in_stack(r) else add_warn)(
                    "несуществующий каталог в шаблонном пути%s: %s"
                    % ("" if in_stack(r) else " на этой машине", head[:56]))
        return

    r = resolve(raw)
    if not os.path.exists(r):
        (add_err if in_stack(r) else add_warn)(
            "путь не существует%s: %s" % ("" if in_stack(r) else " на этой машине", raw[:70]))


errors = collections.defaultdict(list)
warns = collections.defaultdict(list)

for f in files:
    n = os.path.relpath(f, AG).replace(".bak-9of10-20260821", "")
    t = open(f, encoding="utf-8", errors="replace").read()
    fm = re.match(r"^---\n(.*?)\n---\n", t, re.S)
    # Сравнение каталогов — через normcase+abspath. Раньше стояло `os.path.dirname(f) == AG`,
    # и при вызове с POSIX-путём (`py -3 agent-lint.py /c/Users/.../agents/x.md`, как это делает
    # Git Bash) сравнение всегда было ложным: проверки карточки МОЛЧА пропускались, а линтер
    # печатал «0 ошибок». Двадцать восемь воркеров отчитались по этой проверке. Найдено 2026-08-22
    # мутационным прогоном — сам мутант и вскрыл дыру, ради которой мутанты и делаются.
    def _same_dir(a, b):
        return os.path.normcase(os.path.abspath(a)) == os.path.normcase(os.path.abspath(b))

    is_card = _same_dir(os.path.dirname(f) or ".", AG) or (bool(targets) and fm is not None)

    front = fm.group(1) if fm else ""
    body = t[fm.end():] if fm else t
    body_own = strip_shared(body)

    def E(msg, _n=n):
        errors[_n].append(msg)

    def W(msg, _n=n):
        warns[_n].append(msg)

    # (а) СТРУКТУРНЫЙ скан по всему тексту, без разбора «путь ли это».
    #     Введён 2026-08-22 после вторых ворот: v2 сканировал только спаны в обратных
    #     кавычках, а шесть склеек «<...>/~/» лежали в ```yaml-блоках — и линтер их не видел,
    #     показывая «0 ошибок» на дереве с незакрытым дефектом. Структурная поломка — это
    #     текстовый шаблон, для его поиска путь распознавать не нужно.
    for m in STRUCT_DOUBLE_ROOT.finditer(t):
        E("двойной корень (плейсхолдер + домашний корень): %s" % m.group(0)[:60])
    for m in STRUCT_UNEXPANDED.finditer(t):
        E("нераскрытая переменная в пути: %s" % m.group(0)[:60])

    # (б) потокенная проверка спанов в обратных кавычках
    for span in set(PATH_IN_TICKS.findall(t)):
        check_path(span, E, W)

    if not is_card:
        continue

    if fm is None:
        E("нет корректного YAML frontmatter карточки")
        continue

    def fv(k):
        m = re.search(r"^%s:\s*(.+)$" % k, front, re.M)
        return m.group(1).strip() if m else None

    name = fv("name")
    tools_raw = fv("tools")
    inherits = tools_raw is None or tools_raw.strip() in ("*", "all")
    tools = set() if inherits else {x.strip() for x in tools_raw.split(",")}

    if not name:
        E("нет обязательного name")
    if not fv("description"):
        E("нет обязательного description")

    if name and name != os.path.basename(n)[:-3]:
        E("frontmatter name=%r не совпадает с именем файла" % name)

    for tool, pat in DUTY:
        if inherits or tool in tools:
            continue
        m = re.search(pat, body_own)
        if m:
            E("нужен %s (обязанность: %r), но во frontmatter его нет" % (tool, m.group(0)[:44]))

    for capname, needpat, havepat in CAPS:
        m = re.search(needpat, body_own)
        if m and not inherits and not re.search(havepat, tools_raw or ""):
            E("метод требует %s (%r), инструмента нет — будет имитация" % (capname, m.group(0)[:40]))

    if "_shared/input_gate.md" not in body:
        E("нет блока валидации входа")
    if "_shared/definition_of_done.md" not in body:
        E("нет Definition of Done")

    # Образ готового (введено 2026-08-31). Шаблон ТЗ brief-architect обязан
    # нести секцию «Образ готового» и все четыре её поля. Разбор 48 доработок одного клиентского продукта:
    # 25% переделок закрывались одним вопросом на входе, и это ровно эти поля. Без секции
    # расшифровка снова фиксирует предмет работы и не фиксирует образ результата — а проверить
    # подставленный образ изнутри работы нельзя, он вскрывается уже у получателя.
    # Проверка узкая по имени карточки намеренно: гейт стоит в одной точке, дублировать
    # требование в остальные 39 карточек — тот же дубль, что ловит harness-optimizer.
    if name == "brief-architect":
        if not re.search(r"^##\s*Образ готового", body, re.M):
            E("шаблон ТЗ без секции «Образ готового» — корзина A (25% переделок) не закрыта")
        else:
            miss = [k for k in ("Образец:", "Уровень готовности:", "Чем проверим:", "устройство")
                    if k not in body]
            if miss:
                E("«Образ готового» без обязательных полей: %s" % ", ".join(miss))

    # согласованность статусов: что предписывают блоки против объявленного enum
    # Перечислением считаем только строку с «|». Одиночное «status: ok» в примере
    # возврата — конкретное значение, а не объявленный enum: первая редакция проверки
    # принимала его за enum и давала ложную ошибку в восьми карточках.
    m = re.search(r"^\s*status:\s*(ok\s*\|[^\n]*)$", body, re.M)
    if m:
        enum = m.group(1)
        for st in ("partial", "error"):
            if re.search(r"статус\s+`%s`|`%s`, не `ok`|status: %s" % (st, st, st), body) and st not in enum:
                E("блоки предписывают статус %r, но объявленный enum его не содержит: %r"
                  % (st, enum[:46]))

    # metadata.type — только из закрытого списка канона.
    # Введено 2026-08-22: 36 карточек из 40 печатали тип вне enum'а, и это не ловилось ничем —
    # судьи находили каждый раз заново, вручную, и каждый раз это считалось новой находкой.
    # Оказалось, брак был не в карточках, а в устаревшем каноне: enum писался под ростер
    # из одиннадцати агентов. Канон расширен, проверка поставлена, чтобы не разъехалось снова.
    for m in re.finditer(r"^(\s*)metadata:\s*$", body, re.M):
        for ln in body[m.end():m.end() + 700].split("\n")[1:12]:
            mm = re.match(r"\s*type:\s*([a-z][a-z-]{2,30})\s*$", ln)
            if mm and CANON_META and mm.group(1) not in CANON_META:
                E("metadata.type вне канона communication_contract: %r" % mm.group(1))

    for r in sorted(set(re.findall(r"\b([a-z][a-z0-9]+(?:-[a-z0-9]+){1,3})\b", body_own))):
        if r.endswith(SUFFIX) and r not in KNOWN and r not in ("sub-agent", "multi-agent"):
            W("упомянут агент, которого нет: %s" % r)

    for m in INVENTORY.finditer(body_own):
        W("зашитый инвентарный факт: %r — брать в рантайме" % m.group(0)[:40])

    d = fv("description")
    if d and len(d) < 120:
        W("description короче 120 символов — оркестратору нечем отличить агента")

# --- хуки: кириллица в .ps1 без BOM = мёртвый хук ------------------------------
# Введено 2026-08-31. PowerShell 5.1 читает .ps1 без BOM в кодировке
# системы, и кириллица превращается в мусор — файл перестаёт парситься целиком.
# Цена уже заплачена дважды: risk-guard.ps1 был мёртв «on arrival» по этой причине,
# а sync-stack.ps1 умер 2026-08-21 и унёс с собой мост ноут→сервер на 9 дней — 11 файлов
# стека, включая правки протокола, физически не доехали до сервера. Отказ молчаливый
# в обе стороны: хук не жалуется, а Stop-хук печатает
# «сессия синхронизирована», потому что синк рабочих папок и синк стека — разные скрипты.
# Проверка машинно-независима: BOM и кириллица видны без PowerShell, поэтому правило
# одинаково работает на ноуте и на сервере моста.
HOOKS = os.path.join(STACK, "hooks")
if os.path.isdir(HOOKS):
    for hp in sorted(glob.glob(os.path.join(HOOKS, "*.ps1"))):
        hn = "hooks/" + os.path.basename(hp)
        with open(hp, "rb") as fh:
            head = fh.read(3)
        raw = open(hp, encoding="utf-8", errors="replace").read()
        cyr = len(re.findall(r"[А-Яа-яЁё]", raw))
        if cyr and head != b"\xef\xbb\xbf":
            errors[hn].append(
                "кириллица (%d симв.) в .ps1 БЕЗ BOM — PowerShell 5.1 не распарсит, хук мёртв "
                "и молчит: убрать кириллицу или пересохранить UTF-8 с BOM" % cyr)
        # PreToolUse-хук обязан читать stdin: именно туда Claude Code кладёт payload.
        # risk-guard.ps1 45 дней читал только $args[0] и возвращал exit 0 на каждой команде.
        # Комментарии вырезаются перед проверкой: первая редакция правила искала подстроку
        # по всему файлу и зеленела на упоминании «[Console]::In» ВНУТРИ комментария —
        # мутант с вырезанным вызовом её не покраснил. Проверка, не краснеющая на
        # подсаженном дефекте, не проверяет ничего.
        # Способов прочитать stdin в PowerShell несколько, и все законны:
        # [Console]::In.ReadToEnd() (secret-guard), OpenStandardInput + StreamReader
        # (entry-file-guard — так сделано намеренно, чтобы кириллические пути не портились
        # консольной кодовой страницей cp866), автоматическая $input. Первая редакция
        # правила требовала буквально «[Console]::In» и дала ложную ошибку на здоровом
        # entry-file-guard — правило-сторож, кричащее на исправный файл, приучает
        # игнорировать сторожа ровно так же, как молчащий.
        code = re.sub(r"(?m)^\s*#.*$", "", raw)
        reads_stdin = any(s in code for s in
                          ("Console]::In", "OpenStandardInput", "$input"))
        if "'run-guard.ps1'" in code and os.path.isfile(os.path.join(HOOKS, 'run-guard.ps1')):
            runner = open(os.path.join(HOOKS, 'run-guard.ps1'), encoding='utf-8-sig').read()
            runner = re.sub(r'(?m)^\s*#.*$', '', runner)
            reads_stdin = 'OpenStandardInput' in runner
        if os.path.basename(hp).endswith("-guard.ps1") and not reads_stdin:
            errors[hn].append(
                "хук-сторож не читает stdin ([Console]::In) — payload Claude Code до него "
                "не доходит, сторож пропустит всё")

ne = sum(len(v) for v in errors.values())
nw = sum(len(v) for v in warns.values())

for n in sorted(set(list(errors) + list(warns))):
    if not errors[n] and QUIET:
        continue
    print("\n%s" % n)
    for e in errors[n]:
        print("   ОШИБКА  %s" % e)
    if not QUIET:
        seen = set()
        for w in warns[n]:
            if w[:50] in seen:
                continue
            seen.add(w[:50])
            print("   пред.   %s" % w)

print("\n%s" % ("=" * 62))
print("проверено файлов: %d | ОШИБОК: %d | предупреждений: %d" % (len(files), ne, nw))

if ne:
    print("Файл с ОШИБКОЙ не должен уезжать в мост — агент выдаст правдоподобный результат")
sys.exit(1 if ne else 0)
