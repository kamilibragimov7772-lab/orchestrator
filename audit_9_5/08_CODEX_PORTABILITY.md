> Исторический срез 8c7cbd8. Текущий статус публикации, независимого ревью и исправлений: [раунд 2](12_RELEASE_REVIEW_R2.md).

# Переносимость в Codex

Локально обнаружен `codex-cli 0.153.4`; выполнены только --version/--help. Проверены актуальные официальные разделы [Subagents](https://learn.chatgpt.com/docs/agent-configuration/subagents), [config reference](https://learn.chatgpt.com/docs/config-file/config-reference), [skills](https://learn.chatgpt.com/docs/build-skills). Документация обновляется быстрее репозитория; наличие CLI не доказывает совместимость данного стека.

| Слой | Переносимость | Что требуется |
|---|---|---|
| Методика брифа, контракты, run-лог | Высокая концептуальная | Адаптация имён tools, прав и lifecycle |
| Python checks/sync/export | Проверены Windows и Linux независимо от модели | Правильные roots и hook payload adapter |
| AGENTS.md | Вход для разработки уже добавлен | Это не порт всего runtime |
| Markdown frontmatter agents Claude | Прямое копирование не аттестовано | Codex custom-agent конфигурация TOML, mapping tools и instructions |
| Модельные aliases opus/sonnet/fable | Привязаны к Claude | Выбор доступных Codex моделей по владельцу; не механическая замена |
| Skills | Формат близок | Установка в поддерживаемую область skills, зависимости, имя и trigger |
| Hooks | Codex поддерживает lifecycle hooks | Преобразовать config и проверить payload, blocking/async, commandWindows |
| Acceptance CLI worker | Зависит от `claude` | Отдельный Codex runner с изоляцией и проверкой output |
| MCP | Принцип общий | Повторная настройка имён, авторизации и контрактов вызова |

Неверно утверждать, что Codex «вообще не имеет hooks/агентов»: текущая официальная конфигурация описывает оба механизма. Но общие названия событий не доказывают одинаковое поведение. Нативный Codex adapter в этой ветке **не реализован и не протестирован**.

Пилот переноса: один read-only reviewer, один синтетический artifact, один blocked malformed payload, один timeout. Затем расширение на роли; не генерировать 41 формально похожий конфиг без проверки исполнения.

## Методологическая опора

- Основной фреймворк: NIST SSDF 1.1, NIST, 2022 — риск, проверка, доказательство и управление остаточным риском.
- Дополнительная модель: SLSA 1.2, 2025 — направление контроля цепочки поставки; уровень SLSA не заявляется.
- Источники: [NIST SSDF](https://csrc.nist.gov/projects/ssdf), [SLSA 1.2](https://slsa.dev/spec/v1.2/), [Claude Code hooks](https://code.claude.com/docs/en/hooks).
- Дата проверки актуальности: 2026-09-06. Оценочная шкала и веса взяты из пользовательского аудиторского брифа; баллы — экспертная оценка, не стандарт NIST.
