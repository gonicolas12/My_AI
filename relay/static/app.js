/* ═══════════════════════════════════════════════════ */
/* My_AI Relay — Mobile Chat Application              */
/* ═══════════════════════════════════════════════════ */

// ── CONFIGURATION ───────────────────────────────────
const TOKEN = window.__RELAY_TOKEN__ || '';
const WS_PROTOCOL = location.protocol === 'https:' ? 'wss:' : 'ws:';
const WS_URL = `${WS_PROTOCOL}//${location.host}/ws?token=${TOKEN}`;
console.log('[Relay] Token:', TOKEN ? TOKEN.substring(0, 6) + '...' : 'EMPTY');
console.log('[Relay] WS URL:', WS_URL);

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
      try {
        ws.send(JSON.stringify({
          type: 'resume',
          last_message_id: lastSentMessageId,
        }));
      } catch (e) {
        console.warn('[Relay] Resume send failed:', e);
      }
    }
  };

  ws.onmessage = function (event) {
    var data = JSON.parse(event.data);

    if (data.type === 'response') {
      // Déduplication : si on a déjà rendu ce message_id (ex. reçu via
      // broadcast ET via resume), ignorer le doublon.
      var mid = data.message_id || '';
      if (mid && renderedMessageIds.has('ai:' + mid)) {
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
      addMessage(data.message, false, data.timestamp);
      updateSendButton();
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
    ws.send(JSON.stringify({ type: 'ping' }));
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
    var res = await fetch('/api/history?token=' + encodeURIComponent(TOKEN));
    if (!res.ok) {
      console.warn('[Relay] /api/history returned', res.status);
      historyLoaded = true;
      return;
    }
    var data = await res.json();
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
async function checkPendingResponse(messageId) {
  if (!messageId) return;
  try {
    var url = '/api/pending?token=' + encodeURIComponent(TOKEN) +
              '&message_id=' + encodeURIComponent(messageId);
    var res = await fetch(url);
    if (!res.ok) return;
    var data = await res.json();
    if (data && data.pending && typeof data.message === 'string') {
      var key = 'ai:' + messageId;
      if (renderedMessageIds.has(key)) return;
      renderedMessageIds.add(key);
      removeTyping();
      isWaiting = false;
      if (messageId === lastSentMessageId) lastSentMessageId = null;
      addMessage(data.message, false, data.timestamp);
      updateSendButton();
    }
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

  addMessage(displayText, true);

  // Envoyer au serveur (inclut les file_ids déjà uploadés)
  var payload = { type: 'chat', message: text };
  if (hasAttachments) {
    payload.file_ids = readyAttachments.map(function (a) { return a.fileId; });
  }
  ws.send(JSON.stringify(payload));
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

function uploadAttachment(file) {
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

  var form = new FormData();
  form.append('file', file);

  var xhr = new XMLHttpRequest();
  xhr.open('POST', '/api/upload?token=' + encodeURIComponent(TOKEN));
  xhr.onload = function () {
    if (xhr.status >= 200 && xhr.status < 300) {
      try {
        var resp = JSON.parse(xhr.responseText);
        entry.fileId = resp.file_id;
        entry.isImage = !!resp.is_image;
        entry.name = resp.filename || entry.name;
        entry.status = 'ready';
      } catch (e) {
        entry.status = 'error';
        entry.error = 'Réponse serveur invalide';
      }
    } else {
      entry.status = 'error';
      try {
        var j = JSON.parse(xhr.responseText);
        entry.error = j.detail || ('HTTP ' + xhr.status);
      } catch (e) {
        entry.error = 'HTTP ' + xhr.status;
      }
    }
    renderAttachments();
    updateSendButton();
  };
  xhr.onerror = function () {
    entry.status = 'error';
    entry.error = 'Erreur réseau';
    renderAttachments();
    updateSendButton();
  };
  xhr.send(form);
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

connect();

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
