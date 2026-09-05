# Orchestrator — оркестраторский стек для Claude Code

**Что это:** оркестраторский режим для Claude Code — главная сессия принимает бриф, расшифровывает его в ТЗ, делегирует специализированным субагентам волнами, проверяет результат воротами и независимой приёмкой, закрывает прогон по валидатору. **Кому:** тем, кто ведёт в Claude Code реальные проекты — ресёрч, стратегия, тексты, сайты, код — и хочет, чтобы «готово» проверялось, а не объявлялось. **Как поставить:** скопировать в `~/.claude/`, смёржить хуки в `settings.json`, заполнить плейсхолдеры — [INSTALL.md](INSTALL.md).

**TL;DR (EN).** Multi-agent orchestration layer for Claude Code: a 9-step orchestrator protocol, 41 subagents (research, competitive intel, decision memos, synthesis, copywriting, a site-build pipeline, engineering, infra, stack self-observation), slash-commands, guard hooks, a deterministic acceptance gate that judges a closed run in a separate context, and an evaluation prompt to verify every agent after install. Everything is Markdown plus small scripts — no framework on top of Claude Code, diffable with git. Written in Russian.

## Что внутри

Числа — по фактическому дереву репозитория, а не из описаний.

| Компонент | Сколько | Что это |
|---|---|---|
| `_orchestr_protocol.md` | 1 · версия 2.16.0 (2026-09-05) | Ядро: Шаг 0 enforcement + алгоритм из 9 шагов, roster, контракт делегирования, триаж возврата, валидатор закрытия, бюджеты, мост между двумя машинами |
| `_orchestr_lazy.md`, `_orchestr_site_build.md` | 2 | Lazy-разделы — грузятся только по триггеру: автотриггер narrator, парный аудит чужого сайта, council mode, чекпоинты длинных прогонов; подреестр site-build (19 агентов, фазы 0–8) |
| `agents/*.md` | 41 | Субагенты по уровням: **3 системных** (brief-architect, knowledge-curator, document-compiler) · **10 ядро** (strategy-researcher, competitor-intel, decision-analyst, synthesizer, ghostwriter, interesting-narrator, task-author, site-editor, infra-engineer, python-build-engineer) · **3 meta** (silent-failure-hunter, harness-optimizer, agent-eval) · **5 on-demand** (report-designer, retro-analyst, voice-checker, b2b-strategy-auditor, visual-design-auditor) · **19 site-build** (site-discoverer → ia-architect → content-strategist → design-system-architect → visual-designer → astro-engineer → аудиторы → final-quality-gate → deploy-engineer, с ревьюером на каждую фазу) · **1 приёмщик** (acceptance-gate — стоит над оркестратором) |
| `agents/_shared/` | 10 | Контракты, общие для всех карточек: `input_gate`, `communication_contract`, `definition_of_done`, `budget_discipline`, `decision_rights`, `handshake_contract`, `migration_checklist` + 3 файла site-build (`critique_format`, `site_quality_definition`, orchestrator-промпт) |
| `commands/*.md` | 10 | `/orchestr`, `/priyomka`, `/oprosi-menya`, `/reviu`, `/retro`, `/harness-audit`, `/checkpoint`, `/session-new`, `/clip-to-vault`, `/openclaw-task` |
| `skills/` | 4 | Свои скилы: `oprosi-menya` (допрос по одному вопросу до готового ТЗ), `arch-report` (архитектурный разбор HTML-отчётом), `video-montage` (вертикальный ролик из папки с клипами), `geo-lead-parser` (база компаний из 2ГИС) |
| `tools/` | 6 | `agent-lint.py` — линтер карточек агентов · `gotovo-counter.py` — счётчик «образа готового» по прогонам · `acceptance-gate/` — детерминированное ядро приёмки `checks.py` + Stop-хук · `repo-inventory/` — срез большого проекта для `/reviu` · `kinetic-promo/` — ролик кинетической типографики из HTML · `silero-tts/` — локальная русская озвучка |
| `hooks/` | 5 `.ps1` + 1 `.vbs` | PreToolUse: `secret-guard` (не даёт записать токен в базу знаний), `risk-guard` (блокирует необратимые и наружные действия). Stop: `entry-file-guard` (у проекта обязан быть свежий `CLAUDE.md`), `export-session` (экспорт транскрипта, зеркало рабочих папок, самопочинка индекса прогонов), `sync-stack` (git-мост между машинами) + тихий запуск моста для планировщика |
| `githooks/pre-commit` | 1 | Линтер карточек на коммит — карточка, которую агент не сможет исполнить, в репозиторий не попадает |
| Каноны | 6 | `_gotovo_canon` (что такое готовый продукт: три уровня, стандарты по классам), `_project_entry_canon` (входной файл проекта), `_methodology_discipline` (опора на именованный фреймворк с источником), `_video_quality_rubric` (семь осей, вето), `_public_apis` (карта бесплатных HTTP-API под задачи), `_ECC_inspirations` (журнал заимствований из everything-claude-code) |
| `CLAUDE.md`, `settings.example.json`, `LICENSE` | 3 | Глобальные инструкции — образец для мёржа в свой `CLAUDE.md`; пример регистрации хуков; MIT |

