// Captures et contrôles de la page Agents (phase 4), sur le serveur de démonstration : grille,
// canvas (clic, liens de port à port, refus d'un cycle, glisser-déposer, suppression, zoom,
// grille), exécution d'un workflow en DAG avec ses fils, arrêt, erreur, diff d'un code joint,
// fils rouverts et supprimés, agents personnalisés, fichiers de workflow (format de Tk) ;
// débat, statistiques et moniteur, tâches planifiées (création, exécution, fil, rapport,
// modification, suppression), exécution venue du téléphone, notification de fin.
// Usage (depuis frontend/) :
//   node scripts/capture_agents.mjs URL_AVEC_JETON [DOSSIER] [étapes séparées par des virgules]
// Étapes : grille, canvas, execution, arret, erreur, diff, fils, perso, fichiers, debat, stats,
// planif, mobile, notif
import { mkdirSync, writeFileSync } from 'node:fs';
import { resolve } from 'node:path';

import { openDemo, usage, waitReady } from './lib.mjs';

const [, , url, out = 'captures/agents', only = ''] = process.argv;
if (!url) usage('node scripts/capture_agents.mjs URL_AVEC_JETON [DOSSIER] [étapes]');
mkdirSync(out, { recursive: true });
const steps = new Set(only ? only.split(',') : []);
const wanted = (name) => !steps.size || steps.has(name);

const { browser, page } = await openDemo(url, { width: 1920, height: 1000 });
const logs = [];
page.on('console', (m) => {
  // 409 : refus attendus (exécution déjà en cours…), contrôlés par les étapes
  if (m.text().includes('status of 409')) return;
  if (m.type() === 'error' || m.type() === 'warning') logs.push(`[${m.type()}] ${m.text()}`);
});
page.on('pageerror', (e) => logs.push(`[pageerror] ${e.message}`));

let n = 0;
async function shot(name, options = {}) {
  n += 1;
  const file = `${out}/${String(n).padStart(2, '0')}_${name}.png`;
  await page.screenshot({ path: file, ...options });
  console.log('capture', file);
}

const checks = [];
function check(label, ok, detail = '') {
  checks.push(ok);
  console.log(`${ok ? 'OK ' : 'ÉCHEC'} ${label}${detail ? ` — ${detail}` : ''}`);
}

const button = (name) => page.getByRole('button', { name, exact: true });
const card = (name) => page.getByRole('button', { name: new RegExp(`^${name} :`) });
const nodes = () => page.locator('.react-flow__node');
const edges = () => page.locator('.react-flow__edge');
const nodeById = (id) => page.locator(`.react-flow__node[data-id="${id}"]`);
const scroller = () => page.locator('main > div').first();
const toast = (text) => page.getByText(text, { exact: false }).first();

async function center(locator) {
  const box = await locator.boundingBox();
  if (!box) throw new Error('élément invisible');
  return { x: box.x + box.width / 2, y: box.y + box.height / 2 };
}

/** Glisse du port de sortie d'un nœud au port d'entrée d'un autre (souris de Playwright) */
async function link(from, to) {
  const start = await center(nodeById(from).locator('.react-flow__handle.source'));
  const end = await center(nodeById(to).locator('.react-flow__handle.target'));
  await page.mouse.move(start.x, start.y);
  await page.mouse.down();
  await page.mouse.move((start.x + end.x) / 2, (start.y + end.y) / 2, { steps: 6 });
  await page.mouse.move(end.x, end.y, { steps: 6 });
  await page.mouse.up();
  await page.waitForTimeout(150);
}

async function clearCanvas() {
  await button('Vider').click();
  await page.waitForTimeout(150);
}

async function setTask(text) {
  const task = page.getByRole('textbox', { name: 'Tâche' });
  await task.fill(text);
}

const RUNS = '[aria-label="Fils d\'exécution"]';

