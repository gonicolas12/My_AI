/* ═══════════════════════════════════════════════════ */
/* My_AI Relay — Vue Code                               */
/*                                                       */
/* La conversation de l'extension VS Code, isolée du     */
/* chat : les messages envoyés et reçus dans VS Code y   */
/* sont, ceux de la page Code du PC aussi. Un message    */
/* tapé ici part à l'extension, qui agit dans son        */
/* workspace ; la réponse arrive en streaming, avec ses  */
/* appels d'outils et, pour une écriture ou une          */
/* commande, les boutons d'approbation. Même saisie que  */
/* le chat ; une réponse est une bulle (turn.js), la     */
/* même que dans VS Code : son texte et, à la suite, ses */
/* appels d'outils.                                      */
/*                                                       */
/* Aperçus (preview.js), comme dans le chat : pièces     */
/* jointes avant et après l'envoi, fichiers qu'une       */
/* réponse finie cite ou nomme (links, calculés par le   */
/* Relay), blocs HTML et SVG (bouton « Aperçu »). Rien   */
/* ne s'ouvre seul, comme sur la page Code du PC.        */
/*                                                       */
/* Protocole (relay/code_hub.py) : code_subscribe à la   */
/* première ouverture (puis à chaque reconnexion), qui   */
/* renvoie code_snapshot ; ensuite code_state, code_user,*/
/* code_chunk, code_tool, code_done, code_cleared,       */
/* code_error. Envois : code_chat, code_stop, code_clear,*/
/* code_approve.                                         */
/* ═══════════════════════════════════════════════════ */

