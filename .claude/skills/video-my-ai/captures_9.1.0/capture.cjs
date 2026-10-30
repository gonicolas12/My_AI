// Tournage des captures de la vidéo My_AI 9.1.0 : fenêtre du PC (serveur de
// démonstration), VS Code web avec la vraie extension, téléphone sur le vrai
// Relay. Une seule conversation Code, partagée par les trois.
//
//   node capture.cjs            tout
//   node capture.cjs sidebar    barre latérale avant/après seulement
const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

const S = path.resolve(__dirname, '..');
const OUT = path.join(S, 'kit', 'raw');
fs.mkdirSync(OUT, { recursive: true });
const API = 'http://127.0.0.1:8770';
const DESK_URL = `${API}/#token=videotoken`;
const FOLDER = `${S}/workspace/bibliotheque-api`;
const VSC_URL = `http://127.0.0.1:8000/?folder=${FOLDER}`;
const info = JSON.parse(fs.readFileSync(`${S}/relay_info.json`, 'utf-8'));
const ONLY = process.argv[2] || 'all';

const MSG_A = "Ajoute une route GET /livres/{id} qui renvoie une 404 si le livre n'existe pas";
const MSG_C = 'Ajoute un test pour cette 404';
const MSG_B = 'Lance les tests';
const MSG_D = 'Écris le message de commit';

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const t0 = Date.now();
const log = (...a) => console.log(`[${((Date.now() - t0) / 1000).toFixed(1)}s]`, ...a);

async function api(pathname, body) {
  const res = await fetch(API + pathname, {
    method: body ? 'POST' : 'GET',
    headers: { Authorization: 'Bearer videotoken', Origin: API, 'Content-Type': 'application/json' },
    body: body ? JSON.stringify(body) : undefined,
  });
  return res.json();
}

async function until(fn, label, timeout = 60000, every = 120) {
  const end = Date.now() + timeout;
  let last;
  while (Date.now() < end) {
    try {
      const v = await fn();
      if (v) return v;
    } catch (err) {
      last = err;
    }
    await sleep(every);
  }
  throw new Error(`Timeout : ${label}${last ? ` (${last.message})` : ''}`);
}

async function lastAssistant() {
  const snap = await api('/api/code');
  const msgs = snap.messages || [];
  return [...msgs].reverse().find((m) => m.role === 'assistant') || null;
}
const tool = (msg, name, status) =>
  (msg?.parts || []).find((p) => p.kind === 'tool' && p.name === name && (!status || p.status === status));
const text = (msg, segment) =>
  ((msg?.parts || []).find((p) => p.kind === 'text' && p.segment === segment) || {}).text || '';

const meta = { surfaces: {}, steps: [], boxes: {} };

// Positions (px CSS) d'éléments clés d'une capture, pour les zooms de la vidéo
async function boxes(name, locators) {
  const found = {};
  for (const [label, locator] of Object.entries(locators)) {
    try {
      const b = await locator.first().boundingBox({ timeout: 1500 });
      if (b) found[label] = { x: Math.round(b.x), y: Math.round(b.y), w: Math.round(b.width), h: Math.round(b.height) };
    } catch {
      /* élément absent de cette capture */
    }
  }
  meta.boxes[name] = found;
}

// Lignes de l'éditeur de VS Code entre deux textes (inclus) : un seul cadre
async function editorLines(page, first, last) {
  return page.evaluate(([a, b]) => {
    const lines = [...document.querySelectorAll('.part.editor .view-line')]
      .map((el) => ({ el, text: el.textContent.replace(/\u00a0/g, ' '), r: el.getBoundingClientRect() }))
      .sort((p, q) => p.r.top - q.r.top);
    const i = lines.findIndex((l) => l.text.includes(a));
    const j = lines.findIndex((l) => l.text.includes(b));
    if (i < 0 || j < 0) return null;
    const top = lines[i].r.top;
    const bottom = lines[j].r.bottom;
    const left = Math.min(...lines.slice(i, j + 1).map((l) => l.r.left));
    const right = Math.max(...lines.slice(i, j + 1).map((l) => l.r.left + l.el.scrollWidth));
    return { x: Math.round(left), y: Math.round(top), w: Math.round(right - left), h: Math.round(bottom - top) };
  }, [first, last]);
}