/** Lance la tâche ; revient quand son fil apparaît dans la liste */
async function execute() {
  const before = await page.locator(`${RUNS} li`).count();
  await button('Exécuter').click();
  await page.waitForFunction(
    ([selector, count]) => document.querySelectorAll(`${selector} li`).length > count,
    [RUNS, before],
    { timeout: 15000 },
  );
}

/** Fin de l'exécution : plus aucun fil en cours, et Exécuter revient */
async function waitRunEnd(timeout = 60000) {
  await page.waitForFunction(
    (selector) => !document.querySelector(`${selector} [aria-label="En cours"]`),
    RUNS,
    { timeout },
  );
  await button('Exécuter').waitFor({ timeout });
  await page.waitForTimeout(300);
}

async function openAgents() {
  await page.getByRole('button', { name: 'Agents', exact: true }).click();
  await page.getByRole('heading', { name: 'Agents IA spécialisés' }).waitFor({ timeout: 15000 });
  await page.waitForTimeout(800);
}

await waitReady(page, 60000);
// Chromium sans fenêtre : animations ralenties la première seconde après le lancement
await page.waitForTimeout(1500);
await openAgents();

if (wanted('grille')) {
  const cards = await page.getByRole('button', { name: /^.+Agent : / }).count();
  check('grille : 9 agents intégrés et les agents personnalisés', cards >= 9, `${cards} cartes`);
  const icons = await page.locator('[aria-label="Agents"] svg').count();
  check('grille : une icône lucide par carte (pas d’émoji)', icons >= cards, `${icons} icônes`);
  await shot('grille');
}

if (wanted('canvas')) {
  await clearCanvas();
  for (const name of ['PlannerAgent', 'CodeAgent', 'SecurityAgent', 'DebugAgent']) {
    await card(name).click();
  }
  check('canvas : un clic sur une carte ajoute son nœud', (await nodes().count()) === 4);
  // Positions : Planner à gauche, Code et Security l'un sous l'autre, Debug à droite
  const flow = page.locator('.react-flow__pane');
  const place = async (id, x, y) => {
    const node = nodeById(id);
    const from = await center(node.locator('.text-\\[15px\\]').first());
    const pane = await flow.boundingBox();
    await page.mouse.move(from.x, from.y);
    await page.mouse.down();
    await page.mouse.move(pane.x + x, pane.y + y, { steps: 8 });
    await page.mouse.up();
    await page.waitForTimeout(100);
  };
  await place('0', 260, 190);
  await place('1', 600, 110);
  await place('2', 600, 270);
  await place('3', 940, 110);
  await link('0', '1');
  await link('0', '2');
  await link('1', '3');
  check('canvas : trois liens tracés de port à port', (await edges().count()) === 3);
  await link('3', '0');
  check('canvas : un cycle est refusé', (await edges().count()) === 3);
  await link('0', '1');
  check('canvas : un lien en double est refusé', (await edges().count()) === 3);
  await shot('canvas_dag');

  // Glisser une carte sur le canvas (glisser-déposer du navigateur)
  const pane = await flow.boundingBox();
  await card('OptimizerAgent').dragTo(flow, { targetPosition: { x: 1150, y: 270 } });
  await page.waitForTimeout(300);
  const dropped = (await nodes().count()) === 5;
  check('canvas : une carte glissée devient un nœud', dropped);
  if (dropped) {
    const box = await nodeById('4').boundingBox();
    const near =
      box &&
      Math.abs(box.x + box.width / 2 - (pane.x + 1150)) < 40 &&
      Math.abs(box.y + box.height / 2 - (pane.y + 270)) < 40;
    check('canvas : le nœud est centré sur le point de dépôt (aimanté)', Boolean(near));
  }
  // Retirer : ✕ du nœud, puis Suppr sur un nœud sélectionné
  await nodeById('4')
    .getByRole('button', { name: /Retirer/ })
    .click();
  check('canvas : ✕ retire le nœud', (await nodes().count()) === 4);
  await card('WebAgent').click();
  const web = nodeById('5');
  await web.click();
  await page.keyboard.press('Delete');
  await page.waitForTimeout(150);
  check('canvas : Suppr retire le nœud sélectionné', (await web.count()) === 0);
  // Clic droit sur un lien : supprimé (CodeAgent → DebugAgent, horizontal)
  const edge = page.locator('.react-flow__edge[data-id="e1-3"] .react-flow__edge-interaction');
  const mid = await center(edge);
  await page.mouse.click(mid.x, mid.y, { button: 'right' });
  await page.waitForTimeout(150);
  check('canvas : clic droit sur un lien le supprime', (await edges().count()) === 2);
  await link('1', '3');
  // Zoom, vue remise à zéro, grille
  const scale = async () =>
    page.locator('.react-flow__viewport').evaluate((el) => el.style.transform);
  const before = await scale();
  await button('Zoom avant').click();
  await page.waitForTimeout(300);
  const zoomed = await scale();
  check('canvas : Zoom avant', zoomed !== before, zoomed);
  await button('Réinitialiser la vue').click();
  await page.waitForTimeout(350);
  check('canvas : vue remise à zéro', (await scale()).includes('scale(1)'), await scale());
  await button('Masquer la grille').click();
  check('canvas : grille masquée', (await page.locator('.react-flow__background').count()) === 0);
  await button('Afficher la grille').click();
  check('canvas : grille affichée', (await page.locator('.react-flow__background').count()) === 1);
}

