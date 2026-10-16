// Vraie fenêtre sur le serveur de démonstration (--window) : visionneuse Word dans le volet
// d'aperçu, par CDP seul (ni touche ni curseur du système). La visionneuse est une fenêtre
// enfant au-dessus de WebView2 (native_viewer.py), absente des captures CDP : win.py children
// la retrouve (fenêtre d'un autre processus, celui d'Office) et win.py capture (PrintWindow)
// la photographie, à regarder. Contrôles : posée sur la place réservée par la page, masquée
// sous la palette puis réaffichée, déchargée à la fermeture du volet.
// Usage (depuis frontend/) : node scripts/window_native.mjs [DOSSIER]
import { mkdirSync } from 'node:fs';

import { composer, connectWindow, waitIdle, waitReady, win } from './lib.mjs';

const [, , out = 'captures/visionneuse'] = process.argv;
mkdirSync(out, { recursive: true });
const { browser, page } = await connectWindow();
await waitReady(page);

const checks = [];
function check(label, ok, detail = '') {
  checks.push(ok);
  console.log(`${ok ? 'OK ' : 'ÉCHEC'} ${label}${detail ? ` — ${detail}` : ''}`);
}

/** Hôte de la visionneuse : l'enfant direct de My_AI qui n'est pas WebView2 */
function viewerHost() {
  const children = JSON.parse(win('children'));
  return (
    children.find((child) => !child.foreign.some((name) => /msedgewebview2/i.test(name))) ?? null
  );
}

const pane = page.locator('aside[aria-label="Aperçu"]');
const slot = page.locator('[data-native-preview]');

check(
  'pont : visionneuses disponibles',
  await page.evaluate(() => window.pywebview?.api?.native_preview_available?.() ?? false),
);

await page.keyboard.press('Control+n');
await page.waitForTimeout(500);
await composer(page).fill('Rédige un document de synthèse');
await composer(page).press('Enter');
await page.waitForSelector('[aria-busy="true"]', { timeout: 10000 }).catch(() => undefined);
await waitIdle(page);
await pane.waitFor({ timeout: 5000 });
// Premier document : le PDF ; le suivant : note_projet.docx
await page.getByRole('button', { name: 'Aperçu suivant' }).click();
const started = Date.now();
await slot.waitFor({ timeout: 5000 });
check(
  'Word : place réservée, « Ouverture de l’aperçu Word… »',
  await page
    .getByText('Ouverture de l’aperçu Word…')
    .isVisible()
    .catch(() => false),
);
await page.waitForSelector('[data-native-preview="ready"]', { timeout: 90000 });
console.log(`info : visionneuse prête en ${((Date.now() - started) / 1000).toFixed(1)} s`);
await page.waitForTimeout(1500);

// Bornes de la place à l'écran (CSS → pixels de l'écran, plus l'origine de la page)
async function screenPlace() {
  const place = await slot.evaluate((element) => {
    const box = element.getBoundingClientRect();
    const ratio = window.devicePixelRatio;
    return [box.left, box.top, box.width, box.height].map((value) => Math.round(value * ratio));
  });
  const [originX, originY] = JSON.parse(win('origin'));
  return [originX + place[0], originY + place[1], place[2], place[3]];
}
const near = (a, b) => Math.max(...a.map((value, i) => Math.abs(value - b[i]))) <= 2;
const host = viewerHost();
check(
  'Word : hôte avec la fenêtre d’Office',
  Boolean(host?.foreign.length),
  host ? host.foreign.join(', ') : 'aucun',
);
const expected = await screenPlace();
check(
  'Word : hôte posé sur la place (± 2 px)',
  Boolean(host?.visible) && near(host?.rect ?? [0, 0, 0, 0], expected),
  `${JSON.stringify(host?.rect)} / ${JSON.stringify(expected)}`,
);
console.log(win('capture', `${out}/01_word.png`), '(Word dans le volet, à regarder)');

// Palette : la visionneuse se masque, puis revient
await page.keyboard.press('Control+k');
await page.getByRole('dialog', { name: 'Palette de commandes' }).waitFor({ timeout: 3000 });
await page.waitForTimeout(400);
check('palette : visionneuse masquée', viewerHost()?.visible === false);
console.log(win('capture', `${out}/02_palette.png`), '(palette sans Word dessous)');
await page.keyboard.press('Escape');
await page.waitForTimeout(600);
check('palette fermée : visionneuse revenue', viewerHost()?.visible === true);

// Toast (Ctrl+S, sauvegarde) : masquée seulement s'il touche sa place
await page.keyboard.press('Control+s');
const toast = page.locator('[data-toast-region] [role="status"]').first();
await toast.waitFor({ timeout: 3000 });
await page.waitForTimeout(400);
const touches = await page.evaluate(() => {
  const a = document.querySelector('[data-toast-region] [role="status"]')?.getBoundingClientRect();
  const b = document.querySelector('[data-native-preview]')?.getBoundingClientRect();
  return Boolean(
    a && b && a.left < b.right && a.right > b.left && a.top < b.bottom && a.bottom > b.top,
  );
});
check(
  `toast ${touches ? 'sur' : 'au-dessus de'} la visionneuse : ${touches ? 'masquée' : 'visible'}`,
  viewerHost()?.visible === !touches,
);
console.log(win('capture', `${out}/03_toast.png`), '(toast au-dessus du volet)');
await page
  .locator('[data-toast-region] [role="status"]')
  .first()
  .waitFor({ state: 'detached', timeout: 8000 });
await page.waitForTimeout(600);
check('toast parti : visionneuse revenue', viewerHost()?.visible === true);

// Volet redimensionné au clavier (poignée, Maj+flèche : 64 px) : l'hôte suit
const separator = page.getByRole('separator', { name: "Largeur du volet d'aperçu" });
await separator.focus();
const before = viewerHost()?.rect ?? [0, 0, 0, 0];
const key = before[2] > 1000 ? 'Shift+ArrowRight' : 'Shift+ArrowLeft';
for (let i = 0; i < 3; i += 1) await page.keyboard.press(key);
await page.waitForTimeout(800);
const resized = viewerHost()?.rect ?? [0, 0, 0, 0];
check(
  'volet redimensionné : l’hôte suit',
  resized[2] !== before[2] && near(resized, await screenPlace()),
  `${JSON.stringify(before)} → ${JSON.stringify(resized)}`,
);

// Fermeture du volet : déchargée
await page.getByRole('button', { name: 'Fermer l’aperçu' }).click();
await page.waitForTimeout(1500);
const after = viewerHost();
check(
  'volet fermé : visionneuse masquée et déchargée',
  Boolean(after) && !after.visible && after.foreign.length === 0,
  JSON.stringify(after),
);

await browser.close(); // se détache sans fermer la fenêtre
const failed = checks.filter((ok) => !ok).length;
console.log(failed ? `${failed} contrôle(s) en échec` : 'Tous les contrôles passent');
process.exitCode = failed ? 1 : 0;
