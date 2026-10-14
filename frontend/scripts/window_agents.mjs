// Vraie fenêtre sur le serveur de démonstration (--window) : page Agents dans WebView2. Par CDP :
// onglet chargé à la demande, nœuds, liens de port à port, exécution d'un workflow (statuts,
// liens animés, fil), Échap. Un seul geste du système : une carte glissée sur le canvas à la vraie
// souris (win.py drag, après 20 s sans clavier ni souris, sinon refus), car un glisser envoyé par
// CDP ne passe pas par le glisser-déposer de Windows. Aucun dialogue de fichiers n'est ouvert.
// Usage (depuis frontend/) : node scripts/window_agents.mjs [DOSSIER]
import { mkdirSync } from 'node:fs';

import { connectWindow, win } from './lib.mjs';

const [, , out = 'captures/fenetre_agents'] = process.argv;
mkdirSync(out, { recursive: true });
const { browser, page } = await connectWindow();
// Appli prête : l'en-tête et ses onglets (la fenêtre peut être restée sur la page Agents)
await page.getByRole('button', { name: 'Agents', exact: true }).waitFor({ timeout: 180000 });
const logs = [];
page.on('console', (m) => {
  if (m.type() === 'error' || m.type() === 'warning') logs.push(`[${m.type()}] ${m.text()}`);
});
page.on('pageerror', (e) => logs.push(`[pageerror] ${e.message}`));

const checks = [];
function check(label, ok, detail = '') {
  checks.push(ok);
  console.log(`${ok ? 'OK ' : 'ÉCHEC'} ${label}${detail ? ` — ${detail}` : ''}`);
}

const button = (name) => page.getByRole('button', { name, exact: true });
const card = (name) => page.getByRole('button', { name: new RegExp(`^${name} :`) });
const nodes = () => page.locator('.react-flow__node');
const nodeById = (id) => page.locator(`.react-flow__node[data-id="${id}"]`);
const RUNS = '[aria-label="Fils d\'exécution"]';

async function center(locator) {
  const box = await locator.boundingBox();
  if (!box) throw new Error('élément invisible');
  return { x: box.x + box.width / 2, y: box.y + box.height / 2 };
}

async function link(from, to) {
  const start = await center(nodeById(from).locator('.react-flow__handle.source'));
  const end = await center(nodeById(to).locator('.react-flow__handle.target'));
  await page.mouse.move(start.x, start.y);
  await page.mouse.down();
  await page.mouse.move(end.x, end.y, { steps: 10 });
  await page.mouse.up();
  await page.waitForTimeout(150);
}

async function runAndWait(timeout = 60000) {
  const before = await page.locator(`${RUNS} li`).count();
  await button('Exécuter').click();
  await page.waitForFunction(
    ([selector, count]) => document.querySelectorAll(`${selector} li`).length > count,
    [RUNS, before],
    { timeout: 15000 },
  );
  await page.waitForFunction(
    (selector) => !document.querySelector(`${selector} [aria-label="En cours"]`),
    RUNS,
    { timeout },
  );
  await page.waitForTimeout(300);
}

await page.getByRole('button', { name: 'Agents', exact: true }).click();
await page.getByRole('heading', { name: 'Agents IA spécialisés' }).waitFor({ timeout: 15000 });
await page.waitForTimeout(800);
const chunk = await page.evaluate(() =>
  performance
    .getEntriesByType('resource')
    .some((entry) => /\/assets\/AgentsPage-[\w-]+\.js$/.test(entry.name)),
);
check('onglet Agents : page chargée à sa première ouverture', chunk);

await button('Vider').click();
await card('PlannerAgent').click();
await card('CodeAgent').click();
check('clic sur une carte : nœud ajouté', (await nodes().count()) === 2);
await link('0', '1');
check(
  'lien de port à port (souris de CDP)',
  (await page.locator('.react-flow__edge').count()) === 1,
);

// Vraie souris : une carte glissée sur le canvas (glisser-déposer de Windows et de WebView2)
const origin = JSON.parse(win('origin'));
const ratio = await page.evaluate(() => window.devicePixelRatio);
const from = await center(card('OptimizerAgent'));
const pane = await page.locator('.react-flow__pane').boundingBox();
const target = { x: pane.x + 900, y: pane.y + Math.min(200, pane.height - 60) };
const screen = (point) => [
  String(Math.round(origin[0] + point.x * ratio)),
  String(Math.round(origin[1] + point.y * ratio)),
];
try {
  win('drag', ...screen(from), ...screen(target));
  await page.waitForTimeout(500);
  check('vraie souris : la carte glissée devient un nœud', (await nodes().count()) === 3);
  const box = await nodeById('2').boundingBox();
  check(
    'vraie souris : nœud centré sur le point de dépôt',
    Boolean(box) &&
      Math.abs(box.x + box.width / 2 - target.x) < 40 &&
      Math.abs(box.y + box.height / 2 - target.y) < 40,
  );
  await nodeById('2')
    .getByRole('button', { name: /Retirer/ })
    .click();
} catch (error) {
  console.log(`info : vrai glisser-déposer non fait (${String(error).split('\n')[0]})`);
}

await page.getByRole('textbox', { name: 'Tâche' }).fill('Une API REST pour une bibliothèque');
await runAndWait();
const done = await page.locator('.react-flow__node', { hasText: 'Terminé' }).count();
check('workflow exécuté : nœuds « Terminé »', done === 2, `${done}`);
check(
  'fil : statut final',
  (await page.getByText('✅ Workflow terminé (100% succès)').count()) > 0,
);
await page
  .locator('main > div')
  .first()
  .evaluate((el) => (el.scrollTop = el.scrollHeight));
await page.waitForTimeout(400);
await page.screenshot({ path: `${out}/01_fil.png` });
win('capture', `${out}/02_fenetre.png`);

await page.getByRole('textbox', { name: 'Tâche' }).fill('Tâche lente pour essayer Échap');
const before = await page.locator(`${RUNS} li`).count();
await button('Exécuter').click();
await page.waitForFunction(
  ([selector, count]) => document.querySelectorAll(`${selector} li`).length > count,
  [RUNS, before],
  { timeout: 15000 },
);
await page
  .locator('.react-flow__node', { hasText: 'En cours' })
  .first()
  .waitFor({ timeout: 15000 });
await page.keyboard.press('Escape');
await page.getByText('⛔ Génération interrompue').first().waitFor({ timeout: 15000 });
check('Échap (clavier de CDP) : exécution interrompue', true);

console.log(logs.length ? logs.join('\n') : 'aucune erreur de console');
const failed = checks.filter((ok) => !ok).length;
console.log(`${checks.length - failed} contrôles sur ${checks.length}`);
await browser.close();
process.exit(failed || logs.length ? 1 : 0);
