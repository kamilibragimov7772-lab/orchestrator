> Исторический срез 8c7cbd8. Текущий статус публикации, независимого ревью и исправлений: [раунд 2](12_RELEASE_REVIEW_R2.md).

# Реестр находок

Статус ниже означает исправление указанного механизма и проверку в указанном объёме. P1/P2 — локальная приоритизация по ущербу и вероятности, не CVSS. Там, где проверка только synthetic/static, компонент в целом не объявляется принятым. Оригинал каждой изменённой строки сохраняется в Git относительно базового commit.

| ID | Приоритет | Проблема / путь | Сделано | Доказательство |
|---|---|---|---|---|
| F01 | P1 | Sync массово захватывает файлы. `hooks/sync-stack.ps1 → tools/sync_stack.py` | Заменён exact allowlist, чужой index сохраняется | test_sync: unknown_secret_file / existing_index |
| F02 | P1 | Git failure выглядит завершением sync. `tools/sync_stack.py` | Коды commit/fetch/merge/push проверяются, locks и FF-only | test_sync: commit_failure / failed_push / network_failure |
| F03 | P1 | Удалённый из HEAD секрет остаётся в outgoing history. `tools/sync_stack.py` | Проверяется каждое outgoing commit tree, не только diff HEAD | test_sync: removed_credential / added_then_removed_private_file |
| F04 | P1 | Автоэкспорт и зеркало способны переносить лишние данные. `hooks/export-session.ps1 → tools/export_session.py` | Opt-in, явные корни, redaction, удалено /MIR | test_export: disabled / outside_root / redacts |
| F05 | P1 | Selftest зависит от приватных backup. `tools/agent-lint.py` | Синтетические fixtures, без backup-файлов | test_agent_lint; agent-lint --selftest |
| F06 | P1 | Пустая выборка или сломанный frontmatter проходит. `tools/agent-lint.py` | Exit 2 для отсутствующего входа/контракта; обязательные поля | test_agent_lint: empty_tree / missing_frontmatter / missing_name |
| F07 | P1 | Рабочая копия скрывает сломанный staged файл. `githooks/pre-commit → tools/pre_commit.py` | Линт isolated staged snapshot | test_pre_commit: unstaged_fix_cannot_hide_broken_index |
| F08 | P1 | Нет воспроизводимой CI-проверки поставки. `tools/verify.py; .github/workflows/ci.yml` | Добавлены core matrix и Gitleaks jobs; удалённый gate открыт | Локальные verify PASS; GitHub run NOT TESTED |
| F09 | P1 | Защита команд пропускает перестановки и quoting. `tools/guard.py` | Нормализация и негативные регрессии; область эвристики ограничена | test_guards: quote_concatenation / reordered_delete_flags / substitution |
| F10 | P1 | Приёмка находит не тот относительный artifact. `tools/acceptance-gate/checks.py` | Привязка к явным базам, ambiguity и missing — ошибки | test_acceptance: path-related cases |
| F11 | P1 | Повреждённый Office и PDF-header дают ложное открытие. `tools/acceptance-gate/checks.py` | Проверка Office XML; PDF остаётся SKIP | test_acceptance: Office/PDF fixtures |
| F12 | P2 | Quoted/commented frontmatter и запятые в путях ломают проверку. `tools/acceptance-gate/checks.py` | Ограниченный детерминированный parser, duplicate keys fail | test_acceptance: frontmatter cases |
| F13 | P1 | Фоновый Start-Job заканчивается с родителем. `tools/acceptance-gate/launch.py` | Синхронный worker, timeout, run lock, проверка наличия отчёта | test_acceptance_launch; реальная модель NOT TESTED |
| F14 | P1 | Ручное копирование установки затирает конфигурацию. `tools/install.py; tools/doctor.py` | Preflight, merge, explicit paths, plan/apply | test_install + clean-install.json |
| F15 | P1 | CSV перемешивает несовпадающие колонки. `skills/geo-lead-parser/scripts/merge_normalize.py` | Выравнивание одного fieldset; разные схемы отклоняются | test_helpers: csv_reordered / incompatible / overwrite |
| F16 | P1 | Media продолжает работу после ошибки ffmpeg. `skills/video-montage/scripts/` | check=True, явные source/work/output, EDL validation | test_helpers + AST; render E2E NOT TESTED |
| F17 | P1 | Анализатор упал, inventory показывает ноль замечаний. `tools/repo-inventory/inventory.py` | Exit checks, fresh report directory, SKIP/error таблица | test_helpers: failed_tools / stale_duplicate_report |

## Открытые риски

| ID | Важность | Остаток | Критерий закрытия |
|---|---|---|---|
| R01 | P1 | Модельный reviewer имеет Edit за пределами одного run-лога; report-only — инструкция | Изолированный workspace или structured response + узкий writer; попытка изменить сторонний файл не проходит |
| R02 | P1 | Нет реального author→reviewer E2E и независимого семантического аудита | Закрытый синтетический прогон, отдельный reviewer, артефакт открыт, invalid case отклонён |
| R03 | P1 | CI не запускался удалённо, main protection не подтверждена | Все jobs зелёные на release SHA; обязательные checks реально блокируют broken PR |
| R04 | P2 | Python 3.10/macOS и media/site-build dependencies не воспроизведены | Матрица либо явно суженный supported scope + проверка optional recipes |
| R05 | P2 | Повторы и объём prompt contracts; 17 предупреждений dependency paths | Versioned shared contract и сравнительные сценарии без снижения качества |
| R06 | P2 | Budget/Trace структурные; legacy entry-file guard fail-open | Реальные source-of-truth usage/events; непроверенное отражается явно |
| R07 | P2 | Export redaction не удаляет все PII; retention не автоматизирован | Проверенная политика хранения и тест по выбранным типам данных |

Нет основания закрывать R01–R03 одной правкой README или повышением балла. Предыдущий аудит как отдельный подписанный артефакт не предоставлен; «все прежние замечания закрыты» не заявляется.

## Методологическая опора

- Основной фреймворк: NIST SSDF 1.1, NIST, 2022 — риск, проверка, доказательство и управление остаточным риском.
- Дополнительная модель: SLSA 1.2, 2025 — направление контроля цепочки поставки; уровень SLSA не заявляется.
- Источники: [NIST SSDF](https://csrc.nist.gov/projects/ssdf), [SLSA 1.2](https://slsa.dev/spec/v1.2/), [Claude Code hooks](https://code.claude.com/docs/en/hooks).
- Дата проверки актуальности: 2026-09-06. Оценочная шкала и веса взяты из пользовательского аудиторского брифа; баллы — экспертная оценка, не стандарт NIST.
