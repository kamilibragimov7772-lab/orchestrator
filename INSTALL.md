# Установка оркестраторского стека в свой Claude Code

Читай целиком до первого копирования файла — раздел 5 про конфликты с уже существующей системой агентов дороже всего пропустить.

## 0. Коротко (если уверен)

1. Бэкап своего `~/.claude/`.
2. Проверь конфликты имён и хуков (раздел 5).
3. Скопируй `agents/`, `commands/`, `skills/`, `tools/`, `hooks/`, `githooks/`, корневые `_*.md` в `~/.claude/`.
4. Смёржь блок `hooks` из `settings.example.json` в свой `settings.json` — добавить в массивы, не перезаписать.
5. Перенеси нужные разделы `CLAUDE.md` пакета в свой `~/.claude/CLAUDE.md`.
6. Заполни плейсхолдеры (раздел 4), заведи базу знаний.
7. Не Windows — перепиши хуки (раздел 6) или работай без них.
8. Проверка (раздел 7), потом `EVAL_PROMPT.md`.

## 1. Требования

- **Claude Code** (CLI) с субагентами (`~/.claude/agents/`), slash-командами, скилами и хуками.
- **Windows PowerShell 5.1** — для хуков `hooks/*.ps1` и `tools/acceptance-gate/acceptance-gate.ps1`. Хуки написаны ASCII-only намеренно: PowerShell 5.1 ломает кириллицу в `.ps1` без BOM. Если правишь `.ps1` с русскими строками — сохраняй UTF-8 с BOM.
- **macOS / Linux** — стек работает без хуков. Linux-вариантов хуков в пакете нет; `githooks/pre-commit` — POSIX sh, работает везде.
- **Python 3** — для `tools/`: `agent-lint.py`, `gotovo-counter.py`, `acceptance-gate/checks.py`, `repo-inventory/inventory.py`, `skills/geo-lead-parser/scripts/merge_normalize.py` — только стандартная библиотека. Вызов на Windows `py -3`, на Linux `python3`; `githooks/pre-commit` сам ищет сначала `py`, потом `python3`.
- **Отдельно и по желанию:** `tools/silero-tts` — torch, soundfile и модель `v4_ru.pt`; `tools/kinetic-promo` — Node, Playwright, ffmpeg; site-build — Node/npm (Astro 5, Tailwind), Lighthouse, axe-core / Pa11y; четыре карточки объявляют в `tools:` инструменты MCP Playwright и Figma.
- **База знаний** — любая папка с markdown. Стек называет её `<VAULT_ROOT>` и `~/vault` (это один каталог: второе — симлинк на первое). Без неё половина агентов не имеет места для вывода, а `knowledge-curator`, `retro-analyst`, `export-session` и приёмка не имеют входа.
- **Модели в frontmatter карточек.** Поле `model:` в карточках — `opus`, `sonnet`, в четырёх карточках `fable`. Если у твоего аккаунта нет модели с таким именем — поправь `model:` на доступную, иначе Task tool вернёт ошибку.

## 2. Куда что ложится

```text
~/.claude/
├── CLAUDE.md                     ← НЕ копировать поверх своего: мёржить разделы (раздел 3, шаг 5)
├── settings.json                 ← смёржить хуки из settings.example.json
├── _orchestr_protocol.md         ← ядро протокола (v2.16.0)
├── _orchestr_lazy.md             ← lazy-разделы
├── _orchestr_site_build.md       ← подреестр site-build
├── _gotovo_canon.md              ← канон готовности продукта
├── _project_entry_canon.md       ← канон входного файла проекта
├── _methodology_discipline.md    ← методологическая дисциплина
├── _video_quality_rubric.md      ← рубрика качества видео
├── _public_apis.md               ← карта бесплатных HTTP-API
├── _ECC_inspirations.md          ← журнал заимствований
├── EVAL_PROMPT.md                ← промпт проверки работоспособности (полный прогон читает его отсюда)
├── agents/                       ← 41 карточка + _shared/ (10 файлов)
├── commands/                     ← 10 slash-команд
├── skills/                       ← 4 скила (oprosi-menya, arch-report, video-montage, geo-lead-parser)
├── tools/                        ← 6 инструментов
├── hooks/                        ← 5 .ps1 + 1 .vbs
├── githooks/pre-commit           ← линтер карточек на коммит (core.hooksPath=githooks)
├── .gitignore, .gitattributes    ← если держишь ~/.claude под git (мост между машинами это предполагает)
└── vault -> <VAULT_ROOT>         ← симлинк на базу знаний (или замени ~/vault в файлах на свой путь)
```

