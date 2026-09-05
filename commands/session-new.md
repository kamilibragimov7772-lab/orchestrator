---
description: Создаёт папку-сессию на Рабочем столе и в vault, генерит _README.md по канону.
argument-hint: <slug> "<тема одной строкой>"
---

# /session-new

Создай новую папку-сессию для текущей задачи. Аргументы: латинский slug + тема в кавычках.

## Что делать

1. Распарси аргументы:
   - `slug` — латинский kebab-case или snake_case, обязательный
   - `theme` — тема в двойных кавычках, обязательная

   Если slug или theme не переданы — спроси, не выдумывай.

2. Сегодняшняя дата (`currentDate` из контекста): `<YYYY-MM-DD>`.

3. Создай ДВЕ папки параллельно:
   - **Desktop:** `<HOME>\Desktop\_Claude_Deliverables\<YYYY-MM>\<YYYY-MM-DD>_<slug>\` (для финальных deliverables пользователю)
   - **Vault:** `<VAULT_ROOT>\08-Работа-Claude\<YYYY-MM-DD>_<slug>\inputs\` (для рабочих артефактов)

4. Создай `_README.md` в Desktop-папке по шаблону:

```markdown
---
session: <YYYY-MM-DD>_<slug>
created: <YYYY-MM-DD>
theme: <theme>
status: in-progress
---

# <theme>

## Что в этой папке

(Финальные артефакты для пользователя — md/docx/xlsx/pdf/png. Рабочие inputs и черновики живут в vault: `08-Работа-Claude/<YYYY-MM-DD>_<slug>/`.)

## Файлы

- (заполняется по мере появления)

## Связанные

- vault: `08-Работа-Claude/<YYYY-MM-DD>_<slug>/`
- decisions-log: `11-Decisions-Log/<YYYY-MM-DD>.md`
```

5. Создай `_README.md` в vault-папке (`08-Работа-Claude/<YYYY-MM-DD>_<slug>/`) с теми же frontmatter полями + поле `purpose: рабочий runtime сессии, не для пользователя`.

6. Verify:
   - `Test-Path` обоих README — должен вернуть True
   - Покажи пользователю: «Создал: Desktop = <path>, vault = <path>. Готов к работе.»

## Конвенции

- slug — короткий, описательный, латиница
- На каждую сессию — одна папка обоих видов (Desktop + vault)
- Любой md/txt в Desktop-папке должен иметь .docx-дубль — это правило ghostwriter/document-compiler

## Примеры

- `/session-new client-q3-strategy "Стратегия <клиент> на Q3 2026"`
- `/session-new feedback-loop "Обработка отзывов клиента"`
