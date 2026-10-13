// Mesures de fluidité sur le serveur de démonstration : images, tâches longues, latence des
// saisies, rendus React (build de profilage), cadence des jetons reçus
// Usage (depuis frontend/) : node scripts/perf.mjs URL_AVEC_JETON [scroll,stream,stress,gil]
import { chromium } from 'playwright';

import { composer, openSidebar, usage, waitIdle, waitReady } from './lib.mjs';

const [, , url, only = 'scroll,stream,stress,gil'] = process.argv;
if (!url) usage('node scripts/perf.mjs URL_AVEC_JETON [scroll,stream,stress,gil]');
const wanted = new Set(only.split(','));
const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
page.on('pageerror', (e) => console.log('pageerror', e.message));

// Jetons reçus par la fenêtre, horodatés à l'arrivée sur le WebSocket
let tokenTimes = [];
page.on('websocket', (ws) => {
  ws.on('framereceived', (frame) => {
    const text = typeof frame.payload === 'string' ? frame.payload : '';
    if (text.includes('"assistant.token"')) tokenTimes.push(performance.now());
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

await browser.close();
