// Vraie fenêtre : une infobulle disparaît quand le vrai curseur quitte la fenêtre (vers la barre
// des tâches, la barre de titre, la gauche). Vrai curseur du système (win.py, qui refuse si le PC
// sert), état de la page lu par CDP. Usage (depuis frontend/) : node scripts/window_tooltips.mjs
import { connectWindow, openSidebar, tooltips, win } from './lib.mjs';

const { browser, page } = await connectWindow();
await openSidebar(page);
const [left, top, width, height] = JSON.parse(win('rect'));
const [pageX, pageY] = JSON.parse(win('origin'));
const dpr = await page.evaluate(() => devicePixelRatio);

/** Vrai curseur au centre du bouton ; renvoie sa position à l'écran et les infobulles visibles */
async function hover(name) {
  const box = await page.getByRole('button', { name }).boundingBox();
  const x = Math.round(pageX + (box.x + box.width / 2) * dpr);
  const y = Math.round(pageY + (box.y + box.height / 2) * dpr);
  win('cursor', String(x), String(y));
  await page.waitForTimeout(1000);
  return { x, y, shown: await tooltips(page) };
}

async function leave(label, name, to) {
  const { x, y, shown } = await hover(name);
  const [tx, ty] = to(x, y);
  win('cursor', String(tx), String(ty));
  await page.waitForTimeout(900);
  console.log(`${label.padEnd(36)} affichée : ${shown}   restante : ${await tooltips(page)}`);
}

await leave('Réglages → sous la fenêtre', /^Réglages/, (x) => [x, top + height + 15]);
await leave('Masquer la barre → barre de titre', 'Masquer la barre latérale', (x) => [
  x,
  Math.round((top + pageY) / 2),
]);
await leave('Prompts → à gauche de la fenêtre', /^Prompts/, (_x, y) => [left - 30, y]);
win('cursor', String(left + Math.round(width / 2)), String(top + Math.round(height / 2)));
await browser.close();
