# Kinetic-promo engine — генератор анимированных промо-роликов из кода

Собирает вертикальный (1080×1920) анимированный ролик кинетической типографики в стиле
рилс/сторис (референс — промо студии INK / inkai.studio): тёмный/кремовый фон,
акцентная терракота, крупная типографика с word-by-word reveal, пиксельный маскот, бит.

**Не** монтаж из клипов (это скил `/video-montage`). Здесь кадры генерируются **из HTML+JS**,
поэтому текст/цвета/тайминг под любой оффер меняются правкой одного файла.

## ПОЛНЫЙ СТЕК (проверено 2026-07-04)

| Слой | Инструмент | Статус |
|---|---|---|
| Рендер из кода | node v24 + Playwright 1.61 + Chromium | ✅ стоит, работает |
| Кодек/склейка/аудио-DSP | ffmpeg 8.1 (libx264, aac, aevalsrc, loudnorm, gif) | ✅ |
| Шрифты (кириллица) | Montserrat 800/900, Manrope 800, Unbounded 800, Oswald 700, JetBrains Mono 700 | ✅ в `fonts/`, вшиты в `fonts.css` (base64) |
| Музыка/бит | ffmpeg-синтез (кик+саб+хэт, 120 BPM) | ✅ (простой бит; для «настоящей» музыки — нужна библиотека или AI) |
| Озвучка RU (TTS) | `edge-tts` (голоса ru-RU Dmitry / Svetlana) через `py` (Python 3.14) | ✅ стоит, синтез проверен |
| Субтитры/караоке | Whisper (локально, GPU GTX1650, fp16=False) → ASS | ✅ (для нарративных версий с голосом) |
| Принципы моушна | скилы `/motion-design`, `/design-motion-principles` | ✅ |
| Доставка на телефон | Telegram bot @<your_bot> (mp4 как **video**) | ✅ |
| AI-генерация (картинки/видео/голос/3D) | Higgsfield connector | ⚠️ инструкции есть, но **тулзы в сессии не подключены** — нужен активный коннектор claude.ai |
| Дизайн + экспорт анимации в mp4 | Figma MCP (`export_video`, `use_figma`) | ✅ доступен (альтернативный путь через таймлайн Figma) |
| Remotion (React-video) | шаблон в `skills/video-montage/remotion-template/` (remotion 4.0.482) | ✅ рендерит (`npx remotion render` → mp4, exit 0). ⚠️ Лицензия: бесплатно только физлицу / компании ≤3 сотрудников → **для роликов клиента-компании нужна платная Company License**, для личных роликов пользователя — free |

Вывод: **полностью самодостаточный локальный конвейер** (код → кадры → бит/озвучка → mp4) готов и не зависит от внешних сервисов. AI-генерация b-roll/картинок/живого голоса — опциональный слой сверху, включается, когда активен Higgsfield-коннектор или Figma.

## Пайплайн (node + Playwright + ffmpeg — всё стоит локально)

1. `scene.html` — сцены + детерминированный таймлайн. Ключ: `window.__render(t)` рисует
   ЛЮБОЙ момент времени `t` (сек) без реального времени → покадровый seek точный.
   Правишь тексты/цвета/тайминг сцен здесь.
2. `render.js` — Playwright headless: viewport 720×1280, deviceScaleFactor 1.5 → кадры 1080×1920.
   Для каждого кадра зовёт `__render(f/FPS)` и делает скриншот в `frames/`.
3. Бит через ffmpeg (`aevalsrc`, 120 BPM: кик+саб+хэт) → `audio.wav`.
4. Склейка: `ffmpeg -framerate 30 -i frames/frame_%04d.png -i audio.wav -c:v libx264 -crf 18 -pix_fmt yuv420p -c:a aac -movflags +faststart out.mp4`

## Запуск

```bash
cd <рабочая-папка>              # скопировать сюда scene.html + render.js
npm i playwright@1.61.1 && npx playwright install chromium   # один раз
node render.js                 # → frames/*.png (~1 мин на 16 c)
# audio.wav — см. команду aevalsrc в истории/README
ffmpeg -y -framerate 30 -i frames/frame_%04d.png -i audio.wav \
  -c:v libx264 -crf 18 -pix_fmt yuv420p -c:a aac -b:a 192k -movflags +faststart out.mp4
```

Бит:
```bash
ffmpeg -y -f lavfi -i "aevalsrc='0.72*sin(2*PI*55*t)*exp(-9*mod(t,0.5)) + 0.13*sin(2*PI*2100*t)*exp(-55*mod(t,0.25)) + 0.09*sin(2*PI*110*t) + 0.05*sin(2*PI*220*t)':s=44100:d=16" \
  -af "highpass=f=22,alimiter=limit=0.94,afade=t=in:st=0:d=0.15,afade=t=out:st=15.1:d=0.9" audio.wav
```

## Грабли / заметки
- Шрифт: Segoe UI Black (weight 900) — стоит в Windows, поддерживает кириллицу, скачивать ничего не надо.
- Inline-блоки схлопывают хвостовой пробел перед акцентным словом → ставить `&nbsp;` («из&nbsp;<accent>кода</accent>»).
- Вывод класть в `<HOME>\Videos\`, НЕ в папку, которую синхронизирует облако (утягивает свежие файлы).
- Смотреть на телефоне → слать в TG как **video** (mp4), не документом.
- Первый прогон: 2026-07-04, демо на 16 с — доказательство, что конвейер собирает ролик из кода без внешних сервисов. Тексты сцен в `scene.html` — заглушки («Ваш оффер здесь»), замени на свой оффер.
