// Vraie fenêtre sur le serveur de démonstration (--window --vraie-voix) : ce qui passe par le
// système. Dialogues de Windows (menu « + », dossiers projet, Export), glisser-déposer depuis
// l'Explorateur à la vraie souris, synthèse vocale et micro, ouverture des fichiers (Explorateur,
// application par défaut, navigateur, Téléchargements).
// Ouvre des fenêtres du système et prend la vraie souris : à lancer PC laissé libre. Le script
// referme chaque fenêtre qu'il a ouverte (repérée par son apparition), supprime sa copie dans
// Téléchargements et remet la lecture automatique comme il l'a trouvée (config.yaml).
// Usage (depuis frontend/) : node scripts/window_system.mjs [DOSSIER] [étapes séparées par des virgules]
// Étapes : dialogues, dossier, export, glisser, voix, ouvrir
import { spawn } from 'node:child_process';
import { copyFileSync, existsSync, mkdirSync, rmSync, statSync } from 'node:fs';

import { composer, connectWindow, openSidebar, waitIdle, waitReady, win } from './lib.mjs';

const [, , out = 'captures', only = ''] = process.argv;
mkdirSync(out, { recursive: true });
const steps = new Set(only ? only.split(',') : []);
const wanted = (name) => !steps.size || steps.has(name);

/** Chemin Windows d'un fichier ou dossier du dépôt */
const repoPath = (relative) =>
  decodeURIComponent(new URL(`../../${relative}`, import.meta.url).pathname)
    .replace(/^\/([A-Za-z]:)/, '$1')
    .replaceAll('/', '\\')
    .replace(/\\$/, '');

const FIXTURES = repoPath('temp/migration_test_data/fichiers');
const fixture = (name) => `${FIXTURES}\\${name}`;
const WORK = repoPath('temp/window_system');
rmSync(WORK, { recursive: true, force: true });
mkdirSync(WORK, { recursive: true });

const { browser, page } = await connectWindow();
await waitReady(page);

const checks = [];
function check(label, ok, detail = '') {
  checks.push(ok);
  console.log(`${ok ? 'OK ' : 'ÉCHEC'} ${label}${detail ? ` — ${detail}` : ''}`);
}

let n = 0;
async function shot(name) {
  n += 1;
  await page.screenshot({ path: `${out}/${String(n).padStart(2, '0')}_${name}.png` });
}

const button = (name) => page.getByRole('button', { name, exact: true });

async function newConversation() {
  await page.keyboard.press('Control+n');
  await page.waitForTimeout(500);
}

async function send(text) {
  await composer(page).fill(text);
  await composer(page).press('Enter');
  await page.waitForSelector('[aria-busy="true"]', { timeout: 10000 }).catch(() => undefined);
  await waitIdle(page);
  await page.waitForTimeout(400);
}

/** Puces de la zone de saisie : noms des pièces jointes */
const chips = () =>
  page.evaluate(() =>
    [...document.querySelectorAll('[aria-label^="Retirer "]')].map((e) =>
      e.getAttribute('aria-label').slice('Retirer '.length),
    ),
  );

async function removeChips() {
  for (const name of await chips()) await button(`Retirer ${name}`).click();
  await page.waitForTimeout(300);
}

/** Dialogue de Windows ouvert par My_AI : rempli avec `path` et validé ; titre et types */
function answerDialog(path) {
  return JSON.parse(win('dialog', path).split('\n')[0]);
}

/** Fenêtres visibles d'une classe Win32 : [hwnd, classe, processus, titre] */
const windowsOf = (className) => JSON.parse(win('windows', className));

/** Première fenêtre de cette classe apparue depuis `before` (liste de hwnd), ou null */
async function newWindow(className, before, timeout = 15000, title = /./) {
  const end = Date.now() + timeout;
  while (Date.now() < end) {
    const fresh = windowsOf(className).find(
      ([hwnd, , , text]) => !before.includes(hwnd) && title.test(text),
    );
    if (fresh) return fresh;
    await page.waitForTimeout(300);
  }
  return null;
}