## Как это работает

Оркестратор — это главная сессия Claude Code по протоколу из девяти шагов плюс нулевой. **Шаг 0** — старт-проверки, привязанные к детерминированному началу, а не к необязательному финалу: подбор зомби-прогонов, сверка индекса с архивом по множествам, реконсиляция бюджетов и хвостов, линт карточек, замер образа готового. Дальше **приём брифа** (маршрут на скил проверяется первым), **run-лог** с frontmatter, **обогащение брифа** в три фазы — контекст из памяти и логов решений, дубль-чек за 7 дней, `brief-architect` разворачивает сырую мысль в ТЗ и задаёт вопросы готовыми вариантами, пользователь выбирает, а не сочиняет. Затем **план волн** (≤5 агентов одновременно, следующая волна не стартует, пока не вернулась предыдущая), **делегирование по единому контракту** из шести полей — путь к ТЗ, run-лог, границы, формат выхода, бюджет, инструкция «верни путь и 1–2 строки summary», **контроль контекста** (чужие артефакты читаются выборочно, head и grep, не целиком), **сборка**, **каталогизация** и **закрытие**: валидатор из семи проверок — каждый путь в `artifacts:` резолвится, статус терминальный и единственный, время с TZ, парные строки на каждую волну, поля `obraz_gotovogo` и `priyomka` заполнены — и только после него прогон уезжает в архив. Приёмку делает `acceptance-gate` отдельным контекстом: он видит ТЗ и артефакты, не видит рассуждений автора, сначала гоняет скрипт, потом судит остаток.

Второй фундамент — **правило владения вызовами**: субагенты вызываются только оркестратором внутри `/orchestr` или явной slash-обёрткой (`/retro`, `/harness-audit`, `/priyomka`, `/openclaw-task`). Главная сессия без `/orchestr` субагентов не дёргает — предлагает команду. Делегирование идёт от потребности, не от шаблона: перед каждым вызовом четыре вопроса (нужен ли специализированный промпт, не дубль ли за 7 дней, атомарная задача или связка, есть ли все входные данные), и дешёвый отказ от агента считается лучше дорогого fan-out. Стек — это agentic workflow поверх штатных механизмов Claude Code: subagents, slash-команды, skills, hooks; промпты карточек — обычный prompt engineering в markdown, без обвязки и без своего рантайма.

## Чем отличается

- **Enforcement на детерминированном старте.** Всё обязательное проверяется в Шаге 0, а не «в конце, если успею». Замер по 259 прогонам: правило, попавшее в валидатор, держится на 76–100%; то же правило текстом в промпте — на 0–39%. Поэтому валидатор закрытия, линтер карточек, счётчик образа готового и хуки — это точки исполнения, а не напоминания.
- **Приёмщик отдельным контекстом.** `acceptance-gate` судит закрытый прогон, не видя, как шла работа; чинит найденное другой агент следующим прогоном. Разделение по образцу OpenHands: verifier судит, чинит другое звено — чинящий проверяющий становится автором, и следующая проверка снова самопроверка. Приёмщик отказывается судить неполный комплект и прогон со `status ≠ done`.
- **Мутационная дисциплина.** Правка стека закрыта не тогда, когда проверка зелёная, а когда она **краснеет на подсаженной копии того же дефекта**. У `agent-lint.py` и `gotovo-counter.py` есть `--selftest`; `python-build-engineer` закрывает этап только тестом, который падает на сломанной модели.
- **Канон образа готового.** Задачу ставят про предмет, а не про результат, и исполнитель молча подставляет свой образ готового. Разбор 48 доработок: 71% предотвратимы — 25% снимались одним вопросом на входе, 46% применением стандарта, который стек знал и не применил. Отсюда `_gotovo_canon.md`, поле `obraz_gotovogo` в run-логе и счётчик, который отсутствие поля считает пропуском.
- **Бюджетная дисциплина как наблюдаемость.** Пресеты quick / standard / deep, effort-scaling по классу задачи, факт токенов переписывается из блока `<usage>` в run-лог в том же ходу, и не скаляром, а разбивкой по типам (`cache_read` — 90% штук и 36% денег; ранжирование агентов по скаляру искажено в 20 раз). Цель — видеть, а не ограничивать.
- **Всё — markdown и короткие скрипты.** Карточка агента, команда, канон, протокол — текстовые файлы, диффятся git'ом, ездят между машинами обычным `pull --rebase`. Хуки — по одному файлу на правило, ASCII-only, fail-open: сломавшийся страж отключат за день, и он перестанет сторожить.

