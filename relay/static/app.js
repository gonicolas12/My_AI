/* ═══════════════════════════════════════════════════ */
/* My_AI Relay — Mobile Chat Application              */
/* ═══════════════════════════════════════════════════ */

// ── CONFIGURATION ───────────────────────────────────
// Textes dans la langue du PC (i18n.js, catalogue injecté par le Relay)
const T = window.RelayI18n ? window.RelayI18n.t : function (key) { return key; };
const TOKEN = window.__RELAY_TOKEN__ || '';
const WS_PROTOCOL = location.protocol === 'https:' ? 'wss:' : 'ws:';
// La session du code d'accès s'y ajoute à chaque connexion (voir connect)
const WS_URL = `${WS_PROTOCOL}//${location.host}/ws?token=${TOKEN}`;
console.log('[Relay] Token:', TOKEN ? TOKEN.substring(0, 6) + '...' : 'EMPTY');
console.log('[Relay] WS URL:', WS_URL);

// Logo de My_AI (le robot de l'appli et de l'extension VS Code)
const ROBOT_SVG =
  '<svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">' +
  '<circle cx="7" cy="1.5" r="1"/><rect x="6.6" y="2.4" width="0.8" height="2.8" rx="0.4"/>' +
  '<circle cx="17" cy="1.5" r="1"/><rect x="16.6" y="2.4" width="0.8" height="2.8" rx="0.4"/>' +
  '<path fill-rule="evenodd" d="M5 4.5H19A4 4 0 0 1 23 8.5V18A4 4 0 0 1 19 22H5A4 4 0 0 1 1 18V8.5A4 4 0 0 1 5 4.5Z' +
  'M6.25 9.25H8.75A1.25 1.25 0 0 1 10 10.5V12A1.25 1.25 0 0 1 8.75 13.25H6.25A1.25 1.25 0 0 1 5 12V10.5A1.25 1.25 0 0 1 6.25 9.25Z' +
  'M15.25 9.25H17.75A1.25 1.25 0 0 1 19 10.5V12A1.25 1.25 0 0 1 17.75 13.25H15.25A1.25 1.25 0 0 1 14 12V10.5A1.25 1.25 0 0 1 15.25 9.25Z' +
  'M9 15.75H15A1 1 0 0 1 15 17.75H9A1 1 0 0 1 9 15.75Z"/></svg>';

// ═══════════════════════════════════════════════════
// E2EE — Chiffrement bout-en-bout AES-256-GCM
//
// La clé est passée par le serveur via le fragment d'URL (#k=<b64u>).
// Le fragment n'est JAMAIS transmis au serveur de tunnel public
// (Cloudflare, serveo, localhost.run) ni à GitHub Pages : seul le
// navigateur le lit. La clé reste donc privée entre le PC qui l'a
// générée et ce navigateur mobile qui a scanné le QR.
// ═══════════════════════════════════════════════════

let e2eKey = null;       // CryptoKey (AES-GCM) une fois importée
let e2eReady = null;     // Promise résolue quand e2eKey est prête

function b64uDecode(s) {
  s = s.replace(/-/g, '+').replace(/_/g, '/');
  while (s.length % 4) s += '=';
  var bin = atob(s);
  var out = new Uint8Array(bin.length);
  for (var i = 0; i < bin.length; i++) out[i] = bin.charCodeAt(i);
  return out;
}

function b64uEncode(bytes) {
  var bin = '';
  for (var i = 0; i < bytes.length; i++) bin += String.fromCharCode(bytes[i]);
  return btoa(bin).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
}