async function snap(page, name, note) {
  const file = path.join(OUT, `${name}.png`);
  await page.screenshot({ path: file });
  meta.steps.push({ file: `${name}.png`, at: +((Date.now() - t0) / 1000).toFixed(2), note });
  log('📸', name, note ? `— ${note}` : '');
}

// ── VS Code ───────────────────────────────────────────────────────────────

async function palette(page, command) {
  const input = page.locator('.quick-input-widget input.input').first();
  for (const keys of ['F1', 'Control+Shift+P', 'F1']) {
    await page.keyboard.press('Escape');
    await page.keyboard.press(keys);
    try {
      await input.waitFor({ state: 'visible', timeout: 4000 });
      break;
    } catch {
      /* nouvel essai */
    }
  }
  await page.keyboard.type(command, { delay: 8 });
  await sleep(900);
  await page.keyboard.press('Enter');
}

async function quickInput(page, value) {
  const input = page.locator('.quick-input-widget input.input').first();
  await input.waitFor({ state: 'visible', timeout: 15000 });
  await sleep(300);
  await input.fill(value);
  await sleep(250);
  await page.keyboard.press('Enter');
}

function webview(page) {
  return page.frameLocator('iframe.webview.ready').first().frameLocator('iframe#active-frame');
}

async function openInEditor(page, file) {
  await page.keyboard.press('Escape');
  await page.keyboard.press('Control+P');
  await page.locator('.quick-input-widget input.input').first().waitFor({ state: 'visible', timeout: 8000 });
  await page.keyboard.type(file, { delay: 10 });
  await sleep(900);
  await page.keyboard.press('Enter');
  await sleep(1000);
}

// Largeur d'une partie du plan de travail, par sa poignée (gauche ou droite)
async function resize(page, selector, edge, width) {
  const part = page.locator(selector).first();
  const b = await part.boundingBox();
  if (!b || Math.abs(b.width - width) < 6) return;
  const x = edge === 'right' ? b.x + b.width + 1 : b.x - 2;
  const y = b.y + b.height / 2;
  const target = edge === 'right' ? b.x + width : b.x + b.width - width;
  await page.mouse.move(x, y);
  await page.mouse.down();
  await page.mouse.move((x + target) / 2, y, { steps: 6 });
  await page.mouse.move(target, y, { steps: 6 });
  await page.mouse.up();
  await sleep(500);
}

async function prepVSCode(context) {
  const page = context.pages()[0] || (await context.newPage());
  await page.goto(VSC_URL);
  await page.waitForSelector('.monaco-workbench', { timeout: 60000 });
  await sleep(6000);
  // Connexion au Relay de la démo : chaîne de connexion, puis code d'accès
  const status = page.locator('.statusbar-item', { hasText: 'My_AI' }).first();
  const connected = async () => /connecté|connected/i.test(await status.innerText()) &&
    !/non connecté|not connected/i.test(await status.innerText());
  if (!(await connected().catch(() => false))) {
    await palette(page, 'My_AI Relay: Connect');
    await quickInput(page, info.connection_string);
    await sleep(1500);
    await quickInput(page, info.access_code);
    await until(connected, 'VS Code connecté', 30000);
  }
  log('VS Code connecté');
  // Éditeurs de la prise précédente fermés, panneau du bas masqué
  await palette(page, 'View: Close All Editors');
  await sleep(800);
  const panel = page.locator('.part.panel').first();
  for (const command of ['View: Hide Panel', 'View: Close Panel']) {
    if (!(await panel.isVisible().catch(() => false))) break;
    await palette(page, command);
    await sleep(800);
  }
  if (await panel.isVisible().catch(() => false)) {
    await page.locator('.part.editor').first().click({ position: { x: 300, y: 10 } }).catch(() => {});
    await page.keyboard.press('Control+J');
    await sleep(800);
  }
  log('panneau du bas visible :', await panel.isVisible().catch(() => false));
  // « Layout: us » de la barre d'état : masqué
  const layout = page.locator('.statusbar-item', { hasText: 'Layout' }).first();
  if (await layout.isVisible().catch(() => false)) {
    await layout.click({ button: 'right' });
    await sleep(600);
    const hide = page.locator('.monaco-menu .action-label', { hasText: /Layout|Keyboard/ }).first();
    if (await hide.count()) await hide.click();
    else await page.keyboard.press('Escape');
    await sleep(400);
  }
  // Explorateur : src et tests ouverts, src/app.py dans l'éditeur
  for (const folder of ['src', 'tests']) {
    const row = page.locator('.explorer-folders-view .monaco-list-row', { hasText: folder }).first();
    if ((await row.getAttribute('aria-expanded')) === 'false') await row.click();
    await sleep(300);
  }
  // Chat My_AI visible à droite, éditeur assez large pour les lignes du projet
  await palette(page, 'My_AI Relay: Open Chat View');
  await sleep(1500);
  await resize(page, '.part.sidebar', 'right', 190);
  await resize(page, '.part.auxiliarybar', 'left', 440);
  await openInEditor(page, 'src/app.py');
  // Haut du fichier, curseur sur une ligne vide (pas de mot surligné)
  await page.keyboard.press('Control+Home');
  await page.keyboard.press('ArrowDown');
  await page.keyboard.press('ArrowDown');
  await sleep(300);
  await page.mouse.move(700, 600);
  await webview(page).locator('#messageInput').waitFor({ state: 'visible', timeout: 20000 });
  return page;
}

