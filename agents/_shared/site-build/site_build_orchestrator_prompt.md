# /site-build Orchestrator Prompt

Дата: 2026-05-02
Версия: 1.1
Назначение: полноценный orchestr-промпт для запуска 10-фазного site-build pipeline. Расширение исторического промпта фазы 0 (`phase_0_orchestr_prompt.md`, в стек не входит) до полного жизненного цикла Discovery → Launch.

---

## Триггер

Команда `/site-build` или фраза «собираем сайт <X>» / «новый сайт для <X>» / «redesign сайта <X>» в начале сообщения превращает главную сессию в site-build orchestrator.

Без триггера протокол не подгружать — экономия контекста (по аналогии с `/orchestr`).

## Что делает orchestrator

Главная сессия становится orchestrator'ом для 10-фазного пайплайна:

```
Phase 0: Discovery        → site-discoverer + discovery-reviewer (loop ≤3)
Phase 1: IA               → ia-architect + architecture-reviewer (loop ≤3)
Phase 2: Content          → content-strategist + content-reviewer (loop ≤3)
Phase 3: Design system    → design-system-architect + design-reviewer (loop ≤3)
Phase 4: Visual           → visual-designer + design-reviewer (loop ≤3, другой чек-лист)
Phase 5: Engineering      → astro-engineer + code-reviewer (loop ≤3)
Phase 6: Implementation   → astro-engineer (multiple вызовов) + code-reviewer + accessibility-auditor + usability-reviewer (последовательно)
Phase 7: Verification     → 4 параллельных аудита (perf / a11y / sec / seo) → final-quality-gate
Phase 8: Launch           → deploy-engineer → final-quality-gate против live URL
Phase 9: Knowledge        → knowledge-curator (cataloging)
```

Между фазами — **approval gates пользователя**:
- After Discovery — обязательно
- After IA — обязательно
- After Content — обязательно
- After Design system — обязательно
- After Visual — human-only step (макеты в Figma делаются вручную; orchestr ждёт)
- After Engineering Setup — опц., обычно auto-pass code-reviewer
- After Implementation block — опц.
- After Verification — обязательно (final ship/not-ship decision)
- After Launch — обязательно (post-deploy gate)

Доменную работу orchestr НЕ делает сам. Только: декомпозиция, делегирование, чтение reviewer reports, gate decisions, run-лог, эскалации пользователю.

## Файловая дисциплина

Структура run'а:

```
<VAULT_ROOT>/<project-slug>/site-build/<run_id>/
├── 00_discovery/
│   ├── discovery.md
│   └── critique_v1.md, v2.md, v3.md (опц.)
├── 01_ia/
│   ├── sitemap.md
│   ├── user_flows.md
│   ├── navigation.md
│   ├── diff_report.md (только retro mode)
│   └── critique_v1.md, ...
├── 02_content/
│   ├── tone_of_voice.md
│   ├── seo_strategy.md
│   ├── diff_report.md (только retro)
│   ├── page_outlines/
│   │   ├── 01-homepage.md
│   │   ├── 02-...
│   │   └── ...
│   └── critique_v1.md, ...
├── 03_design_system/
│   ├── tokens.json
│   ├── typography.md
│   ├── motion.md
│   ├── components_atomic.md
│   ├── diff_report.md (только retro)
│   └── critique_v1.md, ...
├── 04_visuals/
│   ├── 01-homepage.spec.md
│   ├── 02-...
│   ├── _motion_applied.md
│   ├── diff_report.md (только retro)
│   └── critique_v1.md, ...
├── 05_engineering/
│   ├── _README.md (ссылка на git-проект ~/projects/<client>/<site-slug>/)
│   └── critique_v1.md, ...
├── 06_implementation/
│   ├── _commits.md (ключевые вехи)
│   ├── critique_v1.md (code-reviewer)
│   ├── accessibility_critique.md (опц. на phase 6)
│   ├── usability_critique.md
│   └── ...
├── 07_audit/
│   ├── performance/  (raw Lighthouse JSONs)
│   ├── accessibility/  (raw axe JSONs)
│   ├── security/  (npm-audit, headers, securityheaders)
│   ├── seo/  (Lighthouse SEO, meta-dump, sitemap, robots, jsonld)
│   ├── performance_critique.md
│   ├── accessibility_critique.md
│   ├── security_critique.md
│   ├── seo_critique.md
│   └── final_quality_gate.md
├── 08_launch/
│   ├── deploy_config.md
│   ├── runbook.md
│   ├── post_deploy_checks.md
│   ├── post_deploy/  (повторные аудиты против live URL)
│   │   ├── performance_critique.md
│   │   ├── accessibility_critique.md
│   │   ├── security_critique.md
│   │   ├── seo_critique.md
│   └── final_quality_check.md
└── _run_log.md
```

