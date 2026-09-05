---
description: Генерит scaffold task_NNN_slug.md для OpenClaw-исполнителя по 10-секционному формату.
argument-hint: <slug> "<заголовок задачи>"
---

# /openclaw-task

Создай scaffold для OpenClaw-задачи. OpenClaw = WSL Ubuntu исполнитель, читает `<VAULT_ROOT>/10-OpenClaw/_ACTIVE/`.

## Что делать

1. Распарси аргументы:
   - `slug` — kebab-case латиницей (например, `competitor-sale-response`)
   - `title` — заголовок задачи в кавычках

2. Найди следующий ID:
   - Glob `<VAULT_ROOT>/10-OpenClaw/_ACTIVE/task_*.md` + `_ARCHIVE/task_*.md`
   - Сортируй по числу, `next_id = max + 1`, форматирование 3-значное (`010`, `011`, `099`)
   - Если max не определён — начать с `001`

3. Создай файл `<VAULT_ROOT>/10-OpenClaw/_ACTIVE/task_<NNN>_<slug>.md` по шаблону:

```markdown
---
id: task_<NNN>
slug: <slug>
created: <YYYY-MM-DD>
status: draft
channel: <канал Telegram>
priority: normal
author: strategist
---

# <title>

## 1. Что нужно сделать
(одна-две строки сути)

## 2. Зачем это нужно
(бизнес-контекст, почему именно сейчас)

## 3. Канал доставки
(Telegram-канал/чат, если ответ-сообщение)

## 4. Пошаговый план
1. (шаг 1)
2. (шаг 2)
3. ...

## 5. Данные для сообщений
(готовые тексты в Telegram-разметке: **жирный**, _курсив_, `код`, > цитата)

## 6. Критерии успеха
- [ ] (что должно быть выполнено)
- [ ] ...

## 7. Риски
- (риск 1 + митигация)
- ...

## 8. Fallback
(что делать, если основной путь не работает)

## 9. После выполнения
- Архив: `mv task_<NNN>_<slug>.md _ARCHIVE/`
- Decisions-log: дописать запись в `11-Decisions-Log/<YYYY-MM-DD>.md`

## 10. Результат
(заполняется OpenClaw'ом по факту выполнения: что отправлено, кому, когда, скриншоты/ссылки)
```

4. Verify:
   - Файл создан, frontmatter валидный
   - Покажи пользователю: путь + первые 3 секции для подтверждения сути

5. Если пользователь одобрил суть — перевести `status: draft` → `status: active` (Edit frontmatter).

## Конвенции

- ID сквозной, не сбрасывается
- Файл сразу в `_ACTIVE/`, в `_ARCHIVE/` уходит после факта выполнения
- Шаблон строго 10 секций (его читает OpenClaw)
- См. `<VAULT_ROOT>/10-OpenClaw/_README.md` для полной спецификации формата

## Примеры

- `/openclaw-task competitor-sale-response "Ответы на возражение про распродажу конкурента"`
- `/openclaw-task morning-summary-template "Шаблон утренней сводки 09:00 MSK"`