if (wanted('execution')) {
  if ((await nodes().count()) !== 4) {
    await clearCanvas();
    for (const name of ['PlannerAgent', 'CodeAgent', 'SecurityAgent', 'DebugAgent']) {
      await card(name).click();
    }
    await link('0', '1');
    await link('0', '2');
    await link('1', '3');
  }
  await setTask('Développe une API REST sécurisée pour gérer une bibliothèque de livres.');
  await execute();
  await button('Arrêter').first().waitFor({ timeout: 10000 });
  check('exécution : Exécuter devient Arrêter', true);
  await page.getByText('En cours ·').first().waitFor({ timeout: 10000 });
  await page
    .locator('.react-flow__node', { hasText: 'En cours' })
    .first()
    .waitFor({ timeout: 15000 });
  check('exécution : un nœud passe « En cours »', true);
  // Étape 2 : CodeAgent et SecurityAgent partent ensemble, mais le modèle n'en sert qu'un
  // à la fois (Ollama avec qwen3.5, imité par le serveur de démonstration) : l'autre attend
  // son tour, et seul le lien de celui qui écrit s'anime
  await page
    .locator('.react-flow__node', { hasText: 'Attend son tour' })
    .first()
    .waitFor({ timeout: 20000 });
  const animated = await page.locator('.agent-edge-running').count();
  const queued = await page
    .getByText(/Le modèle répond d’abord à (CodeAgent|SecurityAgent) : cet agent écrira ensuite/)
    .count();
  check('exécution : en parallèle, l’agent pas encore servi attend son tour', queued === 1);
  check('exécution : seul le lien de l’agent qui écrit s’anime', animated === 1, `${animated}`);
  await page.waitForTimeout(600);
  await scroller().evaluate((el) => (el.scrollTop = el.scrollHeight));
  await page.waitForTimeout(400);
  await shot('execution_en_cours');
  await page.locator('.react-flow__node', { hasText: 'En cours' }).first().scrollIntoViewIfNeeded();
  await shot('execution_canvas');
  await waitRunEnd();
  const done = await page.locator('.react-flow__node', { hasText: 'Terminé' }).count();
  check('exécution : les 4 nœuds finissent « Terminé »', done === 4, `${done}`);
  const statusText = await page.getByText('✅ Workflow terminé (100% succès)').count();
  check('exécution : statut final du fil', statusText > 0);
  const plan = await page
    .getByText(/Étape 1 : PlannerAgent · Étape 2, en parallèle : CodeAgent, SecurityAgent/)
    .count();
  check('exécution : plan du DAG affiché', plan > 0);
  const sections = await page.getByText(/Étape \d\/3/).count();
  check('exécution : une section par agent, avec son étape', sections === 4, `${sections}`);
  const written = await page.getByText('Plan de développement').count();
  check('exécution : sortie Markdown rendue', written > 0);
  await scroller().evaluate((el) => (el.scrollTop = el.scrollHeight));
  await page.waitForTimeout(300);
  await shot('execution_terminee');
}

