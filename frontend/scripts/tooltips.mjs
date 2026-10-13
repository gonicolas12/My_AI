// Infobulles : elles apparaissent au survol et disparaissent dès que la souris s'en va
// Usage (depuis frontend/) : node scripts/tooltips.mjs URL_AVEC_JETON   (Chromium sans fenêtre)
//                            node scripts/tooltips.mjs --window          (vraie fenêtre, par CDP)
// Souris de Playwright dans les deux cas : le vrai curseur ne bouge pas (window_tooltips.mjs)
import {
  connectWindow,
  openDemo,
  openSidebar,
  sidebarOpen,
  tooltips,
  usage,
  waitReady,
} from './lib.mjs';

const [, , target] = process.argv;
if (!target) usage('node scripts/tooltips.mjs URL_AVEC_JETON | --window');
const { browser, page } = target === '--window' ? await connectWindow() : await openDemo(target);
await waitReady(page);
await openSidebar(page);

const { width, height } = await page.evaluate(() => ({
  width: innerWidth,
  height: innerHeight,
}));
const center = async (locator) => {
  const box = await locator.boundingBox();
  return box && { x: box.x + box.width / 2, y: box.y + box.height / 2, box };
};
const away = async () => {
  await page.mouse.move(width * 0.6, height / 3, { steps: 8 });
  await page.waitForTimeout(600);
};
const report = (label, shown, left) =>
  console.log(`${label.padEnd(40)} affichée : ${shown}   restante : ${left}`);

// 1. Survol puis départ, boutons actifs et désactivés
async function hoverThenLeave(label, locator) {
  const c = await center(locator);
  if (!c) return console.log(`${label} : introuvable`);
  await page.mouse.move(c.x, c.y, { steps: 6 });
  await page.waitForTimeout(900);
  const shown = await tooltips(page);
  await away();
  report(label, shown, await tooltips(page));
}
await hoverThenLeave('Réglages (désactivé)', page.getByRole('button', { name: /^Réglages/ }));
await hoverThenLeave('Prompts (désactivé)', page.getByRole('button', { name: /^Prompts/ }));
await hoverThenLeave(
  'Joindre un fichier',
  page.getByRole('button', { name: 'Joindre un fichier' }),
);
await hoverThenLeave('Dossiers du projet (div)', page.getByText('Dossiers du projet'));
await hoverThenLeave(
  'Masquer la barre latérale',
  page.getByRole('button', { name: 'Masquer la barre latérale' }),
);

// 2. Balayage rapide de la barre du bas, puis départ
const first = await center(page.getByRole('button', { name: /^Relay/ }));
const last = await center(page.getByRole('button', { name: /^Exporter/ }));
if (first && last) {
  await page.mouse.move(first.box.x + 5, first.y, { steps: 4 });
  await page.waitForTimeout(700);
  await page.mouse.move(last.x, last.y, { steps: 25 });
  await page.waitForTimeout(400);
  const during = await tooltips(page);
  await page.mouse.move(first.box.x + 60, first.y - 260, { steps: 10 });
  await page.waitForTimeout(700);
  report('balayage de la barre du bas', during, await tooltips(page));
}

// 3. Sortie de la page par le bas, depuis la barre du bas
let c = await center(page.getByRole('button', { name: /^Réglages/ }));
await page.mouse.move(c.x, c.y, { steps: 5 });
await page.waitForTimeout(900);
let shown = await tooltips(page);
await page.mouse.move(c.x, height + 60, { steps: 3 });
await page.waitForTimeout(800);
report('sortie de la page par le bas', shown, await tooltips(page));
await away();

// 4. Clic sur « Masquer la barre latérale » (le bouton reste sous la souris)
c = await center(page.getByRole('button', { name: 'Masquer la barre latérale' }));
await page.mouse.move(c.x, c.y, { steps: 5 });
await page.waitForTimeout(900);
shown = await tooltips(page);
await page.mouse.click(c.x, c.y);
await page.waitForTimeout(500);
await page.mouse.move(c.x + 30, c.y + 40, { steps: 5 });
await page.waitForTimeout(800);
report(
  `clic sur Masquer (barre ouverte : ${await sidebarOpen(page)})`,
  shown,
  await tooltips(page),
);

// 5. Clic sur « Afficher la barre latérale » (le bouton disparaît)
c = await center(page.getByRole('button', { name: 'Afficher la barre latérale' }));
await page.mouse.move(c.x, c.y, { steps: 5 });
await page.waitForTimeout(900);
shown = await tooltips(page);
await page.mouse.click(c.x, c.y);
await page.waitForTimeout(500);
await page.mouse.move(c.x + 300, c.y + 300, { steps: 5 });
await page.waitForTimeout(800);
report('clic sur Afficher', shown, await tooltips(page));

// 6. Infobulle ouverte, puis Ctrl+B : la barre se ferme sous la souris
c = await center(page.getByRole('button', { name: /^Prompts/ }));
await page.mouse.move(c.x, c.y, { steps: 5 });
await page.waitForTimeout(900);
shown = await tooltips(page);
await page.keyboard.press('Control+b');
await page.waitForTimeout(500);
await page.mouse.move(c.x + 200, c.y - 200, { steps: 5 });
await page.waitForTimeout(800);
report("Ctrl+B sous l'infobulle", shown, await tooltips(page));
await openSidebar(page);

await browser.close(); // vraie fenêtre : se détache sans la fermer