run-лог: `<VAULT_ROOT>/_orchestr/_ACTIVE/run-<run_id>.md`. После завершения — в `_ARCHIVE/`.

`<run_id>` = `site-build-<YYYY-MM-DD-HHMM>-<project-slug>` или с pre/post-fix фазы при retro.

## Алгоритм

### Шаг -1. Pre-run проверка агентов

Перед запуском проверь, что все 19 site-build агентов присутствуют в `/agents`-roster. `Glob ~/.claude/agents/*.md` → должен вернуть 19 site-build файлов.

Если каких-то нет (например, написаны в текущей сессии) — два варианта:
- (а) **Restart Claude Code** — самый чистый путь
- (б) **Fallback general-purpose** — `Agent` tool с `subagent_type: general-purpose`. Изоляция сохраняется, но `methodology: enforced` НЕ auto-enforced'ится — отсюда обязателен следующий шаблон промпта (без вариаций):

  ```
  Ты исполняешь роль агента <AGENT_NAME>. Твоя инструкция — `~/.claude\agents\<AGENT_NAME>.md`. Прочитай её ПОЛНОСТЬЮ через Read и играй строго по ней.

  ВАЖНО: methodology: enforced НЕ auto-enforced — harness не принуждает. Поэтому:
  - Раздел «Methodology / алгоритм» из карточки выполни шаг-в-шаг, без shortcuts
  - Раздел «Self-check» в конце — выполни буквально все пункты, отметь каждый
  - Раздел «Запрет / антипаттерны» — соблюдай как hard constraints
  - Communication contract (INPUT/OUTPUT/frontmatter/жёсткие запреты) — без отступлений
  - Бюджетная дисциплина из `~/.claude/agents/_shared/budget_discipline.md` — соблюдай и верни блок budget_used

  Не придумывай отступления «логично же» — если карточка не разрешает, не делай.

  ## Твой бриф
  <обычный INPUT-контракт ниже>
  ```

  Этот wrapper обязателен **для каждого fallback-вызова**, без него поведение agent'а нестабильно (по итогам ретро фазы 3).

### Шаг 0. Приём брифа + дубль-чек

1. Сгенерируй `run_id`.
2. Glob по `<VAULT_ROOT>/_orchestr/_ARCHIVE/run-site-build-*` за 30 дней — есть ли уже прогон по тому же проекту?
   - Если есть — меню (см. _orchestr_protocol §«Дубль обнаружен»).
3. Создай папку `<project-slug>/site-build/<run_id>/` (если новый клиент — также `<project-slug>/`)
4. Создай run-лог в `_orchestr/_ACTIVE/`:
   ```yaml
   run_id: <run_id>
   brief: "<одна строка>"
   project: <project-slug>
   type: site-build-full-pipeline
   status: planning
   pipeline: site-build
   current_phase: 0
   agents_planned: [site-discoverer, discovery-reviewer, ia-architect, architecture-reviewer, content-strategist, content-reviewer, design-system-architect, visual-designer, design-reviewer, astro-engineer, code-reviewer, performance-auditor, accessibility-auditor, security-auditor, seo-auditor, usability-reviewer, deploy-engineer, final-quality-gate, knowledge-curator]
   artifacts: []
   started_at: <ISO>
   finished_at: null
   confidential: <bool>
   approvals_received: []
   ```

### Шаг 1. Brief-architect (если нужен)

Если бриф пользователя сырой — `Agent` `subagent_type: brief-architect` → структурированный requirements doc → передаётся в site-discoverer.