// ── Fenêtre du PC ─────────────────────────────────────────────────────────

async function prepDesktop(browser) {
  const context = await browser.newContext({
    viewport: { width: 1440, height: 900 }, deviceScaleFactor: 2, locale: 'fr-FR',
  });
  const page = await context.newPage();
  await page.goto(DESK_URL);
  await page.locator('textarea').first().waitFor({ state: 'visible', timeout: 60000 });
  await sleep(1500);
  const aside = page.locator('aside').first();
  if ((await aside.getAttribute('aria-hidden')) === 'true') {
    await page.keyboard.press('Control+b');
    await sleep(800);
  }
  await page.mouse.move(900, 700);
  log('PC prêt');
  return page;
}

const codeButton = (page) => page.locator('aside button:has(svg.lucide-code-xml)').first();

async function measureSidebar(page) {
  return page.evaluate(() => {
    const aside = document.querySelector('aside');
    const box = (el) => {
      if (!el) return null;
      const r = el.getBoundingClientRect();
      return { x: Math.round(r.x), y: Math.round(r.y), w: Math.round(r.width), h: Math.round(r.height) };
    };
    const items = [];
    const push = (label, el) => items.push({ label, ...box(el) });
    push('aside', aside);
    push('titre My_AI', aside.querySelector('span.text-accent'));
    const buttons = [...aside.querySelectorAll('div.space-y-1\\.5 > *')];
    buttons.forEach((el, i) => push(`ligne ${i + 1} : ${el.textContent.trim().slice(0, 40)}`, el));
    const label = [...aside.querySelectorAll('div')].find((d) => d.textContent.trim() === 'Conversations' && d.children.length >= 1);
    push('libellé Conversations', label);
    aside.querySelectorAll('ul li').forEach((li) => push(`conversation : ${li.textContent.trim().slice(0, 40)}`, li));
    const bottom = aside.querySelector('div.border-t.flex');
    push('barre du bas (Relay, voix, Réglages, Mémoire, Prompts, Export)', bottom);
    return items;
  });
}

// ── Téléphone ─────────────────────────────────────────────────────────────

async function prepPhone(browser) {
  const context = await browser.newContext({
    viewport: { width: 390, height: 844 }, deviceScaleFactor: 3, isMobile: true, hasTouch: true,
    locale: 'fr-FR',
    userAgent: 'Mozilla/5.0 (iPhone; CPU iPhone OS 18_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.6 Mobile/15E148 Safari/604.1',
  });
  const page = await context.newPage();
  await page.goto(info.local_url);
  const unlock = page.locator('#unlockInput');
  try {
    await unlock.waitFor({ state: 'visible', timeout: 8000 });
    await unlock.fill(info.access_code);
    await page.locator('#unlockBtn').click();
  } catch {
    /* déjà déverrouillé */
  }
  await until(async () => /connect/i.test(await page.locator('#statusText').innerText()) &&
    !(await page.locator('#statusText').innerText()).includes('...'), 'téléphone connecté', 30000);
  await sleep(1200);
  log('Téléphone prêt :', await page.locator('#statusText').innerText());
  return page;
}

// ── Tournage ──────────────────────────────────────────────────────────────