`~/.claude/` — стандартный путь конфигурации Claude Code, его менять не нужно. Для tools каталог стека переопределяется переменной `CLAUDE_HOME`, корень базы знаний — `VAULT_ROOT`.

## 3. Установка по шагам

**Шаг 1 — бэкап.**
```bash
cp -r ~/.claude ~/.claude.backup-$(date +%F)
```

**Шаг 2 — конфликты (раздел 5). Не пропускай.**

**Шаг 3 — копируй.** Из пакета в `~/.claude/`: `agents/` (вместе с `_shared/`), `commands/`, `skills/`, `tools/`, `hooks/`, `githooks/`, корневые `_orchestr_*.md` и `_*_canon.md` / `_methodology_discipline.md` / `_video_quality_rubric.md` / `_public_apis.md` / `_ECC_inspirations.md`, `EVAL_PROMPT.md` (промпт полной проверки ссылается на `~/.claude/EVAL_PROMPT.md`), `.gitattributes`. `.gitignore` — если ведёшь `~/.claude` под git.

**Шаг 4 — смёржь `settings.json`.** В `settings.example.json` три группы хуков:
- `PreToolUse` на `Write|Edit|Bash` → `secret-guard.ps1`; на `Bash` → `risk-guard.ps1`;
- `Stop` → `entry-file-guard.ps1`, `export-session.ps1` (async), `sync-stack.ps1` (async).

Команды хуков используют `$HOME` при `"shell": "powershell"` — имя пользователя в путях не нужно. **Если у тебя уже есть хуки `Stop` или `PreToolUse` — добавь записи в существующие массивы.** Копирование файла целиком снесёт твои хуки.

Stop-хук приёмки (`tools/acceptance-gate/acceptance-gate.ps1`) в `settings.example.json` не входит — регистрируется отдельно по инструкции в `tools/acceptance-gate/README.md`. Ему нужен `claude` в PATH: он ищет в `<VAULT_ROOT>/_orchestr/_ACTIVE/` прогон со `status: done` без секции `## Приёмка` и запускает приёмку фоном, режим report-only.

**Шаг 5 — `CLAUDE.md`.** Файл в пакете — глобальный `~/.claude/CLAUDE.md` автора, обезличенный. Не копируй поверх своего: возьми разделы, без которых стек не работает — «Оркестраторский режим (lazy-load)» (триггер `/orchestr` и слово «оркестр*»), «Правило владения субагентами», «Допрос по задаче», «Что такое законченный продукт», «Методологическая дисциплина», «Правило №0.1: у каждого проекта — входной файл» (его исполняет `entry-file-guard`). Раздел «Сервер: порты» — только если у тебя есть сервер.

**Шаг 6 — плейсхолдеры (раздел 4).**

**Шаг 7 — база знаний.** Создай папку, положи в неё `CLAUDE.md` с картой разделов (стек читает его первым при задаче по проекту) и каталоги, на которые опирается протокол: `_orchestr/_ACTIVE/`, `_orchestr/_ARCHIVE/`, `_orchestr/00_runs_index.md`, `_orchestr/_AGENT_USAGE.md`, `_orchestr/_CONFIDENTIAL_TOPICS.md` (реестр тем, которые агенты не выносят наружу; можно пустой список — без файла `knowledge-curator` и `competitor-intel` эскалируют на первом же прогоне), `08-Работа-Claude/`, `11-Decisions-Log/`. Сделай симлинк `~/vault` на неё (Windows: `mklink /D %USERPROFILE%\vault <путь>`, Linux: `ln -s <путь> ~/vault`) и задай `VAULT_ROOT` в окружении.

**Шаг 8 — git для `~/.claude` (по желанию).** Мост между машинами и pre-commit-линтер предполагают, что `~/.claude` — репозиторий:
```bash
cd ~/.claude && git init && git config core.hooksPath githooks
```
Remote для `sync-stack.ps1` — bare-репозиторий на твоём сервере, см. шапку скрипта.

**Шаг 9 — не Windows → раздел 6. Шаг 10 — проверка → раздел 7.**

## 4. Плейсхолдеры — что заменить и где

