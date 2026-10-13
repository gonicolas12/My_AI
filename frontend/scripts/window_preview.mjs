// Vraie fenêtre sur le serveur de démonstration (--window) : volet d'aperçu dans WebView2, par
// CDP seul (ni touche ni curseur du système). L'artefact HTML tourne isolé : pas de pont
// pywebview dans son iframe, pas d'accès à la page de l'appli, et un message au pont envoyé
// depuis l'iframe n'arrive pas en Python (avec le journal du serveur : « SONDE-PAGE » y est,
// « SONDE-IFRAME » non). Le PDF s'affiche dans le lecteur de WebView2 : il dessine hors de la
// page, absent des captures CDP, d'où une capture de la fenêtre (win.py capture, PrintWindow :
// ni premier plan ni saisie), à regarder.
// Usage (depuis frontend/) : node scripts/window_preview.mjs [DOSSIER] [JOURNAL_DU_SERVEUR]
import { mkdirSync, readFileSync } from 'node:fs';

import { composer, connectWindow, waitIdle, waitReady, win } from './lib.mjs';

const [, , out = 'captures', serverLog] = process.argv;
mkdirSync(out, { recursive: true });
// Seules comptent les lignes du journal écrites pendant ce passage
const logStart = serverLog ? readFileSync(serverLog, 'utf-8').length : 0;
const { browser, page } = await connectWindow();
await waitReady(page);

const checks = [];
function check(label, ok, detail = '') {
  checks.push(ok);
  console.log(`${ok ? 'OK ' : 'ÉCHEC'} ${label}${detail ? ` — ${detail}` : ''}`);
}

async function send(text) {
  await page.keyboard.press('Control+n');
  await page.waitForTimeout(500);
  await composer(page).fill(text);
  await composer(page).press('Enter');
  await page.waitForSelector('[aria-busy="true"]', { timeout: 10000 }).catch(() => undefined);
  await waitIdle(page);
  await page.waitForTimeout(400);
}

const pane = page.locator('aside[aria-label="Aperçu"]');

// Témoin : le pont existe dans la page de l'appli, et son message arrive en Python
const bridge = await page.evaluate(() => {
  window.chrome.webview.postMessage(['console', JSON.stringify('SONDE-PAGE'), 'sonde']);
  return typeof window.pywebview?.api?.platform === 'function';
});
check("page de l'appli : pont pywebview présent", bridge);
check(
  'surlignage de la recherche : CSS.highlights',
  await page.evaluate(() => 'highlights' in CSS),
);

// Artefact HTML : son script tourne, isolé de l'appli
await send('Fais-moi un artefact HTML');
await pane.waitFor({ timeout: 5000 });
const view = page.frameLocator('aside[aria-label="Aperçu"] iframe');
await view.locator('text=Compteur').waitFor({ timeout: 5000 });
await view.locator('button', { hasText: 'Cliquer' }).click();
check('artefact : son script tourne', (await view.locator('#n').textContent()) === '1');
await view.locator('#api:has-text("API")').waitFor({ timeout: 5000 });
const api = (await view.locator('#api').textContent()) ?? '';
check("artefact : pas d'accès à l'API de l'appli", /403|bloqué/.test(api), api);
const frame = page.frames().find((f) => f.url().includes('/preview/'));
const inside = await frame.evaluate(() => {
  let parent = 'lisible';
  try {
    void window.parent.document.title;
  } catch {
    parent = 'bloqué';
  }
  const webview = window.chrome?.webview;
  webview?.postMessage(['console', JSON.stringify('SONDE-IFRAME'), 'sonde']);
  return {
    origin: window.origin,
    pywebview: typeof window.pywebview,
    webview: typeof webview,
    parent,
  };
});
check('artefact : origine opaque', inside.origin === 'null', inside.origin);
check('artefact : pas de pont pywebview', inside.pywebview === 'undefined', inside.pywebview);
check("artefact : page de l'appli illisible", inside.parent === 'bloqué', inside.parent);
// WebView2 donne chrome.webview à chaque cadre, mais pywebview n'écoute que le document
// principal (CoreWebView2.WebMessageReceived) : la sonde du journal le vérifie
console.log(`info : chrome.webview dans l'iframe : ${inside.webview}`);
await page.screenshot({ path: `${out}/fenetre_artefact.png` });
await page.getByRole('button', { name: 'Fermer l’aperçu' }).click();

// Document PDF : volet ouvert seul sur le PDF, lecteur de WebView2
await send('Rédige un document de synthèse');
await pane.waitFor({ timeout: 5000 });
const pdf = await pane.locator('iframe').evaluate((el) => ({
  src: el.getAttribute('src') ?? '',
  sandbox: el.getAttribute('sandbox'),
}));
check('PDF : servi par lien signé', /^\/files\/.+\.pdf$/.test(pdf.src), pdf.src);
check('PDF : iframe hors bac à sable (lecteur)', pdf.sandbox === null);
await page.waitForTimeout(2500);
console.log(win('capture', `${out}/fenetre_pdf.png`), '(lecteur PDF, à regarder)');
await page.getByRole('button', { name: 'Aperçu suivant' }).click();
await page.waitForTimeout(1500);
await page.screenshot({ path: `${out}/fenetre_docx.png` });
await page.getByRole('button', { name: 'Fermer l’aperçu' }).click();

if (serverLog) {
  await page.waitForTimeout(500);
  const log = readFileSync(serverLog, 'utf-8').slice(logStart);
  check('sonde : le message de la page arrive en Python', log.includes('SONDE-PAGE'));
  check("sonde : celui de l'iframe n'arrive pas", !log.includes('SONDE-IFRAME'));
} else {
  console.log("info : sans journal du serveur, la sonde de l'iframe n'est pas vérifiée");
}
await browser.close(); // se détache sans fermer la fenêtre
const failed = checks.filter((ok) => !ok).length;
console.log(failed ? `${failed} contrôle(s) en échec` : 'Tous les contrôles passent');
process.exitCode = failed ? 1 : 0;
