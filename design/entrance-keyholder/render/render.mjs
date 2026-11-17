// Render the designs with three.js in headless Chromium (no web server needed:
// requests are answered from disk through Playwright's request routing).
//
// Usage: node render.mjs <three-package-dir> <views.json> <out-dir> [view-name ...]
//   <three-package-dir> is an unpacked three@0.160.0 (the folder holding build/ and examples/).
import { createRequire } from 'module';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

// CommonJS require so a globally installed Playwright is found too.
const { chromium } = createRequire(import.meta.url)('playwright');

const [threeDir, viewsFile, outDir, ...only] = process.argv.slice(2);
const khDir = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const views = JSON.parse(fs.readFileSync(viewsFile, 'utf8'));
fs.mkdirSync(outDir, { recursive: true });

const TYPES = { '.html': 'text/html', '.js': 'text/javascript', '.json': 'application/json', '.stl': 'application/octet-stream' };
function serve(route) {
  const u = new URL(route.request().url());
  let file;
  if (u.pathname.startsWith('/three/')) file = path.join(threeDir, u.pathname.slice('/three/'.length));
  else if (u.pathname.startsWith('/kh/')) file = path.join(khDir, u.pathname.slice('/kh/'.length));
  if (!file || !fs.existsSync(file)) return route.fulfill({ status: 404, body: 'not found' });
  return route.fulfill({ status: 200, body: fs.readFileSync(file), contentType: TYPES[path.extname(file)] || 'application/octet-stream' });
}

const browser = await chromium.launch({
  args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'],
});
for (const v of views) {
  if (only.length && !only.includes(v.name)) continue;
  const W = v.width || 1600, H = v.height || 1200;
  const page = await browser.newPage({ viewport: { width: W, height: H }, deviceScaleFactor: 1 });
  await page.route('http://kh.local/**', serve);
  page.on('console', (m) => { if (m.type() === 'error') console.error('[page]', m.text()); });
  page.on('pageerror', (e) => console.error('[pageerror]', e.message));
  await page.goto(`http://kh.local/kh/render/scene.html#${encodeURIComponent(JSON.stringify(v))}`);
  await page.waitForFunction('window.DONE === true', null, { timeout: 600000 });
  const out = path.join(outDir, v.name + '.png');
  await page.locator('canvas').screenshot({ path: out });
  console.log('wrote', out);
  await page.close();
}
await browser.close();