Найти все разом: `grep -rhoE '<[A-Za-z_][A-Za-z0-9_-]*>' ~/.claude --include=*.md --include=*.ps1 | sort | uniq -c | sort -rn` (HTML-теги в выдаче игнорируй). Найти файлы по одному плейсхолдеру: `grep -rlF '<VAULT_ROOT>' ~/.claude`.

| Плейсхолдер | Чем заменить | Обязательно? |
|---|---|---|
| `<VAULT_ROOT>`, `~/vault` | Путь к базе знаний | **Да** — на нём `knowledge-curator`, `brief-architect`, `retro-analyst`, run-логи, приёмка, `export-session` |
| `<HOME>` | Домашний каталог | Да, где встречается в путях |
| `<VAULT>`, `<DESK>` | Сокращения внутри одной карточки — `retro-analyst` (таблица в её шапке): `~/vault` и `<HOME>/Рабочий стол/_Claude_Deliverables/` | Нет — разворачиваются из `<VAULT_ROOT>` и `<HOME>` |
| `<AUTHOR_PROFILE_DIR>` | Папка профиля автора (лингвистический отпечаток, корпус цитат, промпт «пиши как я») | Если используешь `ghostwriter` / `voice-checker`; иначе `voice-checker` честно вернёт `missing_input` |
| `<PERSONA_LIBRARY_DIR>` | Библиотека персоны для `interesting-narrator` | Если нужен narrator в полном режиме |
| `<own-brand>` | Slug своего бренда | Если `document-compiler` собирает документы под свой бренд |
| `<server>`, `<user>`, `<path-to-bare-repo>`, `<account>` | Свой сервер, учётка, bare-репозиторий | Только для моста между машинами и handoff |
| `<port>` | Порт локального превью сайта | Только для `visual-regression-auditor` |
| `<email>` | Почта для алертов мониторинга | Только для `deploy-engineer` |
| `@<your_bot>` | Свой Telegram-бот | Только для доставки роликов из `kinetic-promo` |
| `<project-folder-1>`, `<project-folder-2>` | Абсолютные пути рабочих папок проектов — прямо в массиве `$projectFolders` внутри `hooks/export-session.ps1`; строки в угловых скобках хук пропускает | Если нужно зеркало папок в базу знаний |
| `<home-project-dir>`, `<vault-project-dir>`, `<project-key>` | Имя папки в `~/.claude/projects/` — Claude Code кодирует путь каталога в имя; смотри `ls ~/.claude/projects/` | Для `knowledge-curator` (путь к `MEMORY.md`) |
| `<клиент>`, `<проект>`, `<город>` | Примеры в текстах карточек | Нет — можно оставить |
| `VAULT_ROOT`, `CLAUDE_HOME`, `SILERO_MODEL` | Переменные окружения для tools и хуков | `VAULT_ROOT` — да, если база не в `~/vault` |

## 5. Если у тебя уже есть своя система агентов

### 5.1 Имена агентов и команд
```bash
ls ~/.claude/agents/      # совпадения по имени файла?
ls ~/.claude/commands/    # orchestr.md, retro.md, checkpoint.md, priyomka.md заняты?
```
Совпадение имени → копирование перезапишет твою карточку. Особо проверь generic-имена, частые в чужих стеках: `code-reviewer`, `security-auditor`, `seo-auditor`, `performance-auditor`, `accessibility-auditor`, `report-designer`. Переименуй свои заранее или выбери, чью карточку оставить; roster в `_orchestr_protocol.md` и `_orchestr_site_build.md` ссылается на имена из пакета.

### 5.2 Хуки — самое опасное место
- `secret-guard` и `risk-guard` висят на **каждом** `Bash` (secret-guard — ещё на `Write|Edit`). Если у тебя там уже стоит хук — сработают оба; проверь, что не спорят по блокировке. `risk-guard` блокирует (exit 2) необратимые и наружные действия по закрытому списку и пишет причину в stderr и `~/.claude/risk-guard.log`.
- Оба стража fail-open: внутренняя ошибка → exit 0 и запись в лог. Страж, который ломает сессию, отключают за день.
- Слепое копирование `settings.json` **снесёт твои `Stop`/`PreToolUse`**. Только мёрж массивов.

