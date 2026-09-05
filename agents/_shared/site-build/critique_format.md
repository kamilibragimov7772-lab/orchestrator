# Формат critique — для всех ревьюеров пайплайна сборки сайтов

Дата: 2026-05-01 (v1.0); 2026-05-02 (v1.1 — добавлено поле `root_phase` для MEDIUM)
Версия: 1.1
Применяется: всеми ревьюерами (`*-reviewer`, `*-auditor`, `final-quality-gate`)
Связан с: `~/.claude/agents/_shared/site-build/site_quality_definition.md`

---

## Зачем этот документ

Ревьюер в этом пайплайне выполняет ДВЕ функции, не одну:

1. **Оценивает артефакт** — выносит вердикт pass / conditional-pass / fail и фиксирует найденные проблемы.
2. **Ставит задачу** автору на следующую итерацию — переформулирует найденные issues в actionable brief, который автор сможет исполнить без дополнительных уточнений.

Это критично. Автору стека было важно подсветить роль ревьюера как «агента, который проверяет задачу и её ставит». Ревьюер, который только критикует, не закрывает цикл — автор получает список проблем, но не понимает, что именно от него хотят. Ревьюер, который умеет переформулировать критику в задание, закрывает цикл.

Этот документ фиксирует обязательный формат critique-файла. Все ревьюеры пайплайна возвращают critique именно в этой структуре.

---

## Структура critique-файла

Файл сохраняется по пути `<run_id>/<phase>/critique_v<N>.md`, где N — номер итерации (начинается с 1).

### Frontmatter

```yaml
---
type: critique
artefact_reviewed: <относительный путь к артефакту, например 00_discovery/discovery.md>
reviewer: <имя агента-ревьюера, например architecture-reviewer>
quality_definition_version: <версия из frontmatter site_quality_definition.md>
critique_format_version: 1.0
iteration: <N>
created: <ISO date>
verdict: <pass | conditional-pass | fail>
---
```

### Тело файла

```markdown
# Critique: <название артефакта>

## Verdict: <pass | conditional-pass | fail>

<Одна-две строки: главный вывод. Например: "Артефакт покрывает все обязательные пункты IA-критериев, но sitemap имеет orphan-страницу /pricing — блокирует прохождение." >

## Quality definition: что проверял

<Перечисли пункты site_quality_definition.md, релевантные для этой фазы и этого артефакта. Например: "Ось АРХИТЕКТУРА — обязательные пункты: глубина sitemap, reachability, orphan pages, URL formatting, mobile-first navigation". Это даёт читателю понять scope ревью.>

## Issues found

### High severity (блокеры)
- **[Issue 1]** — <конкретное описание, не обтекаемое> — <ссылка на пункт quality_definition: "ось АРХИТЕКТУРА, обязательные критерии, пункт 'нет orphan-страниц'"> — <местоположение в артефакте: путь + строка/раздел>
- **[Issue 2]** — ...

### Medium severity (важно, не блокеры)
- **[Issue X]** — <описание> — <ссылка на quality_definition пункт> — <местоположение> — `root_phase: <N|N-1|N-2|null>` *(см. правило ниже про cross-phase tracker)*
- ...

### Low severity (nice-to-have)
- ...

## What passed (явные сильные стороны)

<Обязательный раздел. Не "артефакт в целом неплохой", а конкретно какие пункты quality_definition прошли. Это (а) валидация автора, (б) защита от ситуации, когда ревью звучит как тотальный разнос.>

- ✓ <пункт 1, прошёл>
- ✓ <пункт 2, прошёл>

## Reframed brief for next iteration

<Это сердце critique. Не «вот что плохо», а «вот что нужно сделать в следующей версии артефакта». Формулировка в imperative: «исправь X», «добавь Y», «удали Z». Если verdict = pass — раздел пуст или содержит «следующая итерация не требуется».>

### Что нужно исправить (high severity issues → actionable steps)

1. **<Issue 1 из High severity, переформулированная как задача>**
   — Что именно сделать: <конкретный шаг>
   — Где: <в каком файле/разделе>
   — Как поймём, что исправлено: <критерий, по которому при следующем ревью пункт закроется>
   — Источник критерия: <ссылка на пункт quality_definition>

2. **<Issue 2 как задача>** — ...

### Что желательно улучшить (medium severity → suggestions)

1. <Issue → suggestion в форме «рассмотри возможность Y»>

### Что можно оставить на потом (low severity → backlog)

1. <Issue → пометка «не блокирует, добавь в backlog проекта»>

## Recommendations за рамками найденных issues

<Опционально. Если ревьюер заметил что-то, что не нарушает quality_definition, но было бы улучшением. Это НЕ задача автору, это совет.>

- ...

## Метаданные

- Iteration: <N> из 3 максимум
- Если N=3 и verdict ≠ pass — следующее действие = эскалация пользователю
- Author session id (если known, для трассировки): <id>
- Reviewer session id: <id>

```

