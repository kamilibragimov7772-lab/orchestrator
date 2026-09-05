# Формат HTML-отчёта

Один самодостаточный файл: стили инлайном, диаграммы — руками написанный SVG, шрифты системные. Внешних запросов ноль — файл открывается без интернета и переживает пересылку в Telegram.

## Скаффолд

```html
<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Архитектурный разбор — {{проект}}</title>
<style>
  :root{
    --bg:#f6f4f1; --card:#fff; --ink:#1c1917; --muted:#78716c; --line:#d6d3d1;
    --deep:#1c1917; --shallow:#e7e5e4; --leak:#b91c1c; --seam:#a8a29e;
    --strong:#047857; --maybe:#b45309; --guess:#57534e;
    --mono:ui-monospace,"Cascadia Mono","Consolas",monospace;
  }
  *{box-sizing:border-box}
  body{margin:0;background:var(--bg);color:var(--ink);
       font:16px/1.55 -apple-system,"Segoe UI",Roboto,sans-serif}
  main{max-width:1040px;margin:0 auto;padding:48px 24px 96px}
  h1{font-size:28px;margin:0 0 4px} h2{font-size:20px;margin:0 0 12px}
  .legend{display:flex;gap:18px;flex-wrap:wrap;color:var(--muted);font-size:13px;margin:16px 0 40px}
  article{background:var(--card);border:1px solid var(--line);border-radius:14px;
          padding:28px;margin-bottom:28px}
  .badge{display:inline-block;padding:3px 10px;border-radius:999px;font-size:12px;
         font-weight:600;color:#fff}
  .files{font-family:var(--mono);font-size:13px;color:var(--muted);margin:10px 0 18px}
  .ba{display:grid;grid-template-columns:1fr 1fr;gap:20px;align-items:start}
  .ba figcaption{font-size:12px;color:var(--muted);text-transform:uppercase;letter-spacing:.06em}
  .wins{margin:14px 0 0;padding-left:18px} .wins li{margin:2px 0}
  .warn{background:#fffbeb;border-left:3px solid var(--maybe);padding:10px 14px;
        font-size:14px;margin-top:16px}
  @media(max-width:720px){.ba{grid-template-columns:1fr}}
  @media(prefers-color-scheme:dark){
    :root{--bg:#0c0a09;--card:#1c1917;--ink:#f5f5f4;--muted:#a8a29e;--line:#292524;
          --deep:#f5f5f4;--shallow:#44403c}
  }
</style>
</head>
<body>
<main>
  <header>
    <h1>Архитектурный разбор — {{проект}}</h1>
    <div class="legend">
      <span>сплошная коробка — модуль</span><span>пунктир — шов</span>
      <span style="color:var(--leak)">красная стрелка — протечка</span>
      <span>тёмная масса — глубокий модуль</span>
    </div>
  </header>
  <section id="candidates"><!-- article на каждого кандидата --></section>
  <section id="start"><!-- С чего начать --></section>
</main>
</body>
</html>
```

Вводного абзаца нет. Сразу шапка → кандидаты.

## Карточка кандидата

Один `<article>`, в нём по порядку:

1. **Заголовок** — называет углубление глаголом: «Собрать разбор телеметрии в один модуль», не «Проблемы парсинга».
2. **Бейдж** силы: `Уверенно` (`--strong`), `Стоит обсудить` (`--maybe`), `Догадка` (`--guess`).
3. **Файлы** — моноширинным, класс `files`.
4. **Диаграмма «было / стало»** — центр карточки, две колонки `.ba`. Паттерны ниже.
5. **Трение** — одно предложение: что болит сейчас.
6. **Что меняется** — одно предложение.
7. **Выигрыш** — список, до шести слов на пункт: «тест цепляется за один интерфейс», «расчёт тяги перестаёт течь», «минус 4 мелких обёртки».
8. **Врезка `.warn`** — если кандидат спорит с записанным в `CLAUDE.md` проекта решением: одной строкой, почему всё-таки стоит вернуться к вопросу.

Абзацев объяснения в карточке нет.

## Паттерны диаграмм

Меняй паттерн от кандидата к кандидату — одинаковые картинки перестают читаться.

**Масса.** Площадь прямоугольника = объём кода. Слева пять одинаковых бледных коробок (`--shallow`) с подписями-именами, справа одна тёмная (`--deep`) той же суммарной площади и узкая светлая полоса сверху — интерфейс. Показывает, что сложность не исчезла, а собралась.

**Разрез.** Два столбика: сверху полоса интерфейса, снизу масса реализации. Мелкий модуль — полоса почти равна массе; глубокий — тонкая полоса поверх большой массы.

**Протечка.** Две коробки, между ними пунктирная вертикаль (`stroke-dasharray:4 4`, цвет `--seam`) — шов. Красная стрелка, идущая сквозь пунктир прямо во внутренности соседа, — протечка. В «стало» стрелка упирается в интерфейс.

**Граф вызовов.** Узлы и рёбра, когда важен именно порядок обхода: «было» — звезда с центром, через который всё ходит; «стало» — цепочка. Держи до 8 узлов, иначе читать нечего.

**Поверхность тестирования.** Пунктирная рамка вокруг того, что накрывает тест. «Было» — рамка вокруг трёх чистых функций, а вызывающий код снаружи (там и живут баги). «Стало» — рамка по интерфейсу модуля целиком.

Минимум SVG, из которого растут остальные:

```html
<figure class="ba">
  <div><figcaption>было</figcaption>
    <svg viewBox="0 0 300 200" width="100%" role="img" aria-label="пять мелких модулей">
      <rect x="10" y="20" width="80" height="46" fill="var(--shallow)" stroke="var(--line)"/>
      <text x="50" y="47" font-size="11" text-anchor="middle">parser.py</text>
      <line x1="150" y1="10" x2="150" y2="190" stroke="var(--seam)" stroke-dasharray="4 4"/>
      <path d="M95 43 H205" stroke="var(--leak)" stroke-width="2" marker-end="url(#a)"/>
      <defs><marker id="a" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6"
        markerHeight="6" orient="auto"><path d="M0 0 L10 5 L0 10 z" fill="var(--leak)"/></marker></defs>
    </svg>
  </div>
  <div><figcaption>стало</figcaption><svg viewBox="0 0 300 200" width="100%">…</svg></div>
</figure>
```

`viewBox` одинаковый в обеих половинах — иначе масса врёт, и глаз сравнивает не то.

## Раздел «С чего начать»

Последним. Один кандидат, три строки: почему он первый, что разблокирует следующим, сколько примерно правок. Списка приоритетов на десять пунктов не бывает — это способ ничего не начать.
