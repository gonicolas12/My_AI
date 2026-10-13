// Captures et contrôles de la parité du Chat (phase 3a), sur le serveur de démonstration :
// artefacts et volet d'aperçu, documents, image générée, fichier généré, chemins et
// citations cliquables. Usage (depuis frontend/) :
//   node scripts/capture_chat.mjs URL_AVEC_JETON [DOSSIER] [étapes séparées par des virgules]
import { mkdirSync } from 'node:fs';

import { composer, openDemo, openSidebar, usage, waitIdle, waitReady } from './lib.mjs';

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

/** Chemin d'un fichier ou dossier du dépôt */
const repoPath = (relative) =>
  decodeURIComponent(new URL(`../../${relative}`, import.meta.url).pathname).replace(
    /^\/([A-Za-z]:)/,
    '$1',
  );

/** Fichier des données de test du suivi (section 4) */
const fixture = (name) =>
  decodeURIComponent(
    new URL(`../../temp/migration_test_data/fichiers/${name}`, import.meta.url).pathname,
  ).replace(/^\/([A-Za-z]:)/, '$1');

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
  const memo = await frame.locator('#memo').textContent();
  check('artefact : stockage en mémoire (localStorage)', memo === 'Stockage : 1', memo ?? '');
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

if (wanted('pieces')) {
  await newConversation();
  // Menu « + » : dans un navigateur, le sélecteur de fichiers de la page
  await page.getByRole('button', { name: 'Joindre un fichier' }).click();
  await page.getByRole('menu', { name: 'Joindre' }).waitFor();
  await shot('menu_joindre');
  const chooser = page.waitForEvent('filechooser');
  await page.getByRole('menuitem', { name: 'PDF' }).click();
  await (await chooser).setFiles(fixture('rapport_trimestriel.pdf'));
  // Image collée (Ctrl+V) et fichier déposé, construits dans la page
  await composer(page).focus();
  await page.evaluate(async () => {
    const canvas = document.createElement('canvas');
    canvas.width = 64;
    canvas.height = 48;
    const context = canvas.getContext('2d');
    context.fillStyle = '#ff6b47';
    context.fillRect(0, 0, 64, 48);
    const blob = await new Promise((resolve) => canvas.toBlob(resolve, 'image/png'));
    const paste = new DataTransfer();
    paste.items.add(new File([blob], 'image.png', { type: 'image/png' }));
    const box = document.querySelector('textarea[aria-label="Message"]');
    box.dispatchEvent(new ClipboardEvent('paste', { clipboardData: paste, bubbles: true }));
    const drop = new DataTransfer();
    drop.items.add(new File(['a,b\n1,2\n'], 'ventes.csv', { type: 'text/csv' }));
    for (const type of ['dragenter', 'dragover', 'drop']) {
      box.dispatchEvent(
        new DragEvent(type, { dataTransfer: drop, bubbles: true, cancelable: true }),
      );
    }
  });
  await page.waitForTimeout(400);
  await shot('pieces_en_lecture');
  await page.waitForFunction(
    () => !document.querySelector('[aria-label="Lecture en cours"]'),
    null,
    { timeout: 15000 },
  );
  const chips = await page.locator('button[aria-label^="Retirer "]').count();
  check('pièces jointes : PDF, image collée, CSV déposé', chips === 3, `${chips} vignettes`);
  const thumbs = await page.locator('img[alt=""]').count();
  check('pièces jointes : miniature de l’image', thumbs >= 1, `${thumbs} miniature`);
  await shot('pieces_pretes');
  await send('Résume ces fichiers');
  await shot('pieces_envoyees');
}

if (wanted('slash')) {
  await newConversation();
  await composer(page).fill('');
  await composer(page).pressSequentially('/');
  const list = page.getByRole('listbox', { name: 'Commandes' });
  await list.waitFor({ timeout: 5000 });
  await shot('slash_liste');
  await composer(page).press('Enter');
  const value = await composer(page).inputValue();
  check('slash : Entrée insère la commande', value === '/code ', JSON.stringify(value));
  await composer(page).fill('');
}

if (wanted('edition')) {
  await newConversation();
  await send('Explique les tuples');
  await send('Et les listes ?');
  // Modifier le premier message : des messages suivent, confirmation demandée
  const first = page.locator('article, .group\\/msg').filter({ hasText: 'Explique les tuples' });
  await first.first().hover();
  await page.getByRole('button', { name: 'Modifier' }).first().click();
  const editor = page.getByRole('textbox', { name: 'Message modifié' });
  await editor.waitFor();
  await editor.fill('Explique les tuples en Python');
  await shot('edition_dialogue');
  await page.getByRole('button', { name: 'Regénérer' }).click();
  await page.getByText(/laisseront place/).waitFor();
  await shot('edition_confirmation');
  await page.getByRole('button', { name: 'Continuer' }).click();
  await page.waitForSelector('[aria-busy="true"]', { timeout: 10000 }).catch(() => undefined);
  await waitIdle(page);
  await page.waitForTimeout(400);
  const variants = await page.getByText('2/2').count();
  check('édition : nouvelle variante ‹ 2/2 ›', variants === 1, `${variants}`);
  await shot('edition_variante');
  // Régénérer la réponse (D5) : troisième variante du même tour
  await page.getByRole('button', { name: 'Régénérer' }).last().click();
  await page.waitForSelector('[aria-busy="true"]', { timeout: 10000 }).catch(() => undefined);
  await waitIdle(page);
  await page.waitForTimeout(400);
  check('régénération : variante ‹ 3/3 ›', (await page.getByText('3/3').count()) === 1);
  await page.getByRole('button', { name: 'Version précédente' }).first().click();
  await page.waitForTimeout(500);
  check('variantes : retour à ‹ 2/3 ›', (await page.getByText('2/3').count()) === 1);
  await shot('edition_navigation');
}

