# 03_handshake-contract — единый формат передачи

> **Перенесено в стек 2026-08-21.** Раньше карточки ссылались на
> `04_Agent-system/02_Communication/handshake-contract.md` — относительный путь без корня, по которому
> агент файл не находил. Оригинал остался в
> `<HOME>/Документы/Claude/Projects/Агентная система/04_Agent-system/` (внешняя зависимость, см. README), здесь рабочая копия.


> Сейчас формат handoff не нормализован: synthesizer и document-compiler читают всё целиком, что хрупко. Здесь фиксируем единый контракт.

## Принципы

1. Единственный «канал связи» — orchestr ↔ агент.
2. Агент получает на вход **минимум, нужный для работы**, и отдаёт **минимум, нужный orchestr'у для следующего шага**.
3. Тело артефакта в чат не возвращается — никогда.
4. Все артефакты получают унифицированный YAML-frontmatter (см. ниже).
5. Протокол ошибок — явный, отдельный от успеха.

## INPUT-контракт (orchestr → агент)

```yaml
# orchestr передаёт агенту структуру:
run_id: <YYYY-MM-DD-HHMM-slug>             # обязательно
agent: <agent-name>                          # обязательно (для самопроверки агентом)
task:
  brief_path: <abs path к ТЗ/брифу>          # обязательно для домен. агентов
  question: <одна фраза цели>                # обязательно
  scope:
    in: [<список: что покрывать>]
    out: [<список: что НЕ трогать>]
output:
  expected_path: <abs path куда сохранить>   # обязательно
  format: md | docx | pptx | pdf | html
  multi_format: false | [список форматов]    # для document-compiler
budget:                                       # для домен. агентов
  research: quick | standard | deep
  word_target: <int|null>
  source_budget: <int|null>
context:
  project: <slug>                            # <проект> | client:<name> | personal | общий
  brandbook_path: <abs path|null>
  corpus_path: <abs path|null>               # для ghostwriter / task-author
  prior_artifacts: [<abs path>, ...]         # для synthesizer / decision-analyst / document-compiler
  confidential: true | false
deadline: <ISO|null>
notes: <строка|null>                         # любые подсказки от orchestr
```

Обязательность по агентам:

| Агент | task.brief | output.expected | budget | prior_artifacts |
|-------|------------|-----------------|--------|------------------|
| brief-architect | ДА (сырой) | ДА | — | — |
| strategy-researcher | ДА | ДА | ДА | опц. |
| competitor-intel | ДА (имя/URL) | ДА | ДА | опц. |
| decision-analyst | ДА | ДА | ДА | ≥1 рекоменд. |
| synthesizer | ДА (тезис) | ДА | ДА (deep по умолч.) | ≥3 ОБЯЗ. |
| ghostwriter | ДА | ДА | ДА | corpus опц. |
| task-author | ДА | ДА | ДА | опц. |
| site-editor | ДА (+ скрин) | ДА (edit_log) | ДА | опц. |
| document-compiler | список путей в context.prior_artifacts | ДА | — | ДА (≥1) |
| knowledge-curator | список изменений | — | — | ДА (что обновлять) |
| infra-engineer | симптом | ДА (fix_log) | ДА | опц. |

## OUTPUT-контракт (агент → orchestr)

> Формат поля `budget_used` здесь приведён для полноты примера; **владелец формата budget_used —
> `~/.claude/agents/_shared/budget_discipline.md`**. Расходятся — истина там.

```yaml
status: ok | partial | needs-user-action | error
artifact:
  path: <abs path>                            # обязательно для status=ok|partial
  format: md | docx | ...
  size_bytes: <int>
summary: <1-3 строки сухого вывода>           # обязательно
methodology_used: [<список фреймворков>]      # для enforced; "exempt" если нет
budget_used:
  spent_words: <int|null>
  sources: <int|null>
  status: ok | exceeded
open_questions: [<строка>, ...]               # если есть
escalations:                                  # если status != ok
  - to: orchestr | user
    type: budget | data_gap | conflict | scope | breaking_risk | needs_credentials | missing_input | tool_unavailable | other
    detail: <строка>
metadata:                                     # домен-специфика
  type: brief | research | dossier | decision-memo | master-synthesis | ghost-text | task | site-edit | doc-final | infra-runbook
        | critique | discovery | content | engineering | deploy | build-report | narration | visual-report | index-diff | silent-failure-scan
        # Единственный владелец списка — communication_contract.md. Расширен 2026-08-22.
  project: <slug>
  confidential: true | false
  source_run: <run_id>
```

Минимум, который агент ОБЯЗАН вернуть всегда: `status`, `summary`, и при `status in {ok, partial}` — `artifact.path`. Всё остальное — по типу агента.

## Унифицированный frontmatter в каждом артефакте

