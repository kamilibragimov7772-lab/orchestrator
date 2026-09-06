> Исторический срез 8c7cbd8. Текущий статус публикации, независимого ревью и исправлений: [раунд 2](12_RELEASE_REVIEW_R2.md).

# Негативные сценарии и внедрение дефектов

Это targeted fault injection: испорченные входы, отказ дочерней команды, конфликт или несогласованное состояние. **Полный mutation engine не запускался; mutation score, killed mutants и процент покрытия не заявляются.** Набор тестов не равен случайному изменению всех строк production code.

| Дефект | Ожидаемая реакция | Сценарии |
|---|---|---|
| Удалены Bash/frontmatter/name/DoD | Линтер отклоняет карточку | test_agent_lint |
| Удалён canonical contract / вся agents tree | NOT CHECKED, nonzero | test_agent_lint |
| Хороший unstaged файл поверх плохого staged | Commit отклонён | test_pre_commit |
| Ключ в JSON escape или staged bytes | Exit 2 / rejected commit | test_guards, test_pre_commit |
| Force-push через quoting или substitution | Guard блокирует распознанный вариант | test_guards |
| Git commit/fetch/push завершается ошибкой | Failure, нет ложного success | test_sync |
| Два caller / index.lock / чужой staged index | Не начинать работу и сохранить чужое состояние | test_sync |
| Секрет добавлен и затем удалён в истории | Push блокируется | test_sync |
| Неоднозначный/missing artifact / сломанный Office | Приёмка не проходит | test_acceptance |
| Процесс приёмки вернул 0, но отчёта нет | Failure | test_acceptance_launch |
| Timeout reviewer | Lock освобождается, failure | test_acceptance_launch |
| Неправильный root экспорта / битый JSONL | Нет готового экспортированного результата | test_export |
| Установочная коллизия / повреждённый settings | Отказ до записи стека | test_install |
| Схемы CSV различаются | Отказ без выходного CSV | test_helpers |
| Анализатор упал, старый JSON лежит на диске | Error, старый результат не используется | test_helpers |

## Следующий этап

Приоритизировать мутации именно control flow: убрать stage scan, разрешить merge без --ff-only, вернуть PASS для отсутствующего artifact, убрать source containment и разрешить чужой index. Проверить, что существующие тесты ловят каждую мутацию. Не выбирать только дефекты, удобные текущему suite. Запускать в изолированном checkout, поскольку тесты содержат Git-операции.

## Методологическая опора

- Основной фреймворк: NIST SSDF 1.1, NIST, 2022 — риск, проверка, доказательство и управление остаточным риском.
- Дополнительная модель: SLSA 1.2, 2025 — направление контроля цепочки поставки; уровень SLSA не заявляется.
- Источники: [NIST SSDF](https://csrc.nist.gov/projects/ssdf), [SLSA 1.2](https://slsa.dev/spec/v1.2/), [Claude Code hooks](https://code.claude.com/docs/en/hooks).
- Дата проверки актуальности: 2026-09-06. Оценочная шкала и веса взяты из пользовательского аудиторского брифа; баллы — экспертная оценка, не стандарт NIST.