if (wanted('notes')) {
  await newConversation();
  await send('Note cette réponse');
  const stars = page.getByRole('button', { name: /étoile/ });
  await stars.nth(3).hover();
  await shot('notes_survol');
  await stars.nth(3).click();
  await page.getByRole('group', { name: 'Réponse notée 4 sur 5' }).waitFor({ timeout: 5000 });
  check('note : 4 étoiles, figée', (await stars.nth(0).isDisabled()) === true);
  await shot('notes_figees');
}

if (wanted('voix')) {
  await newConversation();
  await send('Lis-moi cette réponse');
  await page.getByRole('button', { name: 'Lire à voix haute' }).click();
  await page.getByRole('button', { name: 'Arrêter la lecture' }).waitFor({ timeout: 5000 });
  await shot('voix_lecture');
  await page.getByRole('button', { name: 'Lire à voix haute' }).waitFor({ timeout: 6000 });
  check('lecture : le bouton revient à la fin', true);
  await composer(page).fill('Bonjour');
  await page.getByRole('button', { name: 'Saisie vocale' }).click();
  await page.getByRole('button', { name: 'Arrêter la dictée' }).waitFor({ timeout: 5000 });
  await shot('voix_dictee');
  await page.getByRole('button', { name: 'Arrêter la dictée' }).click();
  await page.waitForFunction(
    () => document.querySelector('textarea[aria-label="Message"]')?.value.includes('dicté'),
    null,
    { timeout: 5000 },
  );
  const value = await composer(page).inputValue();
  check('dictée : insérée au curseur', value === 'Bonjour texte dicté (démo)', value);
  await composer(page).fill('');
}

if (wanted('barre')) {
  await newConversation();
  await openSidebar(page);
  // Recherche globale : Entrée, puis ouverture du résultat et surlignage
  const search = page.getByRole('textbox', { name: 'Recherche globale' });
  await search.fill('pagination');
  await search.press('Enter');
  const results = page.getByRole('list', { name: 'Résultats' }).locator('button');
  await results.first().waitFor({ timeout: 10000 });
  await shot('recherche_resultats');
  const found = await results.count();
  check('recherche : résultats affichés', found >= 1, `${found} résultat(s)`);
  await results.first().click();
  await page.waitForTimeout(1500);
  const marked = await page.evaluate(
    () =>
      (CSS.highlights?.get('search-hit')?.size ?? 0) +
      document.querySelectorAll('.search-hit-message').length,
  );
  check('recherche : passage surligné dans la conversation', marked > 0, `${marked}`);
  await shot('recherche_surlignage');
  await page.getByRole('button', { name: 'Effacer la recherche' }).click();

  // Historique : réutiliser une requête
  await page.getByRole('button', { name: 'Historique' }).click();
  await page.waitForTimeout(600);
  await shot('historique');
  const history = page.getByRole('button', { name: /favoris/ });
  check('historique : entrées listées', (await history.count()) >= 1, `${await history.count()}`);
  const first = page.locator('aside[aria-label="Barre latérale"] button[title]').first();
  const query = await first.getAttribute('title');
  await first.click();
  const draft = await composer(page).inputValue();
  check('historique : requête remise dans la saisie', draft === query, draft);
  await composer(page).fill('');

  // Dossier projet : attaché par l'API (le dialogue du système n'existe pas ici)
  await page.getByRole('button', { name: /^Dossiers du projet/ }).click();
  const docs = repoPath('docs');
  await page.evaluate(async (path) => {
    const token = sessionStorage.getItem('my_ai.token');
    await fetch('/api/folders', {
      method: 'POST',
      headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
      body: JSON.stringify({ path }),
    });
  }, docs);
  await page.getByText(/Indexation : \d+\/\d+/).waitFor({ timeout: 10000 });
  await shot('dossiers_indexation');
  await page.getByRole('button', { name: 'Réindexer' }).first().waitFor({ timeout: 20000 });
  await page.waitForTimeout(400);
  const folders = await page.getByRole('button', { name: 'Détacher' }).count();
  check('dossiers : dossier indexé et listé', folders === 1, `${folders}`);
  await shot('dossiers_indexes');

  // Export (navigateur : sans dialogue, dans outputs/exports du serveur)
  await send('Bonjour');
  await page.getByRole('button', { name: 'Exporter la conversation' }).click();
  await page.getByRole('menuitem', { name: 'Markdown (.md)' }).click();
  await page.getByText(/Exporté en MARKDOWN/).waitFor({ timeout: 10000 });
  check('export : fichier écrit', true);
  await shot('export');
}

console.log(logs.length ? logs.join('\n') : 'Console : aucune erreur');
const failed = checks.filter((item) => !item.ok);
console.log(`${checks.length - failed.length}/${checks.length} contrôles réussis`);
await browser.close();
process.exit(failed.length ? 1 : 0);