function importE2EKey() {
  // Format du fragment : #k=<base64url-32-bytes>
  var hash = location.hash.replace(/^#/, '');
  var params = {};
  hash.split('&').forEach(function (pair) {
    var idx = pair.indexOf('=');
    if (idx < 0) return;
    params[pair.slice(0, idx)] = pair.slice(idx + 1);
  });
  if (!params.k) {
    return Promise.reject(new Error(T('e2e.missingKey')));
  }
  var rawKey;
  try {
    rawKey = b64uDecode(decodeURIComponent(params.k));
  } catch (e) {
    return Promise.reject(new Error(T('e2e.badKey')));
  }
  if (rawKey.length !== 32) {
    return Promise.reject(new Error(T('e2e.badKeySize', { size: rawKey.length })));
  }
  return crypto.subtle.importKey(
    'raw', rawKey, { name: 'AES-GCM' }, false, ['encrypt', 'decrypt']
  );
}

e2eReady = importE2EKey().then(function (k) {
  e2eKey = k;
  console.log('[Relay] E2EE prête (AES-256-GCM)');
  return k;
}).catch(function (err) {
  console.error('[Relay] Échec import clé E2EE :', err);
  // Bloquer l'application : sans clé, tout est inutilisable.
  document.body.innerHTML =
    '<div style="padding:32px;color:#fff;background:#0f0f0f;font-family:sans-serif;min-height:100vh">' +
    '<h2 style="color:#ef4444">' + escapeHtml(T('e2e.failTitle')) + '</h2>' +
    '<p>' + escapeHtml(err && err.message ? err.message : T('e2e.noKey')) + '</p>' +
    '<p style="color:#9ca3af;font-size:14px;margin-top:16px">' + escapeHtml(T('e2e.rescan')) + '</p>' +
    '</div>';
  throw err;
});

async function aesGcmEncryptBytes(plainBytes) {
  await e2eReady;
  var nonce = crypto.getRandomValues(new Uint8Array(12));
  var ct = await crypto.subtle.encrypt(
    { name: 'AES-GCM', iv: nonce }, e2eKey, plainBytes
  );
  var wire = new Uint8Array(12 + ct.byteLength);
  wire.set(nonce, 0);
  wire.set(new Uint8Array(ct), 12);
  return wire;
}

async function aesGcmDecryptBytes(wireBytes) {
  await e2eReady;
  if (wireBytes.length < 12 + 16) throw new Error('ciphertext trop court');
  var nonce = wireBytes.slice(0, 12);
  var ct = wireBytes.slice(12);
  var plain = await crypto.subtle.decrypt(
    { name: 'AES-GCM', iv: nonce }, e2eKey, ct
  );
  return new Uint8Array(plain);
}

async function encryptObject(obj) {
  var enc = new TextEncoder();
  var plain = enc.encode(JSON.stringify(obj));
  var wire = await aesGcmEncryptBytes(plain);
  return { e: b64uEncode(wire) };
}

async function decryptEnvelope(wrapper) {
  if (!wrapper || typeof wrapper.e !== 'string') {
    throw new Error('enveloppe E2EE absente (clé "e" manquante)');
  }
  var wire = b64uDecode(wrapper.e);
  var plain = await aesGcmDecryptBytes(wire);
  return JSON.parse(new TextDecoder().decode(plain));
}

async function wsSendEncrypted(obj) {
  if (!ws || ws.readyState !== 1) return;
  var wrapper = await encryptObject(obj);
  ws.send(JSON.stringify(wrapper));
}

// ═══════════════════════════════════════════════════
// CODE D'ACCÈS
//
// En plus du lien du QR code, le Relay exige le code affiché sous le QR
// code sur le PC (POST /api/unlock, code chiffré par la clé E2EE). La
// session qu'il ouvre est gardée par ce navigateur avec le jeton du lien
// (localStorage : Safari quitté sur iOS efface sessionStorage, pas lui) :
// pas de nouvelle saisie tant que le Relay tourne. Son redémarrage change
// le jeton et oublie les sessions (WebSocket fermé en 4003) : le code est
// redemandé. Un autre navigateur ou appareil n'a pas la session.
// ═══════════════════════════════════════════════════

const SESSION_KEY = 'myai.relay.session';
let accessSession = readSession();

function readSession() {
  try {
    var saved = JSON.parse(localStorage.getItem(SESSION_KEY) || 'null');
    return saved && saved.token === TOKEN ? saved.session : '';
  } catch (e) {
    return '';
  }
}

function saveSession(session) {
  accessSession = session || '';
  try {
    if (accessSession) {
      localStorage.setItem(SESSION_KEY, JSON.stringify({ token: TOKEN, session: accessSession }));
    } else {
      localStorage.removeItem(SESSION_KEY);
    }
  } catch (e) {
    // Stockage indisponible : session gardée en mémoire pour cette page
  }
}

// Paramètres des requêtes à l'API : jeton du lien et session du code d'accès
function authQuery() {
  return 'token=' + encodeURIComponent(TOKEN) + '&session=' + encodeURIComponent(accessSession);
}

const unlockScreen = document.getElementById('unlockScreen');
const unlockForm = document.getElementById('unlockForm');
const unlockInput = document.getElementById('unlockInput');
const unlockError = document.getElementById('unlockError');
const unlockBtn = document.getElementById('unlockBtn');

function showUnlock() {
  unlockScreen.classList.add('visible');
  setTimeout(function () {
    if (!unlockInput.disabled) unlockInput.focus();
  }, 50);
}

function unlockMessage(result) {
  if (result.error === 'locked') return T('unlock.locked');
  if (result.error === 'format') return T('unlock.format');
  return T('unlock.wrong', { count: result.remaining });
}

async function submitUnlock(event) {
  event.preventDefault();
  var code = unlockInput.value.replace(/\D/g, '');
  if (code.length !== 6) {
    unlockError.textContent = unlockMessage({ error: 'format' });
    return;
  }
  unlockBtn.disabled = true;
  unlockError.textContent = '';
  var locked = false;
  try {
    var body = await encryptObject({ code: code });
    var res = await fetch('/api/unlock?token=' + encodeURIComponent(TOKEN), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    if (!res.ok) throw new Error('HTTP ' + res.status);
    var result = (await decryptEnvelope(await res.json())) || {};
    if (result.ok && result.session) {
      saveSession(result.session);
      unlockInput.value = '';
      unlockScreen.classList.remove('visible');
      connect();
      return;
    }
    locked = result.error === 'locked';
    unlockError.textContent = unlockMessage(result);
    if (!locked) unlockInput.select();
  } catch (err) {
    console.error('[Relay] Code d\'accès non vérifié :', err);
    unlockError.textContent = T('unlock.noAnswer');
  } finally {
    unlockBtn.disabled = locked;
    unlockInput.disabled = locked;
  }
}

unlockForm.addEventListener('submit', submitUnlock);
// Sans session, l'écran du code s'affiche avant tout le reste
if (!accessSession) showUnlock();

// ── STATE ───────────────────────────────────────────
let ws = null;
let reconnectTimer = null;
let reconnectAttempts = 0;
let isWaiting = false;
let typingEl = null;

// Dernier message_id envoyé (reçu via "ack" du serveur). Permet de
// récupérer la réponse après reconnexion si elle est tombée pendant
// que l'onglet Safari était en arrière-plan.
let lastSentMessageId = null;
// Nombre de messages déjà rendus venant de l'historique, pour éviter
// les doublons si on recharge l'historique.
let renderedMessageIds = new Set();
// Signal "historique déjà chargé au moins une fois"
let historyLoaded = false;
let slashPrompts = [];        // bibliothèque de prompts (slash commands)
let slashPromptsLoaded = false;

// Pièces jointes en attente d'envoi : [{localId, fileId, name, isImage, status}]
let pendingAttachments = [];
let attachmentCounter = 0;

// Bulle IA en cours de streaming (rendue en direct token par token).
// Un seul stream peut être actif à la fois côté mobile.
let streamingMessageId = null;
let streamingMessageEl = null;

// Documents générés reçus (événements `ai_document`) en attente d'être
// rattachés à la bulle de réponse. L'outil s'exécute avant que le modèle ne
// rédige sa synthèse : le document arrive donc AVANT la réponse finale.
// Chacun est un élément de l'aperçu (preview.js), son contenu déjà reçu.
let pendingDocuments = [];

// Demandes d'aperçu d'un fichier du PC en cours (file_preview) : request_id →
// { resolve, reject, timer }
let previewRequests = {};
let previewCounter = 0;

// Le scroll auto pendant le streaming ne doit pas se battre contre
// l'utilisateur qui a fait défiler vers le haut pour relire quelque chose.
// On considère "collé au bas" s'il y a moins de 80px sous la viewport.
let userPinnedToBottom = true;

// ── DOM ELEMENTS ────────────────────────────────────
const messagesEl = document.getElementById('messages');
const inputEl = document.getElementById('messageInput');
const sendBtn = document.getElementById('sendBtn');
const statusDot = document.getElementById('statusDot');
const statusText = document.getElementById('statusText');
const connBanner = document.getElementById('connBanner');
const welcomeEl = document.getElementById('welcome');
const attachmentsEl = document.getElementById('attachments');
const attachBtn = document.getElementById('attachBtn');
const fileInputEl = document.getElementById('fileInput');
const trashBtn = document.getElementById('trashBtn');

// ═══════════════════════════════════════════════════
// WEBSOCKET
// ═══════════════════════════════════════════════════

function connect() {
  if (ws && ws.readyState <= 1) return;
  if (!accessSession) {
    showUnlock();
    return;
  }

  console.log('[Relay] Connecting to', WS_URL);
  setStatus('connecting');

  try {
    ws = new WebSocket(WS_URL + '&session=' + encodeURIComponent(accessSession));
  } catch (e) {
    console.error('[Relay] WebSocket creation failed:', e);
    setStatus('offline');
    scheduleReconnect();
    return;
  }

  ws.onopen = function () {
    console.log('[Relay] Connected!');
    reconnectAttempts = 0;
    setStatus('connected');
    connBanner.classList.remove('visible');

    // (1) Au tout premier open : charger l'historique serveur pour
    //     restaurer les conversations précédentes (si la page a été
    //     rechargée ou ouverte sur un relay déjà actif).
    if (!historyLoaded) {
      loadHistory();
    }

    // (1b) Charger la bibliothèque de prompts (slash commands) pour l'autocomplétion "/".
    loadPrompts();

    // (1c) Notifier le module Agents qu'on est connecté (pour rafraîchir
    //      la liste des agents si la page Agents est ouverte).
    if (window.AgentsUI && typeof window.AgentsUI.onConnect === 'function') {
      window.AgentsUI.onConnect();
    }
    // (1d) Vue Code déjà ouverte : la conversation entière à nouveau
    if (window.CodeUI && typeof window.CodeUI.onConnect === 'function') {
      window.CodeUI.onConnect();
    }

    // (2) Si on était en attente d'une réponse quand la connexion est
    //     tombée, demander au serveur s'il a une réponse en attente pour
    //     notre dernier message_id.
    if (isWaiting && lastSentMessageId) {
      console.log('[Relay] Resuming wait for message_id:', lastSentMessageId);
      wsSendEncrypted({
        type: 'resume',
        last_message_id: lastSentMessageId,
      }).catch(function (e) {
        console.warn('[Relay] Resume send failed:', e);
      });
    }
  };

  ws.onmessage = async function (event) {
    var data;
    try {
      var wrapper = JSON.parse(event.data);
      data = await decryptEnvelope(wrapper);
    } catch (err) {
      console.error('[Relay] Message WS rejeté (E2EE invalide) :', err);
      return;
    }

    if (data.type === 'response') {
      // Déduplication : si on a déjà rendu ce message_id (ex. reçu via
      // broadcast ET via resume), ignorer le doublon.
      var mid = data.message_id || '';
      if (mid && renderedMessageIds.has('ai:' + mid)) {
        // Nettoyer toute bulle de streaming résiduelle pour ce message.
        if (streamingMessageId === mid) finalizeStreaming(mid, null, null);
        return;
      }
      if (mid) renderedMessageIds.add('ai:' + mid);

      removeTyping();
      isWaiting = false;
      // Si on reçoit la réponse à notre dernier message, on peut
      // oublier son id (il n'y a plus rien en attente à reprendre).
      if (mid && mid === lastSentMessageId) {
        lastSentMessageId = null;
      }
      // Si on était en train de streamer ce message, on finalise la bulle
      // existante au lieu d'en créer une nouvelle (évite le doublon visuel).
      // links : fichiers cités ou nommés, files : documents et images produits
      finalizeStreaming(mid, data.message, data.timestamp, { links: data.links, files: data.files });
      updateSendButton();
    } else if (data.type === 'chunk') {
      // Chunk de streaming : texte cumulatif courant de la génération.
      var cmid = data.message_id || '';
      if (!cmid) return;
      // Si la réponse finale a déjà été rendue, ignorer les chunks tardifs.
      if (renderedMessageIds.has('ai:' + cmid)) return;
      removeTyping();
      updateStreamingBubble(cmid, data.text || '');
    } else if (data.type === 'ack') {
      // Le serveur confirme avoir reçu notre message. On mémorise son id
      // pour pouvoir demander la réponse en cas de reconnexion, et on
      // marque le message utilisateur comme déjà rendu (évite un doublon
      // si l'historique est rechargé ensuite).
      if (data.message_id) {
        lastSentMessageId = data.message_id;
        renderedMessageIds.add('user:' + data.message_id);
      }
    } else if (data.type === 'ai_image') {
      // 🎨 Image générée (texte → image) reçue chiffrée dans l'enveloppe WS.
      // `data.data` est le PNG en base64 ; on l'affiche en data: URI.
      removeTyping();
      isWaiting = false;
      addImageMessage(data.data, data.mime || 'image/png', data.filename || '', data.timestamp);
      updateSendButton();
    } else if (data.type === 'ai_document') {
      // 📄 Document généré (docx, pdf, pptx, xlsx…) reçu chiffré dans
      // l'enveloppe WS. `data.html` est l'aperçu rendu côté hôte et
      // `data.data` le fichier réel en base64 pour le téléchargement.
      // On le met en attente : il sera rattaché à la bulle de réponse.
      var docName = data.filename || 'document';
      pendingDocuments.push({
        type: 'file',
        name: docName,
        path: data.path || '',
        payload: {
          ok: true,
          kind: 'document',
          name: docName,
          label: data.label || T('doc.default'),
          html: data.html || '',
          fileData: data.data || '',
          size: data.data ? Math.floor(data.data.length * 3 / 4) : undefined
        }
      });
    } else if (data.type === 'file_preview') {
      // Aperçu (ou fichier) demandé au PC : la demande en attente le reçoit
      settlePreview(data);
    } else if (data.type === 'resume_empty') {
      // Le serveur n'a pas de réponse en attente pour notre dernier id.
      // Soit la réponse est déjà arrivée, soit elle n'a pas encore fini
      // de se générer — on continue simplement d'attendre le broadcast.
      console.log('[Relay] Resume: aucune réponse en attente côté serveur');
    } else if (data.type === 'language') {
      // Langue de My_AI changée sur le PC : la page se recharge dans la nouvelle
      // (la session du code d'accès et la clé du lien restent)
      if (data.language && data.language !== (window.RelayI18n && window.RelayI18n.lang)) {
        location.reload();
      }
    } else if (typeof data.type === 'string' && data.type.indexOf('code_') === 0) {
      // Conversation Code (extension VS Code) : vue Code, module code.js
      if (window.CodeUI && typeof window.CodeUI.onMessage === 'function') {
        window.CodeUI.onMessage(data);
      }
    } else if (typeof data.type === 'string' && data.type.indexOf('agent') === 0) {
      // Messages de la page « Agents » (agents_list_result, agent_section_*,
      // agent_exec_*, agent_create_result, ...). Délégués au module agents.js.
      if (window.AgentsUI && typeof window.AgentsUI.onMessage === 'function') {
        window.AgentsUI.onMessage(data);
      }
    }
    // type === 'pong' → rien à faire
  };

  ws.onclose = function (event) {
    console.log('[Relay] Connection closed:', event.code, event.reason);
    setStatus('offline');
    // Les aperçus demandés n'arriveront plus sur ce WS
    failPreviews();
    if (event.code === 4003) {
      // Session refusée : redemander le code plutôt que de boucler
      saveSession('');
      showUnlock();
      return;
    }
    connBanner.classList.add('visible');
    scheduleReconnect();
  };

  ws.onerror = function (event) {
    console.error('[Relay] WebSocket error:', event);
    setStatus('offline');
  };
}

function scheduleReconnect() {
  if (reconnectTimer) return;
  reconnectAttempts++;
  const delay = Math.min(2000 * Math.pow(1.5, reconnectAttempts - 1), 30000);
  reconnectTimer = setTimeout(function () {
    reconnectTimer = null;
    setStatus('connecting');
    connect();
  }, delay);
}

function setStatus(state) {
  statusDot.className = 'status-dot ' + (
    state === 'connected' ? '' :
    state === 'connecting' ? 'connecting' : 'offline'
  );
  const labels = {
    connected: T('status.connected'),
    connecting: T('status.connecting'),
    offline: T('status.offline'),
  };
  statusText.textContent = labels[state] || state;
}

// Keepalive ping every 25s
setInterval(function () {
  if (ws && ws.readyState === 1) {
    wsSendEncrypted({ type: 'ping' }).catch(function () { /* swallow */ });
  }
}, 25000);

// ── HISTORY RESTORATION ─────────────────────────────
// Charge l'historique complet de la session relay côté serveur et
// rejoue les messages dans l'UI. Appelé au premier open du WebSocket
// (pour restaurer la conversation après un rechargement de la page
// Safari en arrière-plan) et via resume lors d'un retour de visibilité.
async function loadHistory() {
  if (historyLoaded) return;
  try {
    await e2eReady;
    var res = await fetch('/api/history?' + authQuery());
    if (!res.ok) {
      console.warn('[Relay] /api/history returned', res.status);
      historyLoaded = true;
      return;
    }
    var wrapper = await res.json();
    var data = await decryptEnvelope(wrapper);
    var items = (data && data.history) ? data.history : [];
    if (items.length === 0) {
      historyLoaded = true;
      return;
    }
    if (welcomeEl) welcomeEl.style.display = 'none';
    for (var i = 0; i < items.length; i++) {
      var m = items[i];
      if (!m || typeof m.text !== 'string') continue;
      var mid = m.message_id || '';
      // Clé de déduplication : user:<id> ou ai:<id>
      var key = (m.is_user ? 'user:' : 'ai:') + mid;
      if (mid && renderedMessageIds.has(key)) continue;
      if (mid) renderedMessageIds.add(key);
      addMessage(m.text, !!m.is_user, m.timestamp, false, m.is_user
        ? { attachments: historyAttachments(m) }
        : { links: m.links, files: m.files });
    }
    historyLoaded = true;
    // Si le dernier message est un message utilisateur sans réponse,
    // l'utilisateur attend peut-être la réponse → on rétablit le
    // spinner de typing et on mémorise son id pour pouvoir la reprendre.
    var last = items[items.length - 1];
    if (last && last.is_user && last.message_id) {
      lastSentMessageId = last.message_id;
      isWaiting = true;
      showTyping();
      updateSendButton();
      // Vérifier immédiatement si une réponse est déjà prête côté serveur
      checkPendingResponse(last.message_id);
    }
  } catch (e) {
    console.warn('[Relay] loadHistory failed:', e);
    historyLoaded = true;
  }
}

// Charge la bibliothèque de prompts (slash commands) pour l'autocomplétion "/".
// Même enveloppe E2EE que l'historique : le clair est {"prompts": [...]}.
async function loadPrompts() {
  if (slashPromptsLoaded) return;
  try {
    await e2eReady;
    var res = await fetch('/api/prompts?' + authQuery());
    if (!res.ok) {
      console.warn('[Relay] /api/prompts returned', res.status);
      return;
    }
    var wrapper = await res.json();
    var data = await decryptEnvelope(wrapper);
    slashPrompts = (data && Array.isArray(data.prompts)) ? data.prompts : [];
    slashPromptsLoaded = true;
  } catch (e) {
    console.warn('[Relay] loadPrompts failed:', e);
  }
}

// Demande au serveur s'il a une réponse IA en attente pour un message_id.
// Le serveur peut répondre :
//   - {pending: true, final: true, message}  → réponse complète
//   - {pending: true, final: false, message} → génération encore en cours
//   - {pending: false}                       → ni l'un ni l'autre
async function checkPendingResponse(messageId) {
  if (!messageId) return;
  try {
    await e2eReady;
    var url = '/api/pending?' + authQuery() +
              '&message_id=' + encodeURIComponent(messageId);
    var res = await fetch(url);
    if (!res.ok) return;
    var wrapper = await res.json();
    var data = await decryptEnvelope(wrapper);
    if (!data || !data.pending || typeof data.message !== 'string') return;

    if (data.final === false) {
      // Génération encore en cours : afficher l'état courant, les chunks
      // suivants arriveront via le WS quand il sera reconnecté.
      if (renderedMessageIds.has('ai:' + messageId)) return;
      removeTyping();
      updateStreamingBubble(messageId, data.message);
      return;
    }

    // Réponse finale
    var key = 'ai:' + messageId;
    if (renderedMessageIds.has(key)) return;
    renderedMessageIds.add(key);
    removeTyping();
    isWaiting = false;
    if (messageId === lastSentMessageId) lastSentMessageId = null;
    finalizeStreaming(messageId, data.message, data.timestamp, { links: data.links, files: data.files });
    updateSendButton();
  } catch (e) {
    console.warn('[Relay] checkPendingResponse failed:', e);
  }
}

// ═══════════════════════════════════════════════════
// MESSAGES
// ═══════════════════════════════════════════════════

function sendMessage() {
  const text = inputEl.value.trim();

  // Fichiers prêts (upload terminé avec succès)
  const readyAttachments = pendingAttachments.filter(function (a) { return a.status === 'ready'; });
  const hasAttachments = readyAttachments.length > 0;

  // On exige au moins du texte OU une pièce jointe
  if ((!text && !hasAttachments) || !ws || ws.readyState !== 1 || isWaiting) return;

  // Si un upload est encore en cours, attendre
  const uploading = pendingAttachments.some(function (a) { return a.status === 'uploading'; });
  if (uploading) return;

  // Hide welcome
  if (welcomeEl) welcomeEl.style.display = 'none';

  // Envoyer un message réinstalle l'intention « suivre la génération »
  userPinnedToBottom = true;
  // Ses pièces jointes, sous la bulle : un toucher ouvre leur aperçu
  addMessage(text, true, null, false, {
    attachments: readyAttachments.map(function (a) {
      return { name: a.name, isImage: a.isImage, fileId: a.fileId, file: a.file };
    })
  });

  // Envoyer au serveur (inclut les file_ids déjà uploadés)
  var payload = { type: 'chat', message: text };
  if (hasAttachments) {
    payload.file_ids = readyAttachments.map(function (a) { return a.fileId; });
  }
  wsSendEncrypted(payload).catch(function (err) {
    console.error('[Relay] Envoi chiffré échoué :', err);
  });
  isWaiting = true;

  // Indicateur de frappe
  showTyping();

  // Reset input + chips
  inputEl.value = '';
  autoResize();
  pendingAttachments = [];
  renderAttachments();
  updateSendButton();

  scrollToBottom();
}

// ═══════════════════════════════════════════════════
// ATTACHMENTS (fichiers / images)
// ═══════════════════════════════════════════════════

function handleFileSelect(event) {
  var files = event.target.files;
  if (!files || files.length === 0) return;
  for (var i = 0; i < files.length; i++) {
    uploadAttachment(files[i]);
  }
  // Reset l'input pour pouvoir re-sélectionner le même fichier plus tard
  event.target.value = '';
}

// Chiffre un fichier (E2EE) et l'envoie à /api/upload. Retourne la réponse
// déchiffrée {file_id, filename, is_image, size}. Logique partagée entre le
// chat (uploadAttachment) et la page Agents (via RelayCore.uploadEncryptedFile).
async function uploadEncryptedFile(file) {
  await e2eReady;
  // 1. Construire le clair : "MYAI" || u16_be(filename_len) || filename || content
  var fileBytes = new Uint8Array(await file.arrayBuffer());
  var fnameBytes = new TextEncoder().encode(file.name || 'fichier');
  if (fnameBytes.length > 256) throw new Error(T('upload.nameTooLong'));
  var header = new Uint8Array(4 + 2 + fnameBytes.length);
  header[0] = 0x4D; header[1] = 0x59; header[2] = 0x41; header[3] = 0x49; // "MYAI"
  header[4] = (fnameBytes.length >> 8) & 0xff;
  header[5] = fnameBytes.length & 0xff;
  header.set(fnameBytes, 6);
  var plain = new Uint8Array(header.length + fileBytes.length);
  plain.set(header, 0);
  plain.set(fileBytes, header.length);

  // 2. Chiffrer
  var wire = await aesGcmEncryptBytes(plain);

  // 3. Envoyer en multipart, avec un nom factice (le vrai nom est dans le clair)
  var blob = new Blob([wire], { type: 'application/octet-stream' });
  var form = new FormData();
  form.append('file', blob, 'enc.bin');
  var res = await fetch('/api/upload?' + authQuery(), {
    method: 'POST',
    body: form,
  });
  if (!res.ok) {
    var detail = 'HTTP ' + res.status;
    try {
      var j = await res.json();
      if (j && j.detail) detail = j.detail;
    } catch (_) {}
    throw new Error(detail);
  }

  // 4. Déchiffrer la réponse (E2EE)
  var wrapper = await res.json();
  return await decryptEnvelope(wrapper);
}

async function uploadAttachment(file) {
  var localId = 'att_' + (++attachmentCounter);
  var isImage = /^image\//i.test(file.type) ||
                /\.(png|jpe?g|gif|bmp|webp|tiff?|heic|heif)$/i.test(file.name);
  var entry = {
    localId: localId,
    fileId: null,
    name: file.name || 'fichier',
    isImage: isImage,
    status: 'uploading',
    error: null,
    // Le fichier lui-même : l'aperçu d'une image ne l'attend pas du PC
    file: file,
  };
  pendingAttachments.push(entry);
  renderAttachments();
  updateSendButton();

  try {
    var resp = await uploadEncryptedFile(file);
    entry.fileId = resp.file_id;
    entry.isImage = !!resp.is_image;
    entry.name = resp.filename || entry.name;
    entry.status = 'ready';
  } catch (err) {
    console.error('[Relay] Upload chiffré échoué :', err);
    entry.status = 'error';
    entry.error = (err && err.message) ? err.message : T('upload.error');
  }
  renderAttachments();
  updateSendButton();
}

function removeAttachment(localId) {
  pendingAttachments = pendingAttachments.filter(function (a) { return a.localId !== localId; });
  renderAttachments();
  updateSendButton();
}

function renderAttachments() {
  if (!attachmentsEl) return;
  attachmentsEl.innerHTML = '';
  pendingAttachments.forEach(function (a) {
    var chip = document.createElement('div');
    chip.className = 'attachment-chip';
    if (a.status === 'uploading') chip.classList.add('uploading');
    if (a.status === 'error') chip.classList.add('error');

    var icon = document.createElement('span');
    icon.className = 'chip-icon';
    icon.textContent = a.status === 'uploading' ? '⏳'
                      : a.status === 'error' ? '⚠️'
                      : (a.isImage ? '🖼️' : '📎');
    chip.appendChild(icon);

    // Prête (ou image du téléphone) : son nom ouvre l'aperçu, comme dans la fenêtre
    var openable = a.status === 'ready' || (a.isImage && a.file && a.status !== 'error');
    var name = document.createElement(openable ? 'button' : 'span');
    name.className = 'chip-name' + (openable ? ' chip-open' : '');
    name.textContent = a.status === 'error' ? (a.name + ' · ' + (a.error || T('attach.error'))) : a.name;
    if (openable) {
      name.type = 'button';
      name.onclick = function () { openPendingAttachment(a.localId); };
    }
    chip.appendChild(name);

    var rm = document.createElement('button');
    rm.className = 'chip-remove';
    rm.type = 'button';
    rm.textContent = '×';
    rm.setAttribute('aria-label', T('attach.remove'));
    rm.onclick = function () { removeAttachment(a.localId); };
    chip.appendChild(rm);

    attachmentsEl.appendChild(chip);
  });
}

// Icônes du bouton d'envoi : avion en papier (envoi) / carré (stop).
var SEND_ICON_HTML =
  '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">' +
  '<line x1="22" y1="2" x2="11" y2="13"></line>' +
  '<polygon points="22 2 15 22 11 13 2 9 22 2"></polygon></svg>';
var STOP_ICON_HTML =
  '<svg viewBox="0 0 24 24"><rect x="6" y="6" width="12" height="12" rx="2" fill="currentColor"></rect></svg>';
var sendBtnMode = 'send';

function setSendBtnMode(mode) {
  if (sendBtnMode === mode) return;
  sendBtnMode = mode;
  if (mode === 'stop') {
    sendBtn.classList.add('stopmode');
    sendBtn.innerHTML = STOP_ICON_HTML;
    sendBtn.onclick = stopGeneration;
    sendBtn.title = T('send.stop');
  } else {
    sendBtn.classList.remove('stopmode');
    sendBtn.innerHTML = SEND_ICON_HTML;
    sendBtn.onclick = sendMessage;
    sendBtn.title = '';
  }
}

function updateSendButton() {
  // La corbeille suit le même état : grisée pendant la génération
  updateTrash();
  // Pendant la génération, le bouton devient un bouton STOP cliquable
  // (carré noir sur fond blanc), comme sur la page Agents.
  if (isWaiting) {
    setSendBtnMode('stop');
    sendBtn.disabled = false;
    return;
  }
  setSendBtnMode('send');
  var hasText = !!inputEl.value.trim();
  var hasReady = pendingAttachments.some(function (a) { return a.status === 'ready'; });
  var uploading = pendingAttachments.some(function (a) { return a.status === 'uploading'; });
  sendBtn.disabled = uploading || (!hasText && !hasReady);
}

// Demande au serveur d'interrompre la génération en cours. Le GUI desktop
// (qui produit la réponse via le bridge) reçoit la demande, appelle
// interrupt_ai() et renvoie la réponse partielle marquée « interrompue »,
// ce qui repasse isWaiting à false côté mobile.
function stopGeneration() {
  if (!isWaiting) return;
  wsSendEncrypted({
    type: 'stop_generation',
    message_id: lastSentMessageId || '',
  }).catch(function () { /* swallow */ });
}

// extra : { attachments } d'un message de l'utilisateur ([{ name, isImage,
// fileId?, path?, file? }]) ; { links, files } d'une réponse (fichiers cités
// ou nommés, documents et images produits)
function addMessage(text, isUser, timestamp, autoOpen, extra) {
  if (welcomeEl) welcomeEl.style.display = 'none';
  extra = extra || {};

  const msg = document.createElement('div');
  msg.className = 'message ' + (isUser ? 'user' : 'ai');

  const time = formatTime(timestamp ? new Date(timestamp) : new Date());

  if (isUser) {
    var attachments = extra.attachments || [];
    if (text || !attachments.length) {
      msg.innerHTML =
        '<div class="bubble" dir="auto">' + escapeHtml(text) +
        '<span class="time">' + time + '</span></div>';
    }
    if (attachments.length) {
      msg.classList.add('with-files');
      var items = attachments.map(attachmentItem);
      msg.appendChild(fileChips(items, items, 0));
    }
  } else {
    msg.innerHTML =
      '<div class="ai-icon">' + ROBOT_SVG + '</div>' +
      '<div class="bubble"><div class="md" dir="auto">' +
      renderMarkdown(text, { preview: true, links: extra.links }) + '</div>' +
      '<span class="time">' + time + '</span></div>';
  }

  messagesEl.appendChild(msg);
  // Dans la page : ses images produites (historique) se placent avant elle
  if (!isUser) attachAnswerFiles(msg, text, extra.files, autoOpen);
  scrollToBottom();
}

// 🎨 Affiche une image générée par l'IA dans une bulle. `b64` est le PNG
// encodé en base64 (déchiffré depuis l'enveloppe WS E2EE). L'image est
// rendue en data: URI (jamais transmise en clair sur le réseau) et cliquable
// pour ouverture plein écran.
function addImageMessage(b64, mime, filename, timestamp) {
  if (welcomeEl) welcomeEl.style.display = 'none';
  if (!b64) return;

  var msg = document.createElement('div');
  msg.className = 'message ai';
  var time = formatTime(timestamp ? new Date(timestamp) : new Date());
  var src = 'data:' + (mime || 'image/png') + ';base64,' + b64;

  var bubble = document.createElement('div');
  bubble.className = 'bubble';

  var img = document.createElement('img');
  img.className = 'generated-image';
  img.src = src;
  img.alt = filename || T('image.generated');
  img.loading = 'lazy';
  // Plein écran dans l'aperçu (une adresse data: ne s'ouvre plus dans un onglet)
  img.addEventListener('click', function () {
    preview.open([{
      type: 'file', name: filename || T('image.generated'),
      payload: { ok: true, kind: 'image', mime: mime || 'image/png', data: b64,
                 name: filename || T('image.generated'), size: Math.floor(b64.length * 3 / 4) }
    }], 0);
  });

  bubble.appendChild(img);

  var timeSpan = document.createElement('span');
  timeSpan.className = 'time';
  timeSpan.textContent = time;
  bubble.appendChild(timeSpan);

  msg.innerHTML = '<div class="ai-icon">&#x1F3A8;</div>';
  msg.appendChild(bubble);
  messagesEl.appendChild(msg);
  scrollToBottom();
}

// ── STREAMING BUBBLE ────────────────────────────────
function ensureStreamingBubble(mid) {
  if (streamingMessageId === mid && streamingMessageEl && streamingMessageEl.isConnected) {
    return streamingMessageEl;
  }
  // Nouveau stream : créer la bulle.
  if (welcomeEl) welcomeEl.style.display = 'none';
  streamingMessageId = mid;
  var msg = document.createElement('div');
  msg.className = 'message ai streaming';
  msg.innerHTML =
    '<div class="ai-icon">' + ROBOT_SVG + '</div>' +
    '<div class="bubble"><div class="md stream-content" dir="auto"></div></div>';
  messagesEl.appendChild(msg);
  streamingMessageEl = msg;
  return msg;
}

// Texte reçu jusqu'ici, le curseur après son dernier caractère
function updateStreamingBubble(mid, text) {
  var bubble = ensureStreamingBubble(mid);
  var content = bubble.querySelector('.stream-content');
  if (content) {
    content.innerHTML = renderMarkdown(text, { cursor: true });
  }
  scrollToBottomStream();
}

// Finalise la bulle de streaming. Si `finalText` est fourni, la bulle est
// convertie en bulle IA définitive (avec timestamp). Sinon, elle est juste
// nettoyée (cas de déduplication). extra : { links, files } de la réponse.
function finalizeStreaming(mid, finalText, timestamp, extra) {
  extra = extra || {};
  if (streamingMessageId !== mid || !streamingMessageEl) {
    // Pas de bulle de streaming en cours pour ce message : rendu normal.
    // C'est une réponse fraîche → l'aperçu s'ouvre tout seul.
    if (finalText !== null && finalText !== undefined) {
      addMessage(finalText, false, timestamp, true, extra);
    }
    return;
  }
  if (finalText === null || finalText === undefined) {
    // Nettoyage sans finalisation : retirer la bulle.
    streamingMessageEl.remove();
  } else {
    var time = formatTime(timestamp ? new Date(timestamp) : new Date());
    streamingMessageEl.classList.remove('streaming');
    streamingMessageEl.innerHTML =
      '<div class="ai-icon">' + ROBOT_SVG + '</div>' +
      '<div class="bubble"><div class="md" dir="auto">' +
      renderMarkdown(finalText, { preview: true, links: extra.links }) + '</div>' +
      '<span class="time">' + time + '</span></div>';
    attachAnswerFiles(streamingMessageEl, finalText, extra.files, true);
  }
  streamingMessageEl = null;
  streamingMessageId = null;
  scrollToBottom();
}

function showTyping() {
  if (typingEl) return;
  typingEl = document.createElement('div');
  typingEl.className = 'message ai';
  typingEl.id = 'typingIndicator';
  typingEl.innerHTML =
    '<div class="ai-icon">' + ROBOT_SVG + '</div>' +
    '<div class="bubble">' +
      '<div class="typing-indicator">' +
        '<div class="typing-dot"></div>' +
        '<div class="typing-dot"></div>' +
        '<div class="typing-dot"></div>' +
      '</div>' +
    '</div>';
  messagesEl.appendChild(typingEl);
  scrollToBottom();
}

function removeTyping() {
  if (typingEl) {
    typingEl.remove();
    typingEl = null;
  }
}

// Corbeille : grisée tant que la page ouverte s'écrit encore (réponse du chat
// ou de la conversation Code, exécution des agents). Elle revient à la fin,
// ou une fois la génération arrêtée par Stop.
function updateTrash() {
  if (window.AgentsUI && window.AgentsUI.isActive()) {
    trashBtn.disabled = window.AgentsUI.isBusy();
  } else if (window.CodeUI && window.CodeUI.isActive()) {
    trashBtn.disabled = window.CodeUI.isBusy();
  } else {
    trashBtn.disabled = isWaiting;
  }
}

// Corbeille de la barre d'onglets : vide la page ouverte, et elle seule
function clearPage() {
  if (window.AgentsUI && window.AgentsUI.isActive()) {
    // Agents : leurs résultats ; le workflow et les deux conversations restent
    window.AgentsUI.clearResults();
  } else if (window.CodeUI && window.CodeUI.isActive()) {
    // Code : nouvelle conversation Code (aussi dans VS Code et sur le PC)
    window.CodeUI.clear();
  } else {
    clearChat();
  }
}

// Chat : ses messages à l'écran (la conversation Code a sa propre vue)
function clearChat() {
  // Remove all messages but keep the welcome element
  var children = Array.from(messagesEl.children);
  for (var i = 0; i < children.length; i++) {
    if (children[i] !== welcomeEl) {
      children[i].remove();
    }
  }
  if (welcomeEl) {
    welcomeEl.style.display = 'flex';
  }
}

function scrollToBottom() {
  requestAnimationFrame(function () {
    messagesEl.scrollTop = messagesEl.scrollHeight;
  });
}

// Scroll agressif pendant le streaming : le rendu markdown réflue la
// hauteur du conteneur après l'innerHTML, donc on applique le scroll
// immédiatement ET à la frame suivante (post-reflow) pour être certain
// que le curseur reste visible. Respecte l'utilisateur s'il a fait
// défiler manuellement vers le haut.
function scrollToBottomStream() {
  if (!userPinnedToBottom) return;
  messagesEl.scrollTop = messagesEl.scrollHeight;
  requestAnimationFrame(function () {
    if (!userPinnedToBottom) return;
    messagesEl.scrollTop = messagesEl.scrollHeight;
  });
}

// Détecter si l'utilisateur s'est volontairement éloigné du bas.
messagesEl.addEventListener('scroll', function () {
  var gap = messagesEl.scrollHeight - (messagesEl.scrollTop + messagesEl.clientHeight);
  userPinnedToBottom = gap < 80;
}, { passive: true });

// ═══════════════════════════════════════════════════
// MARKDOWN
// ═══════════════════════════════════════════════════

// Rendu partagé avec la vue de l'extension VS Code (markdown.js) : titres,
// listes imbriquées, tableaux, code, liens, citations [n] du bloc 📚 Sources.
// options.cursor : curseur du streaming après le dernier caractère ;
// options.preview : réponse écrite du chat, ses blocs HTML et SVG portent un
// bouton « Aperçu » ; options.links : fichiers qu'elle cite ou nomme (PC),
// cliquables comme dans la fenêtre (les dossiers restent du texte).
function renderMarkdown(text, options) {
  options = options || {};
  var opts = { codeActions: options.preview && !options.cursor ? CHAT_CODE_ACTIONS : CODE_ACTIONS };
  if (options.cursor) opts.cursor = true;
  if (options.links) {
    opts.links = options.links.filter(function (link) {
      return link && link.text && link.path && !link.dir;
    }).map(function (link) {
      return { text: link.text, path: link.path, whole: !!link.name };
    });
  }
  return window.MyAIMarkdown.render(text, opts);
}

// Bouton « Copier » des blocs de code : chat, vue Code et page Agents
var CODE_ACTIONS = [{ action: 'copy', label: T('md.copy') }];
// Réponse du chat : « Aperçu » sur un bloc HTML ou SVG (comme dans la fenêtre)
var CHAT_CODE_ACTIONS = [
  {
    action: 'preview',
    label: T('preview.button'),
    accepts: function (code, lang) { return !!window.MyAIPreview.artifactKind(code, lang); }
  },
  { action: 'copy', label: T('md.copy') }
];

function copyText(text) {
  if (navigator.clipboard && window.isSecureContext) {
    return navigator.clipboard.writeText(text);
  }
  // Page servie en http (réseau local) : l'ancienne copie du navigateur
  return new Promise(function (resolve, reject) {
    var area = document.createElement('textarea');
    area.value = text;
    area.setAttribute('readonly', '');
    area.style.position = 'fixed';
    area.style.opacity = '0';
    document.body.appendChild(area);
    area.select();
    try {
      if (document.execCommand('copy')) resolve();
      else reject(new Error('copy'));
    } catch (err) {
      reject(err);
    } finally {
      document.body.removeChild(area);
    }
  });
}

document.addEventListener('click', function (event) {
  var target = event.target instanceof Element ? event.target : null;
  if (!target) return;
  // Fichier cité ou nommé par une réponse : son aperçu, demandé au PC
  var link = target.closest('a.md-file');
  if (link) {
    event.preventDefault();
    var path = link.getAttribute('data-path') || '';
    preview.open([{ type: 'file', name: baseName(path), path: path }], 0);
    return;
  }
  var button = target.closest('.md-code-btn');
  if (button && button.dataset.action === 'preview') {
    openBlockPreview(button);
    return;
  }
  if (!button || button.dataset.action !== 'copy') return;
  var code = button.closest('.md-code').querySelector('pre code');
  copyText(code ? code.textContent : '').then(function () {
    button.textContent = T('md.copied');
    setTimeout(function () { button.textContent = T('md.copy'); }, 1200);
  }).catch(function (err) {
    console.warn('[Relay] Copie impossible :', err);
  });
});

// ═══════════════════════════════════════════════════
// APERÇU (preview.js) : fichiers et blocs HTML/SVG dans une modale plein
// écran (pas de volet de côté sur un téléphone). Un fichier du PC (pièce
// jointe, fichier cité, document produit) est demandé au Relay
// (file_preview), qui ne montre que ceux de la conversation.
// ═══════════════════════════════════════════════════

var preview = window.MyAIPreview.create({
  strings: {
    close: T('preview.close'),
    previous: T('preview.previous'),
    next: T('preview.next'),
    position: T('preview.position'),
    download: T('preview.download'),
    openBrowser: T('preview.openBrowser'),
    preview: T('preview.button'),
    code: T('preview.code'),
    copy: T('md.copy'),
    copied: T('md.copied'),
    loading: T('preview.loading'),
    none: T('preview.none'),
    failed: T('preview.failed'),
    truncated: T('preview.truncated')
  },
  locale: window.RelayI18n ? window.RelayI18n.locale : undefined,
  // Le bouton Retour du téléphone ferme l'aperçu au lieu de quitter la page
  history: true,
  request: requestFilePreview,
  save: saveFile,
  copy: copyText,
  // Fallback « Ouvrir dans le navigateur » : Blob local, nouvel onglet
  openBrowser: function (html) {
    try {
      var blob = new Blob([html], { type: 'text/html' });
      window.open(URL.createObjectURL(blob), '_blank', 'noopener');
    } catch (err) { /* no-op */ }
  }
});

function untitledArtifact(kind, index) {
  return T(kind === 'svg' ? 'artifact.svg' : 'artifact.html', { n: index + 1 });
}

function baseName(path) {
  return String(path || '').split(/[\\/]/).pop() || String(path || '');
}

// Envoi du téléphone, rangé sur le PC sous « <identifiant>_<nom> »
function uploadName(path) {
  return baseName(path).replace(/^[0-9a-f]{16}_(?=.)/, '');
}

var IMAGE_NAME = /\.(png|jpe?g|gif|bmp|webp|svg|ico|avif|heic|heif|tiff?)$/i;

// Pièces jointes d'un message de l'historique (chemins sur le PC)
function historyAttachments(message) {
  var list = [];
  if (message.image_path) {
    list.push({ name: uploadName(message.image_path), path: message.image_path, isImage: true });
  }
  (message.file_paths || []).forEach(function (path) {
    list.push({ name: uploadName(path), path: path, isImage: IMAGE_NAME.test(path) });
  });
  return list;
}

// Pièce jointe → élément de l'aperçu
function attachmentItem(att) {
  return {
    type: 'file', name: att.name, path: att.path || '', fileId: att.fileId || '',
    file: att.file || null, isImage: !!att.isImage, icon: att.isImage ? '🖼️' : '📎'
  };
}

// Vignettes cliquables (pièces jointes, documents) : chacune ouvre l'aperçu
// sur elle, ‹ k/n › passe aux autres éléments du groupe
function fileChips(items, group, offset) {
  var box = document.createElement('div');
  box.className = 'file-chips';
  items.forEach(function (item, i) {
    var chip = document.createElement('button');
    chip.type = 'button';
    chip.className = 'file-chip';
    var label = item.payload && item.payload.label;
    chip.innerHTML =
      '<span class="file-chip-icon">' + (item.icon || '📄') + '</span>' +
      '<span class="file-chip-name" dir="auto">' + escapeHtml(item.name) + '</span>' +
      (label ? '<span class="file-chip-meta">' + escapeHtml(label) + '</span>' : '');
    chip.title = item.name;
    chip.onclick = function () { preview.open(group, offset + i); };
    box.appendChild(chip);
  });
  return box;
}

// Réponse finie : ses blocs HTML/SVG, ses documents (cartes) et, depuis
// l'historique, ses images produites. Fraîche, l'aperçu s'ouvre tout seul sur
// son premier élément, comme dans la fenêtre.
function attachAnswerFiles(msgEl, text, files, fresh) {
  var bubble = msgEl.querySelector('.bubble');
  if (!bubble) return;
  var blocks = window.MyAIPreview.detectArtifacts(text, untitledArtifact);
  var documents = [];
  if (fresh && pendingDocuments.length) {
    documents = pendingDocuments;
    pendingDocuments = [];
  }
  (files || []).forEach(function (file) {
    if (!file || !file.path) return;
    if (file.kind === 'image') {
      // Réponse en direct : l'image est déjà affichée (ai_image)
      if (!fresh) historyImage(msgEl, file);
      return;
    }
    if (documents.some(function (doc) { return doc.path === file.path; })) return;
    documents.push({ type: 'file', name: file.name || baseName(file.path), path: file.path });
  });
  var items = blocks.concat(documents);
  msgEl._previewItems = items;
  if (documents.length) {
    bubble.insertBefore(fileChips(documents, items, blocks.length), bubble.querySelector('.time'));
  }
  if (fresh && items.length) {
    setTimeout(function () { if (msgEl.isConnected) preview.open(items, 0); }, 120);
  }
}

// Image produite, depuis l'historique : demandée au PC, puis affichée comme en direct
function historyImage(msgEl, file) {
  var holder = document.createElement('div');
  holder.className = 'message ai';
  holder.innerHTML = '<div class="ai-icon">&#x1F3A8;</div>';
  var bubble = document.createElement('div');
  bubble.className = 'bubble';
  holder.appendChild(bubble);
  var item = { type: 'file', name: file.name || baseName(file.path), path: file.path, icon: '🖼️' };
  bubble.appendChild(fileChips([item], [item], 0));
  msgEl.parentNode.insertBefore(holder, msgEl);
  requestFilePreview(item, false).then(function (payload) {
    if (!payload || payload.ok === false || payload.kind !== 'image') return;
    item.payload = payload;
    var img = document.createElement('img');
    img.className = 'generated-image';
    img.alt = item.name;
    img.src = 'data:' + (payload.mime || 'image/png') + ';base64,' + payload.data;
    img.addEventListener('click', function () { preview.open([item], 0); });
    bubble.innerHTML = '';
    bubble.appendChild(img);
  }).catch(function () { /* la vignette reste */ });
}

// « Aperçu » d'un bloc : la modale s'ouvre sur lui, les autres éléments de la
// réponse à côté (‹ k/n ›)
function openBlockPreview(button) {
  var block = button.closest('.md-code');
  var codeEl = block ? block.querySelector('pre code') : null;
  if (!codeEl) return;
  var code = codeEl.textContent.trim();
  // Éléments de la réponse (chat) ou de la section (page Agents) qui le contient
  var items = [];
  for (var node = button; node && node !== document; node = node.parentNode) {
    if (node._previewItems) { items = node._previewItems; break; }
  }
  var index = -1;
  for (var i = 0; i < items.length; i++) {
    if (items[i].type === 'artifact' && items[i].code === code) { index = i; break; }
  }
  if (index === -1) {
    var langEl = block.querySelector('.md-code-lang');
    var kind = window.MyAIPreview.artifactKind(code, langEl ? langEl.textContent : '');
    if (!kind) return;
    items = [{ type: 'artifact', kind: kind, code: code, title: untitledArtifact(kind, 0) }];
    index = 0;
  }
  preview.open(items, index);
}

// Pièce jointe pas encore envoyée : son aperçu (les autres prêtes à côté)
function openPendingAttachment(localId) {
  var openable = pendingAttachments.filter(function (a) {
    return a.status === 'ready' || (a.isImage && a.file && a.status !== 'error');
  });
  var index = openable.findIndex(function (a) { return a.localId === localId; });
  if (index === -1) return;
  preview.open(openable.map(attachmentItem), index);
}

// Image du téléphone : lue sur place, sans attendre le PC
function readLocalImage(item) {
  return new Promise(function (resolve, reject) {
    var reader = new FileReader();
    reader.onload = function () {
      var url = String(reader.result || '');
      var comma = url.indexOf(',');
      resolve({
        ok: true, kind: 'image', name: item.name, size: item.file.size,
        mime: item.file.type || 'image/png', data: comma === -1 ? '' : url.slice(comma + 1)
      });
    };
    reader.onerror = function () { reject(reader.error || new Error(T('upload.error'))); };
    reader.readAsDataURL(item.file);
  });
}

// Aperçu (ou fichier, download) d'un fichier du PC : message file_preview,
// la réponse arrive dans l'enveloppe chiffrée (settlePreview)
function requestFilePreview(item, download) {
  if (!download && item.file && item.isImage) return readLocalImage(item);
  return new Promise(function (resolve, reject) {
    if (!ws || ws.readyState !== 1) {
      reject(new Error(T('preview.offline')));
      return;
    }
    var id = 'pv' + (++previewCounter) + '_' + Date.now().toString(36);
    var request = { type: 'file_preview', request_id: id };
    if (item.fileId) request.file_id = item.fileId;
    else request.path = item.path || '';
    if (download) request.download = true;
    var timer = setTimeout(function () {
      delete previewRequests[id];
      reject(new Error(T('preview.timeout')));
    }, 90000);
    previewRequests[id] = { resolve: resolve, reject: reject, timer: timer };
    wsSendEncrypted(request).catch(function (err) {
      clearTimeout(timer);
      delete previewRequests[id];
      reject(err);
    });
  });
}

function settlePreview(data) {
  var pending = previewRequests[data.request_id];
  if (!pending) return;
  delete previewRequests[data.request_id];
  clearTimeout(pending.timer);
  pending.resolve(data);
}

function failPreviews() {
  var pending = previewRequests;
  previewRequests = {};
  Object.keys(pending).forEach(function (id) {
    clearTimeout(pending[id].timer);
    pending[id].reject(new Error(T('preview.offline')));
  });
}

// Reconstitue le fichier depuis son base64 et déclenche le téléchargement
// (il n'a jamais transité en clair).
function saveFile(name, mime, data) {
  try {
    var binary = atob(data);
    var bytes = new Uint8Array(binary.length);
    for (var i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
    var url = URL.createObjectURL(new Blob([bytes], { type: mime || 'application/octet-stream' }));
    var link = document.createElement('a');
    link.href = url;
    link.download = name || 'fichier';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    // Laisser au navigateur le temps de démarrer le téléchargement.
    setTimeout(function () { URL.revokeObjectURL(url); }, 10000);
  } catch (err) {
    console.error('[Relay] Téléchargement du fichier échoué :', err);
  }
}

// ═══════════════════════════════════════════════════
// UTILITIES
// ═══════════════════════════════════════════════════

function escapeHtml(text) {
  var div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

function formatTime(date) {
  var locale = window.RelayI18n ? window.RelayI18n.locale : 'fr-FR';
  return date.toLocaleTimeString(locale, { hour: '2-digit', minute: '2-digit' });
}

// ═══════════════════════════════════════════════════
// INPUT HANDLING
// ═══════════════════════════════════════════════════

// ── Autocomplétion des slash commands ("/" en début de saisie) ──────
let slashMenuEl = null;
let slashItems = [];
let slashIndex = 0;
let slashMenuOpen = false;

function slashNormalize(s) {
  return (s || '').normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase();
}

function ensureSlashMenu() {
  if (slashMenuEl) return slashMenuEl;
  slashMenuEl = document.createElement('div');
  slashMenuEl.className = 'slash-menu';
  slashMenuEl.style.display = 'none';
  var anchor = inputEl.closest('.input-area') || document.body;
  anchor.appendChild(slashMenuEl);
  return slashMenuEl;
}

function hideSlashMenu() {
  slashMenuOpen = false;
  slashItems = [];
  if (slashMenuEl) slashMenuEl.style.display = 'none';
}

function updateSlashActive() {
  if (!slashMenuEl) return;
  var rows = slashMenuEl.querySelectorAll('.slash-item');
  rows.forEach(function (r, i) {
    r.classList.toggle('active', i === slashIndex);
    if (i === slashIndex && r.scrollIntoView) {
      r.scrollIntoView({ block: 'nearest' });
    }
  });
}

function slashMove(delta) {
  if (!slashItems.length) return;
  slashIndex = (slashIndex + delta + slashItems.length) % slashItems.length;
  updateSlashActive();
}

function renderSlashMenu() {
  var el = ensureSlashMenu();
  el.innerHTML = '';
  slashItems.forEach(function (item, i) {
    var row = document.createElement('div');
    row.className = 'slash-item' + (i === slashIndex ? ' active' : '');

    var cmd = document.createElement('div');
    cmd.className = 'slash-cmd';
    cmd.textContent = '/' + (item.command || '');
    row.appendChild(cmd);

    var sub = (item.title || '') + (item.description ? ' — ' + item.description : '');
    if (sub.trim()) {
      var desc = document.createElement('div');
      desc.className = 'slash-desc';
      desc.textContent = sub;
      row.appendChild(desc);
    }

    // mousedown (et non click) : devance le blur du textarea / fiable au tactile.
    row.addEventListener('mousedown', function (e) {
      e.preventDefault();
      slashAccept(item);
    });
    row.addEventListener('mouseenter', function () {
      slashIndex = i;
      updateSlashActive();
    });
    el.appendChild(row);
  });
}

function updateSlashMenu() {
  var m = /^\/(\S*)$/.exec(inputEl.value);
  if (!m || !slashPrompts.length) {
    hideSlashMenu();
    return;
  }
  var pref = slashNormalize(m[1]);
  slashItems = slashPrompts.filter(function (p) {
    return p.command && slashNormalize(p.command).indexOf(pref) === 0;
  }).slice(0, 8);
  if (!slashItems.length) {
    hideSlashMenu();
    return;
  }
  slashIndex = 0;
  renderSlashMenu();
  ensureSlashMenu().style.display = 'block';
  slashMenuOpen = true;
}

function slashAccept(item) {
  // Insère seulement « /commande » ; l'utilisateur tape ensuite son texte.
  // L'expansion en prompt détaillé se fait côté hôte (desktop) au moment de l'envoi.
  inputEl.value = '/' + (item.command || '') + ' ';
  hideSlashMenu();
  inputEl.focus();
  var len = inputEl.value.length;
  try { inputEl.setSelectionRange(len, len); } catch (e) { /* noop */ }
  autoResize();
  updateSendButton();
}

inputEl.addEventListener('input', function () {
  autoResize();
  updateSendButton();
  updateSlashMenu();
});

inputEl.addEventListener('blur', function () {
  // Léger délai : laisse le mousedown d'une ligne s'exécuter avant de fermer.
  setTimeout(hideSlashMenu, 150);
});

inputEl.addEventListener('keydown', function (e) {
  if (slashMenuOpen) {
    if (e.key === 'ArrowDown') { e.preventDefault(); slashMove(1); return; }
    if (e.key === 'ArrowUp') { e.preventDefault(); slashMove(-1); return; }
    if (e.key === 'Enter' || e.key === 'Tab') {
      e.preventDefault();
      if (slashItems[slashIndex]) slashAccept(slashItems[slashIndex]);
      return;
    }
    if (e.key === 'Escape') { e.preventDefault(); hideSlashMenu(); return; }
  }
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    sendMessage();
  }
});

function autoResize() {
  inputEl.style.height = 'auto';
  inputEl.style.height = Math.min(inputEl.scrollHeight, 120) + 'px';
}

// ═══════════════════════════════════════════════════
// PONT POUR LE MODULE AGENTS (agents.js)
// ═══════════════════════════════════════════════════
// agents.js est chargé dans un <script> séparé : il accède à la connexion
// WebSocket chiffrée, au rendu Markdown et à l'état de connexion via cet
// objet exposé sur window. Tout passe par la même enveloppe E2EE.
window.RelayCore = {
  send: function (obj) { return wsSendEncrypted(obj); },
  isConnected: function () { return !!(ws && ws.readyState === 1); },
  renderMarkdown: renderMarkdown,
  escapeHtml: escapeHtml,
  uploadEncryptedFile: function (file) { return uploadEncryptedFile(file); },
  e2eReady: function () { return e2eReady; },
  getToken: function () { return TOKEN; },
  // Vue Code (code.js) : bulles identiques à celles du chat
  formatTime: formatTime,
  robotSvg: ROBOT_SVG,
  codeActions: CODE_ACTIONS,
  // État de la corbeille, à revoir quand une page commence ou finit d'écrire
  updateTrash: updateTrash,
  // Aperçu (page Agents) : pièces jointes [{ name, fileId, isImage, file? }], blocs
  // HTML/SVG d'un texte, vignettes cliquables
  openAttachments: function (list, index) { preview.open(list.map(attachmentItem), index); },
  answerArtifacts: function (text) {
    return window.MyAIPreview.detectArtifacts(text, untitledArtifact);
  },
  attachmentChips: function (list) {
    var items = list.map(attachmentItem);
    return fileChips(items, items, 0);
  },
};

// ═══════════════════════════════════════════════════
// INIT
// ═══════════════════════════════════════════════════

// On attend que la clé E2EE soit importée avant d'ouvrir le WS : sans
// elle, aucun message ne pourrait être chiffré/déchiffré et le serveur
// fermerait la connexion (4002 E2EE requis).
e2eReady.then(function () {
  connect();
}).catch(function () {
  // L'erreur a déjà été rendue visible dans le DOM par importE2EKey().
});

// Handle visibility change (phone lock/unlock or Safari backgrounded)
document.addEventListener('visibilitychange', function () {
  if (document.visibilityState !== 'visible') return;

  // Cas 1 : WS tombé → reconnecter. L'onopen appellera loadHistory() +
  // enverra un message "resume" si isWaiting, ce qui récupère la
  // réponse générée pendant l'absence.
  if (!ws || ws.readyState > 1) {
    setStatus('connecting');
    connect();
    return;
  }

  // Cas 2 : WS encore vivant mais on attendait une réponse et iOS a
  // peut-être gelé le traitement JS pendant qu'on était en background.
  // On interroge directement le serveur via HTTP (plus fiable que le
  // WS qui peut être dans un état zombie) pour voir si la réponse est
  // déjà prête.
  if (isWaiting && lastSentMessageId) {
    checkPendingResponse(lastSentMessageId);
  }
});
