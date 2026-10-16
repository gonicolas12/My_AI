// Captures des états clés de l'interface, sur le serveur de démonstration
// Usage (depuis frontend/) : node scripts/capture.mjs URL_AVEC_JETON [DOSSIER] [largeur hauteur]
import { mkdirSync } from 'node:fs';

import { composer, openDemo, usage, waitIdle } from './lib.mjs';

const [, , url, out = 'captures', width = '1440', height = '900'] = process.argv;
if (!url) usage('node scripts/capture.mjs URL_AVEC_JETON [DOSSIER] [largeur hauteur]');
mkdirSync(out, { recursive: true });
const { browser, page } = await openDemo(url, { width: Number(width), height: Number(height) });
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

async function send(text) {
  await composer(page).fill(text);
  await composer(page).press('Enter');
}

/** La réponse commence (message reçu par le serveur), puis se termine */
async function waitAnswer() {
  await page.waitForSelector('[aria-busy="true"]', { timeout: 10000 }).catch(() => undefined);
  await waitIdle(page);
}

/** Session des données de test (suivi, section 4), si elle existe */
async function openSession(name) {
  const button = page.getByRole('button', { name });
  if (!(await button.count())) {
    console.log(`session absente, étape sautée : ${String(name)}`);
    return false;
  }
  await button.first().click();
  return true;
}

// La molette agit sous la souris : au-dessus du fil de messages
const overThread = () => page.mouse.move(Number(width) / 2 + 130, Number(height) / 2);

// 1. Écran de chargement (sans --fast-launch, il dure quelques secondes)
await page.waitForSelector('text=Démarrage d', { timeout: 15000 }).catch(() => undefined);
await page.waitForTimeout(250);
await shot('chargement');
await page.waitForSelector('text=Placement du modèle', { timeout: 15000 }).catch(() => undefined);
await page.waitForTimeout(900);
await shot('chargement_placement');

// 2. Accueil
await page.waitForSelector('textarea[aria-label="Message"]', { timeout: 60000 });
await page.waitForTimeout(600);
await shot('accueil');
await composer(page).fill('Bonjour, peux-tu m’aider ?');
await shot('accueil_saisie');
await composer(page).fill('');

// 3. Barre latérale et sessions
await page.keyboard.press('Control+b');
await page.waitForTimeout(400);
await shot('barre_laterale');

// 4. Session « Projet API REST » (code, tableau, citations, variantes)
if (await openSession(/^Projet API REST/)) {
  await page.waitForTimeout(1200);
  await shot('session_projet_api');
  await overThread();
  await page.mouse.wheel(0, -1500);
  await page.waitForTimeout(500);
  await shot('session_projet_api_haut');
}

// 5. Conversation longue (200 messages)
if (await openSession(/^Conversation longue/)) {
  await page.waitForTimeout(1500);
  await shot('conversation_longue_bas');
  await overThread();
  for (let i = 0; i < 6; i += 1) {
    await page.mouse.wheel(0, -900);
    await page.waitForTimeout(120);
  }
  await page.waitForTimeout(400);
  await shot('conversation_longue_remontee');
  await page.getByRole('button', { name: 'Revenir en bas' }).click();
  await page.waitForTimeout(900);
}

// 6. Nouvelle conversation (Ctrl+N), réponse courte : code et formule
await page.keyboard.press('Control+n');
await page.waitForTimeout(600);
await send('Montre-moi un exemple court');
await page.waitForTimeout(900);
await shot('streaming_court');
await waitAnswer();
await page.waitForTimeout(800);
await shot('reponse_courte_code_formule');

// 7. Réflexion
await send('Fais une réflexion sur les deux approches');
// Le bouton du bloc, pas le message (« text=… » ignore la casse)
await page.getByRole('button', { name: /^Réflexion/ }).waitFor({ timeout: 10000 });
await page.waitForTimeout(1200);
await shot('reflexion_en_cours');
await waitIdle(page);
await page.waitForTimeout(500);
await shot('reflexion_terminee');

// 8. Outils
await send('Utilise tes outils pour chercher les nouveautés de Python');
await page.waitForSelector('text=Recherche sur internet', { timeout: 15000 });
await page.waitForTimeout(400);
await shot('outil_en_cours');
await page.waitForSelector('text=3 sources', { timeout: 15000 });
await page.waitForTimeout(300);
await shot('outil_termine_synthese');
await waitIdle(page);
await page.waitForTimeout(500);
await shot('outils_reponse');

// 9. Longue réponse en streaming, Stop, file d'attente
await send('Écris une réponse long format');
await page.waitForTimeout(6000);
await shot('streaming_long');
await send('Et ensuite, une autre question ?');
await page.waitForTimeout(500);
await shot('file_attente');
await page.keyboard.press('Escape');
await page.waitForTimeout(1500);
await shot('apres_echap');
await waitIdle(page);
await page.waitForTimeout(800);
await shot('apres_file');

// 10. Confirmation de suppression
await send('Supprime le brouillon');
await page.waitForSelector('role=dialog', { timeout: 15000 });
await page.waitForTimeout(400);
await shot('confirmation_suppression');
await page.getByRole('button', { name: 'Non, annuler' }).click();
await waitAnswer();

// 11. Erreur
await send('Provoque une erreur');
await waitAnswer();
await page.waitForTimeout(500);
await shot('erreur');

// 12. Page Agents
await page.getByRole('button', { name: 'Agents' }).click();
await page.waitForTimeout(400);
await shot('agents');

console.log(logs.length ? logs.join('\n') : 'console : aucune erreur');
await browser.close();