const hwnds = (className) => windowsOf(className).map(([hwnd]) => hwnd);

/** Texte des dernières notifications (toasts) */
const toasts = () =>
  page.evaluate(() =>
    [...document.querySelectorAll('[role="status"]')].map((e) => e.textContent.trim()),
  );

await newConversation();
await removeChips();

if (wanted('dialogues')) {
  // Menu « + » : un dialogue de Windows par type, filtres de Tk
  const kinds = [
    ['PDF', 'rapport_trimestriel.pdf'],
    ['DOCX', 'note_projet.docx'],
    ['Excel / CSV', 'budget_2026.xlsx'],
    ['PowerPoint', 'presentation_equipe.pptx'],
    ['Code', 'script_tri.py'],
    ['Image', 'schema.png'],
  ];
  for (const [label, file] of kinds) {
    await button('Joindre un fichier').click();
    await page.getByRole('menuitem', { name: label, exact: true }).click({ noWaitAfter: true });
    const dialog = answerDialog(fixture(file));
    const ok = await button(`Retirer ${file}`)
      .waitFor({ timeout: 20000 })
      .then(() => true)
      .catch(() => false);
    check(`« + » ${label} : « ${dialog.titre} », ${dialog.types.join(' ; ')}`, ok, file);
  }
  await page.waitForTimeout(1500);
  await shot('dialogues_pieces');
  // Une seule image en attente, comme Tk
  copyFileSync(fixture('schema.png'), `${WORK}\\schema_2.png`);
  await button('Joindre un fichier').click();
  await page.getByRole('menuitem', { name: 'Image', exact: true }).click({ noWaitAfter: true });
  answerDialog(`${WORK}\\schema_2.png`);
  await button('Retirer schema_2.png').waitFor({ timeout: 20000 });
  const images = (await chips()).filter((name) => name.endsWith('.png'));
  check('une seule image en attente', images.length === 1, images.join(', '));
  await removeChips();
  check('pièces retirées', (await chips()).length === 0);
}

if (wanted('dossier')) {
  // Dossiers du projet : dialogue de choix d'un dossier
  await openSidebar(page);
  const section = button('Dossiers du projet');
  if ((await section.getAttribute('aria-expanded')) === 'false') await section.click();
  await button('Attacher un dossier').click({ noWaitAfter: true });
  const dialog = answerDialog(FIXTURES);
  const attached = await button('Détacher')
    .first()
    .waitFor({ timeout: 30000 })
    .then(() => true)
    .catch(() => false);
  check(`dossier projet : « ${dialog.titre} », dossier indexé et listé`, attached);
  await shot('dossier_projet');
  if (attached) {
    await button('Détacher').first().click();
    await page.getByRole('dialog').getByRole('button', { name: 'Détacher', exact: true }).click();
    await page.waitForTimeout(800);
  }
  await newConversation();
}

if (wanted('export')) {
  await send('Bonjour');
  for (const [label, extension] of [
    ['Markdown (.md)', 'md'],
    ['HTML (.html)', 'html'],
    ['PDF (.pdf)', 'pdf'],
  ]) {
    await openSidebar(page);
    await button('Exporter la conversation').click();
    await page.getByRole('menuitem', { name: label, exact: true }).click({ noWaitAfter: true });
    const target = `${WORK}\\export.${extension}`;
    const dialog = answerDialog(target);
    const end = Date.now() + 20000;
    while (!existsSync(target) && Date.now() < end) await page.waitForTimeout(300);
    const size = existsSync(target) ? statSync(target).size : 0;
    check(`export ${extension} : « ${dialog.titre} »`, size > 0, `${size} octets`);
  }
  await shot('export');
  await newConversation();
}

