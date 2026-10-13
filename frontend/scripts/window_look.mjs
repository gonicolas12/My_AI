// Vraie fenêtre : adresse, pont pywebview, captures du chargement puis de l'accueil (CDP seul,
// ni touche ni curseur du système)
// Usage (depuis frontend/) : node scripts/window_look.mjs [DOSSIER]
import { mkdirSync } from 'node:fs';

import { connectWindow, waitReady } from './lib.mjs';

const [, , out = 'captures'] = process.argv;
mkdirSync(out, { recursive: true });
const { browser, page } = await connectWindow();
const look = () =>
  page.evaluate(() => ({
    url: location.href.replace(/#.*/, '#…'),
    ua: navigator.userAgent,
    dpr: devicePixelRatio,
    taille: [innerWidth, innerHeight],
    pont: Boolean(window.pywebview?.api?.open_external),
    texte: document.body.innerText.slice(0, 160),
  }));
console.log(JSON.stringify(await look()));
await page.screenshot({ path: `${out}/fenetre_chargement.png` });
await waitReady(page);
await page.waitForTimeout(800);
await page.screenshot({ path: `${out}/fenetre_prete.png` });
console.log(JSON.stringify(await look()));
await browser.close(); // se détache sans fermer la fenêtre
