// usage: node shoot.js <base-url> <outdir> view[:w:h[:extra]] ...
const { chromium } = require('playwright');
(async () => {
  const [base, out, ...views] = process.argv.slice(2);
  const browser = await chromium.launch({ args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] });
  for (const v of views) {
    const [name, w = 1000, h = 1000, extra = ''] = v.split(':');
    const page = await browser.newPage({ viewport: { width: +w, height: +h }, deviceScaleFactor: 2 });
    page.on('console', m => { if (m.type() === 'error') console.log('console:', m.text()); });
    page.on('pageerror', e => console.log('pageerror:', e.message));
    await page.goto(`${base}?view=${name}&w=${w}&h=${h}${extra ? '&' + extra : ''}`);
    await page.waitForFunction(() => document.body.dataset.done === '1', null, { timeout: 120000 });
    await page.screenshot({ path: `${out}/render_${name}.png` });
    console.log(name, await page.title());
    await page.close();
  }
  await browser.close();
})();