(async () => {
  // Projet de démo et conversation remis à zéro
  execSync('git checkout -q -- . && git clean -qfd', { cwd: FOLDER });
  await api('/api/code/clear', {});

  const browser = await chromium.launch();
  const vscContext = await chromium.launchPersistentContext(`${S}/chrome-vscode`, {
    viewport: { width: 1440, height: 900 }, deviceScaleFactor: 2, locale: 'en-US',
  });
  try {
    const vsc = await prepVSCode(vscContext);
    const desk = await prepDesktop(browser);
    const phone = await prepPhone(browser);
    await until(async () => (await api('/api/code/state')).state.vscode, 'VS Code vu par le hub', 20000);

    // ── 1. Barre latérale : avant / après le bouton Code ──
    await codeButton(desk).waitFor({ state: 'visible' });
    await until(async () => (await desk.locator('aside button:has(svg.lucide-code-xml) span.bg-success').count()) > 0,
      'pastille verte', 15000);
    await snap(desk, 'D02_pc_barre_avec_code', 'barre latérale avec le bouton Code (VS Code connecté)');
    meta.surfaces.sidebar_after = await measureSidebar(desk);
    await boxes('D02_pc_barre_avec_code', { barre_laterale: desk.locator('aside'), bouton_code: codeButton(desk) });
    await codeButton(desk).screenshot({ path: path.join(OUT, 'D02b_bouton_code_seul.png') });
    await desk.locator('aside').first().screenshot({ path: path.join(OUT, 'D02c_barre_laterale_seule_avec_code.png') });
    await desk.evaluate(() => {
      document.querySelector('aside button:has(svg.lucide-code-xml)').style.display = 'none';
    });
    await sleep(300);
    await snap(desk, 'D01_pc_barre_sans_code', 'même écran, sans le bouton Code (avant la 9.1.0)');
    meta.surfaces.sidebar_before = await measureSidebar(desk);
    await desk.locator('aside').first().screenshot({ path: path.join(OUT, 'D01c_barre_laterale_seule_sans_code.png') });
    await desk.evaluate(() => {
      document.querySelector('aside button:has(svg.lucide-code-xml)').style.display = '';
    });
    await snap(phone, 'M01_tel_chat_barre_onglets', "téléphone : vue Chat, nouvelle barre d'onglets");
    await boxes('M01_tel_chat_barre_onglets', {
      barre_onglets: phone.locator('.tab-bar'), bouton_code: phone.locator('#tabCode'),
      onglet_chat: phone.locator('#tabChat'), onglet_agents: phone.locator('#tabAgents'),
      corbeille: phone.locator('#trashBtn'),
    });
    await snap(vsc, 'V00_vscode_pret', 'VS Code : projet ouvert, chat My_AI connecté');
    await boxes('V00_vscode_pret', {
      chat_my_ai: vsc.locator('.part.auxiliarybar'), editeur: vsc.locator('.part.editor'),
      explorateur: vsc.locator('.part.sidebar'),
    });
    if (ONLY === 'sidebar') return;

    // ── 2. PC → VS Code ──
    await codeButton(desk).click();
    await sleep(1200);
    await desk.mouse.move(1200, 800);
    await snap(desk, 'D03_pc_page_code_vide', 'page Code du PC, conversation vide');
    const deskInput = desk.locator('textarea').first();
    await boxes('D03_pc_page_code_vide', { zone_de_saisie: deskInput.locator('xpath=../..') });
    await deskInput.click();
    await desk.keyboard.type(MSG_A, { delay: 18 });
    await sleep(300);
    await snap(desk, 'D04_pc_message_tape', 'message tapé sur le PC');
    await boxes('D04_pc_message_tape', { zone_de_saisie: deskInput.locator('xpath=../..') });
    await desk.keyboard.press('Enter');
    await until(async () => tool(await lastAssistant(), 'edit_file', 'awaiting-approval'), 'approbation edit_file', 30000);
    await sleep(700);
    await desk.mouse.move(1200, 820);
    await snap(desk, 'D05_pc_approbation', "PC : la modification attend l'accord (boutons)");
    await boxes('D05_pc_approbation', {
      carte_accord: desk.getByText('My_AI attend votre accord pour continuer.').locator('..'),
      bouton_autoriser: desk.locator('button', { hasText: 'Autoriser une fois' }),
      message_utilisateur: desk.getByText(MSG_A, { exact: true }),
    });
    const wv = webview(vsc);
    await snap(vsc, 'V01_vscode_message_du_pc', 'VS Code : le message du PC et la même demande d’accord');
    await boxes('V01_vscode_message_du_pc', {
      chat_my_ai: vsc.locator('.part.auxiliarybar'), editeur: vsc.locator('.part.editor'),
      accord_dans_vscode: wv.locator('.tool-approval'),
      message_du_pc: wv.getByText(MSG_A, { exact: true }),
    });
    await snap(phone, 'M00_tel_chat_pendant_pc', 'téléphone toujours sur le Chat');
    await desk.locator('button', { hasText: 'Autoriser une fois' }).first().click();
    await until(async () => text(await lastAssistant(), 1).length > 200, 'réponse finale qui s’écrit', 30000, 40);
    await snap(desk, 'D06_pc_reponse_en_cours', 'PC : réponse en streaming (pastille Code orange)');
    await snap(vsc, 'V02_vscode_fichier_modifie_streaming', 'VS Code : route ajoutée dans src/app.py, réponse en streaming');
    meta.boxes.V02_vscode_fichier_modifie_streaming = {
      nouvelle_route: await editorLines(vsc, '@app.get("/livres/{livre_id}")', 'return LIVRES[livre_id]'),
    };
    await until(async () => (await lastAssistant())?.status === 'done', 'réponse A finie', 30000);
    await sleep(900);
    await snap(desk, 'D07_pc_reponse_finale', 'PC : réponse finale avec le code');
    await boxes('D07_pc_reponse_finale', { bloc_de_code: desk.locator('pre').last(), bouton_code: codeButton(desk) });
    await snap(vsc, 'V03_vscode_fichier_modifie_final', 'VS Code : src/app.py modifié (marges vertes), réponse finale');
    await boxes('V03_vscode_fichier_modifie_final', {
      chat_my_ai: vsc.locator('.part.auxiliarybar'), editeur: vsc.locator('.part.editor'),
    });
    meta.boxes.V03_vscode_fichier_modifie_final.nouvelle_route =
      await editorLines(vsc, '@app.get("/livres/{livre_id}")', 'return LIVRES[livre_id]');

    // ── 3. VS Code → PC ──
    await wv.locator('#messageInput').click();
    await vsc.keyboard.type(MSG_C, { delay: 22 });
    await sleep(300);
    await snap(vsc, 'V04_vscode_message_tape', 'message tapé dans VS Code');
    await boxes('V04_vscode_message_tape', { saisie_vscode: wv.locator('#messageInput') });
    await vsc.keyboard.press('Enter');
    await until(async () => tool(await lastAssistant(), 'edit_file', 'awaiting-approval'), 'approbation VS Code', 30000);
    await vsc.locator('.monaco-dialog-box').first().waitFor({ state: 'visible', timeout: 15000 });
    await sleep(600);
    await snap(vsc, 'V05_vscode_dialogue_approbation', "VS Code : fenêtre d'accord de VS Code");
    await boxes('V05_vscode_dialogue_approbation', { dialogue: vsc.locator('.monaco-dialog-box') });
    await snap(desk, 'D08_pc_message_de_vscode_attente', 'PC : le message de VS Code, accord demandé dans VS Code');
    await boxes('D08_pc_message_de_vscode_attente', {
      message_de_vscode: desk.getByText(MSG_C, { exact: true }),
      attente_vscode: desk.getByText('Approbation demandée dans VS Code.'),
    });
    await vsc.locator('.monaco-dialog-box .monaco-button', { hasText: 'Autoriser une fois' }).first().click();
    await until(async () => text(await lastAssistant(), 1).length > 40, 'réponse C qui s’écrit', 30000, 60);
    await snap(desk, 'D09_pc_reponse_vscode_en_cours', 'PC : la réponse au message de VS Code s’écrit');
    await until(async () => (await lastAssistant())?.status === 'done', 'réponse C finie', 30000);
    await sleep(900);
    await snap(vsc, 'V06_vscode_test_ajoute', 'VS Code : test ajouté dans tests/test_app.py');
    meta.boxes.V06_vscode_test_ajoute = {
      nouveau_test: await editorLines(vsc, 'def test_livre_introuvable', '"Livre introuvable"'),
    };
    await snap(desk, 'D10_pc_reponse_vscode_finale', 'PC : réponse au message de VS Code');

    // ── 4. Téléphone → VS Code ──
    await phone.locator('#tabCode').click();
    await sleep(1500);
    await snap(phone, 'M02_tel_vue_code', 'téléphone : vue Code (</> souligné), même conversation');
    await phone.evaluate(() => { document.getElementById('codeMessages').scrollTop = 0; });
    await sleep(600);
    await snap(phone, 'M02b_tel_vue_code_haut', 'téléphone : vue Code remontée, le message envoyé du PC');
    await boxes('M02b_tel_vue_code_haut', { message_du_pc: phone.locator('#codeMessages .message.user').first() });
    await phone.evaluate(() => {
      const box = document.getElementById('codeMessages');
      box.scrollTop = box.scrollHeight;
    });
    await sleep(600);
    await phone.locator('#codeInput').click();
    await phone.keyboard.type(MSG_B, { delay: 40 });
    await sleep(300);
    await snap(phone, 'M03_tel_message_tape', 'message tapé sur le téléphone');
    await phone.locator('#codeSendBtn').click();
    await until(async () => tool(await lastAssistant(), 'run_command', 'awaiting-approval'), 'approbation run_command', 30000);
    await sleep(800);
    await snap(phone, 'M04_tel_approbation', "téléphone : accord pour lancer la commande, corbeille grisée");
    await boxes('M04_tel_approbation', {
      accord: phone.locator('.tool-approval'), bouton_autoriser: phone.locator('.tool-approval-btn.primary'),
      corbeille: phone.locator('#trashBtn'),
    });
    await snap(vsc, 'V07_vscode_message_du_tel', 'VS Code : le message du téléphone et sa commande');
    await boxes('V07_vscode_message_du_tel', {
      chat_my_ai: vsc.locator('.part.auxiliarybar'), accord_dans_vscode: wv.locator('.tool-approval'),
    });
    await snap(desk, 'D11_pc_message_du_tel', 'PC : le message du téléphone');
    await phone.locator('.tool-approval-btn.primary').first().click();
    await until(async () => text(await lastAssistant(), 1).length > 30, 'réponse B qui s’écrit', 60000, 60);
    await snap(phone, 'M05_tel_reponse_en_cours', 'téléphone : sortie de pytest, réponse en streaming, corbeille grisée');
    await until(async () => (await lastAssistant())?.status === 'done', 'réponse B finie', 30000);
    await sleep(900);
    await snap(phone, 'M06_tel_reponse_finale', 'téléphone : 4 tests passent, corbeille de nouveau orange');
    await boxes('M06_tel_reponse_finale', { corbeille: phone.locator('#trashBtn') });
    await snap(vsc, 'V08_vscode_tests_du_tel', 'VS Code : la commande lancée depuis le téléphone');

    // ── 5. VS Code → téléphone ──
    await wv.locator('#messageInput').click();
    await vsc.keyboard.type(MSG_D, { delay: 22 });
    await vsc.keyboard.press('Enter');
    await until(async () => text(await lastAssistant(), 0).length > 70, 'réponse D qui s’écrit', 30000, 60);
    await snap(phone, 'M07_tel_message_de_vscode_en_cours', 'téléphone : le message de VS Code et sa réponse en streaming');
    await until(async () => (await lastAssistant())?.status === 'done', 'réponse D finie', 30000);
    await sleep(900);
    await snap(phone, 'M08_tel_message_de_vscode_final', 'téléphone : message de commit écrit depuis VS Code');
    await snap(vsc, 'V09_vscode_commit', 'VS Code : message de commit');
    await snap(desk, 'D12_pc_conversation_complete', 'PC : toute la conversation');

    // ── 6. Retour au Chat ──
    await phone.locator('#tabChat').click();
    await sleep(800);
    await snap(phone, 'M09_tel_retour_chat', 'téléphone : retour au Chat');
  } finally {
    fs.writeFileSync(path.join(OUT, 'meta.json'), JSON.stringify(meta, null, 2));
    await vscContext.close();
    await browser.close();
  }
  log('terminé');
})().catch((err) => {
  console.error(err);
  process.exit(1);
});
