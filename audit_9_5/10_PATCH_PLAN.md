> Исторический срез 8c7cbd8. Текущий статус публикации, независимого ревью и исправлений: [раунд 2](12_RELEASE_REVIEW_R2.md).

# Пакет изменений и порядок review

Все перечисленные реализации уже внесены в локальную ветку. Diff от базового commit позволяет оценивать изменения отдельно от исходной поставки.

| Группа | Файлы | Проверка перед включением |
|---|---|---|
| Core guards и приватность | tools/guard.py, secret_scan.py, export_session.py, hooks/*guard*, export-session | Negative fixtures + Gitleaks |
| Sync и staged защита | sync_stack.py, sync-allowlist.txt, pre_commit.py, githooks/pre-commit | Disposable bare remotes, index preservation, outgoing history |
| Валидаторы и приёмка | agent-lint.py, acceptance-gate/*, agent acceptance card | Frontmatter/path/Office fixtures, lifecycle mocks |
| Установка и CI | install.py, doctor.py, verify.py, fetch_gitleaks.py, .github/workflows | Clean destination, repeat install, matrix pending remote |
| Optional helper fixes | repo-inventory, merge_normalize, video scripts | Error propagation/schema/EDL tests; media render pending |
| Документация | AGENTS, README, INSTALL, SECURITY, CONTRIBUTING, CHANGELOG, audit_9_5 | Проверка соответствия фактическому поведению |

## Что не выкатывать автоматически

Не включать export/sync/acceptance Stop hooks в живой профиль без конфигурации. Не применять эту ветку поверх существующего стека копированием всего каталога. Не переименовывать модельные aliases только по памяти: fable существует в актуальной документации Claude. Не запускать старые медиа-рецепты на личной папке без явных source/work/output.

## Откат разработки

Базовый commit сохранён и неизменяем в локальной истории. Для изучения оригинала можно создать отдельный worktree от указанного base; это предпочтительнее сброса текущей ветки. Существующие незакоммиченные пользовательские изменения в удалённом/живом стеке не трогались.

## Методологическая опора

- Основной фреймворк: NIST SSDF 1.1, NIST, 2022 — риск, проверка, доказательство и управление остаточным риском.
- Дополнительная модель: SLSA 1.2, 2025 — направление контроля цепочки поставки; уровень SLSA не заявляется.
- Источники: [NIST SSDF](https://csrc.nist.gov/projects/ssdf), [SLSA 1.2](https://slsa.dev/spec/v1.2/), [Claude Code hooks](https://code.claude.com/docs/en/hooks).
- Дата проверки актуальности: 2026-09-06. Оценочная шкала и веса взяты из пользовательского аудиторского брифа; баллы — экспертная оценка, не стандарт NIST.
