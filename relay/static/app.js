/* ═══════════════════════════════════════════════════ */
/* My_AI Relay — Mobile Chat Application              */
/* ═══════════════════════════════════════════════════ */

// ── CONFIGURATION ───────────────────────────────────
const TOKEN = window.__RELAY_TOKEN__ || '';
const WS_PROTOCOL = location.protocol === 'https:' ? 'wss:' : 'ws:';
const WS_URL = `${WS_PROTOCOL}//${location.host}/ws?token=${TOKEN}`;
console.log('[Relay] Token:', TOKEN ? TOKEN.substring(0, 6) + '...' : 'EMPTY');
console.log('[Relay] WS URL:', WS_URL);

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
    return Promise.reject(new Error('Clé E2EE absente du fragment URL — ' +
      'rescannez le QR code depuis l\'application My_AI sur le PC.'));
  }
  var rawKey;
  try {
    rawKey = b64uDecode(decodeURIComponent(params.k));
  } catch (e) {
    return Promise.reject(new Error('Clé E2EE malformée dans l\'URL.'));
  }
  if (rawKey.length !== 32) {
    return Promise.reject(new Error('Clé E2EE de taille invalide (' + rawKey.length + ' octets).'));
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
    '<h2 style="color:#ef4444">⚠️ Connexion impossible</h2>' +
    '<p>' + (err && err.message ? err.message : 'Clé de chiffrement manquante.') + '</p>' +
    '<p style="color:#9ca3af;font-size:14px;margin-top:16px">Rescannez le QR code depuis le panneau My_AI Relay sur votre PC.</p>' +
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

// Pièces jointes en attente d'envoi : [{localId, fileId, name, isImage, status}]
let pendingAttachments = [];
let attachmentCounter = 0;

// Bulle IA en cours de streaming (rendue en direct token par token).
// Un seul stream peut être actif à la fois côté mobile.
let streamingMessageId = null;
let streamingMessageEl = null;

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

// ═══════════════════════════════════════════════════
// WEBSOCKET
// ═══════════════════════════════════════════════════

function connect() {
  if (ws && ws.readyState <= 1) return;

  console.log('[Relay] Connecting to', WS_URL);
  setStatus('connecting');

  try {
    ws = new WebSocket(WS_URL);
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
      finalizeStreaming(mid, data.message, data.timestamp);
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
    } else if (data.type === 'resume_empty') {
      // Le serveur n'a pas de réponse en attente pour notre dernier id.
      // Soit la réponse est déjà arrivée, soit elle n'a pas encore fini
      // de se générer — on continue simplement d'attendre le broadcast.
      console.log('[Relay] Resume: aucune réponse en attente côté serveur');
    }
    // type === 'pong' → rien à faire
  };

  ws.onclose = function (event) {
    console.log('[Relay] Connection closed:', event.code, event.reason);
    setStatus('offline');
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
    connected: 'Connecté',
    connecting: 'Connexion...',
    offline: 'Hors ligne',
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
    var res = await fetch('/api/history?token=' + encodeURIComponent(TOKEN));
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
      addMessage(m.text, !!m.is_user, m.timestamp);
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

// Demande au serveur s'il a une réponse IA en attente pour un message_id.
// Le serveur peut répondre :
//   - {pending: true, final: true, message}  → réponse complète
//   - {pending: true, final: false, message} → génération encore en cours
//   - {pending: false}                       → ni l'un ni l'autre
async function checkPendingResponse(messageId) {
  if (!messageId) return;
  try {
    await e2eReady;
    var url = '/api/pending?token=' + encodeURIComponent(TOKEN) +
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
    finalizeStreaming(messageId, data.message, data.timestamp);
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

  // Construire l'affichage local du message (texte + chips)
  var attachDisplay = readyAttachments.map(function (a) {
    return (a.isImage ? '🖼️ ' : '📎 ') + a.name;
  }).join('\n');
  var displayText = text;
  if (attachDisplay) {
    displayText = displayText ? (text + '\n' + attachDisplay) : attachDisplay;
  }

  // Envoyer un message réinstalle l'intention « suivre la génération »
  userPinnedToBottom = true;
  addMessage(displayText, true);

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
  };
  pendingAttachments.push(entry);
  renderAttachments();
  updateSendButton();

  try {
    await e2eReady;

    // 1. Construire le clair : "MYAI" || u16_be(filename_len) || filename || content
    var fileBytes = new Uint8Array(await file.arrayBuffer());
    var fnameBytes = new TextEncoder().encode(entry.name);
    if (fnameBytes.length > 256) {
      throw new Error('nom de fichier trop long');
    }
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

    // Utilisation de fetch (XHR ne gère pas async/await proprement ici)
    var res = await fetch('/api/upload?token=' + encodeURIComponent(TOKEN), {
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
    var resp = await decryptEnvelope(wrapper);
    entry.fileId = resp.file_id;
    entry.isImage = !!resp.is_image;
    entry.name = resp.filename || entry.name;
    entry.status = 'ready';
  } catch (err) {
    console.error('[Relay] Upload chiffré échoué :', err);
    entry.status = 'error';
    entry.error = (err && err.message) ? err.message : 'Erreur upload';
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

    var name = document.createElement('span');
    name.className = 'chip-name';
    name.textContent = a.status === 'error' ? (a.name + ' · ' + (a.error || 'erreur')) : a.name;
    chip.appendChild(name);

    var rm = document.createElement('button');
    rm.className = 'chip-remove';
    rm.type = 'button';
    rm.textContent = '×';
    rm.setAttribute('aria-label', 'Retirer');
    rm.onclick = function () { removeAttachment(a.localId); };
    chip.appendChild(rm);

    attachmentsEl.appendChild(chip);
  });
}

function updateSendButton() {
  var hasText = !!inputEl.value.trim();
  var hasReady = pendingAttachments.some(function (a) { return a.status === 'ready'; });
  var uploading = pendingAttachments.some(function (a) { return a.status === 'uploading'; });
  sendBtn.disabled = isWaiting || uploading || (!hasText && !hasReady);
}

function addMessage(text, isUser, timestamp) {
  if (welcomeEl) welcomeEl.style.display = 'none';

  const msg = document.createElement('div');
  msg.className = 'message ' + (isUser ? 'user' : 'ai');

  const time = formatTime(timestamp ? new Date(timestamp) : new Date());

  if (isUser) {
    msg.innerHTML =
      '<div class="bubble">' + escapeHtml(text) +
      '<span class="time">' + time + '</span></div>';
  } else {
    msg.innerHTML =
      '<div class="ai-icon">&#x1F916;</div>' +
      '<div class="bubble">' + renderMarkdown(text) +
      '<span class="time">' + time + '</span></div>';
  }

  messagesEl.appendChild(msg);
  scrollToBottom();
}

// ── STREAMING BUBBLE ────────────────────────────────
// Ferme provisoirement un bloc de code ``` non terminé pour que le rendu
// markdown pendant le streaming reste stable (sinon le ``` ouvrant
// apparaît en texte brut tant que la clôture n'est pas reçue).
function balanceMarkdownForStreaming(text) {
  if (!text) return '';
  // Compter les séquences ``` en début de ligne ou précédées d'un \n.
  var fenceMatches = text.match(/(^|\n)```/g);
  var count = fenceMatches ? fenceMatches.length : 0;
  if (count % 2 === 1) {
    // Ajouter une fermeture fantôme : le renderer voit un bloc complet,
    // et la prochaine mise à jour arrivera avec plus de contenu.
    text = text + '\n```';
  }
  return text;
}

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
    '<div class="ai-icon">&#x1F916;</div>' +
    '<div class="bubble">' +
      '<div class="stream-content"></div>' +
      '<span class="stream-cursor"></span>' +
    '</div>';
  messagesEl.appendChild(msg);
  streamingMessageEl = msg;
  return msg;
}

function updateStreamingBubble(mid, text) {
  var bubble = ensureStreamingBubble(mid);
  var content = bubble.querySelector('.stream-content');
  if (content) {
    content.innerHTML = renderMarkdown(balanceMarkdownForStreaming(text));
  }
  scrollToBottomStream();
}

// Finalise la bulle de streaming. Si `finalText` est fourni, la bulle est
// convertie en bulle IA définitive (avec timestamp). Sinon, elle est juste
// nettoyée (cas de déduplication).
function finalizeStreaming(mid, finalText, timestamp) {
  if (streamingMessageId !== mid || !streamingMessageEl) {
    // Pas de bulle de streaming en cours pour ce message : rendu normal.
    if (finalText !== null && finalText !== undefined) {
      addMessage(finalText, false, timestamp);
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
      '<div class="ai-icon">&#x1F916;</div>' +
      '<div class="bubble">' + renderMarkdown(finalText) +
      '<span class="time">' + time + '</span></div>';
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
    '<div class="ai-icon">&#x1F916;</div>' +
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
// MARKDOWN LIGHT RENDERER
// ═══════════════════════════════════════════════════

function renderMarkdown(text) {
  if (!text) return '';
  var html = escapeHtml(text);

  // Code blocks ``` ... ```
  html = html.replace(/```(\w*)\n([\s\S]*?)```/g, function (_, lang, code) {
    return '<pre><code>' + code.trim() + '</code></pre>';
  });

  // Inline code
  html = html.replace(/`([^`]+)`/g, '<code>$1</code>');

  // Headings # through ######
  html = html.replace(/^(#{1,6}) (.+)$/gm, function (_, hashes, content) {
    var lvl = hashes.length;
    return '<h' + lvl + '>' + content + '</h' + lvl + '>';
  });

  // Bold **text**
  html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');

  // Italic *text*
  html = html.replace(/(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)/g, '<em>$1</em>');

  // Tables  (must run before line-break conversion)
  html = html.replace(/((?:^\|[^\n]+\n?)+)/gm, function (tableBlock) {
    var lines = tableBlock.trim().split('\n').filter(function (l) { return l.trim(); });
    if (lines.length < 2) return tableBlock;
    // Second line must be a separator row (only |, -, :, spaces)
    if (!/^\|[\s:\-|]+\|?$/.test(lines[1].trim())) return tableBlock;
    var parseRow = function (line) {
      return line.replace(/^\||\|$/g, '').split('|').map(function (c) { return c.trim(); });
    };
    var headers = parseRow(lines[0]);
    var out = '<table><thead><tr>';
    headers.forEach(function (h) { out += '<th>' + h + '</th>'; });
    out += '</tr></thead><tbody>';
    for (var i = 2; i < lines.length; i++) {
      var row = lines[i].trim();
      if (!row) continue;
      var cells = parseRow(row);
      out += '<tr>';
      cells.forEach(function (c) { out += '<td>' + c + '</td>'; });
      out += '</tr>';
    }
    out += '</tbody></table>';
    return out;
  });

  // Lists (ordered + unordered)
  // Convert to placeholder tags first, then wrap contiguous blocks.
  html = html.replace(/^\s*(\d+)[\.)]\s+(.+)$/gm, '<oli>$2</oli>');
  html = html.replace(/^\s*[\-\*]\s+(.+)$/gm, '<uli>$1</uli>');

  html = html.replace(/(?:<oli>[\s\S]*?<\/oli>\n?)+/g, function (block) {
    var items = block.replace(/<oli>/g, '<li>').replace(/<\/oli>/g, '</li>');
    return '<ol>' + items + '</ol>';
  });

  html = html.replace(/(?:<uli>[\s\S]*?<\/uli>\n?)+/g, function (block) {
    var items = block.replace(/<uli>/g, '<li>').replace(/<\/uli>/g, '</li>');
    return '<ul>' + items + '</ul>';
  });

  // Line breaks -> paragraphs
  html = html.replace(/\n\n/g, '</p><p>');
  html = html.replace(/\n/g, '<br>');
  html = '<p>' + html + '</p>';

  // Clean up empty paragraphs and nesting issues
  html = html.replace(/<p><\/p>/g, '');
  html = html.replace(/<p>(<pre>)/g, '$1');
  html = html.replace(/(<\/pre>)<\/p>/g, '$1');
  html = html.replace(/<p>(<ul>)/g, '$1');
  html = html.replace(/(<\/ul>)<\/p>/g, '$1');
  html = html.replace(/<p>(<ol>)/g, '$1');
  html = html.replace(/(<\/ol>)<\/p>/g, '$1');
  html = html.replace(/<p>(<h[1-6]>)/g, '$1');
  html = html.replace(/(<\/h[1-6]>)<\/p>/g, '$1');
  html = html.replace(/<p>(<table>)/g, '$1');
  html = html.replace(/(<\/table>)<\/p>/g, '$1');

  // Fix spurious <br> inside lists (from \n → <br> applied after <ul> wrapping)
  html = html.replace(/(<\/li>)<br>(<li>)/g, '$1$2');
  html = html.replace(/<ul><br>/g, '<ul>');
  html = html.replace(/<br><\/ul>/g, '</ul>');
  html = html.replace(/<ol><br>/g, '<ol>');
  html = html.replace(/<br><\/ol>/g, '</ol>');

  return html;
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
  return date.toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' });
}

// ═══════════════════════════════════════════════════
// INPUT HANDLING
// ═══════════════════════════════════════════════════

inputEl.addEventListener('input', function () {
  autoResize();
  updateSendButton();
});

inputEl.addEventListener('keydown', function (e) {
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