if (wanted('arret')) {
  await clearCanvas();
  await card('CodeAgent').click();
  await card('DebugAgent').click();
  await link('0', '1');
  await setTask('Tâche lente pour essayer Arrêter');
  await execute();
  await page
    .locator('.react-flow__node', { hasText: 'En cours' })
    .first()
    .waitFor({ timeout: 15000 });
  await page.waitForTimeout(800);
  await page.keyboard.press('Escape');
  await waitRunEnd(15000);
  const stopped = await page.getByText('⛔ Génération interrompue').count();
  check('arrêt : Échap interrompt l’exécution', stopped > 0);
  const skipped = await page.getByText('Non exécuté').count();
  check('arrêt : l’agent suivant n’est pas lancé', skipped > 0);
  await scroller().evaluate((el) => (el.scrollTop = el.scrollHeight));
  await shot('arret');
}

if (wanted('erreur')) {
  await clearCanvas();
  await card('WebAgent').click();
  await setTask('Provoque une erreur');
  await execute();
  await waitRunEnd(20000);
  const failed = await page.locator('.react-flow__node', { hasText: 'Erreur' }).count();
  check('erreur : le nœud passe « Erreur »', failed === 1);
  await scroller().evaluate((el) => (el.scrollTop = el.scrollHeight));
  await shot('erreur');
}

if (wanted('diff')) {
  const code = resolve(out, 'utils_demo.py');
  writeFileSync(
    code,
    [
      'def chercher(livres, mot):',
      '    print("debug", mot)',
      '    resultats = []',
      '    for livre in livres:',
      '        if livre.titre == None:',
      '            continue',
      '        if mot in livre.titre:',
      '            resultats.append(livre)',
      '    return resultats',
      '',
    ].join('\n'),
  );
  await clearCanvas();
  await card('OptimizerAgent').click();
  await setTask('Optimise ce code');
  await page.getByRole('button', { name: 'Joindre un fichier' }).last().click();
  const chooser = page.waitForEvent('filechooser');
  await page.getByRole('menuitem', { name: 'Code' }).click();
  await (await chooser).setFiles(code);
  await page.getByText('utils_demo.py').first().waitFor({ timeout: 10000 });
  check('diff : fichier de code joint (puce)', true);
  await execute();
  await waitRunEnd(30000);
  const toggle = page.getByRole('button', { name: /^Diff/ });
  await toggle.waitFor({ timeout: 5000 });
  const label = await toggle.innerText();
  check(
    'diff : sortie lue en diff, lignes ajoutées et retirées',
    /\+\d+\s*−\d+/.test(label),
    label,
  );
  const removed = await page.getByText('print("debug", mot)').count();
  check('diff : la ligne retirée est montrée', removed > 0);
  const explanation = () => page.getByText('Voici la version revue du code fourni').count();
  check('diff : l’onglet Diff ne montre que le code', (await explanation()) === 0);
  await page.locator('table').last().scrollIntoViewIfNeeded();
  await shot('diff');
  await page.getByRole('button', { name: 'Sortie', exact: true }).click();
  await page.waitForTimeout(200);
  check('diff : l’explication de l’agent est dans Sortie', (await explanation()) > 0);
  await shot('diff_sortie');
}