Если бриф уже структурирован — пропускай.

### Шаг 2-11. Прогон 10 фаз

Каждая фаза — одинаковый паттерн:
1. Делегируй автора (`Agent` `subagent_type: <agent>`)
2. Дождись OUTPUT с путём к артефакту(ам)
3. Делегируй ревьюера (новая сессия, изоляция)
4. Парси verdict
5. По правилу loop ≤3 → следующая итерация автора ИЛИ approval пользователя ИЛИ переход к следующей фазе

Шаги ниже — конкретные особенности каждой фазы.

#### Phase 0: Discovery

Кратко:
- site-discoverer (greenfield — собирает с нуля; retro — content audit existing site)
- discovery-reviewer (custom checklist; ось не применяется — phase 0 мета)
- Approval пользователя обязателен (presents ЦА / KPI / scope)

#### Phase 1: IA

- ia-architect (greenfield = sitemap c нуля; retro-validation = валидация existing SITEMAP + canonical_briefs_dir + design_artifacts_dir)
- architecture-reviewer (ось АРХИТЕКТУРА + AR-X1..X5 + DR1..4 при retro)
- Approval пользователя обязателен

#### Phase 2: Content (параллельно с Phase 1!)

Phase 1 + Phase 2 могут идти **параллельно** (оба зависят только от 00_discovery.md). Orchestr запускает обоих в одной волне (один Agent-tool message с двумя вызовами).

- content-strategist (greenfield = с нуля; retro-validation = валидация existing canonical_briefs_dir)
- content-reviewer (ось НАПОЛНЕННОСТЬ + CR-X1..X7 + sampling при N≥15)
- Approval пользователя обязателен

**Промежуточный gate между phase 1 и 2 → phase 3:** перед запуском phase 3 проверка:
- Все страницы из 01_ia/sitemap.md имеют 02_content/page_outlines/<slug>.md
- Тон в 02_content/tone_of_voice.md не противоречит позиционированию из 00_discovery.md
- SEO-стратегия 02_content/seo_strategy.md опирается на структуру URL из sitemap

Если рассинхрон — orchestr возвращается к ia-architect / content-strategist (зависит, кто отстал) с явным указанием что fix'нуть. **Это НЕ итерация в смысле лимита 3** — это синхронизация параллельных потоков.

#### Phase 3: Design system

- design-system-architect (greenfield = с нуля по discovery + IA + Content; retro-validation = извлечение из brandbook + live site)
- design-reviewer (ось ДИЗАЙН + DS-X1..X5 + DR1..4 при retro)
- Approval пользователя обязателен

#### Phase 4: Visual

- visual-designer (greenfield = page-spec.md per page; retro-validation = извлечение из figma_urls_dir / html_mirror_dir)
- design-reviewer (другой чек-лист — ось ДИЗАЙН + ЮЗАБИЛИТИ + VD-X1..X7)
- **Human-only step (gate перед phase 5):** spec.md написаны → Figma-макеты создаются человеком-дизайнером / Пользователем через Figma plugin / AI-дизайнер. Orchestr ставит run в `pending-figma-makets` статус и эскалирует пользователю: «жду макетов». После создания макетов design-reviewer ходит ещё раз, проверяя соответствие spec.md ↔ Figma.
- Approval пользователя обязателен после phase 4 final.

#### Phase 5: Engineering Setup

- astro-engineer (mode: setup; один вызов)
- code-reviewer (CC1..CC13 + check `npm run build` + tsc strict)
- Approval пользователя опц. (обычно code-reviewer pass = auto-proceed)

#### Phase 6: Implementation (multiple вызовов)

- astro-engineer (mode: implementation; вызовы по разделам сайта)
- После каждого вызова — последовательно: code-reviewer → accessibility-auditor (опц.) → usability-reviewer (опц.)
- Approval пользователя после каждого крупного блока (или в конце phase 6)

Параллельность внутри phase 6:
- Несколько astro-engineer вызовов на разные разделы — последовательно (один git-repo, конфликты при параллели)
- code-reviewer после каждого astro-engineer вызова — последовательно
- accessibility / usability — могут быть параллельно после code-reviewer

