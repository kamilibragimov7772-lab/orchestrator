# 05_migration-checklist — что меняется в каждом из 11 агентов

> **Перенесено в стек 2026-08-21.** Раньше карточки ссылались на
> `04_Agent-system/02_Communication/migration-checklist.md` — относительный путь без корня, по которому
> агент файл не находил. Оригинал остался в
> `<HOME>/Документы/Claude/Projects/Агентная система/04_Agent-system/` (внешняя зависимость, см. README), здесь рабочая копия.


> Источник: профили из `_RAW_profiles.md` + новые конвенции из `01_dependency-graph.md`, `02_decision-rights.md`, `03_handshake-contract.md`, `04_parallelism-and-overload.md`.
> Эту таблицу применяем на Шаге 3, когда переписываем `~/.claude/agents/<name>.md`.

## Общие правки для ВСЕХ 11 (вписать единым блоком)

В каждый агент дописать **раздел «Communication contract»**, который:

1. Запрещает прямой вызов другого агента — всё через orchestr.
2. Требует получать вход и отдавать выход в YAML-структуре `03_handshake-contract.md`.
3. Требует ставить унифицированный frontmatter в любой создаваемый артефакт.
4. Лимитирует summary в чат: до 3 строк / 350 символов.
5. Запрещает вставлять тело артефакта в ответ.
6. Описывает протокол ошибок (status: error + escalations).

Базовый блок (вставляется в каждый агент-промпт как один и тот же раздел; перед ним сохраняется текущая методологическая часть).

## По агентам

| # | Агент | Решение | Что делаем |
|---|-------|---------|------------|
| 1 | brief-architect | **переписать** | Добавить INPUT/OUTPUT YAML; уточнить, что рекомендация цепочки идёт в `summary.next_agents`, а не в чат прозой. Сохранить лимит «≤2 уточняющих». |
| 2 | knowledge-curator | **переписать (минимально)** | Добавить требование к INPUT: список путей + run_id; в OUTPUT — `index_diff` структурой. Запретить трогать MEMORY других проектов (OpenClaw/<клиент>/system32). |
| 3 | document-compiler | **переписать** | Жёстко зафиксировать: запуск только при `is_final=true` от orchestr. Brandbook-резолвер по project. Кириллица-проверка как обязательный шаг. Конфликты данных → `escalations`, не молча. |
| 4 | strategy-researcher | **переписать (минимально)** | Унифицировать frontmatter; добавить `escalations.type=data_gap` если нет источников <24 мес; формат budget_used строго по контракту. |
| 5 | competitor-intel | **переписать (минимально)** | То же + явная проверка `_CONFIDENTIAL_TOPICS.md` и установка `confidential: true` в frontmatter если попало. |
| 6 | decision-analyst | **переписать (минимально)** | Усилить, что финальное go/no-go — НЕ агент, а пользователь. Conditional-go формализован: список условий в outputs.metadata. |
| 7 | synthesizer | **переписать (минимально)** | Зафиксировать минимум 3 prior_artifacts. Если бюджет standard но запросили full — `escalations` (а не молча сужать). |
| 8 | ghostwriter | **переписать (минимально)** | corpus_used → frontmatter. low_confidence_style как `status: partial` + `escalations`. |
| 9 | task-author | **переписать (минимально)** | Definition of Done — обязательная секция в артефакте. Отрицательный list «Не входит» — обязателен. |
| 10 | site-editor | **переписать** | Жёстко: одна задача = одна правка. Backup перед правкой — обязателен. Если правка может сломать соседнее — `escalations` к пользователю, не делаем. |
| 11 | infra-engineer | **переписать** | needs-user-action как отдельный `status`, не «ошибка». Один симптом = одна гипотеза = один фикс. Список действий пользователя в `outputs.metadata.user_actions`. |

Новых агентов на этом круге **не добавляем**. Если в Шаге 3 после теста выяснится, что нужен, например, «orchestrator-router» или «test-author» — добавляем как Шаг 4.

## Что НЕ меняется

- Имена файлов агентов в `~/.claude/agents/*.md` — сохраняются.
- Модели (opus / sonnet) — сохраняются.
- Methodology discipline (enforced/exempt) — сохраняется.
- Research budget уровни (quick/standard/deep) — сохраняются.
- Алгоритм orchestr из `~/.claude/CLAUDE.md` — без изменений (триггер `/orchestr`, 9 шагов).

## Чек ШАГ-3 готовности (для каждого агента)

```
[ ] промпт перенесён из 01_Custom-агенты/<name>.md в новый текст
[ ] добавлен раздел Communication contract (тот же для всех)
[ ] добавлены примеры INPUT / OUTPUT YAML, специфичные для агента
[ ] frontmatter в шаблонах артефактов унифицирован
[ ] прописана связь decision-rights (что сам / что к orchestr / что к user)
[ ] формат escalations задан явно
[ ] прогнан smoke-тест (один сценарий end-to-end)
[ ] knowledge-curator обновил INDEX.md / MEMORY
```
