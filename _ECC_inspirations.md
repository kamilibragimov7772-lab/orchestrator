# ECC — извлечённые концепции (журнал)

**Источник:** [affaan-m/everything-claude-code](https://github.com/affaan-m/everything-claude-code) v2.0.0-rc.1 (Apr 2026), 192k stars, 30k forks, MIT, global rank #36.

**Дата изучения:** 2026-05-25
**Решение пользователя:** не ставить целиком, cherry-pick концепций.

Этот файл — журнал того, что взято из ECC, как адаптировано к стеку пользователя, и что отвергнуто. Не запускается, не подгружается автоматически. Открывать вручную при ретроспективе harness.

---

## Что взято и портировано

### 1. silent-failure-hunter (агент)
- **Источник:** ECC `agents/silent-failure-hunter` — поиск тихих ошибок
- **Где у меня:** `~/.claude/agents/silent-failure-hunter.md`
- **Адаптация:** добавлен чек-лист категории D (agent-specific) — silent failures именно в оркестраторе и subagents пользователя (run-лог done при пустом артефакте, council mode без chairman, knowledge-curator не обновил MEMORY и т.д.). Тулы только Read/Glob/Grep/Bash — без правок.
- **Применение:** запускать после долгих run'ов, после OpenClaw тасков, после site-build пайплайна

### 2. harness-optimizer (агент) + /harness-audit (команда)
- **Источник:** ECC `commands/harness-audit` + `skills/agent-architecture-audit`
- **Где у меня:** `~/.claude/agents/harness-optimizer.md` + `~/.claude/commands/harness-audit.md`
- **Адаптация:** scope привязан к МОЕМУ стеку (38 agents, 5+2 commands, _orchestr_protocol.md, MEMORY.md, hooks, vault/CLAUDE.md), а не к generic Claude Code инсталляции. Категории классификации KEEP/RENAME/MERGE/RETIRE/FIX — мои, не ECC.
- **Применение:** раз в 2-4 недели или после крупных добавлений

### 3. agent-eval (агент)
- **Источник:** ECC `skills/agent-eval` + `skills/ai-regression-testing`
- **Где у меня:** `~/.claude/agents/agent-eval.md`
- **Адаптация:** 5-осевой rubric с осями специфично под пользователя — «Ценность для пользователя» как пятая ось (signal-to-noise для владельца стека). Вердикты KEEP/TUNE/REWRITE/RETIRE.
- **Применение:** для каждого доменного агента раз в квартал, после серии run'ов

### 4. /checkpoint (команда)
- **Источник:** ECC `commands/checkpoint` + `commands/save-session`
- **Где у меня:** `~/.claude/commands/checkpoint.md`
- **Адаптация:** save в decisions-log vault, не в отдельную папку sessions. Не закрывает сессию — middle-snap для возврата/передачи в другую вкладку.
- **Применение:** при длинных задачах 2+ часа, перед созвонами, при приближении к лимиту контекста

---

## Что рассмотрено и отвергнуто

### Не подходит мне:

- **61 language-specific reviewer** (python-reviewer, rust-reviewer, typescript-reviewer, go-reviewer, kotlin-reviewer, swift-reviewer и т.д.) — я не пишу production-код на этих языках. Generic code-reviewer (уже есть в моём стеке для site-build) покрывает Astro/TS, чего хватает.

- **Все language-build-resolver** (cpp-build-resolver, dart-build-resolver, go-build-resolver, java/kotlin/swift/rust/django/pytorch...) — не моя поверхность.

- **76 команд из ECC** — `/feature-dev`, `/test-coverage`, `/refactor-clean`, `/promote`, `/jira`, `/pm2`, `/multi-backend`, `/multi-frontend` — это рабочий процесс classical dev-команды, не оператора стратегического слоя. Не нужны.

- **AgentShield (security-scanner pre-commit)** — у меня нет production-кода в публичном репозитории, который требует автоматического security-scan. Если появится production-код в open-source — пересмотреть.

- **Hookify** (4 команды) — отдельная система управления hooks. У меня настроен Stop-хук руками (`export-session.ps1`), своя система не нужна.

- **Loop-operator / autonomous-loops** — у меня есть нативный skill `/loop`, делает то же.

- **Skills `continuous-learning v1/v2`** — extract patterns mid-work. У меня этот слой реализован через `auto memory` в глобальном CLAUDE.md (MEMORY.md + per-fact файлы). Идеи extract-rules в моём стеке уже работают.

- **`council` skill** — у меня в `decision-analyst` есть встроенный council mode (с 2026-05-04, A/B-тест до 60 дней). Не дублировать.

- **`deep-research` skill** — у меня есть `strategy-researcher` агент. Не дублировать.

- **`agentic-os`, `enterprise-agent-ops`, `marketing-agent`, `chief-of-staff` агенты** — масштаб «команда из 10 человек». Не масштабируется в контекст одного оператора.

### Концепции которые понравились, но взять нельзя:

- **`/cost-report`** — отчёт о расходах токенов. У меня в оркестраторе есть блок «Бюджеты» (word_target / source_budget / time_budget_min). Cost в долларах — отдельная история; Claude Code сам отслеживает в `/status`, моих миддл-слоёв не нужно. Если ECC покажет конкретный встраиваемый формат — пересмотреть.

- **`/skill-create` + `skill-health`** — у меня уже есть `example-skills:skill-creator` в marketplace. Дублировать смысла нет.

- **`harmony-os-app-resolver`, `homelab-architect`, `customs-trade-compliance`, `carrier-relationship-management`** — узкие домены, не пересекаются с моими.

---

## Что отложено «на потом»

Если когда-то появится — пересмотреть.

- **Свой Claude Code plugin** — упаковать стек как plugin для распространения внутри команды клиента / OpenClaw. Тогда взять у ECC паттерны `plugin.json`, no-duplicate hooks, rules-distribution-limitation (см. их CLAUDE.md). **Триггер пересмотра:** запрос от клиента на «продайте мне ваш AI-стек».

- **Multi-harness adapter** — портирование моих агентов в Cursor / Codex / OpenCode. Их `dmux-workflows` skill — концепция. **Триггер пересмотра:** если перееду с Claude Code основной IDE.

- **AgentShield-подобный security pre-commit** для кода, который работает с деньгами или ключами. **Триггер:** если такой код выйдет в реальную эксплуатацию (не песочницу) — обязательный pre-commit security audit перед каждой правкой операций/keys.

---

## Принципы из ECC обсуждений, которые я разделяю

(Без портирования кода — только как философия.)

1. **«Skills и rules — разная распределяемость»** — Skills могут быть в plugin, rules должны копироваться руками. У меня тоже: hooks и agents в `~/.claude/`, vault-policy в `vault/CLAUDE.md`. Разные слои.

2. **«No duplicate hooks in plugin.json — Claude Code v2.1+ auto-loads them»** — Anthropic merge моего pattern (один источник истины для hooks). Прикладной вывод: не дублировать инструкции в нескольких CLAUDE.md.

3. **«Harness = система, не tool»** — Claude Code как execution-environment, а не как «AI-помощник». Это уже моя позиция (CLAUDE.md как первый класс гражданина, оркестратор-протокол, vault-policy).

4. **«Continuous learning extracts patterns mid-work»** — реализовано через `auto memory`. Не строить вторую систему.

---

## Анти-паттерны из ECC, которых избегаю

1. **«Всё для всех»** — 246 skills × 12 языков = AGI-каталог. Сначала собираешь, потом тонешь в поддержке. Мой стек = 38 агентов под МОИ домены (клиентские, личный, infra, OpenClaw, vault). Растёт по факту запроса, не по факту «может пригодится».

2. **Duplicate concepts across folders** — у них есть `continuous-learning` и `continuous-learning-v2`, `council` skill параллельно с decision-skills. Знак того, что миграции делаются без удаления старого. У меня — RETIRE через `_archive/`.

3. **Generic naming** — `architect`, `planner`, `chief-of-staff`. У меня — конкретные: `ia-architect`, `design-system-architect`, `brief-architect`. Имя несёт scope.

---

## Эскалация

Если когда-то ECC станет industry-стандартом и Anthropic его поглотит в Claude Code core — пересмотреть всё. На 2026-05-25 — самостоятельный проект одного автора, 4 месяца, статус «бурно растёт, sustainability ещё не доказана».

Перепроверка релевантности: **2026-08-25** (через 3 месяца).
