# Работа с изменениями

Читайте AGENTS.md. Не используйте живой vault, credentials или чужие Git-индексы как тестовые данные.

```sh
python tools/verify.py
git config core.hooksPath githooks
```

Guard, sync, validator и installer требуют регрессии, которая воспроизводит исправляемую ошибку. Тесты используют временные каталоги и локальные bare remotes. Модельные вызовы в tests замокированы; качество модели этим не подтверждается. Ожидаемые сообщения об ошибках внутри негативных тестов допустимы: смотрите итог unittest и exit команды.

При добавлении распространяемого файла обновите точный sync-allowlist после просмотра содержимого. Wildcards, личные настройки, журналы и vault туда не включать. Перед PR: verify, staged pre-commit, Gitleaks history и рабочей копии, diff --check. Workflow нужно реально выполнить на GitHub; необязательный skipped check не считать pass. Для новых зависимости нужны версия, источник, способ воспроизведения и граница доверия.

Минимальные регрессии не доказывают полный mutation score. Не подменяйте сценарии внедрения дефектов запуском mutation engine и не называйте подсчёт строк семантическим ревью.

## Методологическая опора

NIST SSDF 1.1 (2022), GitHub Actions security (проверено 2026-09-06): [SSDF](https://csrc.nist.gov/projects/ssdf), [secure use](https://docs.github.com/en/actions/reference/security/secure-use).
