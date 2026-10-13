// Vraie fenêtre : une vraie réponse d'Ollama, pilotée par CDP (ni touche ni curseur du système).
// Images par seconde, tâches longues, premier texte, captures pendant et après la réponse.
// Usage (depuis frontend/) : node scripts/window_chat.mjs "QUESTION" [DOSSIER]
import { mkdirSync } from 'node:fs';

import { composer, connectWindow, usage } from './lib.mjs';

const [, , question, out = 'captures'] = process.argv;
if (!question) usage('node scripts/window_chat.mjs "QUESTION" [DOSSIER]');
mkdirSync(out, { recursive: true });
const { browser, page } = await connectWindow();
await page.evaluate(() => {
  const rec = { frames: [], longTasks: [], on: true, last: 0 };
  window.__real = rec;
  const tick = (t) => {
    if (rec.on && rec.last) rec.frames.push(t - rec.last);
    rec.last = t;
    if (rec.on) requestAnimationFrame(tick);
  };
  requestAnimationFrame(tick);
  new PerformanceObserver((list) => {
    for (const e of list.getEntries()) rec.longTasks.push(e.duration);
  }).observe({ type: 'longtask' });
});

await composer(page).fill(question);
const t0 = Date.now();
await composer(page).press('Enter');
await page.waitForSelector('[aria-busy="true"]', { timeout: 15000 });
let firstText = null;
let shot = 0;
while (await page.locator('[aria-busy="true"]').count()) {
  if (firstText === null) {
    const len = await page.evaluate(
      () => document.querySelector('article[aria-busy="true"] .md')?.textContent.length ?? 0,
    );
    if (len > 0) firstText = Date.now() - t0;
  }
  if (shot < 3 && Date.now() - t0 > 2500 * (shot + 1)) {
    await page.screenshot({ path: `${out}/fenetre_streaming_${shot}.png` });
    shot += 1;
  }
  await page.waitForTimeout(200);
  if (Date.now() - t0 > 240000) break;
}
const total = Date.now() - t0;
await page.waitForTimeout(600);
await page.screenshot({ path: `${out}/fenetre_reponse.png` });
const stats = await page.evaluate(() => {
  const rec = window.__real;
  rec.on = false;
  const f = [...rec.frames].sort((a, b) => a - b);
  const q = (p) => f[Math.min(f.length - 1, Math.floor(p * f.length))] ?? 0;
  const articles = document.querySelectorAll('article');
  const meta = articles[articles.length - 1]?.querySelector('.tabular-nums')?.textContent ?? '';
  return {
    images: f.length,
    image_p50_ms: +q(0.5).toFixed(1),
    image_p95_ms: +q(0.95).toFixed(1),
    image_max_ms: +(f.at(-1) ?? 0).toFixed(1),
    images_sup_33ms: f.filter((x) => x > 33.4).length,
    taches_longues: rec.longTasks.length,
    pied_du_message: meta,
  };
});
console.log(JSON.stringify({ premier_texte_ms: firstText, total_ms: total, ...stats }));
await browser.close(); // se détache sans fermer la fenêtre