if (wanted('fils')) {
  const rows = page.getByRole('list', { name: "Fils d'exécution" }).getByRole('listitem');
  const count = await rows.count();
  check('fils : un fil par exécution', count >= 1, `${count}`);
  if (count >= 2) {
    await rows
      .nth(count - 1)
      .getByRole('button')
      .first()
      .click();
    await page.waitForTimeout(500);
    await shot('fil_rouvert');
    check('fils : un ancien fil se rouvre', true);
    await rows.nth(count - 1).hover();
    await rows
      .nth(count - 1)
      .getByRole('button', { name: 'Supprimer ce fil' })
      .click();
    await page.waitForTimeout(500);
    check('fils : un fil se supprime', (await rows.count()) === count - 1);
  }
  // Gardés d'un lancement à l'autre (D33) : relus après un rechargement de la page
  await page.reload();
  await waitReady(page, 60000);
  await openAgents();
  await page.waitForTimeout(800);
  const kept = await page
    .getByRole('list', { name: "Fils d'exécution" })
    .getByRole('listitem')
    .count();
  check('fils : relus après rechargement', kept >= 1 && kept === Math.max(count - 1, 1), `${kept}`);
}

if (wanted('perso')) {
  await button('Créer un agent').click();
  const dialog = page.getByRole('dialog', { name: 'Créer un agent personnalisé' });
  await dialog.waitFor({ timeout: 5000 });
  await button('Créer').click();
  check(
    'perso : nom requis',
    (await dialog.getByText("Veuillez entrer un nom pour l'agent.").count()) === 1,
  );
  await dialog.getByLabel("Nom de l'agent").fill('JuristeAgent');
  await dialog.getByLabel('Rôle / Description').fill('Conseil juridique en droit du numérique');
  await button('Créer').click();
  await dialog.getByText('Génération du system prompt en cours…').waitFor({ timeout: 3000 });
  await shot('perso_generation');
  await dialog.waitFor({ state: 'detached', timeout: 15000 });
  await card('JuristeAgent').waitFor({ timeout: 5000 });
  check('perso : agent créé, carte ajoutée', true);
  await card('JuristeAgent').click();
  const added = nodes().filter({ hasText: 'JuristeAgent' });
  check('perso : l’agent personnalisé va sur le canvas', (await added.count()) === 1);
  await card('JuristeAgent').hover();
  await page.getByRole('button', { name: 'Modifier JuristeAgent' }).click();
  const edit = page.getByRole('dialog', { name: 'Modifier JuristeAgent' });
  await edit.getByLabel("Nom de l'agent").fill('LegalAgent');
  await button('Sauvegarder').click();
  await edit.waitFor({ state: 'detached', timeout: 10000 });
  await card('LegalAgent').waitFor({ timeout: 5000 });
  check('perso : renommé sans réécrire son prompt', true);
  await card('LegalAgent').hover();
  await shot('perso_carte');
  await page.getByRole('button', { name: 'Supprimer LegalAgent' }).click();
  await button('Supprimer').click();
  await card('LegalAgent').waitFor({ state: 'detached', timeout: 5000 });
  check('perso : supprimé, carte retirée', true);
  check(
    'perso : ses nœuds quittent le canvas',
    (await nodes().filter({ hasText: 'JuristeAgent' }).count()) === 0,
  );
}

