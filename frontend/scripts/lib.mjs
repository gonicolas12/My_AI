// Outils communs aux scripts de vérification (README.md de ce dossier)
import { execFileSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';

import { chromium } from 'playwright';

/** Port de débogage de la vraie fenêtre : même variable que le lanceur */
export const CDP_URL = `http://127.0.0.1:${process.env.MY_AI_WEBVIEW_CDP_PORT ?? '9333'}`;

const WIN_PY = fileURLToPath(new URL('../../tools/interface_web/win.py', import.meta.url));

/**
 * Pilotage Win32 de la vraie fenêtre (tools/interface_web/win.py). Touches et
 * curseur du système : win.py refuse si le PC sert ou si My_AI n'est pas au
 * premier plan, et le script s'arrête alors sur une erreur.
 */
export function win(...args) {
  return execFileSync(process.env.PYTHON ?? 'python', [WIN_PY, ...args], {
    encoding: 'utf-8',
    // Sortie en UTF-8 : en cp1252, la console de Windows ne sait pas écrire « → »
    env: { ...process.env, PYTHONIOENCODING: 'utf-8' },
  }).trim();
}

/** Page de la vraie fenêtre WebView2 (lancée avec MY_AI_WEBVIEW_CDP_PORT), sans toucher au focus */
export async function connectWindow() {
  const browser = await chromium.connectOverCDP(CDP_URL);
  const page = browser.contexts()[0]?.pages()[0];
  if (!page) throw new Error(`aucune page sur ${CDP_URL}`);
  return { browser, page };
}

/** Chromium sans fenêtre, sur l'adresse du serveur de démonstration (jeton compris) */
export async function openDemo(url, viewport = { width: 1440, height: 900 }) {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport, deviceScaleFactor: 1 });
  await page.goto(url);
  return { browser, page };
}

export function usage(text) {
  console.error(`Usage : ${text}`);
  process.exit(1);
}

export const composer = (page) => page.getByRole('textbox', { name: 'Message' });

export const tooltips = (page) => page.locator('[role="tooltip"]').count();

/** Fin du chargement : la zone de saisie apparaît */
export async function waitReady(page, timeout = 180000) {
  await page.waitForSelector('textarea[aria-label="Message"]', { timeout });
}

/** Aucune réponse en cours */
export async function waitIdle(page, timeout = 300000) {
  await page.waitForFunction(() => !document.querySelector('[aria-busy="true"]'), null, {
    timeout,
  });
}

export function sidebarOpen(page) {
  return page.evaluate(
    () =>
      document.querySelector('aside[aria-label="Barre latérale"]')?.getAttribute('aria-hidden') ===
      'false',
  );
}

/** Ouvre la barre latérale (Ctrl+B envoyé à la page, pas au système) */
export async function openSidebar(page) {
  if (!(await sidebarOpen(page))) {
    await page.keyboard.press('Control+b');
    await page.waitForTimeout(500);
  }
}
