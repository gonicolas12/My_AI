// Vraie fenêtre : journal de ce qui s'y passe pendant un essai fait à la main (téléphone, dictée,
// raccourcis), par CDP seul, en lecture : aucune touche, aucun clic, rien d'écrit. Une ligne
// horodatée à chaque changement : panneau ouvert ou fermé, raccourci reçu par la page (Ctrl,
// Alt, F1 à F12, Échap ; jamais la frappe ordinaire), état du micro, texte de la zone de saisie,
// état du Relay (tunnels, appareils ; ni adresse ni jeton), messages de la conversation (source
// « mobile » comprise), réponse en cours, toasts. S'arrête quand la fenêtre se ferme, ou après
// MINUTES minutes. Usage (depuis frontend/) : node scripts/window_watch.mjs [MINUTES]
import { connectWindow } from './lib.mjs';

const minutes = Number(process.argv[2] ?? 40);
const { browser, page } = await connectWindow();
const stamp = () => new Date().toLocaleTimeString('fr-FR');
const say = (text) => console.log(`${stamp()}  ${text}`);

// Raccourcis reçus par la page : enregistrés dans la page, relus à chaque relevé
const listen = () =>
  page
    .evaluate(() => {
      if (window.__watchKeys) return;
      window.__watchKeys = [];
      window.addEventListener(
        'keydown',
        (event) => {
          if (['Control', 'Alt', 'Shift', 'Meta'].includes(event.key)) return;
          const special = /^F\d+$|^Escape$/.test(event.key);
          if (!special && !event.ctrlKey && !event.altKey && !event.metaKey) return;
          const parts = [];
          if (event.ctrlKey) parts.push('Ctrl');
          if (event.altKey) parts.push('Alt');
          if (event.shiftKey && event.key.length > 1) parts.push('Maj');
          parts.push(event.key.length === 1 ? event.key.toUpperCase() : event.key);
          window.__watchKeys.push(parts.join('+'));
        },
        true,
      );
    })
    .catch(() => undefined);
await listen();
page.on('load', () => void listen());

function snapshot() {
  return page.evaluate(async () => {
    // Jeton de la page : ôté de l'adresse au chargement, gardé dans sessionStorage (api.ts)
    const token =
      sessionStorage.getItem('my_ai.token') ??
      new URLSearchParams(location.hash.slice(1)).get('token') ??
      '';
    const get = (path) =>
      fetch(path, { headers: { Authorization: `Bearer ${token}` } })
        .then((response) => (response.ok ? response.json() : null))
        .catch(() => null);
    const [relay, conversation] = await Promise.all([get('/api/relay'), get('/api/conversation')]);
    const titles = [...document.querySelectorAll('[role="dialog"]')].map(
      (dialog) =>
        document.getElementById(dialog.getAttribute('aria-labelledby') ?? '')?.textContent ??
        dialog.getAttribute('aria-label') ??
        'dialogue',
    );
    const mic = document.querySelector(
      'button[aria-label="Saisie vocale"], button[aria-label="Arrêter la dictée"], button[aria-label="Transcription en cours…"]',
    );
    const toasts = [
      ...document.querySelectorAll(
        '[data-toast-region] [role="status"], [data-toast-region] [role="alert"]',
      ),
    ].map((toast) => toast.textContent?.trim() ?? '');
    const messages = conversation?.messages ?? [];
    const last = messages.at(-1);
    return {
      keys: window.__watchKeys?.splice(0) ?? [],
      dialogs: titles.join(' + '),
      mic: mic?.getAttribute('aria-label') ?? '',
      draft: document.querySelector('textarea[aria-label="Message"]')?.value ?? '',
      relay: relay
        ? `${relay.running ? 'en marche' : 'arrêté'} · tunnels : ${
            Object.keys(relay.tunnels ?? {})
              .sort()
              .join(', ') || 'aucun'
          } · page de routage : ${relay.url ? 'oui' : 'non'} · appareils : ${relay.clients}`
        : '',
      count: messages.length,
      last: last
        ? `${last.role}${last.source === 'mobile' ? ' (mobile)' : ''} : ${(last.text ?? '').replace(/\s+/g, ' ').slice(0, 90)}`
        : '',
      busy: Boolean(conversation?.busy || conversation?.active),
      conversation: conversation?.name ?? '',
      toasts,
    };
  });
}

const seen = {};
const deadline = Date.now() + minutes * 60_000;
say(`suivi de la fenêtre pendant ${minutes} min au plus`);
while (Date.now() < deadline) {
  let state;
  try {
    state = await snapshot();
  } catch {
    say('fenêtre fermée');
    break;
  }
  for (const key of state.keys) say(`touche reçue par la page : ${key}`);
  for (const [field, label] of [
    ['dialogs', 'panneau'],
    ['mic', 'micro'],
    ['draft', 'zone de saisie'],
    ['relay', 'Relay'],
    ['conversation', 'conversation'],
    ['last', 'dernier message'],
    ['busy', 'réponse en cours'],
  ]) {
    const value = String(state[field]);
    if (seen[field] !== value) {
      if (seen[field] !== undefined || value) say(`${label} : ${value || '(aucun)'}`);
      seen[field] = value;
    }
  }
  if (seen.count !== state.count) {
    if (seen.count !== undefined) say(`messages : ${seen.count} → ${state.count}`);
    seen.count = state.count;
  }
  for (const toast of state.toasts) {
    if (!seen[`toast:${toast}`]) say(`toast : ${toast}`);
  }
  for (const key of Object.keys(seen).filter((name) => name.startsWith('toast:'))) {
    if (!state.toasts.includes(key.slice(6))) delete seen[key];
  }
  for (const toast of state.toasts) seen[`toast:${toast}`] = true;
  await new Promise((resolve) => setTimeout(resolve, 400));
}
await browser.close().catch(() => undefined);