---

## Правила для ревьюера при заполнении

### 1. Severity не на твоё усмотрение

Severity каждого issue должна соответствовать severity, заявленной в `site_quality_definition.md` для соответствующего пункта. Если пункт там помечен как HIGH — issue HIGH. Если MEDIUM — issue MEDIUM. Ревьюер НЕ имеет права повышать severity по своей инициативе.

Если ревьюер считает, что найденная проблема не соответствует ни одному пункту quality_definition — он не может поднимать её как High. В разделе «Recommendations за рамками найденных issues» — пожалуйста.

### 2. Каждый issue должен быть привязан к quality_definition

Не «мне кажется, sitemap плохой», а «sitemap нарушает пункт «глубина ≤3 уровней», ось АРХИТЕКТУРА, обязательные критерии». Без явной привязки — issue не валиден.

### 3. Каждый issue должен быть actionable

«Контент слабый» — не actionable. «На странице /services отсутствует TL;DR в первом экране, что нарушает пункт «явный value proposition в первом экране» из оси НАПОЛНЕННОСТЬ» — actionable.

### 4. Verdict определяется присутствием/отсутствием High severity issues

- **pass** — нет high severity issues, medium ≤2, low — без ограничений
- **conditional-pass** — нет high severity, medium 3-5, либо high есть, но автор может закрыть их в рамках того же артефакта без переоткрытия других фаз. Условие: явно указать в reframed brief, что должно быть в backlog
- **fail** — есть high severity, требующие переделки артефакта или возврата к предыдущей фазе

### 5. Reframed brief — обязателен для conditional-pass и fail

Если verdict не pass — раздел «Reframed brief for next iteration» НЕ может быть пустым. Это требование защищает от ситуации, когда автор получает критику без понимания «что делать».

### 6. What passed — обязателен всегда

Даже при verdict = fail. Минимум 1-2 пункта, что прошло. Это (а) калибровка чек-листа (если ничего не прошло — может быть, чек-лист слишком жёсткий), (б) поддержка автора в продолжении.

### 7. `root_phase` для MEDIUM — обязательно

Для каждого MEDIUM issue ревьюер указывает `root_phase`: номер фазы, в которой *корень* проблемы (не где она вылезла). Допустимые значения:

- `root_phase: <N>` (текущая фаза) — issue полностью fixable автором этой же фазы
- `root_phase: <N-1>` / `<N-2>` / … — корень в предыдущей фазе. **Триггерит retroactive_backlog tracker** в orchestr-промпте → `<run_id>/_run_log.md` (или run-лог фазы N-K) получает запись в `retroactive_backlog:` секцию
- `null` — корень неоднозначен; orchestr запросит уточнение или поставит `root_phase = N` дефолтом

**Примеры:**
- phase-4 reviewer находит «8 skeleton-stubs missing для Wave 1 без canonical» — `root_phase: 4` (visual-designer self-check Glob), хотя hint о canonical-gap идёт от phase 2 → root_phase можно поставить `4`, отметить в reframed brief
- phase-7 performance-auditor находит «LCP 4.2s из-за hero image 2.5MB» — `root_phase: 4` (visual-designer не указал target-size в page_spec) или `root_phase: 6` (astro-engineer не сжал)
- phase-7 accessibility-auditor находит «контраст 3.5:1 на secondary text» — `root_phase: 3` (design-system-architect — tokens.json дал плохую пару)

Для **HIGH** issues `root_phase` опционален, но рекомендуется (помогает при escalation Type 2 cross-phase rework loop).
Для **LOW** — не требуется.

---

## Алгоритм ревью

1. **Прочитать артефакт целиком**.
2. **Прочитать `~/.claude/agents/_shared/site-build/site_quality_definition.md`** (актуальную версию).
3. **Прочитать предыдущий critique_v<N-1>.md** (если это итерация 2+) — чтобы убедиться, что предыдущие issues закрыты или не закрыты, и не добавлять новые без причины (защита от scope-creep ревьюера).
4. **Пройтись по релевантным пунктам quality_definition** — отметить, что прошло, что нет.
5. **Сформулировать issues** в порядке severity (high → medium → low).
6. **Сформулировать what passed** — обязательно.
7. **Переформулировать issues в reframed brief** — это самая важная часть.
8. **Вынести verdict** — по правилу из пункта 4 выше.
9. **Сохранить файл** в `<run_id>/<phase>/critique_v<N>.md`.
10. **Вернуть оркестратору** только: путь к critique-файлу + verdict + 1 строкой главное (например: «conditional-pass, 2 high issues по orphan-страницам, переформулировано в reframed brief»).

---

## Антипаттерны (что ревьюер НЕ делает)

