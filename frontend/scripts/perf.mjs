// Mesures de fluidité sur le serveur de démonstration : images, tâches longues, latence des
// saisies, rendus React (build de profilage), cadence des jetons reçus
// Usage (depuis frontend/) : node scripts/perf.mjs URL_AVEC_JETON [scénarios séparés par des virgules]
// Chat : scroll, stream, stress, gil (par défaut) ; page Agents : canvas (workflow de 50 nœuds :
// zoom, déplacement de la vue, d'un nœud), agentstream (sortie d'agent de 5 000 jetons, saisie et
// défilement pendant l'écriture), agentscroll (défilement de la page Agents)
import { mkdtempSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';

import { chromium } from 'playwright';

import { composer, openSidebar, usage, waitIdle, waitReady } from './lib.mjs';

const [, , url, only = 'scroll,stream,stress,gil'] = process.argv;
if (!url) usage('node scripts/perf.mjs URL_AVEC_JETON [scroll,stream,stress,gil,canvas,…]');
const wanted = new Set(only.split(','));
const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
page.on('pageerror', (e) => console.log('pageerror', e.message));

// Jetons reçus par la fenêtre (chat), suites de texte (agents), horodatés à l'arrivée sur le
// WebSocket
let tokenTimes = [];
page.on('websocket', (ws) => {
  ws.on('framereceived', (frame) => {
    const text = typeof frame.payload === 'string' ? frame.payload : '';
    if (text.includes('"assistant.token"') || text.includes('"agents.agent_section_delta"'))
      tokenTimes.push(performance.now());
  });
});

function tokenStats() {
  const gaps = [];
  for (let i = 1; i < tokenTimes.length; i += 1) gaps.push(tokenTimes[i] - tokenTimes[i - 1]);
  const s = [...gaps].sort((a, b) => a - b);
  const q = (p) => (s.length ? s[Math.min(s.length - 1, Math.floor(p * s.length))] : 0);
  const span = (tokenTimes.at(-1) ?? 0) - (tokenTimes[0] ?? 0);
  return {
    jetons: tokenTimes.length,
    jetons_par_s: span ? +((tokenTimes.length / span) * 1000).toFixed(1) : 0,
    ecart_p50_ms: +q(0.5).toFixed(1),
    ecart_p99_ms: +q(0.99).toFixed(1),
    ecart_max_ms: +(s.at(-1) ?? 0).toFixed(1),
  };
}

// Enregistreurs dans la page : intervalles entre images, tâches longues,
// latence des saisies (Event Timing) ; les rendus React viennent du build de
// profilage (VITE_REACT_PROFILE=1, window.__myAiCommits)
await page.addInitScript(() => {
  const rec = { frames: [], longTasks: [], events: [], recording: false };
  window.__perf = rec;
  let last = 0;
  const tick = (t) => {
    if (rec.recording && last) rec.frames.push(t - last);
    last = t;
    requestAnimationFrame(tick);
  };
  requestAnimationFrame(tick);
  new PerformanceObserver((list) => {
    if (!rec.recording) return;
    for (const e of list.getEntries()) rec.longTasks.push(e.duration);
  }).observe({ type: 'longtask', buffered: false });
  new PerformanceObserver((list) => {
    if (!rec.recording) return;
    for (const e of list.getEntries()) {
      if (['keydown', 'keypress', 'input', 'wheel'].includes(e.name))
        rec.events.push({ name: e.name, duration: e.duration });
    }
  }).observe({ type: 'event', durationThreshold: 16, buffered: false });
});

async function start() {
  tokenTimes = [];
  await page.evaluate(() => {
    const rec = window.__perf;
    rec.frames = [];
    rec.longTasks = [];
    rec.events = [];
    window.__myAiCommits = [];
    rec.recording = true;
  });
}

async function stop(label) {
  const data = await page.evaluate(() => {
    const rec = window.__perf;
    rec.recording = false;
    return {
      frames: rec.frames,
      longTasks: rec.longTasks,
      events: rec.events,
      commits: (window.__myAiCommits ?? []).map((c) => c.actualDuration),
    };
  });
  const q = (arr, p) => {
    if (!arr.length) return 0;
    const s = [...arr].sort((a, b) => a - b);
    return s[Math.min(s.length - 1, Math.floor(p * s.length))];
  };
  const f = data.frames;
  const c = data.commits;
  const out = {
    scenario: label,
    images: f.length,
    image_p50_ms: +q(f, 0.5).toFixed(1),
    image_p95_ms: +q(f, 0.95).toFixed(1),
    image_max_ms: +Math.max(0, ...f).toFixed(1),
    images_sup_33ms: f.filter((x) => x > 33.4).length,
    taches_longues: data.longTasks.length,
    taches_longues_ms: Math.round(data.longTasks.reduce((a, b) => a + b, 0)),
    saisies_lentes: data.events.length,
    saisie_max_ms: Math.max(0, ...data.events.map((e) => e.duration)),
    rendus_react: c.length,
    rendu_p50_ms: +q(c, 0.5).toFixed(2),
    rendu_p95_ms: +q(c, 0.95).toFixed(2),
    rendu_max_ms: +Math.max(0, ...c).toFixed(2),
  };
  console.log(JSON.stringify({ ...out, ...tokenStats() }));
}

async function wheel(times, dy, pause = 16) {
  await page.mouse.move(850, 450);
  for (let i = 0; i < times; i += 1) {
    await page.mouse.wheel(0, dy);
    await page.waitForTimeout(pause);
  }
}

await page.goto(url);
await waitReady(page);
await page.waitForTimeout(800);

if (wanted.has('scroll')) {
  // Défilement d'une conversation de 200 messages (données de test du suivi, section 4)
  await openSidebar(page);
  const session = page.getByRole('button', { name: /^Conversation longue/ });
  if (await session.count()) {
    await session.first().click();
    await page.waitForTimeout(1500);
    await start();
    await wheel(60, -240);
    await wheel(60, 240);
    await page.waitForTimeout(300);
    await stop('defilement_200_messages_rapide');
    // Molette à vitesse réaliste : 120 px toutes les 50 ms (~2 400 px/s)
    await page.waitForTimeout(500);
    await start();
    await wheel(60, -120, 50);
    await wheel(60, 120, 50);
    await page.waitForTimeout(300);
    await stop('defilement_200_messages_molette');
  } else {
    console.log('session « Conversation longue » absente : défilement non mesuré');
  }
}

async function streamScenario(label, message, typeDuringMs) {
  await page.keyboard.press('Control+n');
  await page.waitForTimeout(500);
  await composer(page).fill(message);
  await composer(page).press('Enter');
  await page.waitForSelector('[aria-busy="true"]', { timeout: 10000 });
  await start();
  // Saisie pendant la réponse : une touche toutes les 120 ms
  const t0 = Date.now();
  await composer(page).click();
  while (Date.now() - t0 < typeDuringMs) {
    await page.keyboard.type('a');
    await page.waitForTimeout(120);
  }
  // Défilement pendant la réponse
  await wheel(15, -200, 30);
  await wheel(15, 200, 30);
  await waitIdle(page);
  await page.waitForTimeout(300);
  await stop(label);
  await composer(page).fill('');
}

if (wanted.has('stress')) {
  await streamScenario('reponse_5000_jetons_charge', 'Écris une réponse long format', 8000);
}
if (wanted.has('stream')) {
  await streamScenario('reponse_5000_jetons', 'Écris une réponse long format', 20000);
}
if (wanted.has('gil')) {
  await streamScenario(
    'indexation_python_gil',
    'Simule une indexe lourde pendant la réponse',
    9000,
  );
}

// ── Page Agents ─────────────────────────────────────────────────────────────

const agentsScenarios = ['canvas', 'agentstream', 'agentscroll'].filter((name) => wanted.has(name));
if (agentsScenarios.length) {
  await page.getByRole('button', { name: 'Agents', exact: true }).click();
  await page.getByRole('heading', { name: 'Agents IA spécialisés' }).waitFor({ timeout: 15000 });
  await page.waitForTimeout(1200);
}

/** Workflow de Tk de `count` nœuds en grille, reliés en chaîne */
function bigWorkflow(count) {
  const kinds = ['planner', 'code', 'security', 'debug', 'optimizer', 'web', 'analyst'];
  const nodes = {};
  for (let i = 0; i < count; i += 1) {
    const kind = kinds[i % kinds.length];
    nodes[i] = {
      agent_type: kind,
      name: `${kind[0].toUpperCase()}${kind.slice(1)}Agent`,
      color: '#3b82f6',
      icon: '🤖',
      x: 75 + (i % 10) * 300,
      y: 50 + Math.floor(i / 10) * 125,
      status: 'idle',
    };
  }
  const connections = [];
  for (let i = 1; i < count; i += 1) connections.push({ from: i - 1, to: i });
  return { version: '9.0.0', nodes, connections, zoom: 1, pan_x: 0, pan_y: 0 };
}

if (wanted.has('canvas')) {
  const file = join(mkdtempSync(join(tmpdir(), 'myai-perf-')), 'workflow_50.json');
  writeFileSync(file, JSON.stringify(bigWorkflow(50)));
  const chooser = page.waitForEvent('filechooser');
  await page.getByRole('button', { name: 'Charger', exact: true }).click();
  await (await chooser).setFiles(file);
  await page.waitForFunction(() => document.querySelectorAll('.react-flow__node').length === 50);
  const flow = page.locator('.react-flow');
  await flow.scrollIntoViewIfNeeded();
  await page.waitForTimeout(800);
  const box = await flow.boundingBox();
  const cx = box.x + box.width / 2;
  const cy = box.y + box.height / 2;
  // Zoom à la molette, puis déplacement de la vue au clic droit, comme dans Tk
  await start();
  await page.mouse.move(cx, cy);
  for (let i = 0; i < 25; i += 1) {
    await page.mouse.wheel(0, i < 12 ? 120 : -120);
    await page.waitForTimeout(30);
  }
  await page.mouse.down({ button: 'right' });
  for (let i = 0; i < 40; i += 1) {
    await page.mouse.move(cx - i * 12, cy - i * 4, { steps: 1 });
    await page.waitForTimeout(16);
  }
  await page.mouse.up({ button: 'right' });
  await page.waitForTimeout(300);
  await stop('canvas_50_noeuds_zoom_et_vue');
  // Déplacement d'un nœud (les liens suivent)
  const node = page.locator('.react-flow__node').nth(25);
  const start0 = await node.boundingBox();
  await start();
  await page.mouse.move(start0.x + 120, start0.y + 40);
  await page.mouse.down();
  for (let i = 0; i < 40; i += 1) {
    await page.mouse.move(start0.x + 120 + i * 6, start0.y + 40 + i * 3, { steps: 1 });
    await page.waitForTimeout(16);
  }
  await page.mouse.up();
  await page.waitForTimeout(300);
  await stop('canvas_50_noeuds_deplacement_noeud');
  await page.getByRole('button', { name: 'Vider', exact: true }).click();
}

if (wanted.has('agentstream')) {
  await page.getByRole('button', { name: /^CodeAgent :/ }).click();
  const task = page.getByRole('textbox', { name: 'Tâche' });
  await task.fill('Écris une réponse long format');
  await page.getByRole('button', { name: 'Exécuter', exact: true }).click();
  await page.getByText('Rapport détaillé').first().waitFor({ timeout: 15000 });
  await start();
  // Saisie dans la zone de tâche pendant l'écriture, une touche toutes les 120 ms
  await task.click();
  const t0 = Date.now();
  while (Date.now() - t0 < 8000) {
    await page.keyboard.type('a');
    await page.waitForTimeout(120);
  }
  // Défilement de la page pendant l'écriture
  await wheel(15, 300, 30);
  await wheel(15, -300, 30);
  await page.getByRole('button', { name: 'Exécuter', exact: true }).waitFor({ timeout: 120000 });
  await page.waitForTimeout(300);
  await stop('agent_5000_jetons');
  await task.fill('');
}

if (wanted.has('agentscroll')) {
  await page.mouse.move(850, 450);
  await page.evaluate(() => document.querySelector('main > div')?.scrollTo({ top: 0 }));
  await page.waitForTimeout(500);
  await start();
  await wheel(50, 240);
  await wheel(50, -240);
  await page.waitForTimeout(300);
  await stop('page_agents_defilement_rapide');
  await page.waitForTimeout(500);
  await start();
  await wheel(50, 120, 50);
  await wheel(50, -120, 50);
  await page.waitForTimeout(300);
  await stop('page_agents_defilement_molette');
}

await browser.close();