if (wanted('glisser')) {
  // Explorateur à gauche, My_AI à droite ; vraie souris de l'un à l'autre
  const before = hwnds('CabinetWClass');
  spawn('explorer.exe', [FIXTURES], { detached: true, stdio: 'ignore' }).unref();
  const explorer = await newWindow('CabinetWClass', before, 15000);
  check('glisser : Explorateur ouvert sur les fichiers de test', Boolean(explorer), explorer?.[3]);
  if (explorer) {
    win('move', '0', '0', '760', '1000', String(explorer[0]));
    win('move', '780', '0', '1140', '1040');
    await page.waitForTimeout(1500);
    const [left, top] = JSON.parse(win('origin'));
    const dpr = await page.evaluate(() => devicePixelRatio);
    const box = await composer(page).boundingBox();
    const drop = [
      Math.round(left + (box.x + box.width / 2) * dpr),
      Math.round(top + (box.y + box.height / 2) * dpr),
    ];
    const item = JSON.parse(win('element', explorer[3], 'rapport_trimestriel.pdf'));
    check('glisser : fichier trouvé dans l’Explorateur', Boolean(item), JSON.stringify(item));
    if (item) {
      win('drag', ...[...item, ...drop].map(String));
      const ok = await button('Retirer rapport_trimestriel.pdf')
        .waitFor({ timeout: 20000 })
        .then(() => true)
        .catch(() => false);
      check('glisser : fichier joint avec son vrai chemin', ok);
      await shot('glisser_fichier');
      await removeChips();
    }
    win('close', String(explorer[0]));
    // Dossier glissé : depuis le dossier parent
    const beforeParent = hwnds('CabinetWClass');
    spawn('explorer.exe', [repoPath('temp/migration_test_data')], {
      detached: true,
      stdio: 'ignore',
    }).unref();
    const parent = await newWindow('CabinetWClass', beforeParent, 15000);
    if (parent) {
      win('move', '0', '0', '760', '1000', String(parent[0]));
      await page.waitForTimeout(1500);
      const folder = JSON.parse(win('element', parent[3], 'fichiers'));
      if (folder) {
        win('drag', ...[...folder, ...drop].map(String));
        await page.waitForTimeout(6000);
        const names = await chips();
        console.log(
          'dossier glissé : pièces',
          JSON.stringify(names),
          'notifications',
          JSON.stringify(await toasts()),
        );
        check(
          'glisser : dossier → ses fichiers joints',
          names.length >= 5,
          `${names.length} pièces`,
        );
        await shot('glisser_dossier');
        await removeChips();
      }
      win('close', String(parent[0]));
    }
  }
}

if (wanted('voix')) {
  await newConversation();
  await send('Bonjour');
  // Lecture d'une réponse (pyttsx3)
  await page.getByRole('button', { name: 'Lire à voix haute' }).last().click();
  const speaking = await button('Arrêter la lecture')
    .last()
    .waitFor({ timeout: 15000 })
    .then(() => true)
    .catch(() => false);
  check('lecture : la réponse est lue à voix haute', speaking);
  const ended = await page
    .getByRole('button', { name: 'Arrêter la lecture' })
    .waitFor({ state: 'detached', timeout: 90000 })
    .then(() => true)
    .catch(() => false);
  check('lecture : le bouton revient à la fin', ended);
  // Dictée : la synthèse de Windows dit une phrase pendant l'enregistrement. Un micro qui
  // annule l'écho (réseau Intel Smart Sound) retire ce que dit le PC : la transcription est
  // alors vide. Contrôlés : enregistrement, transcription, retour au repos ; le texte est
  // rapporté, la vraie dictée se vérifie à la voix
  await composer(page).fill('');
  await button('Saisie vocale').click();
  const recording = await button('Arrêter la dictée')
    .waitFor({ timeout: 20000 })
    .then(() => true)
    .catch(() => false);
  check('micro : enregistrement lancé', recording);
  if (recording) {
    await page.waitForTimeout(800);
    await new Promise((resolve) => {
      spawn(
        'powershell.exe',
        [
          '-NoProfile',
          '-Command',
          "Add-Type -AssemblyName System.Speech; $s = New-Object System.Speech.Synthesis.SpeechSynthesizer; $s.Volume = 100; $s.Speak('Bonjour, ceci est un essai de dictée pour My AI.')",
        ],
        { stdio: 'ignore' },
      ).on('exit', resolve);
    });
    await page.waitForTimeout(500);
    await button('Arrêter la dictée').click();
    const back = await button('Saisie vocale')
      .waitFor({ timeout: 120000 })
      .then(() => true)
      .catch(() => false);
    check('dictée : transcrite, micro de nouveau disponible', back);
    await page.waitForTimeout(500);
    console.log(`info : texte dicté inséré : ${JSON.stringify(await composer(page).inputValue())}`);
    await shot('dictee');
  }
  await composer(page).fill('');
  // Lecture automatique : activée, une réponse lue seule, puis désactivée (config.yaml)
  await openSidebar(page);
  await button('Lecture automatique : désactivée').click();
  await send('Bonjour encore');
  const auto = await button('Arrêter la lecture')
    .last()
    .waitFor({ timeout: 15000 })
    .then(() => true)
    .catch(() => false);
  check('lecture automatique : la réponse suivante est lue seule', auto);
  if (auto) await button('Arrêter la lecture').last().click();
  await button('Lecture automatique : activée').click();
  await page.waitForTimeout(500);
  check(
    'lecture automatique : désactivée de nouveau',
    (await button('Lecture automatique : désactivée').count()) === 1,
  );
}

