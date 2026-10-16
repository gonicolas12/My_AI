// Vraie fenêtre : une infobulle disparaît quand le vrai curseur quitte la fenêtre (vers le bas, la
// barre de titre, la gauche). Vrai curseur du système (win.py, qui attend que le PC ne serve plus),
// état de la page lu par CDP. Fenêtre restaurée plutôt qu'agrandie : sur un seul écran, une fenêtre
// agrandie n'a rien à sa gauche. Usage (depuis frontend/) : node scripts/window_tooltips.mjs
import { connectWindow, openSidebar, tooltips, win } from './lib.mjs';

const { browser, page } = await connectWindow();
await openSidebar(page);
win('front'); // le curseur doit survoler My_AI, pas une fenêtre posée dessus
const [left, top, width, height] = JSON.parse(win('rect'));
const [pageX, pageY] = JSON.parse(win('origin'));
const [sx, sy, sw, sh] = JSON.parse(win('screen'));
const dpr = await page.evaluate(() => devicePixelRatio);
const onScreen = (x, y) => x >= sx && x < sx + sw && y >= sy && y < sy + sh;

/** Centre du bouton, en pixels d'écran */
async function center(name) {
  const box = await page.getByRole('button', { name }).boundingBox();
  return {
    x: Math.round(pageX + (box.x + box.width / 2) * dpr),
    y: Math.round(pageY + (box.y + box.height / 2) * dpr),
  };
}

/** Survol du bouton au vrai curseur, puis départ vers le point `to(x, y)` */
async function leave(label, name, to) {
  const { x, y } = await center(name);
  const [tx, ty] = to(x, y);
  if (!onScreen(tx, ty)) {
    console.log(`${label.padEnd(36)} sauté : point de sortie hors de l'écran`);
    return;
  }
  win('cursor', String(x), String(y));
  await page.waitForTimeout(1000);
  const shown = await tooltips(page);
  win('cursor', String(tx), String(ty));
  await page.waitForTimeout(900);
  console.log(`${label.padEnd(36)} affichée : ${shown}   restante : ${await tooltips(page)}`);
}

console.log(`fenêtre ${win('state')} : [${left}, ${top}, ${width}, ${height}], échelle ${dpr}`);
await leave('Réglages → sous la fenêtre', /^Réglages/, (x) => [x, top + height + 15]);
await leave('Masquer la barre → barre de titre', 'Masquer la barre latérale', (x) => [
  x,
  Math.round((top + pageY) / 2),
]);
await leave('Prompts → à gauche de la fenêtre', /^Prompts/, (_x, y) => [left - 30, y]);
win('cursor', String(left + Math.round(width / 2)), String(top + Math.round(height / 2)));
await browser.close();
