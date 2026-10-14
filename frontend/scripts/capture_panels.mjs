// Captures et contrôles des panneaux (phase 3b), sur le serveur de démonstration : assistant de
// premier lancement (serveur lancé avec --premier-lancement), Réglages, Mémoire, Prompts, Relay,
// Aide, palette Ctrl+K. Usage (depuis frontend/) :
//   node scripts/capture_panels.mjs URL_AVEC_JETON [DOSSIER] [étapes séparées par des virgules]
// Étapes : assistant, reglages, aide
import { mkdirSync } from 'node:fs';

import { openDemo, usage, waitReady } from './lib.mjs';

const [, , url, out = 'captures/panneaux', only = ''] = process.argv;
if (!url) usage('node scripts/capture_panels.mjs URL_AVEC_JETON [DOSSIER] [étapes]');
mkdirSync(out, { recursive: true });
const steps = new Set(only ? only.split(',') : []);
const wanted = (name) => !steps.size || steps.has(name);

const { browser, page } = await openDemo(url);
const logs = [];
page.on('console', (m) => {
  if (m.type() === 'error' || m.type() === 'warning') logs.push(`[${m.type()}] ${m.text()}`);
});
page.on('pageerror', (e) => logs.push(`[pageerror] ${e.message}`));

let n = 0;
async function shot(name) {
  n += 1;
  const file = `${out}/${String(n).padStart(2, '0')}_${name}.png`;
  await page.screenshot({ path: file });
  console.log('capture', file);
}

const checks = [];
function check(label, ok, detail = '') {
  checks.push(ok);
  console.log(`${ok ? 'OK ' : 'ÉCHEC'} ${label}${detail ? ` — ${detail}` : ''}`);
}

const button = (name) => page.getByRole('button', { name, exact: true });
const dialog = (name) => page.getByRole('dialog', { name });

if (wanted('assistant')) {
  // Le lancement s'arrête sur l'assistant (serveur lancé avec --premier-lancement)
  const wizard = page.getByRole('region', { name: 'Bienvenue dans My_AI' });
  await wizard.waitFor({ timeout: 30000 });
  await page.getByText('Ollama détecté et actif').waitFor({ timeout: 15000 });
  await page.waitForTimeout(400);
  await shot('assistant_accueil');
  const recommended = await page.locator('select').inputValue();
  check('assistant : modèle recommandé présélectionné', Boolean(recommended), recommended);
  await button('Installer').click();
  await page
    .getByText(/pulling/)
    .first()
    .waitFor({ timeout: 10000 });
  await page.waitForTimeout(1200);
  await shot('assistant_installation');
  await button('Démarrer My_AI').waitFor({ timeout: 30000 });
  const log = await page.getByLabel("Journal de l'installation").innerText();
  check(
    'assistant : installation terminée',
    log.includes('Configuration terminée'),
    log.split('\n').at(-1),
  );
  await shot('assistant_termine');
  await button('Démarrer My_AI').click();
}

await waitReady(page, 60000);

if (wanted('reglages')) {
  await page.keyboard.press('Control+,');
  const panel = dialog('Réglages');
  await panel.waitFor({ timeout: 5000 });
  await page.getByText('Ollama actif').waitFor({ timeout: 10000 });
  await page.waitForTimeout(500);
  await shot('reglages');
  const bases = await panel.locator('select').first().locator('option').allInnerTexts();
  check(
    'réglages : bases sans my_ai',
    bases.length > 0 && !bases.some((b) => b.startsWith('my_ai')),
    bases.join(', '),
  );
  // Téléchargement simulé, progression et journal
  await panel.getByPlaceholder('ex : qwen3.5:4b').fill('mistral:7b');
  await button('Pull').click();
  await panel
    .getByText(/pulling/)
    .first()
    .waitFor({ timeout: 10000 });
  await page.waitForTimeout(800);
  await shot('reglages_telechargement');
  await page.getByText('mistral:7b téléchargé', { exact: true }).waitFor({ timeout: 20000 });
  check('réglages : modèle téléchargé, toast', true);
  await page.waitForTimeout(600);
  const after = await panel.locator('select').first().locator('option').allInnerTexts();
  check(
    'réglages : liste relue après le téléchargement',
    after.includes('mistral:7b'),
    after.join(', '),
  );
  // Paramètres de génération
  await panel.getByLabel('Timeout requête LLM (s) :').fill('5');
  await button('Enregistrer les paramètres').click();
  await page.getByText('Paramètres enregistrés', { exact: true }).waitFor({ timeout: 5000 });
  const timeout = await panel.getByLabel('Timeout requête LLM (s) :').inputValue();
  check('réglages : délai borné à 30 s', timeout === '30', timeout);
  // Relay au lancement (en mémoire dans la démonstration)
  await panel.getByRole('switch', { name: 'Démarrer le Relay au lancement' }).click();
  await page.getByText('Relay auto-start enregistré', { exact: true }).waitFor({ timeout: 5000 });
  check('réglages : Relay au lancement enregistré', true);
  await panel.getByRole('heading', { name: 'Autres réglages' }).scrollIntoViewIfNeeded();
  await shot('reglages_autres');
  await page.keyboard.press('Escape');
  await panel.waitFor({ state: 'detached', timeout: 3000 });
  check('réglages : Échap ferme le panneau', true);
}

if (wanted('aide')) {
  await page.keyboard.press('F1');
  const panel = dialog('Aide — My_AI');
  await panel.waitFor({ timeout: 5000 });
  await page.waitForTimeout(400);
  await shot('aide');
  const shortcuts = await panel.locator('kbd').count();
  check('aide : raccourcis listés', shortcuts >= 10, `${shortcuts}`);
  await panel.locator('footer').getByRole('button', { name: 'Fermer' }).click();
  await panel.waitFor({ state: 'detached', timeout: 3000 });
  check('aide : « Fermer » la ferme', true);
}

console.log(logs.length ? logs.join('\n') : 'Console : aucune erreur');
const failed = checks.filter((ok) => !ok).length;
console.log(`${checks.length - failed}/${checks.length} contrôles réussis`);
await browser.close();
process.exitCode = failed || logs.length ? 1 : 0;
