# Публичные API — карта под задачи пользователя

> **Версия:** 1.0.0 · **Собрана:** 2026-07-28 · **Источник:** [public-apis/public-apis](https://github.com/public-apis/public-apis) (1625 API, 50 категорий, MIT).
> **Подгружать ТОЛЬКО по указателю из `_orchestr_protocol.md`** (секция «Публичные API»). Без нужды не читать — экономия контекста.
> Локальная копия README каталога: `~/.claude/projects/<project-key>/*/tool-results/mcp-open-websearch-fetchGithubReadme-*.txt` (обновляется через `mcp__open-websearch__fetchGithubReadme`, у WebFetch `github.com` заблокирован).

Отобраны позиции, которые ложатся на классы задач стека (см. роутер ниже). Всё остальное (аниме, покемоны, гороскопы, транспорт Осло) — не внесено намеренно.

---

## Четыре правила, без которых карта вредна

### 1. Дёргает тот, у кого есть Bash — иначе оркестратор кладёт срез в `inputs/`

Это тот же паттерн, что «агенты не ходят по SSH» (P0-6): **интеллект — агенту, сетевое действие — оркестратору.**

- `WebFetch` **не годится для API**: он скармливает страницу маленькой модели и возвращает пересказ. JSON после него — уже не JSON. Для API нужен сырой ответ: `Invoke-RestMethod` / `curl` через Bash/PowerShell.
- Агенты с сырым доступом (`Bash` в списке тулзов): `general-purpose`, `claude`, `python-build-engineer`, `astro-engineer`, `infra-engineer`, `document-compiler`, `deploy-engineer`, `security-auditor`, `performance-auditor`, `seo-auditor`, `accessibility-auditor`, `final-quality-gate`, `knowledge-curator`, `silent-failure-hunter`, `harness-optimizer`, `visual-regression-auditor`, `b2b-strategy-auditor`, `visual-design-auditor`.
- Агенты **без** Bash (`strategy-researcher`, `competitor-intel`, `decision-analyst`, `synthesizer`, `ghostwriter`, `interesting-narrator`, `task-author`, `content-strategist`, `visual-designer`, `design-system-architect`, `brief-architect`, ревьюеры фаз 0-4) — API дёрнуть **не могут**. Им данные кладёт оркестратор в `<VAULT_ROOT>/08-Работа-Claude/<session>/inputs/` готовым JSON/CSV.
- Не переписывай тулзы агенту ради одного запроса. Дешевле — один вызов оркестратором.

### 2. 152-ФЗ: чужие персональные данные в сторонний API не уходят

Базы ЛПР, контакты клиентов заказчика, анкеты с выставок, выгрузки из CRM клиента — это **персональные данные третьих лиц**. Прогон их через зарубежный валидатор почты/телефона = трансграничная передача ПДн без основания.

- **Можно:** валидировать *синтаксис и домен* локально (regex + MX-проверка через `host-t.com` или свой резолвер).
- **Можно:** гнать через внешний API **обезличенное** — только домен компании, только город, только ИНН.
- **Нельзя без решения пользователя:** заливать список email/телефонов физлиц в Disify/EVA/Kickbox/Numverify и подобные.
- Спорный случай → останавливаемся и спрашиваем, а не «ну это же просто валидация».

### 3. Каталог — не живая правда

Строка в public-apis говорит, что API *существовал* на момент правки. Перед тем как строить на нём работу — **один пробный запрос**. Ответ 200 + ожидаемая схема = можно. Иначе берём соседа из той же строки таблицы, а карту правим.

### 4. Сеть может быть обрывочной

Часть доменов из CLI может не подниматься (маркетплейсы, github, npm). Порядок действий при таймауте: (1) повторить, (2) попросить пользователя проверить VPN на его машине, (3) только потом объявлять API нерабочим. **Не выдавать сетевой отказ за отсутствие данных.** Проксировать трафик через рабочие серверы запрещено.

---

## Быстрый роутер: задача → куда смотреть

| Пришло от пользователя | Раздел ниже | Кто дёргает |
|---|---|---|
| «посчитай сделку / КП / маржу», закупка в валюте | §1 Деньги | оркестратор → финкалькулятор проекта (внешний скил, см. README) |
| «когда выставка», «рабочий ли день», контент-план, дедлайны | §2 Календарь | оркестратор, `task-author` (данные в inputs/) |
| уличное мероприятие, выездная съёмка, полёт дрона | §3 Погода | оркестратор → `python-build-engineer` |
| «собери базу компаний», города, координаты, радиусы | §4 Гео | `/geo-lead-parser` |
| «почисти базу перед рассылкой» | §5 Чистка баз | оркестратор (см. правило 2!) |
| «разведай контрагента», санкции, юрриск, патент | §6 Разведка | `competitor-intel`, `decision-analyst` |
| ресёрч рынка, нужны свежие авторитетные источники | §7 Наука и статистика | оркестратор → в inputs/ для `strategy-researcher` |
| график/схема в отчёт, docx, презентацию | §8 Графика в документы | `document-compiler`, `report-designer` |
| ролик, заставка, палитра, иконки, музыка | §9 Ассеты | `/hyperframes` + `/media-use` (вендорные скилы, внешняя зависимость) |
| QR, штрихкод, маркировка коробов | §10 Печать и коды | `task-author`, генераторы доков |
| скан анкет, PDF, конверсия форматов | §11 Документы | `document-compiler` |
| «проверь сайт», аудит, безопасность | §12 Аудит сайта | `security-auditor`, `seo-auditor` |
| прокси лёг, DNS, «сервис живой?» | §13 Инфра | `infra-engineer` |
| прототип дашборда/сайта, нужны фейковые данные | §14 Тестовые данные | `astro-engineer`, `site-editor` |
| постинг, мультиканал | §15 Соцсети | `ghostwriter` |
| перевод, зарубежные поставщики, тональность | §16 Тексты | оркестратор → в inputs/ |
| авиация и БПЛА, рельеф, ветер по высотам | §17 БПЛА | `python-build-engineer` |

---

## §1. Деньги, курсы, налоги

Под финкалькулятор проекта (внешний скил), `decision-analyst`, финмодели клиентских проектов.

| API | Что даёт | Ключ | Заметка |
|---|---|---|---|
| [Банк России](https://www.cbr.ru/development/SXML/) | Официальные курсы ЦБ, XML | нет | **Основной для рублёвых расчётов.** Курс валюты закупок — отсюда. ✅ `GET https://www.cbr.ru/scripts/XML_daily.asp` (кодировка windows-1251) |
| [Currency-api](https://github.com/fawazahmed0/currency-api#readme) | 150+ валют + крипта, без лимита | нет | ✅ Живой, RUB и CNY есть, с ЦБ сходится (28.07: USD/RUB 78,02 против 78,0172 у ЦБ). Быстрый JSON вместо XML: `https://cdn.jsdelivr.net/npm/@fawazahmed0/currency-api@latest/v1/currencies/usd.json` |
| [Frankfurter](https://www.frankfurter.app/docs) | Курсы ЕЦБ, история, временные ряды | нет | ⚠️ **Рубля не отдаёт** — ЕЦБ не публикует RUB с 2022, запрос `to=RUB` даёт 404. Годится для EUR/USD/CNY и исторических рядов, для рубля — нет |
| ~~exchangerate.host~~ | | | ❌ **Требует ключ** (проверено 28.07.2026, в каталоге помечен как бесплатный — каталог устарел). Не использовать |
| [VATComply](https://www.vatcomply.com/documentation) | Курсы + проверка VAT (ЕС) | нет | Только ЕС; российского ИНН не знает |
| [Statistics of the World](https://statisticsoftheworld.com/api-docs) | ВВП, инфляция, 440+ индикаторов IMF/World Bank, 218 стран | нет | Макро-фон в стратегические записки |

**Чего нет:** налоговых ставок РФ, ключевой ставки ЦБ отдельным эндпоинтом, данных ФНС. НДС 22% с 2026 и прайсы — в финкалькуляторе проекта, а не отсюда.

---

## §2. Календарь, рабочие дни, праздники

Под календарное планирование: выставки, контент-планы, сроки в ТЗ.

| API | Что даёт | Ключ | Заметка |
|---|---|---|---|
| [isdayoff.ru](https://isdayoff.ru) | Рабочий / выходной / сокращённый день по производственному календарю РФ и СНГ | нет | **Главный по РФ.** `GET https://isdayoff.ru/20260728` → `0` рабочий, `1` выходной |
| [Russian Calendar](https://github.com/egno/work-calendar) | То же, вторым источником | нет | Сверять при расхождении на переносах |
| [Nager.Date](https://date.nager.at) | Праздники 90+ стран | нет | Для международных дедлайнов и китайских поставщиков (китайский Новый год = стоп производства) |
| [caldays](https://caldays.com/api) | Праздники 195+ стран | нет | Фолбэк к Nager |

**Правило:** срок в ТЗ, попадающий на выходной или длинные праздники, — помечать при постановке задачи, а не после срыва. Особенно январь и майские.

---

## §3. Погода, воздух, съёмочные условия

Под выездные съёмки, уличные мероприятия, расчёты полётов.

| API | Что даёт | Ключ | Заметка |
|---|---|---|---|
| [Open-Meteo](https://open-meteo.com/) | Прогноз, история, почва, ветер по высотам | нет | **Рабочая лошадка.** Лицензия — некоммерческое использование; для клиентского продукта смотреть их тариф |
| [Meltema](https://meltema.com/docs) | GFS + ECMWF + ансамбль GEFS, точечный прогноз | нет | Когда важна не «погода», а разброс сценариев |
| [Pirate Weather](https://pirateweather.net/en/latest/) | Аналог Dark Sky | нет | |
| [wttr.in](https://wttr.in/:help) | Погода строкой или JSON | нет | Быстрая справка прямо в терминале |
| [RainViewer](https://www.rainviewer.com/api.html) | Радар осадков | нет | «Успеем снять до дождя» |
| [Sunrise and Sunset](https://sunrise-sunset.org/api) | Восход/закат по координатам | нет | **Золотой час для съёмки** — считать до выезда, а не на месте |
| [AviationWeather (NOAA)](https://www.aviationweather.gov/dataserver) | METAR/TAF, авиапрогнозы | нет | Ветер и видимость под полёты |
| [OpenAQ](https://docs.openaq.org/) | Качество воздуха | да, free | |
| [AQICN](https://aqicn.org/api/) | Индекс качества воздуха, 1000+ городов | да, free | |

---

## §4. Гео: координаты, адреса, административное деление

Под `/geo-lead-parser`, карты в дашбордах, логистику клиента.

| API | Что даёт | Ключ | Заметка |
|---|---|---|---|
| [Nominatim (OSM)](https://nominatim.org/release-docs/latest/api/Overview/) | Прямой и обратный геокодинг по всему миру | нет | **Жёсткий лимит 1 запрос/сек и обязательный User-Agent.** Массовый прогон — только с задержкой, иначе бан |
| [OpenStreetMap API](http://wiki.openstreetmap.org/wiki/API) | Сырые объекты карты | OAuth | Тяжелее Nominatim, но даёт объекты, а не строки |
| [Geokeo](https://geokeo.com) | Геокодинг, 2500 запросов/день | нет | Фолбэк Nominatim |
| [GeoNames](http://www.geonames.org/export/web-services.html) | Населённые пункты, иерархия, координаты | нет | Только HTTP — данные не чувствительные, но помнить |
| [administrative-divisions-db](https://github.com/kamikazechaser/administrative-divisions-db) | Административное деление стран | нет | Регионы РФ для нарезки баз по территориям |
| [REST Countries](https://restcountries.com) | Страны: валюта, языки, флаги, границы | нет | Справочник в дашборды и презентации |
| [Open Topo Data](https://www.opentopodata.org) | Высота над уровнем моря по координатам | нет | Рельеф — см. §17 |
| [LocationIQ](https://locationiq.org/docs/) / [OpenCage](https://opencagedata.com) | Геокодинг с нормальным лимитом | да, free | Когда Nominatim не тянет объём |

**Чего нет и не будет:** 2ГИС и Яндекс.Карты без ключа. Массовый сбор карточек компаний остаётся за `/geo-lead-parser` (боевой прогон — headful, 2ГИС режет headless).

---

## §5. Чистка баз перед обзвоном и рассылкой

⚠️ **Сначала перечитать правило 2 (152-ФЗ).** Всё ниже — только по решению пользователя и по возможности на обезличенных данных.

| API | Что даёт | Ключ | Заметка |
|---|---|---|---|
| [Disify](https://www.disify.com/) | Одноразовые и мусорные почтовые домены | нет | Проверка **домена**, не адреса — самый безопасный режим |
| [MailCheck.ai](https://www.mailcheck.ai/#documentation) | То же, второй источник | нет | |
| [EVA](https://eva.pingutil.com/) | Валидность адреса | нет | Адрес уходит третьей стороне — см. правило 2 |
| [Kickbox open](https://open.kickbox.com/) | Проверка доставляемости | нет | Тот же риск |
| [Agify](https://agify.io) · [Genderize](https://genderize.io) · [Nationalize](https://nationalize.io) | Возраст / пол / страна по имени | нет | **Обращение в письме** («уважаемый / уважаемая»). По русским именам ошибается — держать словарь-исключения |
| [Veriphone](https://veriphone.io) / [Numverify](https://numverify.com) | Валидация телефона, оператор | да, free | Номер — это ПДн. Отдельное решение пользователя |
| [Hunter](https://hunter.io/api) | Поиск корпоративной почты по домену | да, free 25/мес | Лидген по компании, не по человеку |
| [host-t.com](https://host-t.com) | DNS-запрос через HTTP GET | нет | **Безопасный путь:** проверить MX домена, не отдавая адрес |

---

## §6. Разведка контрагентов, санкции, интеллектуальная собственность

Под `competitor-intel`, `b2b-strategy-auditor`, `decision-analyst`, due diligence по контрагентам клиентов и партнёрским проектам.

| API | Что даёт | Ключ | Заметка |
|---|---|---|---|
| [OpenSanctions](https://www.opensanctions.org/docs/api/) | Санкционные списки, PEP, розыск | нет | **Обязательная проверка** перед сделкой с иностранным контрагентом |
| [OpenCorporates](http://api.opencorporates.com/documentation/API-Reference) | Юрлица и директора многих юрисдикций | да | Офшоры и материнские структуры холдингов |
| [Microlink.io](https://microlink.io) | Структурированные данные с любого сайта | нет | Быстрый снимок сайта конкурента без поднятия браузера |
| [Domainsdb.info](https://domainsdb.info/) | Поиск доменов по подстроке | нет | Смежные бренды, домены-клоны |
| [Wikipedia](https://www.mediawiki.org/wiki/API:Main_page) / [Wikidata](https://www.wikidata.org) | Факты, структура холдингов | нет | Проверяемая фактура вместо «модель помнит» |
| [USPTO](https://www.uspto.gov/learning-and-resources/open-data-and-mobility) · [PatentsView](https://patentsview.org/apis/purpose) | Патенты США | нет | Аналоги решений клиента на внешних рынках |
| [EPO](https://developers.epo.org/) | Европейские патенты | OAuth | |
| [markerapi](https://markerapi.com) | Поиск товарных знаков (US) | нет | По РФ бесполезен |

**Чего нет:** ЕГРЮЛ/ЕГРИП, ФНС, Роспатент, DaData. Российская юрпроверка — руками через открытые реестры, каталог тут не помощник.

---

## §7. Наука, статистика, первоисточники

Прямо под требование методологической дисциплины из `CLAUDE.md` — «свежие авторитетные источники, не старше 24 месяцев».

| API | Что даёт | Ключ | Заметка |
|---|---|---|---|
| [arXiv](https://arxiv.org/help/api/user-manual) | Препринты: ИИ, экономика, физика | нет | Первоисточник вместо пересказа в блоге |
| [OpenAlex](https://docs.openalex.org/) | 250М+ научных работ, авторы, цитирования | нет | Проверить, жив ли фреймворк и кто его критиковал |
| [CORE](https://core.ac.uk/services#api) | Полные тексты открытого доступа | да, free | |
| [World Bank](https://datahelpdesk.worldbank.org/knowledgebase/topics/125589) | Макропоказатели по странам | нет | |
| [Open Science Framework](https://developer.osf.io) | Дизайны исследований, данные | нет | |

**Как применять:** оркестратор дёргает и кладёт выжимку в `inputs/` — у `strategy-researcher` и `synthesizer` нет Bash (правило 1). В секции «Методологическая опора» ссылаться на конкретную работу с DOI, а не на «исследования показывают».

---

## §8. Графики и схемы в документы

Под `document-compiler`, `report-designer`, `synthesizer`. Закрывает больную тему: картинка в docx/pptx/Telegram без запуска браузера и matplotlib.

| API | Что даёт | Ключ | Заметка |
|---|---|---|---|
| [QuickChart](https://quickchart.io/) | Chart.js-график картинкой по URL | нет | **Основной.** PNG/SVG вставляется в docx, pptx и уходит в Telegram как есть |
| [Image-Charts](https://documentation.image-charts.com/) | Графики + QR | нет | Фолбэк QuickChart |
| [Kroki](https://kroki.io) | Диаграммы из текста: Mermaid, Graphviz, PlantUML → PNG/SVG | нет | **Issue tree и causal map** — текстом, без ручной рисовки |
| [CodeCogs](https://editor.codecogs.com/docs/4-LaTeX_rendering.php) | Формулы LaTeX → PNG/SVG | нет | Финмодели и инженерные расчёты |
| [DummyImage](https://dummyimage.com/) | Плейсхолдеры с размером и цветом | нет | Макеты до реальных фото |

**Правило смоук-чека (P1-14) действует:** картинку из API открыть в том виде, где её увидит адресат — в реальном Word, реальном PowerPoint, в Telegram на телефоне.

---

## §9. Ассеты: цвет, иконки, шрифты, музыка, конверсия

Под `/hyperframes` + `/media-use` (вендорные скилы — внешняя зависимость, см. README), `visual-designer`, `design-system-architect`, `site-editor`, `kinetic-promo`.

| API | Что даёт | Ключ | Заметка |
|---|---|---|---|
| [Colormind](http://colormind.io/api-access/) | Генератор палитр | нет | Стартовая палитра, дальше — брендбук проекта |
| [xColors](https://x-colors.herokuapp.com/) · [Serialif Color](https://color.serialif.com/) | Конверсия цветов, контраст, комплементарные | нет | Проверка контраста под WCAG |
| [Icons8](https://img.icons8.com/) | Иконки | нет | |
| [Lordicon](https://lordicon.com/) | **Анимированные** иконки | нет | Прямо в моушн-сцены |
| [Icon Horse](https://icon.horse) | Фавикон любого сайта | нет | Логотипы конкурентов в сравнительные таблицы |
| [EmojiHub](https://github.com/cheatsnake/emojihub) | Эмодзи по категориям | нет | |
| [Lorem Picsum](https://picsum.photos/) | Фото-плейсхолдеры | нет | |
| [PHP-Noise](https://php-noise.com/) | Шумовые фоны | нет | Текстура вместо плоского градиента — прямое лекарство от «скудного» вывода |
| [Google Fonts](https://developers.google.com/fonts/docs/developer_api) | Метаданные шрифтов, поддержка кириллицы | да, free | **Проверять кириллицу до вёрстки** |
| [Jamendo](https://developer.jamendo.com/v3.0/docs) | Музыка под лицензией CC | OAuth | Легальный трек в ролик |
| [Freesound](https://freesound.org/docs/api/) | Звуки и семплы | да, free | Шумы, удары, переходы |
| [Radio Browser](https://api.radio-browser.info/) | Каталог интернет-радио | нет | |
| [oyyi](https://oyyi.xyz/docs/1.0) | Конверсия и оптимизация картинок/видео, PDF, превью | нет | Без локального ffmpeg |
| [Vector Express](https://vector.express) | Конверсия векторов: AI, EPS, SVG, PDF | нет | **Логотипы клиентов в печать** |
| [jsDelivr](https://github.com/jsdelivr/data.jsdelivr.com) · [CDNJS](https://api.cdnjs.com/libraries/jquery) · [Statically](https://statically.io/) | Библиотеки с CDN | нет | GSAP всё равно **вендорить локально** — на VPN CDN рвётся |

---

## §10. QR, штрихкоды, маркировка

Под `task-author`, генераторы отгрузочных документов, печать на упаковке клиента.

| API | Что даёт | Ключ | Заметка |
|---|---|---|---|
| [QR & Barcode](https://solsigs.com/qrapi/) | QR + Code 128, EAN-13, Data Matrix, PDF417; SVG/PNG | нет | **EAN-13 и Data Matrix — маркировка коробов и паллет** |
| [goQR.me](http://goqr.me/api/) | Генерация и чтение QR | нет | Простой GET, вставляется в HTML-генераторы |
| [QR code (qrtag)](https://www.qrtag.net/api/) | QR + короткая ссылка | нет | |
| [QR Code Crafter](https://qrcodecrafter.com/qr-code-api) | QR в SVG, PDF, EPS | нет | **Векторный QR в типографию** — растр печатать нельзя |

---

## §11. Документы, сканы, оцифровка

Под `document-compiler` и оцифровку бумажных анкет.

| API | Что даёт | Ключ | Заметка |
|---|---|---|---|
| [OCR.Space](https://ocr.space/ocrapi) | OCR картинок и PDF, русский поддерживается | да, free | Кандидат в **фолбэк** к связке PyMuPDF + vision-агенты. Живой контур не менять без замера точности |
| [iLovePDF](https://developer.ilovepdf.com/) | Слияние, разбивка, сжатие, текст из PDF | да, free 250 док/мес | Пакетная обработка вместо ручной |
| [Vector Express](https://vector.express) | Конверсия векторных форматов | нет | См. §9 |
| [oyyi](https://oyyi.xyz/docs/1.0) | Оптимизация PDF, превью | нет | |

⚠️ Анкеты с выставки содержат ПДн — правило 2 применяется целиком. Внешний OCR для них только с решения пользователя.

---

## §12. Аудит сайта: безопасность, доступность, SEO

Под `security-auditor`, `seo-auditor`, `performance-auditor` фазы 7 site-build. Все трое **с Bash** — дёргают сами.

| API | Что даёт | Ключ | Заметка |
|---|---|---|---|
| [Mozilla HTTP Observatory](https://github.com/mozilla/http-observatory/blob/master/httpobs/docs/api.md) | Оценка заголовков безопасности | нет | Второй источник к securityheaders.com |
| [Mozilla TLS Observatory](https://github.com/mozilla/tls-observatory#api-endpoints) | Проверка TLS-конфигурации | нет | |
| [National Vulnerability Database](https://nvd.nist.gov/vuln/Data-Feeds/JSON-feed-changelog) | CVE официально | нет | Сверять находки `npm audit` |
| [URLhaus](https://urlhaus.abuse.ch/api/) | База вредоносных URL | нет | Проверка внешних ссылок на сайте клиента |
| [Website Carbon](https://api.websitecarbon.com/) | Углеродный след страницы | нет | Аргумент в ESG-разделах для B2B |
| [Open Page Rank](https://www.domcop.com/openpagerank/) | Сравнение доменов | да, free | клиент против конкурента одной цифрой |
| [isitdownstatus](https://isitdownstatus.com) | Сайт лежит или только у нас | нет | До того как чинить то, что не сломано |

**Не отменяет правило ворот (P1-8):** ставим против **работающего сайта**, не против спеки.

---

## §13. Инфра, сеть, диагностика

Под `infra-engineer` и вечную историю с прокси и VPN.

| API | Что даёт | Ключ | Заметка |
|---|---|---|---|
| [Cloudflare Trace](https://github.com/fawazahmed0/cloudflare-trace-api) | Свой IP, страна, TLS, HTTP-версия | нет | **Быстрый ответ «через какую страну я сейчас хожу»** |
| [IPify](https://www.ipify.org/) · [ip-fast](https://ip-fast.com/docs/) · [icanhazip](https://major.io/icanhazip-com-faq/) | Внешний IP | нет | Три независимых — годятся для сверки |
| [IPLogs](https://iplogs.com/docs) | Детект VPN, прокси, Tor, дата-центра | нет | Проверить, как нас видит внешний сервис |
| [host-t.com](https://host-t.com) | DNS через HTTP GET | нет | Когда резолвер локально врёт |
| [NetworkCalc](https://networkcalc.com/api/docs) | Подсети, DNS, бинарные калькуляторы | нет | |
| [DownStatus](https://isitdownstatus.com) | Статус GitHub, AWS, Discord и 90+ сервисов | нет | Отделить «упал сервис» от «упали мы» |
| [npm Registry](https://github.com/npm/registry/blob/master/docs/REGISTRY-API.md) | Версии и метаданные пакетов | нет | Проверить версию, не запуская `npm install` на рвущемся канале |
| [Httpbin](https://httpbin.org/) | Эхо-сервер HTTP | нет | Отладка заголовков и прокси |

**Порты сервера не трогаем** — правило из `CLAUDE.md` действует; карта портов — внешняя зависимость, см. README.

---

## §14. Тестовые данные и прототипы

Под `astro-engineer`, `site-editor`, `python-build-engineer`, макеты дашбордов до реальных данных.

| API | Что даёт | Ключ | Заметка |
|---|---|---|---|
| [DummyJSON](https://dummyjson.com/) | Товары, юзеры, посты, корзины | нет | Прототип каталога до выгрузки клиента |
| [JSONPlaceholder](https://jsonplaceholder.typicode.com) | Классический фейковый REST | нет | |
| [FakerAPI](https://fakerapi.it/en) | Наборы фейковых данных | нет | |
| [RandomUser](https://randomuser.me) | Пользователи с фото | нет | |
| [Dicebear](https://avatars.dicebear.com/) · [RoboHash](https://robohash.org/) | Аватары | нет | Вместо стоковых лиц |
| [Mocky](https://designer.mocky.io/) · [Beeceptor](https://beeceptor.com/) | Свой мок-эндпоинт за минуту | нет | Фронт живёт, пока бэка нет |
| [ReqRes](https://reqres.in/) | Готовый REST с авторизацией | нет | |

⚠️ Фейковые данные **не должны доехать до демо клиенту**. Помечать в коде и вычищать перед сдачей — это ровно тот класс тихого отказа, который ловит `silent-failure-hunter`.

---

## §15. Соцсети и публикация

Под `ghostwriter` и задачи публикации.

| API | Что даёт | Ключ | Заметка |
|---|---|---|---|
| [Telegram Bot](https://core.telegram.org/bots/api) | Боты, отправка, файлы | токен | Отправка файлов — через multipart-клиент (.NET / curl); Python urllib на файлах таймаутит |
| [Telegraph](https://telegra.ph/api) | Публикация лонгридов | токен | Длинный текст в Telegram без ботов |
| [VK](https://vk.com/dev/sites) | Публикация и чтение | OAuth | Живой канал для РФ-клиентов |
| [Bluesky](https://docs.bsky.app/) | AT-протокол | нет | Открытый протокол, ключ не нужен |
| [Ayrshare](https://www.ayrshare.com) · [PostLake](https://postlake.dev/docs/) | Мультипостинг в один запрос | да | Бенчмарк функционала для собственных SMM-инструментов и возможный бэкенд |
| [HackerNews](https://github.com/HackerNews/API) | Тренды у разработчиков | нет | |

**Чего нет:** Instagram и TikTok без OAuth-приложения. Публикация в IG — только через собственное OAuth-приложение (токен истекает — за сроком следить).

---

## §16. Тексты: перевод, тональность, язык

| API | Что даёт | Ключ | Заметка |
|---|---|---|---|
| [LibreTranslate](https://libretranslate.com/docs) | Перевод, 17 языков | нет | Переписка с зарубежными поставщиками, англоязычные источники |
| [Lecto](https://rapidapi.com/lecto-lecto-default/api/lecto-translation/) · [Kiprio Translate](https://kiprio.com/v1/translate) | Перевод получше, 50-100 языков | да, free | Когда LibreTranslate ломает термины |
| [Perspective](https://perspectiveapi.com) | Вероятность токсичности текста | да, free | Проверка комментариев и UGC перед публикацией |
| [languagelayer](https://languagelayer.com/) | Определение языка, 173 | OAuth | Разбор смешанных выгрузок |

⚠️ **Тексты «от лица пользователя» через машинный перевод не гоняем.** Голос проверяет `voice-checker`, а не переводчик.

---

## §17. БПЛА: авиация, рельеф, атмосфера

Под `python-build-engineer` и расчётные задачи по авиации и БПЛА.

| API | Что даёт | Ключ | Заметка |
|---|---|---|---|
| [Open Topo Data](https://www.opentopodata.org) | Высота рельефа по координатам | нет | Профиль маршрута, запас по высоте |
| [Open-Meteo](https://open-meteo.com/) | Ветер по высотам, плотность воздуха, история | нет | **Условия полёта** вместо константы «штиль» |
| [AviationWeather (NOAA)](https://www.aviationweather.gov/dataserver) | METAR/TAF | нет | Видимость, порывы, обледенение |
| [OpenSky Network](https://opensky-network.org/apidoc/index.html) | Реальные треки ADS-B | нет | Валидация модели на живых траекториях |
| [ADS-B Exchange](https://www.adsbexchange.com/data/) | То же, шире покрытие | нет | |
| [TLE](https://tle.ivanstanojevic.me/#/docs) | Орбитальные элементы спутников | нет | Окна связи и съёмки |
| [USGS Earthquake](https://earthquake.usgs.gov/fdsnws/event/1/) | Сейсмика в реальном времени | нет | Сценарии МЧС-применения |

**Дисциплина базы:** внешние данные проходят валидатор так же, как таблицы вендоров. Источник, дата, метод парсинга — в метаданные строки. Парсинг детерминированный, не через модель.

---

## §18. ИИ-инференс мимо Anthropic

Ставить только когда задача реально не для Claude: массовая разметка, эмбеддинги, дешёвый батч.

| API | Что даёт | Ключ | Заметка |
|---|---|---|---|
| [Groq](https://console.groq.com/docs/quickstart) | Очень быстрый инференс Llama/Mixtral, free tier | да, free | Массовая мелкая классификация |
| [Hugging Face](https://huggingface.co) | Инференс моделей NLP/CV/audio | да, free | |
| [Jina AI](https://jina.ai) | Эмбеддинги и реранк | да, free | Поиск по vault, если понадобится RAG |
| [OpenVisionAPI](https://openvisionapi.com) | Компьютерное зрение на открытых моделях | нет | |

⚠️ Ключи — в `.env`, **не в vault, не в run-логи, не в decisions-log**. Правило из vault-CLAUDE.md распространяется и сюда.

---

## Чего в каталоге нет — не искать

Экономит волну поиска. Проверено при сборке 2026-07-28:

- **ЕГРЮЛ, ФНС, Роспатент, DaData** — российских юридических реестров в каталоге нет вообще.
- **Почта России, СДЭК, Деловые Линии** — трекинг только зарубежный (UPS, PostNord, Correios).
- **2ГИС, Яндекс.Карты, Яндекс.Метрика** — бесплатных входов нет; Яндекс.Геокодер и Погода только по ключу.
- **Wildberries, Ozon, маркетплейсы РФ** — нет; для маркетплейс-проектов остаётся свой парсинг.
- **Ключевая ставка ЦБ, налоговые ставки РФ** — только курсы валют.
- **Российские новостные ленты** — есть Noozra (RSS-агрегатор) и зарубежные с ключом, отечественных нет.

---

## Смоук-проверка 2026-07-28 (при сборке карты)

Ключевые позиции дёрнуты живьём с ноутбука, не взяты на веру из каталога.

| API | Результат |
|---|---|
| isdayoff.ru | ✅ 200, `0` — 28.07.2026 рабочий день |
| ЦБ РФ (XML_daily) | ✅ 200, USD 78,0172 · CNY 11,5218 |
| Currency-api | ✅ 200, USD/RUB 78,02 — с ЦБ сходится |
| Open-Meteo | ✅ 200, температура и ветер по <город> |
| Nominatim | ✅ 200, требует свой User-Agent (без него банит) |
| Sunrise-Sunset | ✅ 200, время в UTC — переводить в местное самим |
| QuickChart | ✅ 200, PNG 5,2 КБ прямо по URL |
| goQR | ✅ 200, PNG 279 байт |
| Frankfurter | ⚠️ жив, но **RUB не отдаёт** (404) |
| exchangerate.host | ❌ теперь требует ключ — **каталог врал** |

**Вывод, который дороже самой таблицы:** из 10 проверенных две строки каталога оказались неточны — 20% брака на выборке. Правило 3 («каталог не живая правда») не формальность, а замеренный факт. Один пробный запрос перед работой обязателен.

## Обслуживание карты

- **Пересобирать раз в квартал** или когда появился проект с новым классом данных. Триггер — руками, не автоматизировать (та же логика, что у dreaming).
- Обновление источника: `mcp__open-websearch__fetchGithubReadme` по `https://github.com/public-apis/public-apis` → выхлоп большой, читать чанками или отдать агенту с Bash.
- **API отвалился** → правим строку сразу, в том же ходу. Карта, которая врёт, хуже отсутствующей: агент строит на ней работу и получает тихий отказ.
- Владелец файла — оркестратор. `harness-optimizer` проверяет его на живость наравне с агентами и командами.