## Быстрый старт

1. Прочитай [INSTALL.md](INSTALL.md) целиком — в первую очередь раздел про конфликты с уже существующими агентами, командами и хуками.
2. Разложи файлы по `~/.claude/`, смёржь блок `hooks` из `settings.example.json` в свой `settings.json` (добавить в массивы, не перезаписать), перенеси нужные разделы из `CLAUDE.md` в свой.
3. Заполни плейсхолдеры (таблица ниже) и заведи базу знаний — папку с markdown, на которую смотрят `<VAULT_ROOT>` и `~/vault`.
4. Запусти `/orchestr <бриф>`. После установки прогони проверку работоспособности — [EVAL_PROMPT.md](EVAL_PROMPT.md): быстрая на 7 агентов и полная по всем 41 карточкам.

## Внешние зависимости (в репозиторий не входят)

Файлы стека ссылаются на них с пометкой «внешняя зависимость, см. README». Без них соответствующая карточка работает в урезанном режиме или возвращает `missing_input` / `tool_unavailable` — это штатное поведение ворот входа, а не поломка.

- **Плагины Anthropic** `docx`, `pptx`, `pdf`, `frontend-design` — их читает `document-compiler` из `~/.claude/plugins/marketplaces/...`. Ставятся из marketplace Claude Code.
- **Вендорные видео-скилы:** `hyperframes` и семейство (`hyperframes-creative`, `hyperframes-animation`, …), `media-use`, `embedded-captions`, `motion-design`, `design-motion-principles`, `figma` — ставятся отдельно с сайтов авторов. Карта маршрутов видео-движков — в roster протокола.
- **`ARCHITECTURE.md`** site-build pipeline — на него ссылаются карточки фаз 0–8; рабочее описание пайплайна есть в `_orchestr_site_build.md` и `agents/_shared/site-build/`, этого достаточно для запуска.
- **`_writing_for_agents.md`** — гайд, как формулировать промпты агентам (указатели вместо пересказа, прополка пустышек). Не публикуется; на него ссылаются `harness-optimizer` и `_project_entry_canon`.
- **`_server_ports.md`** — карта портов твоего сервера. Заведи свою, если у стека есть вторая машина; `infra-engineer` и `CLAUDE.md` требуют читать её перед правкой nginx / ufw / systemd.
- **Linux-варианты хуков** — `hooks/sync-stack.sh` для cron на сервере и Stop-хук приёмки под Linux. В пакете только `.ps1`-версии; логика описана в INSTALL.md, переписывается под свой shell.
- **Доменные скилы** — например, финкалькулятор клиента, на который ссылается `_public_apis.md`. Исключены как клиентские; сделай свой под свою предметную область.
- **Библиотека персоны** для `interesting-narrator` (`<PERSONA_LIBRARY_DIR>`: мастер-промпт персоны, матрица «задача → режим»). Без неё агент работает по описанию режимов в карточке.
- **Профиль автора** для `ghostwriter` и `voice-checker` (`<AUTHOR_PROFILE_DIR>`: лингвистический отпечаток, корпус цитат, промпт «пиши как я»). Без него `voice-checker` возвращает `missing_input`, `ghostwriter` пишет по описанию стиля из `CLAUDE.md`.
- **Форма постановки задачи** («шесть фраз в одно голосовое»), на которую ссылается `CLAUDE.md`, — часть канона готовности; сама форма в пакете не публикуется, правила канона в `_gotovo_canon.md` самодостаточны.
- **Оригиналы** `decision_rights`, `handshake_contract`, `migration_checklist` из внешней папки «Агентная система» — в `agents/_shared/` лежат рабочие копии, оригиналы не нужны.
- **Модель Silero `v4_ru.pt`** для `tools/silero-tts` — скачать с официального релиза (ссылка в `tools/silero-tts/README.md`), путь задать через `SILERO_MODEL`.
- **MCP-серверы и CLI** для части карточек: Playwright и Figma MCP (`visual-regression-auditor`, `visual-designer`, `accessibility-auditor`, `visual-design-auditor`), Lighthouse, axe-core / Pa11y, npm — для аудиторов site-build; Node + Playwright + ffmpeg — для `kinetic-promo`; torch + soundfile — для `silero-tts`.