if (wanted('fichiers')) {
  const tk = resolve(out, 'workflow_tk.json');
  writeFileSync(
    tk,
    JSON.stringify(
      {
        version: '8.1.0',
        nodes: {
          3: {
            agent_type: 'planner',
            name: 'PlannerAgent',
            color: '#06b6d4',
            icon: '📋',
            x: 75,
            y: 100,
            status: 'idle',
          },
          7: {
            agent_type: 'code',
            name: 'CodeAgent',
            color: '#3b82f6',
            icon: '🐍',
            x: 375,
            y: 25,
            status: 'done',
          },
          9: {
            agent_type: 'security',
            name: 'SecurityAgent',
            color: '#ec4899',
            icon: '🛡',
            x: 375,
            y: 200,
            status: 'idle',
          },
        },
        connections: [
          { from: 3, to: 7 },
          { from: 3, to: 9 },
        ],
        zoom: 1.0,
        pan_x: 0.0,
        pan_y: 0.0,
      },
      null,
      2,
    ),
  );
  const chooser = page.waitForEvent('filechooser');
  await button('Charger').click();
  await (await chooser).setFiles(tk);
  await toast('Workflow chargé').waitFor({ timeout: 5000 });
  check(
    'fichiers : workflow de Tk chargé',
    (await nodes().count()) === 3 && (await edges().count()) === 2,
  );
  const ids = await nodes().evaluateAll((els) =>
    els.map((el) => el.getAttribute('data-id')).join(','),
  );
  check('fichiers : nœuds renumérotés depuis 0, comme from_dict', ids === '0,1,2', ids);
  await page.locator('.react-flow').scrollIntoViewIfNeeded();
  await shot('fichiers_charge');
  await button('Enregistrer').click();
  await toast('Workflow sauvegardé').waitFor({ timeout: 5000 });
  check('fichiers : enregistré (outputs/workflows/ hors de la fenêtre)', true);
  await button('Exporter').click();
  await toast('Workflow exporté').waitFor({ timeout: 5000 });
  check('fichiers : exporté en Markdown', true);
}

/** Requête au serveur avec le jeton de la page (routes de démonstration, focus) */
async function serverPost(path, body) {
  return page.evaluate(
    async ([url, data]) => {
      const token = sessionStorage.getItem('my_ai.token');
      const response = await fetch(url, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
      });
      return response.json();
    },
    [path, body],
  );
}

const runRows = () => page.getByRole('list', { name: "Fils d'exécution" }).getByRole('listitem');

if (wanted('debat')) {
  await button('Débat').click();
  const dialog = page.getByRole('dialog', { name: 'Mode Débat entre deux agents' });
  await dialog.waitFor({ timeout: 5000 });
  await dialog.getByLabel('Agent B — Opposant').selectOption('code');
  await button('Démarrer le débat').click();
  check(
    'débat : deux agents différents requis',
    (await dialog.getByText('❌ Choisis deux agents différents').count()) === 1,
  );
  await dialog.getByLabel('Agent B — Opposant').selectOption('creative');
  await dialog.getByLabel('Sujet du débat').fill('Faut-il imposer une convention de nommage ?');
  await dialog.getByLabel('Nombre de tours :').fill('2');
  await shot('debat_dialogue');
  await button('Démarrer le débat').click();
  await dialog.waitFor({ state: 'detached', timeout: 5000 });
  await page.getByText('Tour 1 — CodeAgent (Proposant)').waitFor({ timeout: 10000 });
  check('débat : son fil s’ouvre, un tour par section', true);
  await page.waitForTimeout(600);
  await shot('debat_en_cours');
  await waitRunEnd(60000);
  const turns = await page.getByText(/^Tour \d — /).count();
  check('débat : le proposant puis l’opposant, à chaque tour', turns === 4, `${turns}`);
  check('débat : statut final', (await page.getByText('✅ Débat terminé (2 tours)').count()) > 0);
  check(
    'débat : proposant, opposant et tours en tête du fil',
    (await page.getByText('Proposant : CodeAgent · Opposant : CreativeAgent · 2 tours').count()) ===
      1,
  );
  check(
    'débat : tokens/s de chaque tour',
    (await page.getByText(/ tok\/s$/).count()) >= 4,
    `${await page.getByText(/ tok\/s$/).count()}`,
  );
  await shot('debat_termine');
}

