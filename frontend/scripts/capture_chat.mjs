// Captures et contrôles de la parité du Chat (phase 3a), sur le serveur de démonstration :
// artefacts et volet d'aperçu, documents, image générée, fichier généré, chemins et
// citations cliquables. Usage (depuis frontend/) :
//   node scripts/capture_chat.mjs URL_AVEC_JETON [DOSSIER] [étapes séparées par des virgules]
import { mkdirSync } from 'node:fs';

import { composer, openDemo, usage, waitIdle, waitReady } from './lib.mjs';

const [, , url, out = 'captures/chat', only = ''] = process.argv;
if (!url) usage('node scripts/capture_chat.mjs URL_AVEC_JETON [DOSSIER] [étapes]');
mkdirSync(out, { recursive: true });
const steps = new Set(only ? only.split(',') : []);
const wanted = (name) => !steps.size || steps.has(name);

const { browser, page } = await openDemo(url);
const logs = [];
page.on('console', (m) => {
  if (m.type() !== 'error' && m.type() !== 'warning') return;
  // Erreurs des artefacts (iframe isolée) : la requête bloquée vers l'API est voulue
  if (m.location().url.includes('/preview/') || m.text().includes("from origin 'null'")) return;
  if (m.text() === 'Failed to load resource: net::ERR_FAILED') return;
  logs.push(`[${m.type()}] ${m.text()}`);
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
  checks.push({ label, ok });
  console.log(`${ok ? 'OK ' : 'ÉCHEC'} ${label}${detail ? ` — ${detail}` : ''}`);
}

async function send(text) {
  await composer(page).fill(text);
  await composer(page).press('Enter');
  await page.waitForSelector('[aria-busy="true"]', { timeout: 10000 }).catch(() => undefined);
  await waitIdle(page);
  await page.waitForTimeout(400);
}

async function newConversation() {
  await page.keyboard.press('Control+n');
  await page.waitForTimeout(500);
}

await waitReady(page, 60000);
await newConversation();

if (wanted('artefact')) {
  await send('Fais-moi un artefact HTML');
  // Ouverture automatique du volet à la fin de la réponse
  const pane = page.locator('aside[aria-label="Aperçu"]');
  await pane.waitFor({ timeout: 5000 });
  const frame = page.frameLocator('aside[aria-label="Aperçu"] iframe');
  await frame.locator('text=Compteur').waitFor({ timeout: 5000 });
  await frame.locator('button', { hasText: 'Cliquer' }).click();
  await frame.locator('button', { hasText: 'Cliquer' }).click();
  const clicks = await frame.locator('#n').textContent();
  check('artefact : son script tourne (2 clics)', clicks === '2', `compteur = ${clicks}`);
  await frame.locator('#api:has-text("API")').waitFor({ timeout: 5000 });
  const api = await frame.locator('#api').textContent();
  check("artefact : pas d'accès à l'API de l'appli", /403|bloqué/.test(api ?? ''), api ?? '');
  const sandbox = await pane.locator('iframe').getAttribute('sandbox');
  check(
    'artefact : iframe sans allow-same-origin',
    !sandbox?.includes('allow-same-origin'),
    sandbox,
  );
  await shot('artefact_apercu');
  await page.getByRole('tab', { name: 'Code' }).click();
  await page.waitForTimeout(600);
  await shot('artefact_code');
  await page.getByRole('button', { name: 'Aperçu suivant' }).click();
  await page.getByRole('tab', { name: 'Aperçu' }).click();
  await page.waitForTimeout(700);
  await shot('artefact_svg');
  // Poignée : élargir le volet de 200 px
  const handle = page.getByRole('separator', { name: "Largeur du volet d'aperçu" });
  const box = await handle.boundingBox();
  const before = (await pane.boundingBox()).width;
  await page.mouse.move(box.x + 3, box.y + 300);
  await page.mouse.down();
  await page.mouse.move(box.x - 197, box.y + 300, { steps: 8 });
  await page.mouse.up();
  const after = (await pane.boundingBox()).width;
  check(
    'volet : la poignée l’élargit',
    Math.abs(after - before - 200) <= 2,
    `${before} → ${after}`,
  );
  await shot('artefact_volet_elargi');
  await page.getByRole('button', { name: 'Fermer l’aperçu' }).click();
  await page.waitForTimeout(300);
  check('volet : fermé', (await pane.count()) === 0);
}

if (wanted('document')) {
  await newConversation();
  await send('Rédige un document de synthèse');
  await page.locator('aside[aria-label="Aperçu"]').waitFor({ timeout: 5000 });
  await page.waitForTimeout(1200);
  await shot('document_pdf_auto');
  const cards = await page
    .locator('article')
    .last()
    .getByRole('button', { name: /^Ouvrir / })
    .count();
  check('documents : une carte par document', cards >= 2, `${cards} cartes`);
  await page.getByRole('button', { name: 'Aperçu suivant' }).click();
  await page.waitForTimeout(1500);
  await shot('document_docx_html');
  await page.getByRole('button', { name: 'Aperçu suivant' }).click();
  await page.waitForTimeout(1000);
  const md = page.frameLocator('aside[aria-label="Aperçu"] iframe');
  const found = await md.locator('text=Synthèse').count();
  check('document Markdown : rendu en page HTML', found > 0, `${found} titre`);
  await shot('document_markdown');
  await page.getByRole('button', { name: 'Fermer l’aperçu' }).click();
}

if (wanted('chemin')) {
  await newConversation();
  await send('Donne un chemin de fichier');
  const paths = page.locator('article .md-path');
  const count = await paths.count();
  check('chemins : seuls les existants sont cliquables', count === 2, `${count} liens`);
  await shot('chemins');
}

if (wanted('citations')) {
  await newConversation();
  await send('Cherche avec des outils');
  const cites = page.locator('article a.md-cite');
  const count = await cites.count();
  const href = count ? await cites.first().getAttribute('href') : '';
  check('citations [n] cliquables', count >= 6, `${count} liens, ${href}`);
  await shot('citations');
}

if (wanted('image')) {
  await newConversation();
  await composer(page).fill('Dessine un phare au coucher du soleil');
  await composer(page).press('Enter');
  await page.waitForSelector('text=Diffusion', { timeout: 10000 });
  await page.waitForTimeout(800);
  await shot('image_progression');
  await waitIdle(page);
  const image = page.locator('article figure img');
  await image.waitFor({ timeout: 5000 });
  check('image générée affichée', (await image.evaluate((img) => img.naturalWidth)) === 768);
  await shot('image_generee');
  await page.getByRole('button', { name: /^Agrandir / }).click();
  await page.waitForTimeout(500);
  await shot('image_en_grand');
  await page.keyboard.press('Escape');
}

if (wanted('fichier')) {
  await newConversation();
  await send('Génère un fichier somme.py');
  const card = page.getByRole('button', { name: 'Ouvrir somme.py' });
  check('fichier généré : carte', (await card.count()) === 1);
  await shot('fichier_genere');
}

console.log(logs.length ? logs.join('\n') : 'Console : aucune erreur');
const failed = checks.filter((item) => !item.ok);
console.log(`${checks.length - failed.length}/${checks.length} contrôles réussis`);
await browser.close();
process.exit(failed.length ? 1 : 0);