## Плейсхолдеры

Стек обезличен. Всё, что в угловых скобках, — подставить своё. Полный список в установленном дереве: `grep -rhoE '<[A-Za-z_][A-Za-z0-9_-]*>' ~/.claude --include=*.md --include=*.ps1 | sort | uniq -c | sort -rn`.

| Плейсхолдер | Что подставить | Где встречается |
|---|---|---|
| `<VAULT_ROOT>` | Абсолютный путь к базе знаний — папке с markdown, куда стек пишет артефакты, run-логи, индексы. В файлах стека она же `~/vault` (симлинк на тот же каталог) | `CLAUDE.md`, карточки, команды, tools |
| `<HOME>` | Домашний каталог (`$HOME` / `%USERPROFILE%`) | карточки, `agents/_shared/` |
| `<VAULT>`, `<DESK>` | Сокращения одной карточки, определены в её шапке: `~/vault` и папка деливераблов на рабочем столе — отдельно не подставляются | `retro-analyst` |
| `~/.claude` | Каталог стека; для tools переопределяется переменной `CLAUDE_HOME` | везде |
| `<AUTHOR_PROFILE_DIR>` | Папка профиля автора: лингвистический отпечаток, корпус цитат, промпт «пиши как я» | `CLAUDE.md`, `ghostwriter`, `voice-checker`, `interesting-narrator`, `retro-analyst` |
| `<PERSONA_LIBRARY_DIR>` | Библиотека персоны «Интересный человек» | `interesting-narrator` |
| `<own-brand>` | Slug собственного бренда для брендбук-резолвера | `document-compiler` |
| `<server>`, `<user>`, `<path-to-bare-repo>`, `<account>`, `<port>` | Свой сервер, учётка, bare-репозиторий моста, порты локального превью | протокол (мост, handoff), `hooks/sync-stack.ps1`, `infra-engineer`, `visual-regression-auditor` |
| `<email>` | Почта владельца сайта для алертов мониторинга | `deploy-engineer` |
| `@<your_bot>` | Свой Telegram-бот, если ролики нужно отдавать на телефон | `tools/kinetic-promo/README.md` |
| `<клиент>`, `<проект>`, `<город>` | Подстановки в примерах — заменить на свои или оставить как есть | карточки, каноны |
| `<project-folder-1>`, `<project-folder-2>` | Рабочие папки проектов, которые Stop-хук зеркалит в базу знаний (список прямо в скрипте) | `hooks/export-session.ps1` |
| `<home-project-dir>`, `<vault-project-dir>`, `<project-key>` | Кодировка пути проекта в `~/.claude/projects/` — Claude Code превращает путь каталога в имя папки; посмотри `ls ~/.claude/projects/` | `knowledge-curator`, `_public_apis.md` |
| `VAULT_ROOT`, `CLAUDE_HOME` (переменные окружения) | Корень базы знаний и каталог стека для tools и хуков; умолчания `~/vault` и `~/.claude` | `tools/*`, `hooks/export-session.ps1`, `tools/acceptance-gate/` |
| `SILERO_MODEL` | Путь к модели `v4_ru.pt` | `tools/silero-tts/gen.py` |

## Об авторе

Камиль — маркетолог с 8+ годами практики: консалтинг, переговоры, поиск слабых мест в бизнесе, упаковка решений и внедрение. Руководит направлением AI-автоматизации бизнеса, ведёт свои проекты в рознице и общепите, консультирует производственные и сервисные компании. Этот стек — рабочий инструмент, на котором ежедневно идут реальные проекты: ресёрч, стратегия, тексты, сайты, видео, инженерные расчёты. Ежедневный стек: Claude Code, Claude API, Obsidian, PowerShell, HTML/CSS/React, Python.

Instagram: [@kamil_ibrgmv](https://instagram.com/kamil_ibrgmv) · Telegram: [@kamil_ibrgmv](https://t.me/kamil_ibrgmv)

## Лицензия

MIT — см. [LICENSE](LICENSE). Свободно используй, меняй, адаптируй под свой Claude Code. Просьба при форке, публикации или включении в свой стек сохранять упоминание автора — **@kamil_ibrgmv**.