if (wanted('stats')) {
  const panel = page.locator('section[aria-labelledby="agents-stats"]');
  await panel.scrollIntoViewIfNeeded();
  await panel.getByRole('meter').first().waitFor({ timeout: 10000 });
  check('ressources : six barres', (await panel.getByRole('meter').count()) === 6);
  const tps = await panel.getByRole('meter', { name: 'Tokens/sec' }).getAttribute('aria-valuetext');
  check('ressources : tokens/s du dernier agent', /tok\/s$/.test(tps ?? ''), tps ?? '');
  const sparks = await panel.locator('svg polyline').count();
  check('ressources : mini-graphiques', sparks >= 4, `${sparks}`);
  const cpu = () => panel.getByRole('meter', { name: 'CPU' }).getAttribute('aria-valuetext');
  const before = await cpu();
  await page.waitForTimeout(3600);
  check(
    'ressources : une mesure toutes les 3 s',
    (await cpu()) !== before,
    `${before} → ${await cpu()}`,
  );
  const tasks = await panel.getByText('Tâches exécutées').locator('xpath=..').innerText();
  check('statistiques : tâches exécutées', /\d+/.test(tasks), tasks.replace(/\s+/g, ' '));
  await shot('stats');
}

if (wanted('planif')) {
  const section = page.locator('section[aria-labelledby="agents-schedule"]');
  await section.scrollIntoViewIfNeeded();
  const rows = section.getByRole('list', { name: 'Tâches planifiées' }).getByRole('listitem');
  await rows.first().waitFor({ timeout: 10000 });
  check('planif : tâches de la copie listées', (await rows.count()) >= 4, `${await rows.count()}`);
  await shot('planif_liste');
  await section.getByRole('button', { name: 'Nouvelle tâche' }).click();
  const dialog = page.getByRole('dialog', { name: 'Nouvelle tâche planifiée' });
  await dialog.waitFor({ timeout: 5000 });
  await dialog.getByRole('button', { name: 'Enregistrer' }).click();
  await dialog.getByText('❌ Nom requis.').waitFor({ timeout: 5000 });
  check('planif : nom requis (message de Tk)', true);
  await dialog.getByLabel('Nom').fill('Veille de démonstration');
  await dialog.getByLabel('Tâche / Sujet (débat)').fill('Résume les nouveautés de FastAPI');
  await dialog.getByRole('radio', { name: 'Intervalle' }).click();
  await dialog.getByLabel('Toutes les').fill('30');
  await dialog.getByLabel('Unité').selectOption('minutes');
  await shot('planif_dialogue');
  await dialog.getByRole('button', { name: 'Enregistrer' }).click();
  await dialog.waitFor({ state: 'detached', timeout: 5000 });
  await toast('Tâche planifiée enregistrée').waitFor({ timeout: 5000 });
  const row = rows.filter({ hasText: 'Veille de démonstration' });
  check('planif : tâche créée', (await row.count()) === 1);
  check('planif : planning en clair', (await row.getByText('toutes les 30 min').count()) === 1);
  await row.getByRole('button', { name: 'Exécuter maintenant' }).click();
  await toast('Exécution lancée').waitFor({ timeout: 5000 });
  const scheduled = runRows().filter({ hasText: 'Veille de démonstration' });
  await scheduled.waitFor({ timeout: 10000 });
  check(
    'planif : son fil apparaît, marqué « Tâche planifiée » (D37)',
    (await scheduled.getByRole('img', { name: 'Tâche planifiée' }).count()) === 1,
  );
  await waitRunEnd(30000);
  await page
    .locator('[data-toast-region]')
    .getByText('Veille de démonstration')
    .waitFor({ timeout: 10000 });
  check('planif : toast de fin (sans notification du système en démo)', true);
  await row.getByText(/réussie/).waitFor({ timeout: 10000 });
  check('planif : dernier résultat', true);
  check('planif : rapport', (await row.getByRole('button', { name: 'Rapport' }).count()) === 1);
  await row.getByRole('button', { name: 'Voir le fil' }).click();
  await page.waitForTimeout(500);
  const thread = page.locator('h3', { hasText: 'Veille de démonstration' });
  check('planif : « Voir le fil » ouvre son fil', (await thread.count()) === 1);
  await shot('planif_fil');
  await section.scrollIntoViewIfNeeded();
  await row.getByRole('button', { name: 'Modifier' }).click();
  const edit = page.getByRole('dialog', { name: 'Modifier la tâche' });
  await edit.waitFor({ timeout: 5000 });
  check(
    'planif : la source reste figée',
    (await edit.getByRole('radiogroup', { name: 'Source' }).count()) === 0,
  );
  await edit.getByLabel('Nom').fill('Veille du soir');
  await edit.getByRole('button', { name: 'Enregistrer' }).click();
  await edit.waitFor({ state: 'detached', timeout: 5000 });
  const renamed = rows.filter({ hasText: 'Veille du soir' });
  await renamed.waitFor({ timeout: 5000 });
  check('planif : modifiée', true);
  await renamed.getByRole('switch').click();
  await renamed.getByText('prochaine : désactivée').waitFor({ timeout: 5000 });
  check('planif : désactivée', true);
  await section.getByRole('switch', { name: "Exécuter même l'appli fermée" }).click();
  await toast('aucune tâche Windows créée').waitFor({ timeout: 5000 });
  check('planif : exécution appli fermée (simulée en démo)', true);
  await section.getByRole('switch', { name: "Exécuter même l'appli fermée" }).click();
  await renamed.getByRole('button', { name: 'Supprimer' }).click();
  const confirm = page.getByRole('dialog', { name: 'Supprimer la tâche' });
  await confirm.getByRole('button', { name: 'Supprimer' }).click();
  await renamed.waitFor({ state: 'detached', timeout: 5000 });
  check('planif : supprimée après confirmation', true);
  await shot('planif_fin');
}