if (wanted('ouvrir')) {
  // Chemin cité : montré dans l'Explorateur (jamais exécuté)
  await newConversation();
  await send('Donne un chemin de fichier');
  const beforeExplorer = hwnds('CabinetWClass');
  await page.locator('article .md-path').first().click();
  const shown = await newWindow('CabinetWClass', beforeExplorer, 15000);
  check('chemin cité : montré dans l’Explorateur', Boolean(shown), shown?.[3]);
  if (shown) win('close', String(shown[0]));
  // Document produit : son application (Word)
  await newConversation();
  await send('Rédige un document de synthèse');
  const beforeWord = hwnds('OpusApp');
  await button('Ouvrir note_projet.docx').click();
  const word = await newWindow('OpusApp', beforeWord, 60000, /note_projet/);
  check('document produit : ouvert dans son application', Boolean(word), word?.[3]);
  if (word) {
    await page.waitForTimeout(2000);
    win('close', String(word[0]));
  }
  // Artefact : navigateur du système
  await newConversation();
  await send('Fais-moi un artefact HTML');
  const beforeChrome = hwnds('Chrome_WidgetWin_1');
  await button('Ouvrir dans le navigateur').click();
  const browserWindow = await newWindow('Chrome_WidgetWin_1', beforeChrome, 20000, /Compteur/);
  check(
    'artefact : ouvert dans le navigateur (nouvelle fenêtre)',
    Boolean(browserWindow),
    browserWindow?.[3] ?? JSON.stringify(windowsOf('Chrome_WidgetWin_1').map((w) => w[3])),
  );
  if (browserWindow) win('close', String(browserWindow[0]));
  // Télécharger : copie dans Téléchargements, supprimée ensuite
  await newConversation();
  await send('Génère un fichier somme.py');
  await button('Télécharger (dossier Téléchargements)').last().click();
  await page.waitForTimeout(1500);
  const message = (await toasts()).find((text) => text.includes('somme')) ?? '';
  const copy = message.match(/[A-Za-z]:\\[^\n]*somme[^\n]*\.py/)?.[0];
  check(
    'télécharger : copie dans Téléchargements',
    Boolean(copy && existsSync(copy)),
    copy ?? message,
  );
  if (copy && existsSync(copy)) rmSync(copy);
}

await browser.close(); // se détache sans fermer la fenêtre
const failed = checks.filter((ok) => !ok).length;
console.log(failed ? `${failed} contrôle(s) en échec` : 'Tous les contrôles passent');
process.exitCode = failed ? 1 : 0;