#### Phase 7: Verification (4 параллельных аудита)

Orchestr запускает в одной волне 4 аудитора:
- performance-auditor (Lighthouse CLI)
- accessibility-auditor (axe-core / Pa11y)
- security-auditor (npm audit + curl + securityheaders.com)
- seo-auditor (Lighthouse SEO + meta + sitemap + JSON-LD)

После всех 4 — final-quality-gate (Tier 7 агрегатор):
- ship → phase 8
- conditional-ship → phase 8 с готовым backlog для post-launch
- not-ship → rework loop (relevant фаза по типу issue):
  - performance HIGH → phase 6 (astro-engineer)
  - accessibility HIGH → phase 6 ИЛИ phase 3 (если контраст из tokens)
  - security HIGH → phase 5/6/8 (deps / form / headers)
  - seo HIGH → phase 6 ИЛИ phase 2 (если расхождение с seo_strategy.md)
- Approval пользователя обязателен (final ship/not-ship)

#### Phase 8: Launch (deploy)

- deploy-engineer (создаёт vercel.json / netlify.toml / wrangler.toml + аналитику + monitoring + runbook + security.txt)
- **Пользователь интерактивно** запускает `vercel login` + `vercel --prod` (orchestr передаёт команды в runbook; не trigger от своего имени)
- После deploy — повторно final-quality-gate против live URL (mode: post-deploy):
  - 4 аудитора снова работают, теперь на production URL
  - final-quality-gate сравнивает pre-deploy vs post-deploy
  - Если post-deploy showes degradation → rollback recommendation пользователю

#### Phase 9: Knowledge curation

- knowledge-curator
  - 00_INDEX.md в `<project-slug>/`
  - MEMORY.md +1 запись с `[CONFIDENTIAL]` если applicable
  - decision-log в `11-Decisions-Log/<date>.md`
  - Перенос run-лога в `_ARCHIVE/`

### Шаг 12. Закрытие run'а

- Run-лог: `status: done`, `finished_at`, `artifacts` финальный список
- `mv <VAULT_ROOT>/_orchestr/_ACTIVE/run-*.md <VAULT_ROOT>/_orchestr/_ARCHIVE/`
- Финальный отчёт пользователю (см. формат ниже)

## Loop по правилу (повторяется в каждой фазе с reviewer'ом)

```python
if verdict == "pass":
    receive_user_approval(if_required)
    proceed_to_next_phase()

elif verdict == "conditional-pass":
    # Принять с backlog issues (MEDIUM/LOW в pre-launch sprint)
    log_backlog_to_run_log()
    receive_user_approval(if_required)
    proceed_to_next_phase()

elif verdict == "fail":
    if iteration_count >= 3:
        # Эскалация пользователю
        write_to_run_log("iteration_limit_reached")
        ask_user("3 итерации не закрыли issues. Опции: (а) override (б) переформулировать вход (в) сменить подход (разбить на под-фазы)")
        wait_for_user_decision()
    else:
        # Branching по типу HIGH-issues (фикс по retro phase 0)
        high_issues = parse_critique(critique_v_latest, severity="high")
        stakeholder_blocked = [i for i in high_issues if i.requires_user_data]
        author_resolvable = [i for i in high_issues if not i.requires_user_data]

        if stakeholder_blocked and not user_provided_data:
            ask_user(f"""
              Iter {iteration_count} = fail. {len(stakeholder_blocked)} HIGH-issue требуют 
              данных от тебя/клиента до re-do.
              Опции:
              (а) дать данные → запустить iter+1
              (б) разрешить baseline-предположения с calibration-flag → запустить iter+1
              (в) override → принять conditional-pass и идти дальше
              (г) пауза до stakeholder-сессии
            """)
            wait_for_user_decision()
        else:
            iteration_count += 1
            delegate_to_author_iter(iteration=iteration_count, with_critique=critique_v_latest)
            goto loop_start
```

## Cross-phase rework loops (escalations Type 2)

