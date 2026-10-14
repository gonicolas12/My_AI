// Vraie fenêtre : les raccourcis du navigateur (F5, Ctrl+Maj+R, Ctrl+P…) ne rechargent,
// n'impriment ni ne cherchent rien. Vraies touches du système (win.py, qui refuse si le PC sert),
// état de la page lu par CDP. Ctrl+R n'est pas envoyé : il ouvre le panneau Relay et démarre le
// Relay, avec de vrais tunnels dans l'appli (vérifié sur le Relay simulé, capture_panels.mjs).
// Usage (depuis frontend/) : node scripts/window_keys.mjs
import { connectWindow, sidebarOpen, win } from './lib.mjs';

const KEYS = [
  'f5',
  'ctrl+shift+r',
  'ctrl+f5',
  'ctrl+p',
  'ctrl+f',
  'f3',
  'f7',
  'ctrl+u',
  'ctrl+g',
  'ctrl+j',
  'ctrl+h',
  'alt+left',
  'ctrl+t',
  'ctrl+w',
  'ctrl+o',
];

const { browser, page } = await connectWindow();
// Marque posée dans la page : elle disparaît si la page se recharge
await page.evaluate(() => {
  window.__verif = 42;
});
const kept = () => page.evaluate(() => window.__verif === 42).catch(() => false);

// Les touches arrivent-elles à la page ? Ctrl+B ouvre puis ferme la barre latérale
const s0 = await sidebarOpen(page);
win('keys', 'ctrl+b');
await page.waitForTimeout(500);
const s1 = await sidebarOpen(page);
win('keys', 'ctrl+b');
await page.waitForTimeout(500);
console.log(`Ctrl+B (les touches arrivent) : ${s0} → ${s1} → ${await sidebarOpen(page)}`);

for (const key of KEYS) {
  win('keys', key);
  await page.waitForTimeout(600);
  console.log(`${key.padEnd(14)} page conservée : ${await kept()}`);
}
await browser.close();
