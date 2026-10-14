// Captures et contrôles des panneaux (phase 3b), sur le serveur de démonstration : assistant de
// premier lancement (serveur lancé avec --premier-lancement), Réglages, Mémoire, Prompts, Relay,
// Aide, palette Ctrl+K. Usage (depuis frontend/) :
//   node scripts/capture_panels.mjs URL_AVEC_JETON [DOSSIER] [étapes séparées par des virgules]
// Étapes : assistant, reglages, memoire, prompts, relay, aide
import { mkdirSync } from 'node:fs';

import { composer, openDemo, openSidebar, usage, waitReady } from './lib.mjs';

const [, , url, out = 'captures/panneaux', only = ''] = process.argv;
if (!url) usage('node scripts/capture_panels.mjs URL_AVEC_JETON [DOSSIER] [étapes]');
mkdirSync(out, { recursive: true });
const steps = new Set(only ? only.split(',') : []);
const wanted = (name) => !steps.size || steps.has(name);

const { browser, page } = await openDemo(url);
const logs = [];
page.on('console', (m) => {
  // 409 : refus attendus, contrôlés par les étapes (commande de prompt déjà prise…)
  if (m.text().includes('status of 409')) return;
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
// Chromium sans fenêtre : animations ralenties la première seconde après le lancement
await page.waitForTimeout(1500);

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

if (wanted('memoire')) {
  await openSidebar(page);
  await page.getByRole('button', { name: 'Mémoire', exact: true }).click();
  const panel = dialog('Mémoire locale');
  await panel.waitFor({ timeout: 5000 });
  const rows = panel.locator('li');
  const pager = panel.getByText(/^Page \d+ \/ \d+/);
  await rows.first().waitFor({ timeout: 10000 });
  await page.waitForTimeout(300);
  await shot('memoire_faits');
  const stats = await panel.getByText(/fait\(s\) ·/).innerText();
  check(
    'mémoire : compteurs',
    /^\d+ fait\(s\) · \d+ chunk\(s\) document · \d+ entrée/.test(stats),
    stats,
  );
  check('mémoire : pages de 20', (await rows.count()) === 20, await pager.innerText());

  // Catégorie, puis recherche
  await panel.getByLabel('Catégorie').selectOption('person');
  await page.waitForFunction(() => document.querySelectorAll('[role=dialog] li').length === 3);
  check('mémoire : filtre par catégorie', (await rows.count()) === 3);
  await panel.getByLabel('Catégorie').selectOption('Toutes');
  const search = panel.getByLabel('Rechercher dans la mémoire');
  await search.fill('rtx');
  await search.press('Enter');
  await page.waitForFunction(() => document.querySelectorAll('[role=dialog] li').length === 1);
  check('mémoire : recherche', (await rows.first().innerText()).includes('RTX 3060'));
  await search.fill('');
  await search.press('Enter');
  await page.waitForFunction(() => document.querySelectorAll('[role=dialog] li').length === 20);

  // Ajout d'un fait
  await button('Ajouter').click();
  const add = dialog('Nouveau fait');
  await add.waitFor({ timeout: 3000 });
  await add.getByLabel('Catégorie').selectOption('decision');
  await add.getByLabel('Contenu').fill('La palette de commandes s’ouvre avec Ctrl+K');
  await page.waitForTimeout(400);
  await shot('memoire_ajout');
  await add.getByRole('button', { name: 'Ajouter' }).click();
  await page.getByText('Fait ajouté', { exact: true }).waitFor({ timeout: 5000 });
  // Toast au-dessus du panneau ; le fermer ne ferme pas le panneau
  const toastOnTop = await page.evaluate(() => {
    const toast = document.querySelector('[data-toast-region] [role=status]');
    if (!toast) return false;
    const box = toast.getBoundingClientRect();
    const hit = document.elementFromPoint(box.left + 8, box.top + box.height / 2);
    return Boolean(hit?.closest('[data-toast-region]'));
  });
  check('mémoire : toast au-dessus du panneau', toastOnTop);
  await page.locator('[data-toast-region] button[aria-label="Fermer"]').first().click();
  await page.waitForTimeout(200);
  check('mémoire : fermer un toast laisse le panneau ouvert', await panel.isVisible());
  await add.waitFor({ state: 'detached', timeout: 3000 });
  await page.waitForTimeout(300);
  check('mémoire : fait ajouté en tête', (await rows.first().innerText()).includes('Ctrl+K'));

  // Modification d'un fait
  await rows.first().getByRole('button', { name: 'Modifier' }).click();
  const editor = panel.getByRole('textbox', { name: 'Modifier le contenu' });
  await editor.fill('La palette de commandes s’ouvre avec Ctrl+K, ou depuis l’en-tête');
  await panel.getByRole('button', { name: 'Enregistrer' }).click();
  await page.getByText('Modifié', { exact: true }).waitFor({ timeout: 5000 });
  await page.waitForTimeout(300);
  check('mémoire : fait modifié', (await rows.first().innerText()).includes('depuis l’en-tête'));

  // Pagination
  await button('Suivant').click();
  await page.getByText(/^Page 2 \/ 2/).waitFor({ timeout: 5000 });
  const paged = await pager.innerText();
  check(
    'mémoire : page suivante',
    (await rows.count()) === Number(/\((\d+)\)/.exec(paged)[1]) - 20,
    paged,
  );
  await button('Précédent').click();
  await page.getByText(/^Page 1 \/ 2/).waitFor({ timeout: 5000 });

  // Conversations : modification à la source, Échap annule la modification
  await page.getByRole('tab', { name: 'Conversations' }).click();
  await page.waitForFunction(() =>
    [...document.querySelectorAll('[role=dialog] li')].some((li) =>
      li.textContent.includes('vous'),
    ),
  );
  await page.waitForTimeout(300);
  await shot('memoire_conversations');
  const first = rows.first();
  const session = (await first.locator('p').last().innerText()).split('·')[0].trim();
  await first.getByRole('button', { name: 'Modifier' }).click();
  await panel.getByText('La modification réécrit le message d').waitFor({ timeout: 3000 });
  await shot('memoire_modification_conversation');
  await page.keyboard.press('Escape');
  await page.waitForTimeout(300);
  check(
    'mémoire : Échap annule la modification sans fermer',
    (await panel.isVisible()) &&
      (await panel.getByRole('textbox', { name: 'Modifier le contenu' }).count()) === 0,
  );
  await rows.first().getByRole('button', { name: 'Modifier' }).click();
  await panel
    .getByRole('textbox', { name: 'Modifier le contenu' })
    .fill('Message réécrit depuis la Mémoire');
  await panel.getByRole('button', { name: 'Enregistrer' }).click();
  await page.waitForFunction(() =>
    [...document.querySelectorAll('[role=dialog] li')].some((li) =>
      li.textContent.includes('Message réécrit depuis la Mémoire'),
    ),
  );
  check('mémoire : message réécrit à la source', true, session);

  // Suppression : confirmation, case « message d'origine » pour une conversation
  await rows.first().getByRole('button', { name: 'Supprimer' }).click();
  const confirm = dialog('Confirmation de suppression');
  await confirm.waitFor({ timeout: 3000 });
  check(
    'mémoire : case « message d’origine » cochée',
    await confirm.getByRole('checkbox').isChecked(),
  );
  await page.waitForTimeout(400);
  await shot('memoire_suppression');
  await confirm.getByRole('button', { name: 'Non, annuler' }).click();
  await confirm.waitFor({ state: 'detached', timeout: 3000 });

  await page.getByRole('tab', { name: 'Documents' }).click();
  await page.waitForFunction(() =>
    [...document.querySelectorAll('[role=dialog] li')].some((li) =>
      li.textContent.includes('document'),
    ),
  );
  const before = await rows.count();
  await rows.first().getByRole('button', { name: 'Supprimer' }).click();
  await dialog('Confirmation de suppression')
    .getByRole('button', { name: 'Oui, supprimer' })
    .click();
  await page.getByText('Supprimé', { exact: true }).waitFor({ timeout: 5000 });
  await page.waitForTimeout(300);
  check(
    'mémoire : document supprimé',
    (await rows.count()) === before - 1,
    `${before} → ${await rows.count()}`,
  );
  await page.keyboard.press('Escape');
  await panel.waitFor({ state: 'detached', timeout: 3000 });
  check('mémoire : Échap ferme le panneau', true);
}

if (wanted('prompts')) {
  await openSidebar(page);
  const openPrompts = async () => {
    await page.getByRole('button', { name: 'Prompts', exact: true }).click();
    const opened = dialog('Bibliothèque de prompts');
    await opened.locator('li').first().waitFor({ timeout: 10000 });
    return opened;
  };
  let panel = await openPrompts();
  await page.waitForTimeout(300);
  await shot('prompts');
  const firstRow = await panel.locator('li').first().innerText();
  check('prompts : défauts listés', firstRow.includes('/code'), firstRow.split('\n')[0]);

  // Formulaire : contrôles de Tk, création
  await button('Nouveau prompt').click();
  const form = dialog('Nouveau prompt');
  await form.waitFor({ timeout: 3000 });
  await form.getByRole('button', { name: 'Enregistrer' }).click();
  check(
    'prompts : nom ou commande exigé',
    (await form.getByRole('alert').innerText()) === 'Renseignez au moins un nom ou une commande.',
  );
  await form.getByLabel('Nom').fill('Plan de tests');
  await form.getByLabel('Commande (slash, optionnel)').fill('plantest');
  await form.getByLabel('Description (optionnel)').fill('Plan de tests d’une fonctionnalité');
  await form
    .getByLabel(/Contenu envoyé/)
    .fill('Écris un plan de tests détaillé pour : {arguments}\n\nCas nominaux, cas limites.');
  await page.waitForTimeout(300);
  await shot('prompts_nouveau');
  await form.getByRole('button', { name: 'Enregistrer' }).click();
  await page.getByText('Prompt créé', { exact: true }).waitFor({ timeout: 5000 });
  await form.waitFor({ state: 'detached', timeout: 3000 });
  const created = panel.locator('li').filter({ hasText: '/plantest' });
  check('prompts : prompt créé dans la liste', (await created.count()) === 1);

  // Commande déjà prise : message de la bibliothèque, dans le formulaire
  await created.getByRole('button', { name: 'Modifier' }).click();
  const edit = dialog('Modifier le prompt');
  await edit.getByLabel('Commande (slash, optionnel)').fill('code');
  await edit.getByRole('button', { name: 'Enregistrer' }).click();
  await edit.getByRole('alert').waitFor({ timeout: 3000 });
  check(
    'prompts : commande déjà prise',
    (await edit.getByRole('alert').innerText()) === 'La commande /code existe déjà.',
  );
  await page.waitForTimeout(300);
  await shot('prompts_commande_prise');
  await edit.getByRole('button', { name: 'Annuler' }).click();
  await page.keyboard.press('Escape');
  await panel.waitFor({ state: 'detached', timeout: 3000 });

  // Autocomplétion de la zone de saisie
  await composer(page).fill('');
  await composer(page).pressSequentially('/plan');
  const commands = page.getByRole('listbox', { name: 'Commandes' });
  await commands.waitFor({ timeout: 5000 });
  check(
    'prompts : commande proposée à la saisie',
    (await commands.innerText()).includes('plantest'),
  );
  await composer(page).fill('');

  // Suppression confirmée
  panel = await openPrompts();
  await panel
    .locator('li')
    .filter({ hasText: '/plantest' })
    .getByRole('button', { name: 'Supprimer' })
    .click();
  const confirm = dialog('Supprimer le prompt');
  await confirm.waitFor({ timeout: 3000 });
  check(
    'prompts : confirmation nommée',
    (await confirm.innerText()).includes('Voulez-vous vraiment supprimer « /plantest » ?'),
  );
  await page.waitForTimeout(300);
  await shot('prompts_suppression');
  await confirm.getByRole('button', { name: 'Supprimer' }).click();
  await page.getByText('Prompt supprimé', { exact: true }).waitFor({ timeout: 5000 });
  await page.waitForTimeout(300);
  check(
    'prompts : prompt supprimé',
    (await panel.locator('li').filter({ hasText: '/plantest' }).count()) === 0,
  );
  await page.keyboard.press('Escape');
  await panel.waitFor({ state: 'detached', timeout: 3000 });
}

if (wanted('relay')) {
  // Relay simulé du serveur de démonstration : tunnels à 1,5 s et 4 s, un téléphone à 8 s
  const origin = new URL(url).origin;
  const token = new URL(url).hash.replace('#token=', '');
  const relayState = async () =>
    (
      await page.request.get(`${origin}/api/relay`, {
        headers: { Authorization: `Bearer ${token}` },
      })
    ).json();
  await page.context().grantPermissions(['clipboard-read', 'clipboard-write'], { origin });

  await page.keyboard.press('Control+r');
  const panel = dialog('My_AI Relay');
  await panel.waitFor({ timeout: 5000 });
  await panel.getByText('Tunnels en cours de connexion…').waitFor({ timeout: 5000 });
  check('relay : Ctrl+R ouvre le panneau et démarre le Relay', (await relayState()).running);
  await page.waitForTimeout(300);
  await shot('relay_connexion');
  await panel.getByRole('button', { name: 'Copier pour l’extension VS Code' }).click();
  check(
    'relay : extension VS Code, tunnel non prêt',
    await panel.getByText('Tunnel non prêt').isVisible(),
  );

  await panel.getByText('Tunnels actifs : cloudflare, localhost.run').waitFor({ timeout: 15000 });
  const qr = panel.getByRole('img', { name: 'QR code du Relay' });
  await qr.waitFor({ timeout: 10000 });
  // Le QR code encode l'adresse de la page de routage, celle copiée par « Copier »
  await panel.getByRole('button', { name: 'Copier', exact: true }).click();
  await panel.getByText('Copié !').waitFor({ timeout: 3000 });
  const copied = await page.evaluate(() => navigator.clipboard.readText());
  const state = await relayState();
  check('relay : « Copier » copie la page de routage', copied === state.url, copied.slice(0, 60));
  check('relay : jeton affiché', await panel.getByText(`Token : ${state.token}`).isVisible());
  await panel.getByText('1 appareil(s) connecté(s)').waitFor({ timeout: 10000 });
  check('relay : appareil connecté', true);
  await page.waitForTimeout(300);
  await shot('relay');

  // Fermer le panneau ne l'arrête pas ; Ctrl+R le rouvre tel quel
  await page.keyboard.press('Escape');
  await panel.waitFor({ state: 'detached', timeout: 3000 });
  check('relay : Échap ferme sans arrêter', (await relayState()).running);
  await page.keyboard.press('Control+r');
  await panel.getByRole('img', { name: 'QR code du Relay' }).waitFor({ timeout: 5000 });
  await panel.getByRole('button', { name: 'Arrêter le Relay' }).click();
  await panel.waitFor({ state: 'detached', timeout: 3000 });
  await page.waitForTimeout(300);
  check('relay : « Arrêter le Relay » l’arrête', !(await relayState()).running);
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
