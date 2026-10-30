// Mesures exactes de la barre latérale pour l'animation « pop » du bouton Code
const { chromium } = require('playwright');
(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 }, deviceScaleFactor: 2, locale: 'fr-FR' });
  await page.goto('http://127.0.0.1:8770/#token=videotoken');
  await page.locator('aside button:has(svg.lucide-code-xml)').first().waitFor({ state: 'visible', timeout: 60000 });
  await page.waitForTimeout(1500);
  const measure = () => page.evaluate(() => {
    const r = (el) => { const b = el.getBoundingClientRect(); return { x: Math.round(b.x), y: Math.round(b.y), w: Math.round(b.width), h: Math.round(b.height) }; };
    const aside = document.querySelector('aside');
    const code = aside.querySelector('button:has(svg.lucide-code-xml)');
    const top = aside.querySelector('div.space-y-1\\.5');
    const search = top.lastElementChild;
    const middle = aside.querySelector('div.mt-3');
    const folders = middle.querySelector(':scope > div.border-t');
    const icon = code.querySelector('svg');
    const dot = code.querySelector('span > span[aria-hidden]');
    return { code: r(code), code_icon: r(icon), code_dot: dot ? r(dot) : null, search: r(search), middle: r(middle), folders: r(folders), gap: parseFloat(getComputedStyle(top).rowGap) || 6 };
  });
  const after = await measure();
  await page.evaluate(() => { document.querySelector('aside button:has(svg.lucide-code-xml)').style.display = 'none'; });
  await page.waitForTimeout(200);
  const before = await measure();
  console.log(JSON.stringify({ before, after }, null, 1));
  await browser.close();
})();
