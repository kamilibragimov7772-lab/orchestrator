# Изменения

## Hardening candidate — 2026-09-06

База: protocol 2.16.0 / commit 0c11e1b6c80e780d66df5e843fa0e44efd902b6a.

- Selftest больше не требует приватных backup-файлов; добавлены синтетические регрессии и общий verify.
- Линтер проверяет недостающий frontmatter и обязательные поля, привязывает локальные ссылки к выбранному checkout.
- Приёмка отклоняет неоднозначные пути, повреждённый Office и пустые обязательные поля; PDF signature возвращает incomplete, а не открытый документ.
- Secret/risk guards вынесены в portable Python; PowerShell служит ASCII wrapper.
- Sync заменяет массовый add/autostash на exact allowlist, locks, staged/outgoing scanning и fast-forward-only.
- Export выключен, требует явных корней и режима. Автоматическое зеркало папок и /MIR удалены.
- Acceptance worker ожидает завершения модели, проверяет наличие отчёта, не использует короткоживущий Start-Job. Live E2E ещё не подтверждён.
- Установщик поддерживает plan/apply, минимальный профиль, preflight и merge настроек. Автоматические Stop hooks не включаются.
- CI проверяет код, PowerShell syntax и Gitleaks. Удалённое исполнение и branch protection остаются отдельным release gate.
- CSV выравнивает одинаковые колонки в другом порядке и отклоняет разные схемы. Video-рецепты требуют явных task directories и прекращаются при ошибке ffmpeg. Inventory показывает провал анализатора и не запускает npx по умолчанию.

Это изменения поведения. Старые рецепты автоматической синхронизации и зеркалирования не сохраняют прежний способ запуска; используйте текущие INSTALL и SECURITY.

## Методологическая опора

Risk-based hardening по NIST SSDF 1.1 (2022), проверено 2026-09-06: [SSDF](https://csrc.nist.gov/projects/ssdf), [Claude hooks](https://code.claude.com/docs/en/hooks).
