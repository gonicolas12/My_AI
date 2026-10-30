// Connecte l'extension My_AI du VS Code web au Relay de la démo (chaîne de
// connexion + code d'accès), puis place le chat dans la barre latérale droite.
const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

const S = path.resolve(__dirname, '..');
const FOLDER = `${S}/workspace/bibliotheque-api`;
const URL = `http://127.0.0.1:8000/?folder=${FOLDER}`;
const info = JSON.parse(fs.readFileSync(`${S}/relay_info.json`, 'utf-8'));
const step = (n) => `${S}/shots/connect_${n}.png`;

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
  await page.waitForTimeout(800);
  await page.keyboard.press('Enter');
}

async function typeInQuickInput(page, text) {
  const input = page.locator('.quick-input-widget input.input').first();
  await input.waitFor({ state: 'visible', timeout: 15000 });
  await page.waitForTimeout(400);
  await input.fill(text);
  await page.waitForTimeout(300);
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

  if (!process.argv.includes('--move-only')) {
    await palette(page, 'My_AI Relay: Connect');
    await typeInQuickInput(page, info.connection_string);
    await page.waitForTimeout(2500);
    await page.screenshot({ path: step(1) });
    await typeInQuickInput(page, info.access_code);
    await page.waitForTimeout(4000);
    await page.screenshot({ path: step(2) });
  }

  // Chat My_AI dans la barre latérale secondaire (droite)
  await palette(page, 'View: Move View');
  await page.waitForTimeout(1200);
  await page.screenshot({ path: step(3) });
  await page.keyboard.type('Chat', { delay: 20 });
  await page.waitForTimeout(800);
  await page.screenshot({ path: step(4) });
  await context.close();
})();