### 5.3 `CLAUDE.md` и стиль работы
- Правило владения меняет поведение главной сессии: вне `/orchestr` и slash-обёрток она перестаёт звать субагентов и предлагает команду. Если ты привык дёргать агентов из main session напрямую — это заметишь сразу.
- Протокол грузится только по триггеру (`/orchestr`, «оркестр*» в начале сообщения). Если это слово у тебя занято под своё — поменяй триггер в `commands/orchestr.md` и в разделе `CLAUDE.md`.
- Методологическая дисциплина требует от каждого содержательного артефакта секцию «Методологическая опора» с именованным фреймворком и источниками. Если тебе это не нужно — не переноси раздел, но тогда часть карточек будет ссылаться на правило, которого нет.

### 5.4 Зависимость от базы знаний
`knowledge-curator`, `brief-architect`, `retro-analyst`, `acceptance-gate`, `export-session`, run-логи оркестратора — все пишут и читают `<VAULT_ROOT>`. Нет базы → эти звенья возвращают ошибки путей. Либо заведи папку (шаг 7), либо не используй эти звенья.

### 5.5 Site-build pipeline
19 агентов заточены под Astro 5 + Tailwind + Lighthouse / axe-core / npm. Строишь не на этом — это шаблон, адаптируй карточки `astro-engineer`, `code-reviewer`, аудиторов. Политика ревью по умолчанию — один проход автора без ревьюера; ревьюеры включаются словами «с проверкой» в брифе.

### 5.6 MCP и внешние инструменты
Карточки с явным списком `tools:` MCP не видят, кроме тех, где инструменты MCP перечислены поимённо (`visual-regression-auditor`, `visual-designer`, `accessibility-auditor`, `visual-design-auditor` — Playwright и Figma). Нет сервера → карточка работает в урезанном режиме и обязана это пометить. Не блокер для ядра.

**Вывод по конфликтам:** ядро — протокол, `brief-architect`, research / decision / synthesis / task-author, meta-агенты, приёмка — переносится чисто. Трения — в хуках (мёрж обязателен), generic-именах, зависимости от базы знаний и поле `model:`. Site-build и личные агенты (`ghostwriter`, `voice-checker`, `interesting-narrator`) — шаблоны под настройку.

## 6. Если ты не на Windows

Без хуков стек работает; теряется автоматика: secret-guard, risk-guard, обязательный `CLAUDE.md` проекта, экспорт сессии и самопочинка индекса, мост между машинами, приёмка на Stop. Всё это можно соблюдать руками (`/priyomka` после закрытия прогона, `agent-lint.py` перед коммитом).

Что портировать, если нужно:
- `secret-guard.ps1` — читает JSON события из stdin, ищет паттерны токенов (`sk-ant-…`, `gh[pousr]_…`, `AKIA…` и др.), `exit 2` для блокировки, иначе `exit 0`, любая ошибка → `exit 0`.
- `risk-guard.ps1` — то же для закрытого списка необратимых команд; причина в stderr.
- `entry-file-guard.ps1` — если в сессии менялись исходники проекта, у проекта обязан быть `CLAUDE.md`, тронутый в этой сессии; иначе сообщение в stdout (JSON) с требованием создать/обновить.
- `export-session.ps1` — копия транскрипта в `<VAULT_ROOT>/08-Работа-Claude/_Логи/`, зеркало рабочих папок (`robocopy /MIR` → `rsync -a --delete`), дописывание пропущенных прогонов в `00_runs_index.md`.
- `sync-stack.ps1` — `git add → commit → pull --rebase --autostash → push` в bare-репозиторий; сеть недоступна → лог и `exit 0`. Серверная сторона в оригинале — тот же скрипт на sh по cron `*/10`.
- `acceptance-gate.ps1` — найти в `_ACTIVE/` прогон со `status: done` без `## Приёмка`, запустить `claude` с промптом приёмки, `exit 0` всегда.
- В `settings.json` заменить `"shell": "powershell"` и команды `powershell -File …` на свой интерпретатор.

`checks.py`, `agent-lint.py`, `gotovo-counter.py`, `inventory.py` — кроссплатформенные, стандартная библиотека.

## 7. Проверка установки

