const { chromium } = require('playwright');
const path = require('path');

(async () => {
  const FPS = 30;
  const DUR = 16.0;
  const total = Math.round(FPS * DUR);
  const url = 'file:///' + path.resolve(__dirname, 'scene.html').replace(/\\/g, '/');

  const browser = await chromium.launch({ args: ['--force-color-profile=srgb', '--disable-lcd-text'] });
  const page = await browser.newPage({
    viewport: { width: 720, height: 1280 },
    deviceScaleFactor: 1.5, // -> 1080x1920 output
  });
  await page.goto(url, { waitUntil: 'networkidle' });
  await page.evaluate(() => document.fonts && document.fonts.ready);

  const t0 = Date.now();
  for (let f = 0; f < total; f++) {
    const t = f / FPS;
    await page.evaluate((tt) => window.__render(tt), t);
    const name = 'frames/frame_' + String(f).padStart(4, '0') + '.png';
    await page.screenshot({ path: path.resolve(__dirname, name) });
    if (f % 30 === 0) process.stdout.write(`  frame ${f}/${total} (${((Date.now()-t0)/1000).toFixed(1)}s)\n`);
  }
  await browser.close();
  console.log(`DONE ${total} frames in ${((Date.now()-t0)/1000).toFixed(1)}s`);
})().catch(e => { console.error(e); process.exit(1); });