```yaml
---
type: <см. metadata.type выше>
project: <slug>
created: <ISO>
source_run: <run_id>
agent: <agent-name>
methodology_framework: [<список>] | exempt
confidential: true | false
budget_used: { spent_words: N, sources: M, status: ok|exceeded }
related:                                     # wiki-ссылки на исходники (для synthesizer / document-compiler)
  - "[[path/to/source-1.md]]"
  - "[[path/to/source-2.md]]"
---
```

## Протокол ошибок

```yaml
status: error
summary: <1 строка: что сломалось>
escalations:
  - to: orchestr
    type: budget | data_gap | conflict | scope | breaking_risk | needs_credentials | missing_input | tool_unavailable | other
    detail: <строка>
recovery_hint: <что нужно дать агенту, чтобы он смог завершить>
```

Поведение orchestr при ошибке:
1. Записать в run-лог.
2. Если recoverable → дать недостающее и перезапустить.
3. Если нет → эскалация пользователю; волна не блокируется (другие агенты идут).

## Примеры handoff

### Пример 1 — orchestr вызывает strategy-researcher

```yaml
# INPUT
run_id: YYYY-MM-DD-HHMM-niche-coffee
agent: strategy-researcher
task:
  brief_path: <VAULT_ROOT>/08-Работа-Claude/<session>/00_tz_extracted_niche.md
  question: "Размер ниши спешелти-кофе в <город> и тренды last 24mo"
  scope:
    in: [<город>, <город-2> как бенчмарк]
    out: [международные данные, классический сегмент]
output:
  expected_path: <VAULT_ROOT>/<проект>/research/01_niche_specialty_city.md
  format: md
budget:
  research: standard
  word_target: 1000
  source_budget: 8
context:
  project: <проект>
  prior_artifacts: []
  confidential: false
```

```yaml
# OUTPUT
status: ok
artifact:
  path: <VAULT_ROOT>/<проект>/research/01_niche_specialty_city.md
  format: md
  size_bytes: 14820
summary: |
  Ниша спешелти в <город>: ~12 точек, рост 2024-2025 +18% выручки. 
  Главный драйвер — переток из сетевого кофе у Z-аудитории.
methodology_used: [TAM-SAM-SOM, Porter Five Forces, JTBD]
budget_used: { spent_words: 980, sources: 7, status: ok }
open_questions:
  - "Доля доставки в выручке точек — нет публичных данных"
metadata:
  type: research
  project: <проект>
  confidential: false
  source_run: <run_id>
```

### Пример 2 — orchestr вызывает synthesizer

```yaml
# INPUT
run_id: YYYY-MM-DD-HHMM-niche-coffee
agent: synthesizer
task:
  brief_path: <VAULT_ROOT>/08-Работа-Claude/<session>/00_tz_extracted_niche.md
  question: "MASTER-сводка: стоит ли открывать вторую точку в центре <город>"
  scope:
    in: [рынок, конкуренты, юнит-экономика, риски]
    out: []
output:
  expected_path: <VAULT_ROOT>/<проект>/MASTER_second_point.md
  format: md
budget:
  research: deep
context:
  project: <проект>
  prior_artifacts:
    - <VAULT_ROOT>/<проект>/research/01_niche_specialty_city.md
    - <VAULT_ROOT>/<проект>/atomic-deep-dive/01_COMPETITOR_A_DOSSIER.md
    - <VAULT_ROOT>/<проект>/atomic-deep-dive/02_COMPETITOR_B_DOSSIER.md
    - <VAULT_ROOT>/<проект>/research/02_unit_economy_2pt.md
    - <VAULT_ROOT>/11-Decisions-Log/YYYY-MM-DD.md   # запись с уроками первой точки
  confidential: false
```

```yaml
# OUTPUT
status: ok
artifact:
  path: <VAULT_ROOT>/<проект>/MASTER_second_point.md
  format: md
  size_bytes: 92140
summary: |
  Рекомендация: conditional-go — открывать через 4 мес. при выполнении 2 условий 
  (рост среднего чека ≥ 18%, найм бариста-наставника).
methodology_used: [Pyramid Principle, MECE Issue Tree]
budget_used: { spent_words: 8200, sources: 5, status: ok }
open_questions:
  - "Чувствительность модели к сезонности июнь–август — требует дополнительной волны"
metadata:
  type: master-synthesis
  project: <проект>
  confidential: false
  source_run: <run_id>
```

### Пример 3 — error и recovery

```yaml
# OUTPUT competitor-intel
status: error
summary: "Источников <3 независимых; SCIP-цикл не закрывается."
escalations:
  - to: orchestr
    type: data_gap
    detail: "Нет открытых данных по выручке <конкурент-A> 2025."
recovery_hint: "Расширить scope на 2024 или дать ручные данные."
```

orchestr: фиксирует в run-логе, либо расширяет scope (если within budget), либо эскалирует пользователю с предложением «расширить или принять как есть».
