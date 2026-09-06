# Матрица проверок

| Проверка | Результат | Evidence / ограничение |
|---|---|---|
| Windows Python 3.12.14 verify | PASS: 86 unittest | verification-current.txt; ожидаемые error сообщения внутри negative tests |
| Ubuntu WSL Python 3.12.3 verify | PASS: 85, SKIP: 1 из 86 | verification-linux.txt; PowerShell не установлен в WSL |
| PowerShell 5.1.26100.9168 parse | PASS: 7 файлов | powershell51-parse.txt |
| PowerShell 7.6.5 parse | PASS: 7 файлов | powershell7-parse.txt |
| Guard wrapper stdin/exit | PASS на обеих Windows PS | test_guards; process-scoped ExecutionPolicy Bypass только для теста |
| Agent/shared lint | PASS: 51, errors 0, warnings 17 | Source warnings главным образом о внешних путях |
| Gotovo counter selftest | PASS: 5 | Внутри verify |
| Minimal/full fresh install | PASS + doctor PASS + repeat 0 | clean-install.json |
| Gitleaks original history / working tree | PASS: findings 0 | gitleaks history/working |
| Acceptance model lifecycle | PASS: 5 mock tests | acceptance-launch-final.txt; реальной модели нет |
| GitHub Actions / Python 3.10 / macOS | NOT TESTED | Workflow подготовлен |
| Claude/MCP/media/site E2E | NOT TESTED | Нужны среда и независимая приёмка |
| Полный mutation engine | NOT RUN | Использованы targeted fault injections, см. 06 |

## Повторение

Из checkout: `python tools/verify.py`. Для конкретного модуля: `python -m unittest discover -s tests -p test_sync.py -v`. Staged check: `python tools/pre_commit.py`. Gitleaks: `gitleaks git . --redact=100 --log-opts=--all` и `gitleaks dir . --redact=100`.

Тесты временные и локальные; bare remotes создаются в temp. Не нужен доступ к личному GitHub, SSH-серверу или vault. Системная политика PowerShell не изменялась. Test engine сообщает реальные skip; их число не добавляется к числу выполненных проверок.

## Методологическая опора

- Основной фреймворк: NIST SSDF 1.1, NIST, 2022 — риск, проверка, доказательство и управление остаточным риском.
- Дополнительная модель: SLSA 1.2, 2025 — направление контроля цепочки поставки; уровень SLSA не заявляется.
- Источники: [NIST SSDF](https://csrc.nist.gov/projects/ssdf), [SLSA 1.2](https://slsa.dev/spec/v1.2/), [Claude Code hooks](https://code.claude.com/docs/en/hooks).
- Дата проверки актуальности: 2026-09-06. Оценочная шкала и веса взяты из пользовательского аудиторского брифа; баллы — экспертная оценка, не стандарт NIST.
