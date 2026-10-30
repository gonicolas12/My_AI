// Configure une fois le VS Code web (profil Chromium persistant) : dossier de
// confiance, réglages utilisateur, puis capture de contrôle.
const { chromium } = require('playwright');
const path = require('path');

const S = path.resolve(__dirname, '..');
const FOLDER = `${S}/workspace/bibliotheque-api`;
const URL = `http://127.0.0.1:8000/?folder=${FOLDER}`;

const SETTINGS = {
  'workbench.colorTheme': 'Default Dark Modern',
  'workbench.startupEditor': 'none',
  'workbench.tips.enabled': false,
  'workbench.enableExperiments': false,
  'workbench.welcomePage.walkthroughs.openOnInstall': false,
  'workbench.layoutControl.enabled': false,
  'security.workspace.trust.enabled': false,
  'telemetry.telemetryLevel': 'off',
  'update.mode': 'none',
  'extensions.ignoreRecommendations': true,
  'chat.disableAIFeatures': true,
  'chat.commandCenter.enabled': false,
  'window.commandCenter': true,
  'keyboard.layout': 'us',
  'files.exclude': {
    '**/__pycache__': true,
    '**/.pytest_cache': true,
    '**/.git': true,
    '**/.vscode': true,
  },
  'editor.fontSize': 14,
  'editor.minimap.enabled': false,
  'editor.stickyScroll.enabled': false,
  'git.enabled': true,
  'git.openRepositoryInParentFolders': 'never',
};

async function palette(page, command) {
  const input = page.locator('.quick-input-widget input.input').first();
  for (const keys of ['F1', 'Control+Shift+P', 'F1']) {
    await page.keyboard.press('Escape');
    await page.locator('.monaco-workbench').first().click({ position: { x: 800, y: 6 } }).catch(() => {});
    await page.keyboard.press(keys);
    try {
      await input.waitFor({ state: 'visible', timeout: 4000 });
      break;
    } catch {
      /* nouvel essai */
    }
  }
  await page.keyboard.type(command, { delay: 15 });
  await page.waitForTimeout(700);
  await page.keyboard.press('Enter');
}

(async () => {
  const context = await chromium.launchPersistentContext(`${S}/chrome-vscode`, {
    viewport: { width: 1600, height: 900 },
    deviceScaleFactor: 1,
    locale: 'en-US',
    permissions: ['clipboard-read', 'clipboard-write'],
  });
  const page = context.pages()[0] || (await context.newPage());
  await page.goto(URL);
  await page.waitForSelector('.monaco-workbench', { timeout: 60000 });
  await page.waitForTimeout(5000);

  if (process.argv.includes('--peek')) {
    await palette(page, 'View: Close All Editors');
    await page.waitForTimeout(1500);
    await page.screenshot({ path: `${S}/shots/peek_vscode2.png` });
    await context.close();
    return;
  }

  // Dossier de confiance (sinon l'extension reste désactivée)
  await palette(page, 'Workspaces: Manage Workspace Trust');
  await page.waitForTimeout(2000);
  const trust = page.getByRole('button', { name: /^Trust$/ }).first();
  if (await trust.count()) {
    await trust.click();
    await page.waitForTimeout(1500);
  }

  // Réglages utilisateur (stockés dans le navigateur)
  await palette(page, 'Preferences: Open User Settings (JSON)');
  await page.waitForTimeout(2500);
  await page.evaluate((text) => navigator.clipboard.writeText(text), JSON.stringify(SETTINGS, null, 2));
  await page.locator('.monaco-editor .view-lines').first().click();
  await page.keyboard.press('Control+A');
  await page.keyboard.press('Control+V');
  await page.waitForTimeout(500);
  await page.keyboard.press('Control+S');
  await page.waitForTimeout(1500);
  await palette(page, 'View: Close All Editors');
  await page.waitForTimeout(1000);

  await page.reload();
  await page.waitForSelector('.monaco-workbench', { timeout: 60000 });
  await page.waitForTimeout(8000);
  await page.screenshot({ path: `${S}/shots/peek_vscode2.png` });
  await context.close();
})();
