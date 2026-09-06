# Установка

Дата проверки: 2026-09-06. Требования ядра: Python 3.10+, Git, UTF-8. Для агентных сценариев отдельно нужен авторизованный Claude Code. Отсутствие ffmpeg, моделей Silero, браузеров или MCP не мешает тестам ядра.

## 1. Проверьте исходники

```sh
python tools/verify.py
```

На Windows используйте `py -3` вместо `python`, если Python установлен через launcher; на Linux/macOS — `python3`, если команда `python` отсутствует. Зависимости ядра входят в стандартную библиотеку.

## 2. Выберите каталоги и профиль

PowerShell, пример с отдельной установкой:

```powershell
py -3 tools/install.py --destination 'C:/Work/orchestrator-stack' --vault 'C:/Work/orchestrator-vault' --mode minimal
py -3 tools/install.py --destination 'C:/Work/orchestrator-stack' --vault 'C:/Work/orchestrator-vault' --mode minimal --apply
py -3 tools/doctor.py --installed --root 'C:/Work/orchestrator-stack'
```

Linux/macOS:

```sh
python3 tools/install.py --destination "$HOME/orchestrator-stack" --vault "$HOME/orchestrator-vault" --mode minimal
python3 tools/install.py --destination "$HOME/orchestrator-stack" --vault "$HOME/orchestrator-vault" --mode minimal --apply
python3 tools/doctor.py --installed --root "$HOME/orchestrator-stack"
```

`minimal`: 7 основных карточек, общие контракты, ядро инструментов и команды orchestr/priyomka/checkpoint. Это ограниченный набор: остальные роли протокола не установлены и до их установки делегироваться не должны. `full`: все карточки и дополнительные рецепты; модели, браузеры, плагины и их зависимости не скачиваются.

Перед записью проверяются коллизии, JSON настроек и пути. Существующие permissions и hooks сохраняются; два guard добавляются без shell-склейки. Абсолютный путь к использованному Python сохраняется в настройках — после переноса или удаления интерпретатора запустите doctor. Записи атомарны по одному файлу; общей транзакции при сбое диска нет. Повтор одинаковой установки идемпотентен. Обновление изменённой установки требует нового каталога и осознанного переноса пользовательских настроек.

## 3. Подключите выбранную конфигурацию к Claude Code

Само наличие `CLAUDE_HOME` не переключает конфигурационный каталог Claude Code. При отдельном каталоге задайте переменную хоста:

```powershell
$env:CLAUDE_CONFIG_DIR = 'C:/Work/orchestrator-stack'
claude
```

```sh
CLAUDE_CONFIG_DIR="$HOME/orchestrator-stack" claude
```

У отдельного каталога может не быть авторизации и MCP основного профиля; настройте их средствами хоста. Установщик не копирует credentials. Для стандартного `~/.claude` используйте тот же установщик после проверки коллизий; не копируйте шаблон settings поверх своих настроек. `settings.example.json` содержит плейсхолдеры и служит схемой, а не готовой настройкой.

Первый агентный smoke: `/orchestr` на небольшом синтетическом брифе без отправок наружу. Проверить, что созданы run-лог и артефакт, ошибки зависимостей видны и приёмщик открыл именно заявленный файл. Автоматические тесты этого не заменяют.

## 4. Дополнительные возможности

- Экспорт: `ORCHESTRATOR_EXPORT_MODE=redacted` или `full`; обязательны `VAULT_ROOT` и `ORCHESTRATOR_TRANSCRIPT_ROOT`. Отдельное описание приватности — SECURITY.md. Зеркало рабочих папок удалено, `/MIR` не используется.
- Sync: точные пути в `sync-allowlist.txt`, заранее настроенные remote/main и ключи. PowerShell wrapper требует `ORCHESTRATOR_SYNC_ENABLED=1`. Не запускайте по расписанию до ручного smoke. Скрипт не трогает посторонний staged index и не разрешает divergence автоматически.
- Acceptance: [tools/acceptance-gate/README.md](tools/acceptance-gate/README.md). Не регистрируется автоматически.
- Video: [skills/video-montage/scripts/README.md](skills/video-montage/scripts/README.md); это адаптируемые рецепты, не универсальный рендерер.
- Silero: torch/soundfile и отдельно полученная доверенная модель. Загрузка pickle исполняет код модели; произвольные файлы не используйте.
- Site-build: отдельные Node/браузерные/MCP зависимости по соответствующей карточке. Их установка и успешность не подтверждаются doctor.

## 5. Откат

Установщик не меняет текущую конфигурацию Claude, если destination — отдельный каталог. Верните прежний `CLAUDE_CONFIG_DIR`, чтобы пользоваться прежним стеком. Пользовательскую базу знаний не удаляйте. Для изменения существующего стека предварительно сохраните его средствами своей системы резервного копирования; встроенного автоматического rollback всей установки нет.

## Методологическая опора

NIST SSDF 1.1 (2022), документация Claude Code (проверка 2026-09-06): [SSDF](https://csrc.nist.gov/projects/ssdf), [settings](https://code.claude.com/docs/en/settings), [hooks](https://code.claude.com/docs/en/hooks). Установка отделена от модельной и интеграционной приёмки.