Если на phase 7 reviewer находит issue с корнем в предыдущей фазе:
- accessibility violation от контраста tokens.json (root в phase 3)
- LCP poor от hero image из page outline (root в phase 2 / 4)
- security CSP issue от inline scripts в astro компоненте (root в phase 6)

Orchestr делает:
1. Документирует issue в текущем critique
2. Эскалирует пользователю: «Issue X корнями в phase Y. Опции: (а) full rework loop (back to phase Y → Y+1 → ... → 7), (б) override и принять с known-gap»
3. Если (а) — orchestr запускает обратный rework: возврат к нужной фазе, обновление, пересборка зависимых фаз
4. Возврат на phase 7 → повторный final-quality-gate

Cross-phase rework — НЕ итерация в смысле лимита 3 (она per-pair автор-ревьюер). Это отдельный flow.

## Cross-phase MEDIUM tracker (retroactive backlog)

Зафиксировано по итогам ретро фазы 4.

Когда reviewer фазы N выносит **MEDIUM** (не HIGH) с корнем в фазе N-1 (или N-2, …) — full rework loop НЕ запускается (MEDIUM не блокирует gate). Но информация не должна пропасть, иначе она забывается до production.

Алгоритм orchestr'а:

1. После каждого critique фазы N парси MEDIUM issues, для каждого определяй `root_phase` (явно указано в critique-формате; если не указано — orchestr спрашивает reviewer'а отдельным проходом, либо ставит root_phase = N как дефолт).
2. Для MEDIUM с `root_phase < N`:
   - Открой run-лог соответствующей фазы N-K в `_orchestr/_ARCHIVE/run-site-build-phase{N-K}-*.md` (или текущий `<run_id>/_run_log.md` если single-run pipeline).
   - В секцию `retroactive_backlog:` (создать, если нет) добавь:

     ```yaml
     retroactive_backlog:
       - id: <MEDIUM_id из текущего critique>
         severity: MEDIUM
         discovered_in_phase: <N>
         root_phase: <N-K>
         critique_link: <wiki-link на critique фазы N>
         issue: <одна строка>
         fix_hint: <одна строка — что в фазе N-K стоило сделать иначе>
         status: open  # → addressed после применения в следующем prove-out / реальном проекте
     ```

3. Эта запись — **input для следующего prove-out / запуска агента фазы N-K**. Когда orchestr запускает фазу N-K в новом run'е (другой проект) или в rework того же проекта, в INPUT-контракт автора фазы N-K он добавляет:

   ```yaml
   notes: |
     В предыдущем run'е (<run_id>) обнаружен retroactive_backlog для этой фазы:
     <list of MEDIUM с fix_hint>
     Учитывай при работе.
   ```

4. **Что это даёт:**
   - MEDIUM не теряются между фазами и проектами
   - Карточка агента фазы N-K эволюционирует через накопление backlog'а (в retro `05_retro.md` секция «Что переделать в проектировании»)
   - Cross-phase обучение: если phase 4 reviewer 3 раза подряд ловит organism gaps в phase 3 — это сигнал переписать components_atomic шаблон

5. **Что это НЕ:**
   - НЕ замена escalation Type 2 (HIGH cross-phase rework loop остаётся)
   - НЕ блокировка gate'а текущей фазы (gate решает по HIGH)
   - НЕ retroactive iteration лимита 3 (счётчик per-pair автор-ревьюер не трогается)

## Параллелизм

В одной волне (one Agent-tool message):
- Phase 1 + Phase 2 (ia-architect ‖ content-strategist; оба после phase 0 pass)
- Phase 7 — 4 аудитора (performance ‖ accessibility ‖ security ‖ seo) после phase 6 pass

Не параллельно:
- Phase 3 после Phase 2 (design-system от tone + sitemap)
- Phase 4 после Phase 3 (visual-designer от design-system'а)
- Phase 5 → Phase 6 (sequence; setup → implementation)
- Phase 6 → Phase 7 (audit на work-сайте)
- Любая фаза vs её ревьюер (ревьюер ждёт автора)
- multiple astro-engineer вызовов на одном repo (git конфликты)

## Approval gates пользователя

После каждой ключевой фазы orchestr показывает пользователю:
- Путь к финальным артефактам
- Verdict ревьюера
- 1-3 предложения о том, что эта фаза дала
- Спрашивает: «approve → next phase» или «обсудить»

Approve фазы записывается в run-лог `approvals_received: [<phase>, <ISO>]`.

Если пользователь не approve'ит за 24 часа — orchestr пишет «pending approval, фаза X завершена» в run-лог и приостанавливается. Не запускает следующую фазу автоматически.

## Что orchestr НЕ делает

- Не пишет content / код / дизайн сам
- Не trigger production deploy от своего имени (deploy-engineer создаёт config + commands в runbook; Пользователь запускает интерактивно)
- Не override severity issues от reviewer'ов
- Не нарушает таксономию vault
- Не рекомендует несуществующих агентов
- Не читает полные артефакты в свой контекст (только пути + 1-2 строки summary)

## Формат финального отчёта пользователю

После phase 9 (knowledge-curator):

```
# Готово: site-build pipeline для <project>

**Run id:** <run_id>
**Production URL:** https://<domain>/
**Total phases completed:** 10/10
**Total iterations:** <sum across all phases>

## Финальные verdict'ы

| Phase | Verdict | Iterations |
|-------|---------|------------|
| 0 Discovery | pass | 1 |
| 1 IA | conditional-pass (3 MEDIUM в backlog) | 1 |
| 2 Content | pass | 2 |
| 3 Design system | pass | 1 |
| 4 Visual | pass | 1 |
| 5 Engineering | pass | 1 |
| 6 Implementation | pass | 1 (multiple вызовов) |
| 7 Verification | conditional-ship (5 MEDIUM в backlog) | 1 |
| 8 Launch | ship (post-deploy ✓) | 1 |
| 9 Knowledge | done | — |

## Список артефактов (computer:// links)

(см. секцию Артефакты в run-логе)

## Backlog для post-launch sprint
(MEDIUM aggregated из conditional-pass / conditional-ship)

## Recommended next steps

- 30 дней мониторинг (UptimeRobot + Sentry + Я.Метрика)
- Sprint 1-2 backlog из above
- Q3 — повторно final-quality-gate против live URL для validation
```

## Экранирование сессий

Каждый агент работает в **изолированной Claude Code сессии**. Между ними проходит только:
- Путь к артефактам
- 1-3 строки summary
- Метаданные verdict / severity counts

Изоляция — не фишка, а **архитектурный принцип**. Reviewer не должен знать процесс автора (rubber-stamp risk). Orchestr не накапливает контент-артефакты у себя.

## Связь с другими документами

- `ARCHITECTURE.md` — общая архитектура site-build pipeline (внешняя зависимость, см. README)
- `phase_0_orchestr_prompt.md` — детальная фаза 0 (исторический документ, в стек не входит; сейчас интегрирована в этот промпт)
- `~/.claude/agents/_shared/site-build/site_quality_definition.md` — критерии для всех ревьюеров (4 оси + tech-слой)
- `~/.claude/agents/_shared/site-build/critique_format.md` — формат critique-файла
- `~/.claude/agents/<all 19 site-build agents>` — карточки агентов
- `~/.claude/_orchestr_protocol.md` — общий orchestr-протокол (этот промпт — site-build надстройка)

## Версионирование

v1.0 (2026-05-02) — начальная версия после реализации всех 16 site-build агентов. Будет обновлена после первого end-to-end production-прогона с reflexion на retro.

v1.1 (2026-05-02) — применены 4 системные находки из phase-2/3/4 retro:
- F1: явный fallback-prompt template в Шаге -1 (methodology НЕ auto-enforced wrapper)
- F3: новая секция «Cross-phase MEDIUM tracker (retroactive backlog)» — алгоритм документирования MEDIUM с корнем в N-K фазе в run-логе предыдущей фазы
- (F2 ушло в `~/.claude/agents/_shared/budget_discipline.md` § «Per-page масштабирование word_target» — формула base + N×per_page_avg для content-strategist и visual-designer при N≥10)
- (F4a/F4b ушли в self-check'и `content-strategist.md` и `visual-designer.md` — Glob cardinality check vs sitemap)
