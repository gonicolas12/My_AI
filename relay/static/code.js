/* ═══════════════════════════════════════════════════ */
/* My_AI Relay — Vue Code                               */
/*                                                       */
/* La conversation de l'extension VS Code, isolée du     */
/* chat : les messages envoyés et reçus dans VS Code y   */
/* sont, ceux de la page Code du PC aussi. Un message    */
/* tapé ici part à l'extension, qui agit dans son        */
/* workspace ; la réponse arrive en streaming, avec ses  */
/* appels d'outils et, pour une écriture ou une          */
/* commande, les boutons d'approbation. Même interface   */
/* que le chat (bulles, saisie, bouton Stop).            */
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

  // Libellé de chaque outil de l'extension (AGENT_TOOLS de core/agentic_executor.py)
  var TOOL_LABELS = {
    read_file: function (x) { return T('code.tool.read_file', { target: x }); },
    write_file: function (x) { return T('code.tool.write_file', { target: x }); },
    edit_file: function (x) { return T('code.tool.edit_file', { target: x }); },
    list_dir: function (x) { return T('code.tool.list_dir', { target: x }); },
    glob: function (x) { return T('code.tool.glob', { target: x }); },
    grep: function (x) { return T('code.tool.grep', { target: x }); },
    run_command: function (x) { return T('code.tool.run_command', { target: x }); },
    get_active_editor: function () { return T('code.tool.get_active_editor'); },
    open_file: function (x) { return T('code.tool.open_file', { target: x }); },
  };
  var TOOL_ICONS = {
    read_file: '📄', write_file: '📝', edit_file: '✏️', list_dir: '📁', glob: '🔎',
    grep: '🔍', run_command: '⌨️', get_active_editor: '🗂️', open_file: '↗️',
  };
  var APPROVALS = {
    'allow-once': function () { return T('code.approval.allowOnce'); },
    'allow-target': function () { return T('code.approval.allowTarget'); },
    'allow-tool': function (tool) { return T('code.approval.allowTool', { tool: tool }); },
    deny: function () { return T('code.approval.deny'); },
  };
  var OPEN_STATUSES = { requested: true, 'awaiting-approval': true, running: true };

  var el = {};
  // Inscrit à la conversation (vue ouverte au moins une fois) : ses événements arrivent
  var subscribed = false;
  var state = { vscode: false, workspace: null, busy: false, message_id: null, origin: null };
  // Transcription, comme celle du hub : questions, réponses et leurs morceaux
  var messages = [];
  // message_id → éléments affichés de sa réponse : conteneur, morceaux, indicateur
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
  // Textes reçus depuis la dernière image, affichés à la suivante : le serveur
  // envoie un code_chunk par token, plus souvent que l'écran ne se redessine
  var dirtyParts = [];
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
      // Pas de bulle vide : une passe qui n'écrit qu'un appel d'outil
      if (!(data.text || '').trim()) return;
      part = { kind: 'text', segment: data.segment, text: data.text };
      reply.parts.push(part);
    } else {
      part.text = data.text;
    }
    if (!dirtyParts.some(function (item) { return item.part === part; })) {
      dirtyParts.push({ reply: reply, part: part });
    }
    if (!dirtyFrame) dirtyFrame = requestAnimationFrame(flushChunks);
  }

  // Textes en attente : à l'image suivante, ou avant tout autre événement
  function flushChunks() {
    if (dirtyFrame) cancelAnimationFrame(dirtyFrame);
    dirtyFrame = 0;
    var queued = dirtyParts;
    dirtyParts = [];
    queued.forEach(function (item) { renderPart(item.reply, item.part); });
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
    renderPart(reply, part);
    scrollToBottomStream();
  }

  function applyDone(data) {
    var reply = findMessage('assistant', data.message_id);
    if (!reply) return;
    reply.status = data.status;
    reply.text = data.text || '';
    reply.timestamp = data.timestamp || reply.timestamp;
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

  // Message refusé (VS Code absent, réponse en cours) : la raison, comme une réponse
  function applyError(data) {
    sending = false;
    if (sentText && !el.input.value) {
      el.input.value = sentText;
      autoResize();
    }
    sentText = '';
    hideWelcome();
    var msg = document.createElement('div');
    msg.className = 'message ai';
    msg.innerHTML =
      '<div class="ai-icon">' + core().robotSvg + '</div>' +
      '<div class="bubble" dir="auto">' + core().escapeHtml(data.message || '') +
      '<span class="time">' + core().formatTime(new Date()) + '</span></div>';
    el.messages.appendChild(msg);
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

  // Question : sa provenance si elle n'a pas été tapée sur ce téléphone
  function renderUser(message) {
    var lines = [message.text || ''].concat((message.attachments || []).map(function (name) {
      return '📎 ' + name;
    })).filter(function (line) { return line; });
    var origin = message.origin === 'vscode' ? T('code.origin.vscode')
      : message.origin === 'desktop' ? T('code.origin.desktop') : '';
    var msg = document.createElement('div');
    msg.className = 'message user' + (origin ? ' with-origin' : '');
    msg.innerHTML =
      (origin ? '<span class="code-origin">' + core().escapeHtml(origin) + '</span>' : '') +
      '<div class="bubble" dir="auto">' + core().escapeHtml(lines.join('\n')) +
      '<span class="time">' + timeOf(message.timestamp) + '</span></div>';
    el.messages.appendChild(msg);
  }

  // Réponse entière : ses morceaux dans l'ordre, puis l'attente, l'arrêt ou l'erreur
  function renderReply(reply) {
    var turn = turns[reply.message_id];
    if (!turn) {
      turn = { box: document.createElement('div'), parts: {}, tail: null };
      turn.box.className = 'code-turn';
      el.messages.appendChild(turn.box);
      turns[reply.message_id] = turn;
    }
    var shown = turn.parts;
    turn.box.innerHTML = '';
    turn.parts = {};
    turn.tail = null;
    reply.parts.forEach(function (part) { renderPart(reply, part, !!shown[partKey(part)]); });
    var hasText = reply.parts.some(function (p) { return p.kind === 'text'; });
    if (reply.status === 'done' && !hasText && reply.text) {
      turn.box.appendChild(textBubble(reply.text, reply.timestamp, false));
    } else if (reply.status === 'error' && reply.text) {
      turn.box.appendChild(textBubble(reply.text, reply.timestamp, false));
    } else if (reply.status === 'stopped') {
      var stopped = document.createElement('div');
      stopped.className = 'code-stopped';
      stopped.textContent = '⏹️ ' + T('code.stopped');
      turn.box.appendChild(stopped);
    }
    renderTail(reply);
  }

  function partKey(part) {
    return part.kind === 'text' ? 't' + part.segment : 'x' + part.call_id;
  }

  // shown : déjà à l'écran avant que la réponse ne soit refaite
  function renderPart(reply, part, shown) {
    var turn = turns[reply.message_id];
    if (!turn) return;
    var key = partKey(part);
    var streaming = reply.status === 'streaming';
    var previous = turn.parts[key];
    // Texte qui s'écrit : seul son contenu change, la bulle reste
    if (!(part.kind === 'text' && streaming && previous && fillStream(previous, part.text))) {
      var node = part.kind === 'text'
        ? textBubble(part.text, reply.timestamp, streaming)
        : toolRow(part);
      // Une bulle remplacée ne rejoue pas son apparition (fadeIn)
      if (previous || shown) node.classList.add('no-fade');
      if (previous) {
        turn.box.replaceChild(node, previous);
      } else if (turn.tail && turn.tail.parentNode === turn.box) {
        turn.box.insertBefore(node, turn.tail);
      } else {
        turn.box.appendChild(node);
      }
      turn.parts[key] = node;
    }
    // Le morceau précédent ne s'écrit plus : son curseur disparaît
    reply.parts.forEach(function (other) {
      if (other !== part && other.kind === 'text' && turn.parts[partKey(other)]) {
        var cursor = turn.parts[partKey(other)].querySelector('.stream-cursor');
        if (cursor) cursor.remove();
      }
    });
    renderTail(reply);
  }

  // Réponse en cours sans rien qui bouge à l'écran : les trois points du chat
  function renderTail(reply) {
    var turn = turns[reply.message_id];
    if (!turn) return;
    var last = reply.parts[reply.parts.length - 1];
    var waiting = reply.status === 'streaming'
      && (!last || (last.kind === 'tool' && !OPEN_STATUSES[last.status]));
    if (waiting && !turn.tail) {
      turn.tail = document.createElement('div');
      turn.tail.className = 'message ai';
      turn.tail.innerHTML =
        '<div class="ai-icon">' + core().robotSvg + '</div>' +
        '<div class="bubble"><div class="typing-indicator">' +
        '<div class="typing-dot"></div><div class="typing-dot"></div><div class="typing-dot"></div>' +
        '</div></div>';
      turn.box.appendChild(turn.tail);
    } else if (!waiting && turn.tail) {
      turn.tail.remove();
      turn.tail = null;
    }
  }

  function textBubble(text, timestamp, streaming) {
    var msg = document.createElement('div');
    msg.className = 'message ai' + (streaming ? ' streaming' : '');
    var body = core().renderMarkdown(streaming ? core().balanceMarkdownForStreaming(text) : text);
    msg.innerHTML =
      '<div class="ai-icon">' + core().robotSvg + '</div>' +
      '<div class="bubble" dir="auto">' +
      (streaming
        ? '<div class="stream-content">' + body + '</div><span class="stream-cursor"></span>'
        : body + '<span class="time">' + timeOf(timestamp) + '</span>') +
      '</div>';
    return msg;
  }

  // Nouveau texte d'une bulle en cours d'écriture (false : bulle déjà finie)
  function fillStream(msg, text) {
    var content = msg.querySelector('.stream-content');
    if (!content) return false;
    content.innerHTML = core().renderMarkdown(core().balanceMarkdownForStreaming(text));
    return true;
  }

  function toolTarget(part) {
    var input = part.input || {};
    var target = part.name === 'run_command' ? input.command
      : (part.name === 'glob' || part.name === 'grep') ? input.pattern
        : (input.path || (part.name === 'list_dir' ? '.' : ''));
    target = String(target || '').replace(/\s+/g, ' ').trim();
    return target.length > 60 ? target.slice(0, 60) + '…' : target;
  }

  function toolStatusText(status) {
    if (status === 'awaiting-approval') return T('code.toolStatus.awaiting');
    if (status === 'failed') return T('code.toolStatus.failed');
    if (status === 'denied') return T('code.toolStatus.denied');
    if (status === 'stopped') return T('code.toolStatus.stopped');
    return '';
  }

  function toolIcon(part) {
    if (part.status === 'requested' || part.status === 'running') return '⏳';
    if (part.status === 'awaiting-approval') return '🔒';
    if (part.status === 'failed') return '⚠️';
    if (part.status === 'denied') return '🚫';
    if (part.status === 'stopped') return '⏹️';
    return TOOL_ICONS[part.name] || '🔧';
  }

  // Appel d'outil : une ligne, son détail au toucher ; les boutons d'approbation
  function toolRow(part) {
    var row = document.createElement('div');
    row.className = 'code-tool ' + (part.status || '');
    var label = TOOL_LABELS[part.name] ? TOOL_LABELS[part.name](toolTarget(part)) : part.name;
    var status = toolStatusText(part.status);
    var head = document.createElement('button');
    head.type = 'button';
    head.className = 'code-tool-head';
    head.innerHTML =
      '<span class="code-tool-icon">' + toolIcon(part) + '</span>' +
      '<span class="code-tool-label">' + core().escapeHtml(label) + '</span>' +
      (status ? '<span class="code-tool-status">' + core().escapeHtml(status) + '</span>' : '');
    row.appendChild(head);

    var details = document.createElement('div');
    details.className = 'code-tool-details';
    details.style.display = 'none';
    var input = part.name === 'run_command' && typeof (part.input || {}).command === 'string'
      ? part.input.command : JSON.stringify(part.input || {}, null, 2);
    details.appendChild(detailBlock(T('code.tool.input'), input));
    if (typeof part.output === 'string') {
      details.appendChild(detailBlock(T('code.tool.output'), part.output || T('code.tool.empty')));
    }
    row.appendChild(details);
    head.addEventListener('click', function () {
      details.style.display = details.style.display === 'none' ? 'block' : 'none';
    });

    if (part.status === 'awaiting-approval') {
      var options = Array.isArray(part.options) ? part.options : [];
      var box = document.createElement('div');
      box.className = 'code-approval';
      var prompt = document.createElement('div');
      prompt.className = 'code-approval-prompt';
      prompt.textContent = options.length ? T('code.approval.prompt') : T('code.approval.inVscode');
      box.appendChild(prompt);
      options.forEach(function (decision, index) {
        if (!APPROVALS[decision]) return;
        var btn = document.createElement('button');
        btn.type = 'button';
        btn.className = 'code-approval-btn' + (index === 0 ? ' primary' : '') +
          (decision === 'deny' ? ' deny' : '');
        btn.textContent = APPROVALS[decision](part.name);
        btn.addEventListener('click', function () {
          box.querySelectorAll('button').forEach(function (b) { b.disabled = true; });
          core().send({ type: 'code_approve', call_id: part.call_id, decision: decision });
        });
        box.appendChild(btn);
      });
      row.appendChild(box);
    }
    return row;
  }

  function detailBlock(label, text) {
    var block = document.createElement('div');
    block.className = 'code-tool-block';
    var title = document.createElement('div');
    title.className = 'code-tool-block-label';
    title.textContent = label;
    var pre = document.createElement('pre');
    pre.dir = 'ltr';
    pre.textContent = text;
    block.appendChild(title);
    block.appendChild(pre);
    return block;
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
    var entry = {
      localId: 'code_att_' + (++attachmentCounter), fileId: null, name: file.name || 'file',
      isImage: /^image\//i.test(file.type), status: 'uploading', error: null,
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
      var name = document.createElement('span');
      name.className = 'chip-name';
      name.textContent = a.status === 'error' ? a.name + ' · ' + (a.error || T('attach.error')) : a.name;
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
