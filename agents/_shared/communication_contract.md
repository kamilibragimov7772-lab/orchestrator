# Communication contract (канонический источник)

> **Источник истины для всех кастомных агентов стека.** Локальные копии этого блока в `~/.claude/agents/<name>.md` — справочные; при расхождении доверять ЭТОМУ файлу. Built-in агентов не касается.
>
> Прецедент выноса — `~/.claude/agents/_shared/budget_discipline.md`. Создан 2026-06-01 (remediation self-audit'а, P1-d: устранение дубля ~120 строк × ~30 файлов и устаревшего «11 кастомных агентов»).

## 1. Канал связи

Агент получает задачу **только от orchestr** и возвращает результат **только orchestr'у**. Прямого диалога с другими агентами и с пользователем нет — даже если в задаче упомянут другой агент. Не хватает данных от другого агента → возврат `escalations` orchestr'у; orchestr решает, кого дёрнуть.

## 2. INPUT-контракт

orchestr передаёт структуру:

```yaml
run_id: <YYYY-MM-DD-HHMM-slug>
agent: <agent-name>           # самопроверка: это должен быть ты
task:
  brief_path: <abs path>
  question: <одна фраза>
  scope: { in: [...], out: [...] }
output:
  expected_path: <abs path>
  format: md|docx|pptx|pdf|html
budget: { research: quick|standard|deep, word_target: N, source_budget: N }
context:
  project: <slug>
  brandbook_path: <path|null>
  corpus_path: <path|null>
  prior_artifacts: [<path>, ...]
  confidential: <bool>
deadline: <ISO|null>
notes: <str|null>
```

Нет обязательного поля → `status: error` + `escalations[type=missing_input]`. Не выдумывать, не угадывать.

## 3. OUTPUT-контракт

```yaml
status: ok | partial | needs-user-action | error
artifact:
  path: <abs path>
  format: md|...
  size_bytes: <int>
summary: <1-3 строки сухого вывода>
methodology_used: [<фреймворки>] | exempt
budget_used: <формат задан в ~/.claude/agents/_shared/budget_discipline.md — здесь не дублируется>
# Раньше здесь стояла своя редакция {spent_words, sources, status}, третья по счёту в стеке
# (ещё две — в budget_discipline.md и в жёстких запретах strategy-researcher). Дубль правила
# опаснее его отсутствия: редакции расходятся, агент выполняет ближайшую. Сведено 2026-08-21.
# Типизированный handoff (v2.0): добавлять при передаче между волнами
inputs: [<что получил>]
outputs: [<что произвёл>]
success_criteria: <выполнено ли задание, одной строкой>
open_questions: [<строка>, ...]
escalations:
  - { to: orchestr|user, type: budget | data_gap | conflict | scope | breaking_risk | needs_credentials | missing_input | tool_unavailable | other, detail: <str> }
metadata:
  type: <brief|research|dossier|decision-memo|master-synthesis|ghost-text|task|site-edit|doc-final|infra-runbook|critique|discovery|content|engineering|deploy|build-report|narration|visual-report|index-diff|silent-failure-scan>
  project: <slug>
  confidential: <bool>
  source_run: <run_id>
```

> **Единый список типов эскалации (сведён 2026-08-22).** До этого в каноне жили три разных
> перечисления, и два типа, предписанных карточкам (`missing_input`, `tool_unavailable`),
> не значились ни в одном. Возврат с незнакомым типом попадал в класс «непонятно» и уходил
> на перезапуск, который недостающего не добавлял. Теперь список один и здесь:
>
> `budget` · `data_gap` · `conflict` · `scope` · `breaking_risk` · `needs_credentials` ·
> `missing_input` (нет обязательного входа) · `tool_unavailable` (нечем выполнить обязательный
> шаг) · `other`.
>
> Прежний `tool_failure` из handshake_contract — синоним `tool_unavailable`, использовать
> второй.

> **Список `metadata.type` расширен 2026-08-22.** Прежние десять значений писались под ростер
> из одиннадцати агентов. Фактически карточки возвращают ещё десять — и все законные:
> `critique` (все ревьюеры пайплайна) · `discovery` · `content` · `engineering` · `deploy` ·
> `build-report` · `narration` · `visual-report` · `index-diff` · `silent-failure-scan`.
> Тридцать шесть карточек из сорока печатали тип вне enum'а — это не их брак, а устаревший канон.
> Список закрытый: нового типа нет — сначала правится этот файл, потом карточка.
> Проверяется линтером (`tools/agent-lint.py`), поэтому разъехаться снова не сможет.

## 4. Принцип

Возвращать **только путь + summary 1-3 строки**, не вставлять содержимое артефакта в ответ orchestr'у (экономия контекста).

## Канонический вердикт-словарь (для meta/judge-агентов)

- Для агентов стека: `KEEP / TUNE / MERGE / RETIRE / FIX`.
- Для доменных оценок (strategy-grader, аудиторы сайта): баллы по своей шкале.