- **Свободный текст без структуры**. Только заданная схема. Иначе оркестратор не сможет распарсить.
- **Без severity или с придуманной severity**. Severity — только из quality_definition.
- **Issues без привязки к quality_definition**. Если не привязано — это recommendation, не issue.
- **Reframed brief без actionable шагов**. «Сделай лучше» — не сойдёт. Только конкретные шаги.
- **Issues без what passed**. Тотальный разнос — сигнал, что ревьюер не справляется или чек-лист сломан.
- **Создание новых критериев на лету**. Если ревьюер считает, что quality_definition нужно расширить — это отдельный сигнал пользователю, не часть critique.
- **Цикл итераций > 3**. После третьей итерации — эскалация, не четвёртая попытка.

---

## Пример заполненного critique-файла

Дан для иллюстрации, не как обязательный шаблон.

```markdown
---
type: critique
artefact_reviewed: 01_ia/sitemap.md
reviewer: architecture-reviewer
quality_definition_version: 1.0
critique_format_version: 1.0
iteration: 1
created: 2026-05-15T14:32:00+03:00
verdict: fail
---

# Critique: 01_ia/sitemap.md

## Verdict: fail

Sitemap имеет два orphan-блока (страницы /pricing и /case-studies/example-2 не присутствуют ни в главном меню, ни в footer, ни в внутренних ссылках) и одну страницу на 4-м уровне глубины (/services/dental/implants/full-jaw), что нарушает обязательные критерии оси АРХИТЕКТУРА.

## Quality definition: что проверял

Ось АРХИТЕКТУРА, обязательные критерии:
- Глубина sitemap ≤3 уровней
- Каждая страница reachable за ≤2 клика
- Нет orphan-страниц
- URL читаемые в kebab-case латиницей
- Mobile-first navigation

## Issues found

### High severity (блокеры)

- **[orphan-pricing]** — Страница /pricing присутствует в sitemap.md (строка 42), но не упоминается ни в навигации, ни во внутренних ссылках. Орфан — нарушает пункт «Нет orphan-страниц» оси АРХИТЕКТУРА. Местоположение: 01_ia/sitemap.md, строка 42.

- **[orphan-case-2]** — Страница /case-studies/example-2 — то же самое, строка 87.

- **[depth-4-implants-full-jaw]** — /services/dental/implants/full-jaw — 4 уровня от главной. Нарушает пункт «Глубина sitemap ≤3 уровней». Местоположение: 01_ia/sitemap.md, строка 64.

### Medium severity

— Нет.

### Low severity

- **[no-breadcrumbs-spec]** — Sitemap не специфицирует breadcrumbs для глубоких страниц. Это пункт MEDIUM в quality_definition, но в текущем артефакте отсутствует. Учесть в финальной версии.

## What passed

- ✓ Все URL в kebab-case латиницей.
- ✓ Mobile-first структура навигации описана корректно.
- ✓ Footer-карта спроектирована.

## Reframed brief for next iteration

### Что нужно исправить

1. **Включить /pricing в навигацию или удалить из sitemap**
   — Что сделать: либо добавить «Цены» в главное меню (рекомендованное расположение), либо удалить страницу из sitemap, если она не запланирована.
   — Где: 01_ia/sitemap.md, строка 42; 01_ia/navigation.md.
   — Как поймём, что исправлено: страница /pricing присутствует либо в главном меню, либо в footer, либо удалена.
   — Источник критерия: site_quality_definition.md → ось АРХИТЕКТУРА → обязательные → «Нет orphan-страниц».

2. **Решить судьбу /case-studies/example-2 аналогично**
   — Что сделать: добавить ссылку с главной страницы кейсов или удалить.
   — Как поймём: страница reachable от главной ≤2 клика.

3. **Сократить глубину /services/dental/implants/full-jaw**
   — Что сделать: либо переместить контент в /services/dental/implants как отдельный раздел страницы, либо реструктурировать sitemap так, чтобы /services/dental/implants содержал anchor-ссылки на конкретные виды имплантации (full-jaw, single, etc).
   — Где: 01_ia/sitemap.md, строка 64.
   — Как поймём: ни одна страница не глубже 3 уровней от главной.

### Что желательно улучшить

— Нет в текущей итерации.

### Что в backlog

1. **Спецификация breadcrumbs** — добавить в sitemap.md секцию «Breadcrumb pattern: <главная> / <раздел> / <страница>». Не блокирует, но желательно для финальной версии.

## Метаданные

- Iteration: 1 / 3
```

---

## Связь с другими документами

- `~/.claude/agents/_shared/site-build/site_quality_definition.md` — что проверять
- `~/.claude/agents/_shared/site-build/critique_format.md` — этот файл, как оформлять ревью
- `~/.claude/agents/_shared/budget_discipline.md` — общий бюджетный протокол (применяется к ревьюерам тоже)
- `ARCHITECTURE.md` — общая архитектура пайплайна и порядок фаз (внешняя зависимость, см. README)