1. Состав: `ls ~/.claude/agents/*.md | wc -l` → 41; `ls ~/.claude/commands/*.md | wc -l` → 10; `ls -d ~/.claude/skills/*/ | wc -l` → 4.
2. Линтер: `py -3 ~/.claude/tools/agent-lint.py --quiet` (Linux — `python3`) → «ОШИБОК: 0». Ошибки — это плейсхолдер в пути или ссылка на файл, которого у тебя нет; чини по строкам выдачи.
   Режим `--selftest` в свежей установке **не пройдёт** — он ищет бэкапы карточек `*.md.bak-9of10-20260821`, которых в пакете нет. Мутационную проверку сделай руками: скопируй любую карточку во временный файл, убери `Bash` из `tools:`, оставив в теле «посчитай …» — `agent-lint.py <файл>` обязан выдать ошибку. Не выдал — линтер не проверяет, разбирайся до запуска агентов.
3. Приёмка без модели: `python3 ~/.claude/tools/acceptance-gate/checks.py <путь-к-любому-run-логу>`. На несуществующем пути — код 2, не трассировка; на прогоне со `status: planning` — код 4.
4. Windows: `$env:ACCEPTANCE_GATE_DRYRUN=1; '{}' | powershell -NoProfile -File "$HOME\.claude\tools\acceptance-gate\acceptance-gate.ps1"` → «DRY-RUN: подходящего прогона нет».
5. Живой прогон: `/orchestr тестовая задача: оцени, стоит ли небольшой кофейне запускать доставку (все данные условные)`. Ожидается: Шаг 0 отчитался строкой, run-лог появился в `<VAULT_ROOT>/_orchestr/_ACTIVE/`, `brief-architect` вернул путь к ТЗ и вопросы готовыми вариантами. Ошибка пути = незаполненный плейсхолдер (раздел 4).
6. Полная проверка каждой карточки — `EVAL_PROMPT.md`: быстрый прогон на 7 агентов и таблица по всем 41.
7. Windows: заверши сессию — хуки должны отработать без ошибок: `~/.claude/entry-file-guard.log`, `risk-guard.log`, `sync-stack.log`, `<VAULT_ROOT>/08-Работа-Claude/_Логи/_hook.log`.
8. По желанию — `/harness-audit`: `harness-optimizer` проверит стек на мёртвые ссылки, сирот и расхождения roster с фактическим списком карточек.

## 8. Что отключить, если не нужно

| Что | Как | Когда |
|---|---|---|
| `sync-stack.ps1` + `sync-stack-silent.vbs` | Убрать из `Stop`; задачу планировщика не создавать | Нет второй машины |
| `entry-file-guard.ps1` | Убрать из `Stop` | Не хочешь обязательный `CLAUDE.md` в каждом проекте |
| `export-session.ps1` | Убрать из `Stop` | Нет базы знаний или не нужен экспорт транскриптов |
| Stop-хук приёмки | Разово — файл `~/.claude/.acceptance-gate-off`; совсем — не регистрировать | Приёмку зовёшь руками через `/priyomka` |
| `risk-guard.ps1` | Убрать из `PreToolUse` | Без причины не отключай: он единственный, кто ловит `rm -rf` под `bypassPermissions` |
| Site-build: 19 карточек, `_orchestr_site_build.md`, `agents/_shared/site-build/` | Не копировать; убрать ссылку в roster протокола, иначе `harness-optimizer` отметит мёртвые пути | Не строишь сайты |
| `skills/video-montage`, `skills/geo-lead-parser`, `tools/kinetic-promo`, `tools/silero-tts` | Не копировать; убрать строки из раздела «Скилы» roster | Не делаешь видео / не собираешь базы компаний |
| `commands/openclaw-task.md` | Не копировать | Нет внешнего исполнителя OpenClaw |

## 9. Как внедрять частично

- **Только оркестрация:** `_orchestr_protocol.md` + `commands/orchestr.md` + `commands/priyomka.md` + `brief-architect`, `strategy-researcher`, `decision-analyst`, `synthesizer`, `task-author`, `knowledge-curator`, `acceptance-gate` + `agents/_shared/` + `tools/acceptance-gate/` + `tools/agent-lint.py`.
- **Только субагенты:** нужные `agents/*.md` с `agents/_shared/`, вызов через Task — без протокола. Правило владения тогда не переноси.
- **Только идея enforcement:** Шаг 0 протокола + валидатор закрытия Шага 9 + `tools/acceptance-gate/checks.py` как образец «всё, что проверяется машиной, проверяет машина».
- **Только каноны:** `_gotovo_canon.md`, `_project_entry_canon.md`, `_methodology_discipline.md` — читаются без остального стека.

---
Автор — см. [AUTHORS.md](AUTHORS.md). Версия протокола 2.16.0, экспорт 2026-09-06.
