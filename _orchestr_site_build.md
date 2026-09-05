<!--
Подреестр site-build pipeline. Подгружается оркестратором ТОЛЬКО по триггеру сборки сайта.
Вынесен из _orchestr_protocol.md 2026-05-29.
-->

# Site-build pipeline — подреестр

Сборка нового корпоративного многостраничного сайта, фазы 0-8. Запускаются строго по фазам.

## Политика ревью (важно для экономии контекста)

По умолчанию каждая фаза = 1 проход агента-автора, БЕЗ обязательного ревьюера. Ревьюер (architecture-reviewer / content-reviewer / design-reviewer / code-reviewer / usability-reviewer и аудиторы) подключается ТОЛЬКО если: (а) пользователь явно просит максимальное качество / "с проверкой"; либо (б) фаза критична (финальный quality-gate перед запуском в прод). Полные 3 итерации автор↔ревьюер — только по явному запросу. Причина: пары автор+ревьюер ×3 — самый дорогой по контексту паттерн, оправдан лишь на часто запускаемых пайплайнах, а site-build запускается редко (по логам — 1 раз за всё время).

## Агенты pipeline (19)

Запускаются строго по фазам, ревьюеры — в паре «автор + ревьюер», лимит 3 итерации (только при включённом ревью, см. политику выше):

- site-discoverer — Tier 1 Discovery (фаза 0). Бизнес-цели, ЦА, KPI, конверсионные сценарии, контент-аудит + конкурентный teardown 3-5 игроков → `00_discovery.md`. Только корпоративные сайты 10-30 страниц (не SaaS, не e-commerce).
- discovery-reviewer — Tier 5 ревьюер фазы 0. Полнота `00_discovery.md` по custom checklist → `critique_v<N>.md`.
- ia-architect — Tier 2 Information Architecture (фаза 1). sitemap (≤3 уровня, mobile-first), user flows (≥3 сценария), navigation. Greenfield + retro-validation.
- architecture-reviewer — Tier 5 ревьюер фазы 1. 4 IA-артефакта по оси АРХИТЕКТУРА.
- content-strategist — Tier 2 Content Strategy (фаза 2). tone_of_voice.md, page_outlines/<slug>.md, seo_strategy.md. Greenfield + retro-validation.
- content-reviewer — Tier 5 ревьюер фазы 2 по оси НАПОЛНЕННОСТЬ.
- design-system-architect — Tier 2 Design System (фаза 3). tokens.json (W3C), typography (кириллица обязательна), motion, components_atomic (Brad Frost). Greenfield + retro-validation.
- visual-designer — Tier 2 Visual Design (фаза 4). `04_visuals/<slug>.spec.md` — текстовая спека каждой страницы (компоненты, состояния, motion). НЕ пиксельные макеты (шаг только для человека).
- design-reviewer — Tier 5 ревьюер фаз 3+4 по осям ДИЗАЙН + ЮЗАБИЛИТИ.
- astro-engineer — Tier 4 Engineering (фазы 5-6). Setup Astro 5+ (TS strict, Tailwind, content collections) + Implementation по spec-файлам. Setup один раз, implementation по разделам.
- code-reviewer — Tier 5 ревьюер фаз 5-6 (Astro/TS/CSS по структурным критериям).
- usability-reviewer — Tier 5 ревьюер фазы 6 (manual, 10 эвристик Nielsen + Mobile UX + Cognitive Load; без автотулов).
- performance-auditor — Tier 5 ревьюер фазы 7. Lighthouse CLI, Core Web Vitals 2026 (LCP<2.5s, INP<200ms, CLS<0.1, Perf≥90 mobile).
- accessibility-auditor — Tier 5 ревьюер фаз 6-7. axe-core/Pa11y + manual screen reader, WCAG 2.2 AA. Threshold: 0 critical/serious.
- security-auditor — Tier 5 ревьюер фазы 7. npm audit + security headers + securityheaders.com + 152-ФЗ комплаенс. Threshold: 0 high CVE, min A.
- seo-auditor — Tier 5 ревьюер фазы 7. Lighthouse SEO≥95, meta/canonical/OG, sitemap.xml, robots.txt, JSON-LD через Rich Results.
- visual-regression-auditor — Tier 5/6 визуальная проверка dist/ против spec/Figma (скриншоты desktop/mobile, pixel-diff regression).
- final-quality-gate — Tier 7 агрегатор фаз 7-8. Собирает 4 отчёта аудиторов + usability + code-review → вердикт ship/not-ship («любой HIGH critical = not-ship»). Сам не аудитит.
- deploy-engineer — Tier 6 Launch (фаза 8). Деплой Vercel/Netlify/Cloudflare + DNS/SSL + аналитика + monitoring + headers → `08_launch/runbook.md`.