(function () {
  'use strict';

  var T = window.RelayI18n ? window.RelayI18n.t : function (key) { return key; };

  // Icône du bouton Code (la même que sur le PC, lucide « code-xml »)
  var CODE_SVG =
    '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" ' +
    'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">' +
    '<path d="m18 16 4-4-4-4"/><path d="m6 8-4 4 4 4"/><path d="m14.5 4-5 16"/></svg>';
  var SEND_ICON_HTML =
    '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">' +
    '<line x1="22" y1="2" x2="11" y2="13"></line>' +
    '<polygon points="22 2 15 22 11 13 2 9 22 2"></polygon></svg>';
  var STOP_ICON_HTML =
    '<svg viewBox="0 0 24 24"><rect x="6" y="6" width="12" height="12" rx="2" fill="currentColor"></rect></svg>';

  var OPEN_STATUSES = { requested: true, 'awaiting-approval': true, running: true };
  var IMAGE_NAME = /\.(png|jpe?g|gif|bmp|webp|svg|ico|avif|heic|heif|tiff?)$/i;

  var el = {};
  // Inscrit à la conversation (vue ouverte au moins une fois) : ses événements arrivent
  var subscribed = false;
  var state = { vscode: false, workspace: null, busy: false, message_id: null, origin: null };
  // Transcription, comme celle du hub : questions, réponses et leurs morceaux
  var messages = [];
  // message_id → sa réponse à l'écran, une bulle (turn.js, comme dans VS Code)
  var turns = {};
  // Message parti, pas encore revenu (code_user) ni refusé (code_error) ; son
  // texte revient dans la saisie s'il est refusé
  var sending = false;
  var sentText = '';
  var pendingAttachments = [];
  var attachmentCounter = 0;
  var userPinnedToBottom = true;
  var lastScrollTop = 0;
  var sendBtnMode = 'send';
  // Réponses dont le texte a changé depuis la dernière image, affichées à la
  // suivante : le serveur envoie un code_chunk par token, plus souvent que
  // l'écran ne se redessine
  var dirtyReplies = [];
  var dirtyFrame = 0;

  function $(id) { return document.getElementById(id); }

  function core() { return window.RelayCore; }

  function init() {
    el.view = $('viewCode');
    el.messages = $('codeMessages');
    el.welcome = $('codeWelcome');
    el.notice = $('codeNotice');
    el.input = $('codeInput');
    el.sendBtn = $('codeSendBtn');
    el.attachBtn = $('codeAttachBtn');
    el.fileInput = $('codeFileInput');
    el.attachments = $('codeAttachments');
    if (!el.view) return;

    el.sendBtn.onclick = sendMessage;
    el.attachBtn.addEventListener('click', function () { el.fileInput.click(); });
    el.fileInput.addEventListener('change', function (event) {
      var files = event.target.files;
      for (var i = 0; files && i < files.length; i++) uploadAttachment(files[i]);
      event.target.value = '';
    });
    el.input.addEventListener('input', function () {
      autoResize();
      updateSendButton();
    });
    el.input.addEventListener('keydown', function (e) {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
      }
    });
    // Le défilement suit la réponse tant qu'on ne remonte pas ; revenu en bas,
    // il la suit à nouveau. Le texte qui s'allonge sous l'écran ne l'arrête pas.
    el.messages.addEventListener('scroll', function () {
      var top = el.messages.scrollTop;
      var gap = el.messages.scrollHeight - (top + el.messages.clientHeight);
      if (gap < 80) userPinnedToBottom = true;
      else if (top < lastScrollTop) userPinnedToBottom = false;
      lastScrollTop = top;
    }, { passive: true });
    renderNotice();
    updateSendButton();
  }

  // ════════════════════════════════════════════════════
  // CYCLE DE VIE
  // ════════════════════════════════════════════════════

  function isActive() {
    return !!(el.view && el.view.classList.contains('active'));
  }

  // Vue ouverte : la première fois, inscription (l'état complet suit)
  function onShow() {
    if (!subscribed && core() && core().isConnected()) {
      subscribed = true;
      core().send({ type: 'code_subscribe' });
    }
    scrollToBottom();
  }

  // WebSocket (re)connecté : la conversation a pu avancer pendant la coupure
  function onConnect() {
    if (subscribed || isActive()) {
      subscribed = true;
      core().send({ type: 'code_subscribe' });
    }
  }

  function onMessage(data) {
    // Un appel d'outil, la fin… s'affichent après le texte reçu avant eux
    if (data.type !== 'code_chunk') flushChunks();
    switch (data.type) {
      case 'code_snapshot': applySnapshot(data); break;
      case 'code_state': applyState(data); break;
      case 'code_user': applyUser(data); break;
      case 'code_chunk': applyChunk(data); break;
      case 'code_tool': applyTool(data); break;
      case 'code_done': applyDone(data); break;
      case 'code_cleared': applyCleared(); break;
      case 'code_error': applyError(data); break;
      default: break;
    }
  }

  // ════════════════════════════════════════════════════
  // ÉVÉNEMENTS DE LA CONVERSATION
  // ════════════════════════════════════════════════════

  function applySnapshot(data) {
    messages = Array.isArray(data.messages) ? data.messages : [];
    messages.forEach(function (message) {
      if (message.role !== 'user' && message.links) message.links = core().fileLinks(message.links);
    });
    renderAll();
    applyState(data.state || {});
    scrollToBottom();
  }

  function applyState(data) {
    state = {
      vscode: !!data.vscode,
      workspace: data.workspace || null,
      busy: !!data.busy,
      message_id: data.message_id || null,
      origin: data.origin || null,
    };
    if (!state.busy) sending = false;
    renderNotice();
    updateSendButton();
  }

  function applyUser(data) {
    sending = false;
    sentText = '';
    if (findMessage('user', data.message_id)) return;
    var user = {
      message_id: data.message_id, role: 'user', text: data.text || '',
      origin: data.origin, timestamp: data.timestamp, attachments: data.attachments || [],
      files: data.files || [],
    };
    var reply = {
      message_id: data.message_id, role: 'assistant', origin: data.origin,
      timestamp: data.timestamp, parts: [], text: '', status: 'streaming',
    };
    messages.push(user, reply);
    hideWelcome();
    userPinnedToBottom = true;
    renderUser(user);
    renderReply(reply);
    scrollToBottom();
    updateSendButton();
  }

  function applyChunk(data) {
    var reply = findMessage('assistant', data.message_id);
    if (!reply) return;
    var part = reply.parts.filter(function (p) {
      return p.kind === 'text' && p.segment === data.segment;
    })[0];
    if (!part) {
      // Pas de texte vide : une passe qui n'écrit qu'un appel d'outil
      if (!(data.text || '').trim()) return;
      part = { kind: 'text', segment: data.segment, text: data.text };
      reply.parts.push(part);
    } else {
      part.text = data.text;
    }
    if (dirtyReplies.indexOf(reply) === -1) dirtyReplies.push(reply);
    if (!dirtyFrame) dirtyFrame = requestAnimationFrame(flushChunks);
  }

  // Textes en attente : à l'image suivante, ou avant tout autre événement
  function flushChunks() {
    if (dirtyFrame) cancelAnimationFrame(dirtyFrame);
    dirtyFrame = 0;
    var queued = dirtyReplies;
    dirtyReplies = [];
    queued.forEach(renderReply);
    if (queued.length) scrollToBottomStream();
  }

  function applyTool(data) {
    var reply = findMessage('assistant', data.message_id);
    if (!reply) return;
    var part = reply.parts.filter(function (p) {
      return p.kind === 'tool' && p.call_id === data.call_id;
    })[0];
    var fields = {
      kind: 'tool', call_id: data.call_id, name: data.name, input: data.input || {},
      status: data.status, output: data.output, options: data.options,
    };
    if (!part) {
      part = fields;
      reply.parts.push(part);
    } else {
      Object.keys(fields).forEach(function (key) { part[key] = fields[key]; });
    }
    renderReply(reply);
    scrollToBottomStream();
  }

  function applyDone(data) {
    var reply = findMessage('assistant', data.message_id);
    if (!reply) return;
    reply.status = data.status;
    reply.text = data.text || '';
    reply.timestamp = data.timestamp || reply.timestamp;
    reply.duration_ms = data.duration_ms;
    // Fichiers qu'elle cite ou nomme, trouvés sur le PC par le Relay
    reply.links = core().fileLinks(data.links);
    reply.parts.forEach(function (part) {
      if (part.kind === 'tool' && OPEN_STATUSES[part.status]) {
        part.status = 'stopped';
        delete part.options;
      }
    });
    renderReply(reply);
    scrollToBottom();
  }

  function applyCleared() {
    messages = [];
    sending = false;
    renderAll();
    updateSendButton();
  }

  // Message refusé (VS Code absent, réponse en cours) : la raison, comme une réponse en erreur
  function applyError(data) {
    sending = false;
    if (sentText && !el.input.value) {
      el.input.value = sentText;
      autoResize();
    }
    sentText = '';
    hideWelcome();
    var refused = { status: 'error', parts: [], text: data.message || '' };
    el.messages.appendChild(window.MyAITurn.create(refused, turnOptions()).el);
    scrollToBottom();
    updateSendButton();
  }

  function findMessage(role, messageId) {
    for (var i = messages.length - 1; i >= 0; i--) {
      if (messages[i].role === role && messages[i].message_id === messageId) return messages[i];
    }
    return null;
  }

  // ════════════════════════════════════════════════════
  // RENDU
  // ════════════════════════════════════════════════════

  function renderAll() {
    Array.from(el.messages.children).forEach(function (child) {
      if (child !== el.welcome) child.remove();
    });
    turns = {};
    messages.forEach(function (message) {
      if (message.role === 'user') renderUser(message);
      else renderReply(message);
    });
    if (el.welcome) el.welcome.style.display = messages.length ? 'none' : 'flex';
  }

  function hideWelcome() {
    if (el.welcome) el.welcome.style.display = 'none';
  }

  function timeOf(iso) {
    return core().formatTime(iso ? new Date(iso) : new Date());
  }

  // Pièces jointes d'un message : leurs chemins sur le PC (files), ou leurs noms
  // seuls (message d'avant les chemins : vignette grisée)
  function sentFiles(message) {
    var files = (Array.isArray(message.files) ? message.files : []).filter(function (file) {
      return file && file.name;
    });
    if (files.length) {
      return files.map(function (file) {
        return { name: file.name, path: file.path || '', isImage: IMAGE_NAME.test(file.name) };
      });
    }
    return (Array.isArray(message.attachments) ? message.attachments : []).filter(function (name) {
      return typeof name === 'string' && name;
    }).map(function (name) {
      return { name: name, isImage: IMAGE_NAME.test(name) };
    });
  }

  // Question : sa provenance si elle n'a pas été tapée sur ce téléphone, ses
  // pièces jointes sous la bulle (un toucher ouvre leur aperçu), comme dans le chat
  function renderUser(message) {
    var files = sentFiles(message);
    var origin = message.origin === 'vscode' ? T('code.origin.vscode')
      : message.origin === 'desktop' ? T('code.origin.desktop') : '';
    var msg = document.createElement('div');
    msg.className = 'message user' + (origin ? ' with-origin' : '') + (files.length ? ' with-files' : '');
    var html = origin ? '<span class="code-origin">' + core().escapeHtml(origin) + '</span>' : '';
    if (message.text || !files.length) {
      html += '<div class="bubble" dir="auto">' + core().escapeHtml(message.text || '') +
        '<span class="time">' + timeOf(message.timestamp) + '</span></div>';
    }
    msg.innerHTML = html;
    if (files.length) msg.appendChild(core().attachmentChips(files));
    el.messages.appendChild(msg);
  }

  // Bulles des réponses, les mêmes que dans la vue de l'extension VS Code (turn.js)
  var turnOpts = null;
  function turnOptions() {
    if (!turnOpts) {
      turnOpts = {
        t: T,
        approve: function (callId, decision) {
          core().send({ type: 'code_approve', call_id: callId, decision: decision });
        },
        robotSvg: core().robotSvg,
        formatTime: core().formatTime,
        locale: window.RelayI18n ? window.RelayI18n.locale : undefined,
        // « Aperçu » sur un bloc HTML ou SVG fini, « Copier » sur tous
        codeActions: core().previewActions || core().codeActions,
        // Message tapé dans VS Code : c'est VS Code qui demande l'accord
        approvalNote: true,
      };
    }
    return turnOpts;
  }

  // Réponse : une bulle, créée à sa première apparition, mise à jour ensuite
  // (texte reçu, appel d'outil, fin) sans être refaite
  function renderReply(reply) {
    var turn = turns[reply.message_id];
    if (turn) {
      turn.update(reply);
    } else {
      turn = window.MyAITurn.create(reply, turnOptions());
      turns[reply.message_id] = turn;
      el.messages.appendChild(turn.el);
    }
    // Réponse finie : l'« Aperçu » d'un de ses blocs HTML ou SVG montre aussi les
    // autres (‹ k/n ›, app.js openBlockPreview)
    turn.el._previewItems = reply.status === 'streaming' ? null
      : core().answerArtifacts(replyText(reply));
  }

  // Texte affiché d'une réponse : celui de ses passes, sinon son texte final
  function replyText(reply) {
    var texts = (reply.parts || []).filter(function (part) {
      return part && part.kind === 'text' && part.text;
    }).map(function (part) { return part.text; });
    return texts.length ? texts.join('\n\n') : (reply.text || '');
  }

  // VS Code absent : rien ne part, et comment le connecter
  function renderNotice() {
    if (!el.notice) return;
    if (state.vscode) {
      el.notice.className = 'code-notice ok';
      el.notice.textContent = T('code.connected', { name: state.workspace || 'VS Code' });
    } else {
      el.notice.className = 'code-notice';
      el.notice.textContent = T('code.offline');
    }
    el.notice.style.display = subscribed ? '' : 'none';
  }

  // ════════════════════════════════════════════════════
  // SAISIE
  // ════════════════════════════════════════════════════

  function sendMessage() {
    var text = el.input.value.trim();
    var ready = pendingAttachments.filter(function (a) { return a.status === 'ready'; });
    var uploading = pendingAttachments.some(function (a) { return a.status === 'uploading'; });
    if ((!text && !ready.length) || uploading || sending || state.busy || !state.vscode) return;
    if (!core() || !core().isConnected()) return;
    var payload = { type: 'code_chat', message: text };
    if (ready.length) payload.file_ids = ready.map(function (a) { return a.fileId; });
    sending = true;
    sentText = text;
    core().send(payload).catch(function () { sending = false; updateSendButton(); });
    el.input.value = '';
    autoResize();
    pendingAttachments = [];
    renderAttachments();
    userPinnedToBottom = true;
    updateSendButton();
  }

  function stopGeneration() {
    if (core() && core().isConnected()) core().send({ type: 'code_stop' });
  }

  // Effacer : nouvelle conversation Code, aussi dans VS Code et sur le PC
  function clear() {
    if (!core() || !core().isConnected()) return;
    if (!window.confirm(T('code.clearConfirm'))) return;
    core().send({ type: 'code_clear' });
  }

  function setSendBtnMode(mode) {
    if (sendBtnMode === mode) return;
    sendBtnMode = mode;
    if (mode === 'stop') {
      el.sendBtn.classList.add('stopmode');
      el.sendBtn.innerHTML = STOP_ICON_HTML;
      el.sendBtn.onclick = stopGeneration;
      el.sendBtn.title = T('send.stop');
    } else {
      el.sendBtn.classList.remove('stopmode');
      el.sendBtn.innerHTML = SEND_ICON_HTML;
      el.sendBtn.onclick = sendMessage;
      el.sendBtn.title = '';
    }
  }

  // Réponse en cours (d'où que vienne son message), ou message tout juste envoyé
  function isBusy() {
    return state.busy || sending;
  }

  function updateSendButton() {
    if (!el.sendBtn) return;
    // La corbeille suit le même état : grisée pendant la réponse
    core().updateTrash();
    if (state.busy) {
      setSendBtnMode('stop');
      el.sendBtn.disabled = false;
      return;
    }
    setSendBtnMode('send');
    var hasText = !!el.input.value.trim();
    var hasReady = pendingAttachments.some(function (a) { return a.status === 'ready'; });
    var uploading = pendingAttachments.some(function (a) { return a.status === 'uploading'; });
    el.sendBtn.disabled = sending || uploading || !state.vscode || (!hasText && !hasReady);
  }

  function autoResize() {
    el.input.style.height = 'auto';
    el.input.style.height = Math.min(el.input.scrollHeight, 120) + 'px';
  }

  async function uploadAttachment(file) {
    // file : une image s'affiche sans attendre la fin de son envoi
    var entry = {
      localId: 'code_att_' + (++attachmentCounter), fileId: null, name: file.name || 'file',
      isImage: /^image\//i.test(file.type), status: 'uploading', error: null, file: file,
    };
    pendingAttachments.push(entry);
    renderAttachments();
    updateSendButton();
    try {
      var resp = await core().uploadEncryptedFile(file);
      entry.fileId = resp.file_id;
      entry.isImage = !!resp.is_image;
      entry.name = resp.filename || entry.name;
      entry.status = 'ready';
    } catch (err) {
      entry.status = 'error';
      entry.error = (err && err.message) ? err.message : T('upload.error');
    }
    renderAttachments();
    updateSendButton();
  }

  function renderAttachments() {
    el.attachments.innerHTML = '';
    pendingAttachments.forEach(function (a) {
      var chip = document.createElement('div');
      chip.className = 'attachment-chip' + (a.status === 'uploading' ? ' uploading' : '') +
        (a.status === 'error' ? ' error' : '');
      var icon = document.createElement('span');
      icon.className = 'chip-icon';
      icon.textContent = a.status === 'uploading' ? '⏳' : a.status === 'error' ? '⚠️'
        : (a.isImage ? '🖼️' : '📎');
      // Prête (ou image du téléphone) : son nom ouvre l'aperçu, comme dans le chat
      var canOpen = openable(a);
      var name = document.createElement(canOpen ? 'button' : 'span');
      name.className = 'chip-name' + (canOpen ? ' chip-open' : '');
      name.textContent = a.status === 'error' ? a.name + ' · ' + (a.error || T('attach.error')) : a.name;
      if (canOpen) {
        name.type = 'button';
        name.onclick = function () { openPending(a); };
      }
      var rm = document.createElement('button');
      rm.className = 'chip-remove';
      rm.type = 'button';
      rm.textContent = '×';
      rm.setAttribute('aria-label', T('attach.remove'));
      rm.onclick = function () {
        pendingAttachments = pendingAttachments.filter(function (x) { return x !== a; });
        renderAttachments();
        updateSendButton();
      };
      chip.appendChild(icon);
      chip.appendChild(name);
      chip.appendChild(rm);
      el.attachments.appendChild(chip);
    });
  }

  function openable(attachment) {
    return attachment.status === 'ready' ||
      (attachment.isImage && attachment.file && attachment.status !== 'error');
  }

  // Pièce jointe pas encore envoyée : son aperçu, les autres prêtes à côté (‹ k/n ›)
  function openPending(attachment) {
    var list = pendingAttachments.filter(openable);
    var index = list.indexOf(attachment);
    if (index !== -1) core().openAttachments(list, index);
  }

  function scrollToBottom() {
    requestAnimationFrame(function () {
      if (el.messages) el.messages.scrollTop = el.messages.scrollHeight;
    });
  }

  function scrollToBottomStream() {
    if (!userPinnedToBottom) return;
    el.messages.scrollTop = el.messages.scrollHeight;
    requestAnimationFrame(function () {
      if (userPinnedToBottom) el.messages.scrollTop = el.messages.scrollHeight;
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

  window.CodeUI = {
    onMessage: onMessage,
    onConnect: onConnect,
    onShow: onShow,
    isActive: isActive,
    isBusy: isBusy,
    clear: clear,
    icon: CODE_SVG,
  };
})();
