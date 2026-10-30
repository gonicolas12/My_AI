// Mise en page propre : emplacements des vues réinitialisés, puis seul le chat
// My_AI dans la barre latérale droite, élargie à ~460 px.
const { chromium } = require('playwright');
const path = require('path');

const S = path.resolve(__dirname, '..');
const FOLDER = `${S}/workspace/bibliotheque-api`;
const URL = `http://127.0.0.1:8000/?folder=${FOLDER}`;
const shot = (page, n) => page.screenshot({ path: `${S}/shots/layout3_${n}.png` });

async function palette(page, command) {
  const input = page.locator('.quick-input-widget input.input').first();
  for (const keys of ['F1', 'Control+Shift+P', 'F1']) {
    await page.keyboard.press('Escape');
    await page.keyboard.press(keys);
    try {
      await input.waitFor({ state: 'visible', timeout: 4000 });
      break;
    } catch {
      /* nouvel essai */
    }
  }
  await page.keyboard.type(command, { delay: 10 });
  await page.waitForTimeout(900);
  await page.keyboard.press('Enter');
}

(async () => {
  const context = await chromium.launchPersistentContext(`${S}/chrome-vscode`, {
    viewport: { width: 1600, height: 900 },
    deviceScaleFactor: 1,
    locale: 'en-US',
  });
  const page = context.pages()[0] || (await context.newPage());
  await page.goto(URL);
  await page.waitForSelector('.monaco-workbench', { timeout: 60000 });
  await page.waitForTimeout(6000);

  await palette(page, 'View: Reset View Locations');
  await page.waitForTimeout(2000);
  await palette(page, 'View: Close Secondary Side Bar');
  await page.waitForTimeout(800);
  await palette(page, 'View: Close Panel');
  await page.waitForTimeout(800);
  await shot(page, 1);

  const myai = page.locator('.activitybar .action-item a[aria-label*="My_AI"], .activitybar .action-label[aria-label*="My_AI"]').first();
  await myai.click({ button: 'right' });
  await page.waitForTimeout(800);
  const menu = page.locator('.monaco-menu');
  await menu.getByText('Move To', { exact: true }).first().hover();
  await page.waitForTimeout(900);
  await menu.getByText(/Secondary Side Bar/).first().click();
  await page.waitForTimeout(2500);

  const aux = page.locator('.part.auxiliarybar');
  const box = await aux.boundingBox();
  if (box && Math.abs(box.width - 464) > 8) {
    const x = box.x - 2;
    const y = box.y + box.height / 2;
    await page.mouse.move(x, y);
    await page.mouse.down();
    await page.mouse.move(x - 30, y, { steps: 5 });
    await page.mouse.move(1600 - 470, y, { steps: 10 });
    await page.mouse.up();
  }
  await page.mouse.move(700, 450);
  await page.waitForTimeout(1200);
  console.log('aux:', JSON.stringify(await aux.boundingBox()));
  const tabs = await page.$$eval('.part.auxiliarybar .composite-bar .action-label',
    (els) => els.map((e) => e.getAttribute('aria-label') || e.textContent.trim()));
  console.log('aux tabs:', JSON.stringify(tabs));
  await shot(page, 2);
  await context.close();
})();