if (wanted('mobile')) {
  await page.locator(RUNS).scrollIntoViewIfNeeded();
  const openedRow = page.locator(`${RUNS} [aria-current="true"]`);
  const opened = await openedRow.innerText();
  const { exec_id: execId } = await serverPost('/api/demo/mobile-run', {
    task: 'Tâche lente envoyée du téléphone',
    agent: 'web',
  });
  const phone = runRows().filter({ has: page.getByRole('img', { name: 'Lancé du téléphone' }) });
  await phone.first().waitFor({ timeout: 10000 });
  check('téléphone : son fil apparaît, marqué (D37)', Boolean(execId));
  check('téléphone : Exécuter attend', await button('Exécuter').isDisabled());
  check(
    'téléphone : le fil ouvert ne change pas',
    (await openedRow.innerText()) === opened,
    opened.split('\n')[0],
  );
  await shot('mobile_en_cours');
  await phone.first().getByRole('button').first().click();
  await page.getByText('Lancé du téléphone', { exact: true }).waitFor({ timeout: 5000 });
  await page.getByRole('button', { name: 'Arrêter', exact: true }).last().click();
  await waitRunEnd(20000);
  check(
    'téléphone : arrêté depuis la fenêtre',
    (await page.getByText('⛔ Génération interrompue').count()) > 0,
  );
  await shot('mobile_arrete');
}

if (wanted('notif')) {
  // Fenêtre sans focus : la fin d'un fil de plus de 8 s est notifiée (démo : dans la fenêtre)
  await serverPost('/api/window/focus', { focused: false });
  await clearCanvas();
  await card('CreativeAgent').click();
  await setTask('Tâche lente, pour la notification de fin');
  await execute();
  await waitRunEnd(60000);
  await toast('Notification du système (démo)').waitFor({ timeout: 5000 });
  check(
    'notification : fin d’un fil long, fenêtre sans focus',
    (await page.getByText('CreativeAgent — tâche terminée').count()) > 0,
  );
  await shot('notification');
  await serverPost('/api/window/focus', { focused: true });
}

console.log(logs.length ? logs.join('\n') : 'aucune erreur de console');
const failed = checks.filter((ok) => !ok).length;
console.log(`${checks.length - failed} contrôles sur ${checks.length}`);
await browser.close();
process.exit(failed || logs.length ? 1 : 0);
