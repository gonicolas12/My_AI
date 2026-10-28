/* ═══════════════════════════════════════════════════ */
/* My_AI Relay — VS Code Webview                       */
/* All wire-protocol/E2EE happens in the extension; the */
/* webview just renders messages and posts user intent. */
/* ═══════════════════════════════════════════════════ */

(function () {
  'use strict';
  const vscode = acquireVsCodeApi();

  // Logo de My_AI (le robot de l'appli, de la barre d'activité et du Marketplace)
  const ROBOT_SVG =
    '<svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">' +
    '<circle cx="7" cy="1.5" r="1"/><rect x="6.6" y="2.4" width="0.8" height="2.8" rx="0.4"/>' +
    '<circle cx="17" cy="1.5" r="1"/><rect x="16.6" y="2.4" width="0.8" height="2.8" rx="0.4"/>' +
    '<path fill-rule="evenodd" d="M5 4.5H19A4 4 0 0 1 23 8.5V18A4 4 0 0 1 19 22H5A4 4 0 0 1 1 18V8.5A4 4 0 0 1 5 4.5Z' +
    'M6.25 9.25H8.75A1.25 1.25 0 0 1 10 10.5V12A1.25 1.25 0 0 1 8.75 13.25H6.25A1.25 1.25 0 0 1 5 12V10.5A1.25 1.25 0 0 1 6.25 9.25Z' +
    'M15.25 9.25H17.75A1.25 1.25 0 0 1 19 10.5V12A1.25 1.25 0 0 1 17.75 13.25H15.25A1.25 1.25 0 0 1 14 12V10.5A1.25 1.25 0 0 1 15.25 9.25Z' +
    'M9 15.75H15A1 1 0 0 1 15 17.75H9A1 1 0 0 1 9 15.75Z"/></svg>';

  // ── DOM ──────────────────────────────────────────────
  const statusDot = document.getElementById('statusDot');
  const statusText = document.getElementById('statusText');
  const connBanner = document.getElementById('connBanner');
  const connectScreen = document.getElementById('connectScreen');
  const connectBtn = document.getElementById('connectBtn');
  const messagesEl = document.getElementById('messages');
  const inputArea = document.getElementById('inputArea');
  const welcomeEl = document.getElementById('welcome');
  const inputEl = document.getElementById('messageInput');
  const sendBtn = document.getElementById('sendBtn');
  const attachBtn = document.getElementById('attachBtn');
  const attachmentsEl = document.getElementById('attachments');
  const clearBtn = document.getElementById('clearBtn');
  const reconnectBtn = document.getElementById('reconnectBtn');
  const attachToggleBtn = document.getElementById('attachToggleBtn');
  const attachToggleLabel = document.getElementById('attachToggleLabel');

  // ── STATE ────────────────────────────────────────────
  let isConnected = false;
  let isWaiting = false;
  let typingEl = null;
  let lastSentMessageId = null;
  const renderedMessageIds = new Set();
  // Réponses closes (reçues en entier, ou arrêtées par Stop) : leurs chunks
  // tardifs sont ignorés. Clear garde cet ensemble, contrairement à
  // renderedMessageIds : l'hôte peut encore envoyer quelques chunks après un
  // Stop, et ils ne doivent pas s'écrire dans le chat vidé.
  const closedMessageIds = new Set();
  // Stop demandé pour la réponse attendue (son id peut n'arriver qu'avec l'ack).
  let stopRequested = false;
  // Clear pendant une génération : la fin de cette réponse n'affiche plus rien.
  let discardingReply = false;
  let pendingAttachments = [];
  let attachmentCounter = 0;
  let streamingMessageId = null;
  let streamingMessageEl = null;
  // Bibliothèque de prompts (slash commands) + état du menu d'autocomplétion.
  let slashPrompts = [];
  let slashItems = [];
  let slashIndex = 0;
  let slashMenuOpen = false;
  let slashMenuEl = null;
  // Mentions « @ » : attache un fichier ou un dossier du workspace VS Code.
  let mentionItems = [];
  let mentionIndex = 0;
  let mentionMenuOpen = false;
  let mentionMenuEl = null;
  let mentionQuery = null;       // requête « @… » courante (null = menu fermé)
  let mentionDebounce = null;
  // Mode du bouton d'envoi : 'send' (avion) ou 'stop' (carré) pendant la génération.
  let sendBtnMode = 'send';
  // Index du segment en cours pour le message en streaming. Un segment =
  // une passe LLM entre deux exécutions d'outils (mode VS Code agentique).
  // À chaque nouveau segment_index reçu dans un chunk, on "fige" la bulle
  // courante et on en crée une nouvelle, ce qui permet aux cartes d'outils
  // (insérées entre-temps via tool-event) d'apparaître inline, dans l'ordre.
  // null tant qu'aucun chunk n'a été reçu.
  let streamingSegmentIndex = null;
  let userPinnedToBottom = true;
  let autoAttachActive = false;
  // Map call_id → DOM node for the tool card. Used by tool-event handlers
  // to update the card's status and output as the agentic loop progresses.
  const toolCardEls = new Map();
  // Last event of each tool card: its texts follow a change of language.
  const toolCardEvents = new Map();
  // Message typed here, sent, not yet acknowledged by the host: its bubble is
  // already shown (a message sent by a command — selection, active file — is
  // shown when its ack arrives).
  let pendingLocalSend = false;
  // The host shares this conversation with the Code page of My_AI and the phone.
  let sharedConversation = false;
  // Locale of the times (My_AI's language), given with the strings.
  let timeLocale;

  // Localized strings injected by the extension on startup, in My_AI's
  // language. The webview renders nothing visible until applyStrings()
  // runs, so the user never sees raw English placeholders.
  let STR = {};
  function t(key) { return (STR && STR[key]) || key; }

  // Language of the page: direction (Arabic is written right to left) and
  // locale of the times. Sent with the strings, again when it changes.
  function applyLanguage(lang, dir, locale) {
    if (lang) document.documentElement.lang = lang;
    document.documentElement.dir = dir === 'rtl' ? 'rtl' : 'ltr';
    timeLocale = locale || undefined;
  }

  function applyStrings(strings) {
    STR = strings || {};
    // Static UI elements that never change after init.
    document.getElementById('connBanner').textContent = t('webview.banner.connectionLost');
    document.getElementById('connectTitle').textContent = t('webview.connect.title');
    document.getElementById('connectDescription').textContent = t('webview.connect.description');
    document.getElementById('connectBtn').textContent = t('webview.connect.button');
    document.getElementById('connectHint').textContent = t('webview.connect.hint');
    document.getElementById('welcomeTitle').textContent = t('webview.welcome.title');
    document.getElementById('welcomeText').textContent = t('webview.welcome.text');
    document.getElementById('welcomeShared').textContent = t('webview.welcome.shared');
    document.getElementById('clearBtn').textContent = t('webview.header.clear');
    document.getElementById('clearBtn').title = t('webview.header.clearTooltip');
    document.getElementById('reconnectBtn').textContent = t('webview.header.reconnect');
    document.getElementById('reconnectBtn').title = t('webview.header.reconnectTooltip');
    document.getElementById('attachToggleBtn').title = t('webview.header.autoAttachTooltip');
    document.getElementById('attachBtn').title = t('webview.input.attachTooltip');
    inputEl.placeholder = t('webview.input.placeholder');
    renderAutoAttachToggle();
    if (sendBtnMode === 'stop') sendBtn.title = t('webview.send.stopTooltip');
    // Texts already on screen: tool cards and code block buttons
    toolCardEls.forEach((card, callId) => {
      const event = toolCardEvents.get(callId);
      if (event) updateToolCard(card, event);
      card.querySelectorAll('.tool-card-section-label').forEach((label) => {
        label.textContent = t(label.dataset.label);
      });
    });
    messagesEl.querySelectorAll('.code-action').forEach((btn) => {
      btn.textContent = t(btn.dataset.action === 'insert' ? 'webview.code.insert' : 'webview.code.copy');
    });
    messagesEl.querySelectorAll('.origin-label').forEach((label) => {
      label.textContent = originText(label.dataset.origin);
    });
  }

  // ── EVENT WIRING ─────────────────────────────────────
  connectBtn.addEventListener('click', () => {
    vscode.postMessage({ type: 'connect-request' });
  });

  sendBtn.addEventListener('click', () => {
    if (sendBtnMode === 'stop') {
      stopGeneration();
    } else {
      sendMessage();
    }
  });
  attachBtn.addEventListener('click', () => vscode.postMessage({ type: 'pick-file' }));
  // New conversation, also on the Code page of My_AI and on the phone: the view
  // clears when the host says so (code_cleared), or by itself (clear-local)
  clearBtn.addEventListener('click', () => vscode.postMessage({ type: 'clear-chat' }));
  reconnectBtn.addEventListener('click', () =>
    vscode.postMessage({ type: 'connect-request' }),
  );

  attachToggleBtn.addEventListener('click', () => {
    autoAttachActive = !autoAttachActive;
    renderAutoAttachToggle();
    vscode.postMessage({ type: 'set-auto-attach', value: autoAttachActive });
  });

  inputEl.addEventListener('input', () => {
    autoResize();
    updateSendButton();
    updateSlashMenu();
    updateMentionMenu();
  });

  inputEl.addEventListener('blur', () => {
    // Léger délai : laisse le mousedown d'une ligne s'exécuter avant de fermer.
    setTimeout(() => { hideSlashMenu(); hideMentionMenu(); }, 150);
  });

  inputEl.addEventListener('keydown', (e) => {
    if (mentionMenuOpen) {
      if (e.key === 'ArrowDown') { e.preventDefault(); mentionMove(1); return; }
      if (e.key === 'ArrowUp') { e.preventDefault(); mentionMove(-1); return; }
      if (e.key === 'Enter' || e.key === 'Tab') {
        e.preventDefault();
        if (mentionItems[mentionIndex]) mentionAccept(mentionItems[mentionIndex]);
        return;
      }
      if (e.key === 'Escape') { e.preventDefault(); hideMentionMenu(); return; }
    }
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

  messagesEl.addEventListener('scroll', () => {
    const gap = messagesEl.scrollHeight - (messagesEl.scrollTop + messagesEl.clientHeight);
    userPinnedToBottom = gap < 80;
  }, { passive: true });

  // Capture clicks on injected code-action buttons (event delegation).
  messagesEl.addEventListener('click', (e) => {
    const target = e.target;
    if (!(target instanceof HTMLElement)) return;
    if (target.classList.contains('code-action')) {
      const action = target.dataset.action;
      const wrapper = target.closest('.code-block-wrapper');
      const pre = wrapper && wrapper.querySelector('pre code');
      if (!pre) return;
      const code = pre.textContent || '';
      if (action === 'insert') {
        vscode.postMessage({ type: 'insert-at-cursor', code });
        flashAction(target, t('webview.code.inserted'));
      } else if (action === 'copy') {
        vscode.postMessage({ type: 'copy-to-clipboard', text: code });
        flashAction(target, t('webview.code.copied'));
      }
    }
  });

  function flashAction(btn, label) {
    const orig = btn.textContent;
    btn.textContent = label;
    setTimeout(() => { btn.textContent = orig; }, 1200);
  }

  // ── EXTENSION → WEBVIEW MESSAGES ─────────────────────
  window.addEventListener('message', (event) => {
    const msg = event.data;
    if (!msg || typeof msg !== 'object') return;
    switch (msg.type) {
      case 'init-strings':
        applyLanguage(msg.lang, msg.dir, msg.locale);
        applyStrings(msg.strings);
        break;
      case 'state':
        sharedConversation = !!msg.shared;
        document.getElementById('welcomeShared').style.display = sharedConversation ? 'block' : 'none';
        applyState(msg.state, msg.hasCredentials);
        break;
      case 'clear-local':
        clearChat();
        break;
      case 'send-failed':
        // Never left VS Code: no reply to wait for
        pendingLocalSend = false;
        isWaiting = false;
        removeTyping();
        updateSendButton();
        break;
      case 'prompts':
        slashPrompts = Array.isArray(msg.items) ? msg.items : [];
        break;
      case 'mention-results':
        applyMentionResults(msg.query, Array.isArray(msg.items) ? msg.items : []);
        break;
      case 'relay-message':
        applyRelayMessage(msg.payload);
        break;
      case 'attachment-uploading':
        addAttachmentChip(msg.localId, msg.name, msg.isImage, 'uploading');
        break;
      case 'attachment-ready':
        markAttachmentReady(msg.localId, msg.fileId, msg.filename, msg.isImage);
        break;
      case 'attachment-error':
        markAttachmentError(msg.localId, msg.error);
        break;
      case 'cleared-attachments':
        pendingAttachments = [];
        renderAttachments();
        updateSendButton();
        break;
      case 'auto-attach-state':
        autoAttachActive = !!msg.value;
        renderAutoAttachToggle();
        break;
      case 'tool-event':
        applyToolEvent(msg.event);
        break;
    }
  });

  // ── TOOL CARDS (agentic mode) ────────────────────────
  function applyToolEvent(event) {
    if (!event || !event.callId || discardingReply) return;
    let card = toolCardEls.get(event.callId);
    if (!card) {
      // Une carte naît de l'événement « requested » de son appel : un outil
      // encore en cours au moment d'un Clear ne la recrée pas dans le chat vidé.
      if (event.kind !== 'requested') return;
      if (welcomeEl) welcomeEl.style.display = 'none';
      card = createToolCard(event);
      // Append at the bottom : la carte arrive APRÈS le segment de texte
      // qui l'a déclenchée (segment N), et AVANT le segment de texte qui
      // intègre son résultat (segment N+1, créé plus tard quand le LLM
      // recommence à streamer). Si la bulle de streaming est encore là,
      // c'est qu'elle est le dernier élément → appendChild la place après.
      messagesEl.appendChild(card);
      toolCardEls.set(event.callId, card);
      // Drop the typing indicator: the agent is clearly working.
      removeTyping();
    }
    updateToolCard(card, event);
    scrollToBottomStream();
  }

  function createToolCard(event) {
    const card = document.createElement('div');
    card.className = 'tool-card';
    card.dataset.callId = event.callId;
    card.dataset.tool = event.toolName || 'tool';
    card.innerHTML =
      '<div class="tool-card-header" role="button" tabindex="0">' +
        '<span class="tool-card-icon"></span>' +
        '<span class="tool-card-title"></span>' +
        '<span class="tool-card-status"></span>' +
        '<span class="tool-card-chev">▾</span>' +
      '</div>' +
      '<div class="tool-card-body">' +
        '<div class="tool-card-section tool-card-input">' +
          '<div class="tool-card-section-label" data-label="webview.tool.input"></div>' +
          '<pre class="tool-card-pre"></pre>' +
        '</div>' +
        '<div class="tool-card-section tool-card-output" style="display:none">' +
          '<div class="tool-card-section-label" data-label="webview.tool.output"></div>' +
          '<pre class="tool-card-pre"></pre>' +
        '</div>' +
      '</div>';
    card.querySelectorAll('.tool-card-section-label').forEach((label) => {
      label.textContent = t(label.dataset.label);
    });

    const header = card.querySelector('.tool-card-header');
    const body = card.querySelector('.tool-card-body');
    body.style.display = 'none';
    header.addEventListener('click', () => {
      const open = body.style.display !== 'none';
      body.style.display = open ? 'none' : 'block';
      card.classList.toggle('open', !open);
    });
    header.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        header.click();
      }
    });

    return card;
  }

  function updateToolCard(card, event) {
    const titleEl = card.querySelector('.tool-card-title');
    const iconEl = card.querySelector('.tool-card-icon');
    const statusEl = card.querySelector('.tool-card-status');
    const inputPre = card.querySelector('.tool-card-input .tool-card-pre');
    const outputSection = card.querySelector('.tool-card-output');
    const outputPre = card.querySelector('.tool-card-output .tool-card-pre');

    titleEl.textContent = describeToolTitle(event.toolName, event.input);
    toolCardEvents.set(event.callId, event);

    let icon = '';
    let statusLabel = '';
    let cls = '';
    switch (event.kind) {
      case 'requested':
      case 'running':
        icon = '⏳';
        statusLabel = t('webview.tool.running');
        cls = 'running';
        break;
      case 'awaiting-approval':
        icon = '🔒';
        statusLabel = t('webview.tool.awaiting');
        cls = 'awaiting';
        break;
      case 'denied':
        icon = '🚫';
        statusLabel = t('webview.tool.denied');
        cls = 'denied';
        break;
      case 'completed':
        icon = '✓';
        statusLabel = t('webview.tool.completed');
        cls = 'ok';
        break;
      case 'failed':
        icon = '⚠️';
        statusLabel = t('webview.tool.failed');
        cls = 'error';
        break;
      case 'stopped':
        icon = '⏹';
        statusLabel = t('webview.tool.stopped');
        cls = 'stopped';
        break;
      default:
        icon = '·';
    }
    iconEl.textContent = icon;
    statusEl.textContent = statusLabel;
    card.classList.remove('running', 'awaiting', 'denied', 'ok', 'error', 'stopped');
    if (cls) card.classList.add(cls);

    inputPre.textContent = formatToolInput(event.input);

    if (event.result || event.error) {
      const text = event.result ? event.result.content : (event.error || '');
      outputPre.textContent = text || t('webview.tool.empty');
      outputSection.style.display = 'block';
    }
    renderApproval(card, event);
  }

  // Approval of a message typed on the PC or the phone: buttons in the card,
  // also on the Code page of My_AI and on the phone; the first answer counts.
  function renderApproval(card, event) {
    let row = card.querySelector('.tool-approval');
    const options = event.kind === 'awaiting-approval' && Array.isArray(event.options)
      ? event.options : [];
    if (!options.length) {
      if (row) row.remove();
      return;
    }
    if (!row) {
      row = document.createElement('div');
      row.className = 'tool-approval';
      card.appendChild(row);
    }
    row.innerHTML = '';
    const prompt = document.createElement('div');
    prompt.className = 'tool-approval-prompt';
    prompt.textContent = t('webview.approval.prompt');
    row.appendChild(prompt);
    options.forEach((decision, index) => {
      const btn = document.createElement('button');
      btn.type = 'button';
      btn.className = 'approval-btn' + (index === 0 ? ' primary' : '')
        + (decision === 'deny' ? ' deny' : '');
      btn.textContent = t('webview.approval.' + decision).replace('{0}', event.toolName || '');
      btn.addEventListener('click', () => {
        row.querySelectorAll('button').forEach((b) => { b.disabled = true; });
        vscode.postMessage({ type: 'approve-tool', callId: event.callId, decision });
      });
      row.appendChild(btn);
    });
  }

  // Tool call of the conversation's state (code_snapshot) as a card event
  function toolEventFromPart(part) {
    const event = {
      kind: part.status || 'requested',
      callId: part.call_id,
      toolName: part.name,
      input: part.input || {},
      options: part.options,
    };
    if (typeof part.output === 'string') event.result = { content: part.output };
    return event;
  }

  function describeToolTitle(name, input) {
    name = name || 'tool';
    if (!input || typeof input !== 'object') return name;
    if (typeof input.path === 'string' && input.path) {
      return name + '(' + input.path + ')';
    }
    if (typeof input.command === 'string' && input.command) {
      const c = input.command;
      return name + ': ' + (c.length > 60 ? c.slice(0, 60) + '…' : c);
    }
    if (typeof input.pattern === 'string' && input.pattern) {
      return name + ' /' + input.pattern + '/';
    }
    return name;
  }

  function formatToolInput(input) {
    if (!input || typeof input !== 'object') return '{}';
    try {
      return JSON.stringify(input, null, 2);
    } catch (_e) {
      return String(input);
    }
  }

  function applyState(state, hasCredentials) {
    const kind = state && state.kind;
    if (kind === 'connected') {
      isConnected = true;
      setStatus('connected', t('webview.status.connected'));
      connBanner.classList.remove('visible');
      showConnectedUI();
    } else if (kind === 'connecting') {
      isConnected = false;
      setStatus('connecting', t('webview.status.connecting'));
      showConnectedUI();
    } else if (kind === 'reconnecting') {
      isConnected = false;
      setStatus('connecting', t('webview.status.reconnecting'));
      connBanner.classList.add('visible');
      showConnectedUI();
    } else {
      // idle | disconnected
      isConnected = false;
      const reason = (state && state.reason)
        || (hasCredentials ? t('webview.status.disconnected') : t('webview.status.notConnected'));
      setStatus('offline', reason);
      if (hasCredentials) {
        connBanner.classList.add('visible');
        showConnectedUI();
      } else {
        showConnectScreen();
      }
    }
    updateSendButton();
  }

  function showConnectScreen() {
    connectScreen.style.display = 'flex';
    messagesEl.style.display = 'none';
    inputArea.style.display = 'none';
  }

  function showConnectedUI() {
    connectScreen.style.display = 'none';
    messagesEl.style.display = 'block';
    inputArea.style.display = 'block';
  }

  // ── CODE CONVERSATION (shared with My_AI on the PC and the phone) ──
  // The host's full state (connection, view reloaded): it replaces the view.
  function applySnapshot(messages, state) {
    removeTyping();
    Array.from(messagesEl.children).forEach((c) => {
      if (c !== welcomeEl) c.remove();
    });
    renderedMessageIds.clear();
    toolCardEls.clear();
    toolCardEvents.clear();
    streamingMessageId = null;
    streamingMessageEl = null;
    streamingSegmentIndex = null;
    pendingLocalSend = false;
    discardingReply = false;
    const list = Array.isArray(messages) ? messages : [];
    list.forEach(renderStoredMessage);
    if (welcomeEl) welcomeEl.style.display = list.length ? 'none' : 'flex';
    applyCodeState(state);
    scrollToBottom();
  }

  function renderStoredMessage(m) {
    if (!m || !m.message_id) return;
    const mid = m.message_id;
    if (m.role === 'user') {
      renderedMessageIds.add('user:' + mid);
      addMessage(userDisplayText(m.text, m.attachments), true, m.timestamp, m.origin);
      return;
    }
    const parts = Array.isArray(m.parts) ? m.parts : [];
    const streaming = m.status === 'streaming';
    const last = parts[parts.length - 1];
    let hasText = false;
    parts.forEach((part) => {
      if (!part) return;
      if (part.kind === 'tool') {
        const event = toolEventFromPart(part);
        const card = createToolCard(event);
        messagesEl.appendChild(card);
        toolCardEls.set(part.call_id, card);
        updateToolCard(card, event);
      } else if (part.kind === 'text' && part.text) {
        hasText = true;
        if (streaming && part === last) {
          // Reply in progress: its next chunks continue this bubble
          updateStreamingBubble(mid, part.text, part.segment);
        } else {
          addMessage(part.text, false, m.timestamp);
        }
      }
    });
    if (streaming) {
      if (!last || last.kind !== 'text') {
        // Tools at work: the next chunk opens a new bubble below them
        streamingMessageId = mid;
        streamingSegmentIndex = null;
        streamingMessageEl = null;
      }
      return;
    }
    renderedMessageIds.add('ai:' + mid);
    closedMessageIds.add(mid);
    // Reply without streamed text, or the reason of its failure
    if (m.text && (!hasText || m.status === 'error')) addMessage(m.text, false, m.timestamp);
  }

  // Reply in progress or not, wherever its message was typed: the send button
  // becomes Stop while My_AI works, here as on the PC and the phone.
  function applyCodeState(state) {
    if (!state || typeof state !== 'object') return;
    if (state.busy) {
      isWaiting = true;
      if (state.message_id) lastSentMessageId = state.message_id;
    } else if (!pendingLocalSend) {
      isWaiting = false;
      stopRequested = false;
      removeTyping();
    }
    updateSendButton();
  }

  // Message typed on the Code page of My_AI or on the phone
  function applyRemoteUser(data) {
    const mid = data.message_id || '';
    if (!mid || renderedMessageIds.has('user:' + mid)) return;
    renderedMessageIds.add('user:' + mid);
    userPinnedToBottom = true;
    addMessage(userDisplayText(data.text, data.attachments), true, data.timestamp, data.origin);
    lastSentMessageId = mid;
    isWaiting = true;
    showTyping();
    updateSendButton();
  }

  // New conversation (Clear here, on the PC or on the phone)
  function resetConversation() {
    removeTyping();
    Array.from(messagesEl.children).forEach((c) => {
      if (c !== welcomeEl) c.remove();
    });
    if (welcomeEl) welcomeEl.style.display = 'flex';
    renderedMessageIds.clear();
    toolCardEls.clear();
    toolCardEvents.clear();
    streamingMessageId = null;
    streamingMessageEl = null;
    streamingSegmentIndex = null;
    isWaiting = false;
    stopRequested = false;
    discardingReply = false;
    pendingLocalSend = false;
    lastSentMessageId = null;
    updateSendButton();
  }

  function userDisplayText(text, attachments) {
    const lines = (Array.isArray(attachments) ? attachments : []).map((name) => '📎 ' + name);
    return [text || ''].concat(lines).filter((line) => line).join('\n');
  }

  function originText(origin) {
    return origin === 'desktop' || origin === 'mobile' ? t('webview.origin.' + origin) : '';
  }

  function applyRelayMessage(data) {
    if (!data || typeof data !== 'object') return;

    if (data.type === 'code_snapshot') {
      applySnapshot(data.messages, data.state);
    } else if (data.type === 'code_state') {
      applyCodeState(data);
    } else if (data.type === 'code_user') {
      applyRemoteUser(data);
    } else if (data.type === 'code_cleared') {
      resetConversation();
    } else if (data.type === 'response') {
      const mid = data.message_id || '';
      if (mid) closedMessageIds.add(mid);
      // Refused by the host (empty id): the message typed here got no reply
      pendingLocalSend = false;
      if (discardingReply) {
        // Fin de la réponse arrêtée par Clear : on rend le bouton d'envoi
        // sans rien afficher dans le chat vidé.
        if (mid) renderedMessageIds.add('ai:' + mid);
        discardingReply = false;
        stopRequested = false;
        isWaiting = false;
        lastSentMessageId = null;
        updateSendButton();
        return;
      }
      if (mid && renderedMessageIds.has('ai:' + mid)) {
        if (streamingMessageId === mid) finalizeStreaming(mid, null, null);
        return;
      }
      if (mid) renderedMessageIds.add('ai:' + mid);
      removeTyping();
      isWaiting = false;
      stopRequested = false;
      if (mid && mid === lastSentMessageId) lastSentMessageId = null;
      const streamed = mid && streamingMessageId === mid && streamingMessageEl
        && streamingMessageEl.querySelector('.stream-content').textContent.trim();
      if (data.status === 'error' && streamed) {
        // Failure after some text: the text stays, the reason follows it
        finalizeStreaming(mid, null, data.timestamp);
        addMessage(data.message || '', false, data.timestamp);
      } else {
        finalizeStreaming(mid, data.message, data.timestamp);
      }
      updateSendButton();
    } else if (data.type === 'chunk') {
      const cmid = data.message_id || '';
      if (!cmid || discardingReply || closedMessageIds.has(cmid)) return;
      if (renderedMessageIds.has('ai:' + cmid)) return;
      removeTyping();
      // segment_index : optionnel (ancien protocole = pas de segments).
      // Si absent, on traite tout comme segment 0.
      const seg = (typeof data.segment_index === 'number') ? data.segment_index : 0;
      updateStreamingBubble(cmid, data.text || '', seg);
    } else if (data.type === 'ack') {
      if (data.message_id) {
        lastSentMessageId = data.message_id;
        if (!pendingLocalSend && typeof data.text === 'string'
          && !renderedMessageIds.has('user:' + data.message_id)) {
          // Sent by a command (selection, active file), not typed here
          userPinnedToBottom = true;
          addMessage(userDisplayText(data.text, data.attachments), true, data.timestamp);
          isWaiting = true;
          showTyping();
          updateSendButton();
        }
        pendingLocalSend = false;
        renderedMessageIds.add('user:' + data.message_id);
        // Stop cliqué avant cet ack : la réponse est déjà arrêtée.
        if (stopRequested) closedMessageIds.add(data.message_id);
      }
    }
  }

  // ── INPUT/SEND ───────────────────────────────────────
  function sendMessage() {
    const text = inputEl.value.trim();
    const ready = pendingAttachments.filter((a) => a.status === 'ready');
    const hasAttachments = ready.length > 0;
    if ((!text && !hasAttachments) || !isConnected || isWaiting) return;

    const uploading = pendingAttachments.some((a) => a.status === 'uploading');
    if (uploading) return;

    if (welcomeEl) welcomeEl.style.display = 'none';

    let displayText = text;
    if (hasAttachments) {
      const lines = ready.map((a) => (a.isImage ? '🖼️ ' : '📎 ') + a.name).join('\n');
      displayText = displayText ? text + '\n' + lines : lines;
    }

    userPinnedToBottom = true;
    addMessage(displayText, true);

    pendingLocalSend = true;
    vscode.postMessage({
      type: 'send-chat',
      text,
      fileIds: ready.map((a) => a.fileId),
    });

    isWaiting = true;
    showTyping();

    inputEl.value = '';
    autoResize();
    pendingAttachments = [];
    renderAttachments();
    updateSendButton();
    scrollToBottom();
  }

  // Icônes du bouton d'envoi : avion en papier (envoi) / carré (stop), identiques
  // au bouton STOP du chat mobile (My_AI Relay).
  const SEND_ICON_HTML =
    '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">' +
    '<line x1="22" y1="2" x2="11" y2="13"></line>' +
    '<polygon points="22 2 15 22 11 13 2 9 22 2"></polygon></svg>';
  const STOP_ICON_HTML =
    '<svg viewBox="0 0 24 24"><rect x="6" y="6" width="12" height="12" rx="2" fill="currentColor"></rect></svg>';

  function setSendBtnMode(mode) {
    if (sendBtnMode === mode) return;
    sendBtnMode = mode;
    if (mode === 'stop') {
      sendBtn.classList.add('stopmode');
      sendBtn.innerHTML = STOP_ICON_HTML;
      sendBtn.title = t('webview.send.stopTooltip');
    } else {
      sendBtn.classList.remove('stopmode');
      sendBtn.innerHTML = SEND_ICON_HTML;
      sendBtn.title = '';
    }
  }

  // Demande au host d'arrêter la génération en cours (LLM + appels d'outils).
  // Le host annule la tâche agentique et renvoie une réponse « interrompue »,
  // ce qui repasse isWaiting à false (via applyRelayMessage). D'ici là, les
  // chunks encore en route sont ignorés : le texte s'arrête tout de suite.
  function stopGeneration() {
    if (!isWaiting) return;
    stopRequested = true;
    if (lastSentMessageId) closedMessageIds.add(lastSentMessageId);
    vscode.postMessage({ type: 'stop-generation', messageId: lastSentMessageId || '' });
  }

  function updateSendButton() {
    // Pendant la génération, le bouton devient un bouton STOP cliquable
    // (carré noir sur fond blanc), exactement comme sur le chat mobile.
    if (isWaiting) {
      setSendBtnMode('stop');
      sendBtn.disabled = false;
      return;
    }
    setSendBtnMode('send');
    const hasText = !!inputEl.value.trim();
    const hasReady = pendingAttachments.some((a) => a.status === 'ready');
    const uploading = pendingAttachments.some((a) => a.status === 'uploading');
    sendBtn.disabled = !isConnected || uploading || (!hasText && !hasReady);
  }

  function autoResize() {
    inputEl.style.height = 'auto';
    inputEl.style.height = Math.min(inputEl.scrollHeight, 160) + 'px';
  }

  // ── SLASH COMMAND AUTOCOMPLETE ("/" en début de saisie) ──────────────
  function slashNormalize(s) {
    return (s || '').normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase();
  }

  function ensureSlashMenu() {
    if (slashMenuEl) return slashMenuEl;
    slashMenuEl = document.createElement('div');
    slashMenuEl.className = 'slash-menu';
    slashMenuEl.style.display = 'none';
    (inputArea || document.body).appendChild(slashMenuEl);
    return slashMenuEl;
  }

  function hideSlashMenu() {
    slashMenuOpen = false;
    slashItems = [];
    if (slashMenuEl) slashMenuEl.style.display = 'none';
  }

  function updateSlashActive() {
    if (!slashMenuEl) return;
    const rows = slashMenuEl.querySelectorAll('.slash-item');
    rows.forEach((r, i) => {
      r.classList.toggle('active', i === slashIndex);
      if (i === slashIndex && r.scrollIntoView) r.scrollIntoView({ block: 'nearest' });
    });
  }

  function slashMove(delta) {
    if (!slashItems.length) return;
    slashIndex = (slashIndex + delta + slashItems.length) % slashItems.length;
    updateSlashActive();
  }

  function renderSlashMenu() {
    const el = ensureSlashMenu();
    el.innerHTML = '';
    slashItems.forEach((item, i) => {
      const row = document.createElement('div');
      row.className = 'slash-item' + (i === slashIndex ? ' active' : '');

      const cmd = document.createElement('div');
      cmd.className = 'slash-cmd';
      cmd.textContent = '/' + (item.command || '');
      row.appendChild(cmd);

      const sub = (item.title || '') + (item.description ? ' — ' + item.description : '');
      if (sub.trim()) {
        const desc = document.createElement('div');
        desc.className = 'slash-desc';
        desc.textContent = sub;
        row.appendChild(desc);
      }

      // mousedown (et non click) : devance le blur du textarea.
      row.addEventListener('mousedown', (e) => { e.preventDefault(); slashAccept(item); });
      row.addEventListener('mouseenter', () => { slashIndex = i; updateSlashActive(); });
      el.appendChild(row);
    });
  }

  function updateSlashMenu() {
    const m = /^\/(\S*)$/.exec(inputEl.value);
    if (!m || !slashPrompts.length) { hideSlashMenu(); return; }
    const pref = slashNormalize(m[1]);
    slashItems = slashPrompts
      .filter((p) => p.command && slashNormalize(p.command).indexOf(pref) === 0)
      .slice(0, 8);
    if (!slashItems.length) { hideSlashMenu(); return; }
    slashIndex = 0;
    renderSlashMenu();
    ensureSlashMenu().style.display = 'block';
    slashMenuOpen = true;
  }

  function slashAccept(item) {
    // Insère seulement « /commande » ; l'utilisateur tape ensuite son texte.
    // L'expansion en prompt détaillé se fait côté hôte (desktop) à l'envoi.
    inputEl.value = '/' + (item.command || '') + ' ';
    hideSlashMenu();
    inputEl.focus();
    const len = inputEl.value.length;
    try { inputEl.setSelectionRange(len, len); } catch (e) { /* noop */ }
    autoResize();
    updateSendButton();
  }

  // ── MENTION « @ » : attacher un fichier / dossier du workspace ───────────
  // Tapez « @ » suivi d'un terme : un menu propose les fichiers et dossiers du
  // workspace VS Code. Un fichier est joint au prochain message ; un dossier
  // est attaché comme @codebase (indexé côté host).
  const MENTION_RE = /(?:^|\s)@([^\s@]*)$/;

  function ensureMentionMenu() {
    if (mentionMenuEl) return mentionMenuEl;
    mentionMenuEl = document.createElement('div');
    mentionMenuEl.className = 'slash-menu mention-menu';
    mentionMenuEl.style.display = 'none';
    (inputArea || document.body).appendChild(mentionMenuEl);
    return mentionMenuEl;
  }

  function hideMentionMenu() {
    mentionMenuOpen = false;
    mentionItems = [];
    mentionQuery = null;
    if (mentionMenuEl) mentionMenuEl.style.display = 'none';
  }

  function updateMentionActive() {
    if (!mentionMenuEl) return;
    const rows = mentionMenuEl.querySelectorAll('.slash-item');
    rows.forEach((r, i) => {
      r.classList.toggle('active', i === mentionIndex);
      if (i === mentionIndex && r.scrollIntoView) r.scrollIntoView({ block: 'nearest' });
    });
  }

  function mentionMove(delta) {
    if (!mentionItems.length) return;
    mentionIndex = (mentionIndex + delta + mentionItems.length) % mentionItems.length;
    updateMentionActive();
  }

  function mentionIcon(item) {
    if (item.kind === 'folder') return item.action === 'attach' ? '📎 ' : '📁 ';
    return '📄 ';
  }

  function renderMentionMenu() {
    const el = ensureMentionMenu();
    el.innerHTML = '';
    mentionItems.forEach((item, i) => {
      const row = document.createElement('div');
      row.className = 'slash-item' + (i === mentionIndex ? ' active' : '');

      const cmd = document.createElement('div');
      cmd.className = 'slash-cmd';
      // Dossier navigable : suffixe « / » et chevron ; dossier-attache : libellé clair.
      let label = mentionIcon(item) + (item.label || '');
      if (item.kind === 'folder' && item.action === 'attach') {
        label = '📎 ' + (item.label || '') + '  —  ' + t('webview.mention.attachFolder');
      } else if (item.kind === 'folder') {
        label = '📁 ' + (item.label || '') + '/';
      }
      cmd.textContent = label;
      row.appendChild(cmd);

      if (item.detail && item.detail !== item.label) {
        const desc = document.createElement('div');
        desc.className = 'slash-desc';
        desc.textContent = item.detail + (item.kind === 'folder' && item.action !== 'attach' ? '/' : '');
        row.appendChild(desc);
      }

      row.addEventListener('mousedown', (e) => { e.preventDefault(); mentionAccept(item); });
      row.addEventListener('mouseenter', () => { mentionIndex = i; updateMentionActive(); });
      el.appendChild(row);
    });
  }

  // Remplace le token « @… » courant (de « @ » jusqu'au curseur) par newText.
  function replaceMentionToken(newText) {
    const text = inputEl.value;
    const caret = (typeof inputEl.selectionStart === 'number')
      ? inputEl.selectionStart : text.length;
    const before = text.slice(0, caret);
    const after = text.slice(caret);
    const atPos = before.lastIndexOf('@');
    const cut = atPos >= 0 ? atPos : before.length;
    inputEl.value = before.slice(0, cut) + newText + after;
    const pos = cut + newText.length;
    try { inputEl.setSelectionRange(pos, pos); } catch (e) { /* noop */ }
    autoResize();
    updateSendButton();
  }

  function updateMentionMenu() {
    const caret = (typeof inputEl.selectionStart === 'number')
      ? inputEl.selectionStart : inputEl.value.length;
    const before = inputEl.value.slice(0, caret);
    const m = MENTION_RE.exec(before);
    if (!m) { hideMentionMenu(); return; }
    // Slash et mention ne coexistent pas.
    hideSlashMenu();
    mentionQuery = m[1];
    clearTimeout(mentionDebounce);
    mentionDebounce = setTimeout(() => {
      vscode.postMessage({ type: 'mention-query', query: mentionQuery || '' });
    }, 120);
  }

  function applyMentionResults(query, items) {
    // Ignorer les résultats obsolètes (l'utilisateur a continué à taper).
    if (mentionQuery === null || query !== (mentionQuery || '')) return;
    mentionItems = items.slice(0, 20);
    if (!mentionItems.length) { hideMentionMenu(); return; }
    mentionIndex = 0;
    renderMentionMenu();
    ensureMentionMenu().style.display = 'block';
    mentionMenuOpen = true;
  }

  function mentionAccept(item) {
    if (!item) return;
    // Dossier navigable : on ENTRE dedans (insère « @dossier/ » et relance la
    // requête), sans attacher. L'attache se fait via l'entrée « 📎 attacher ce
    // dossier » ou en choisissant un fichier.
    if (item.kind === 'folder' && item.action !== 'attach') {
      replaceMentionToken('@' + (item.detail || item.label) + '/');
      inputEl.focus();
      updateMentionMenu();   // relance la requête sur le nouveau dossier
      return;
    }
    // Fichier ou « attacher ce dossier » : on retire le token et on attache
    // (retour visuel = barre de progression / notification d'indexation côté host).
    replaceMentionToken('');
    hideMentionMenu();
    inputEl.focus();
    if (item.path) {
      vscode.postMessage({
        type: 'attach-mention', kind: item.kind || 'file', path: item.path, name: item.label,
      });
    }
  }

  // ── ATTACHMENT CHIPS ─────────────────────────────────
  function addAttachmentChip(localId, name, isImage, status) {
    pendingAttachments.push({ localId, fileId: null, name, isImage: !!isImage, status, error: null });
    renderAttachments();
    updateSendButton();
  }

  function markAttachmentReady(localId, fileId, filename, isImage) {
    const a = pendingAttachments.find((x) => x.localId === localId);
    if (!a) return;
    a.fileId = fileId;
    a.name = filename || a.name;
    a.isImage = !!isImage;
    a.status = 'ready';
    renderAttachments();
    updateSendButton();
  }

  function markAttachmentError(localId, error) {
    const a = pendingAttachments.find((x) => x.localId === localId);
    if (!a) return;
    a.status = 'error';
    a.error = error || 'Upload failed';
    renderAttachments();
    updateSendButton();
  }

  function removeAttachment(localId) {
    pendingAttachments = pendingAttachments.filter((a) => a.localId !== localId);
    renderAttachments();
    updateSendButton();
    vscode.postMessage({ type: 'remove-attachment', localId });
  }

  function renderAttachments() {
    attachmentsEl.innerHTML = '';
    pendingAttachments.forEach((a) => {
      const chip = document.createElement('div');
      chip.className = 'attachment-chip';
      if (a.status === 'uploading') chip.classList.add('uploading');
      if (a.status === 'error') chip.classList.add('error');

      const icon = document.createElement('span');
      icon.className = 'chip-icon';
      icon.textContent = a.status === 'uploading' ? '⏳'
                       : a.status === 'error' ? '⚠️'
                       : (a.isImage ? '🖼️' : '📎');
      chip.appendChild(icon);

      const name = document.createElement('span');
      name.className = 'chip-name';
      name.textContent = a.status === 'error'
        ? (a.name + ' · ' + (a.error || t('webview.attachment.error')))
        : a.name;
      chip.appendChild(name);

      const rm = document.createElement('button');
      rm.className = 'chip-remove';
      rm.type = 'button';
      rm.textContent = '×';
      rm.setAttribute('aria-label', t('webview.attachment.remove'));
      rm.onclick = () => removeAttachment(a.localId);
      chip.appendChild(rm);

      attachmentsEl.appendChild(chip);
    });
  }

  function renderAutoAttachToggle() {
    attachToggleLabel.textContent = autoAttachActive
      ? t('webview.header.autoAttachOn')
      : t('webview.header.autoAttachOff');
    attachToggleBtn.classList.toggle('active', autoAttachActive);
  }

  // ── MESSAGE RENDERING ────────────────────────────────
  // origin: where a user message was typed ('desktop', 'mobile'), labelled
  function addMessage(text, isUser, timestamp, origin) {
    if (welcomeEl) welcomeEl.style.display = 'none';
    const msg = document.createElement('div');
    msg.className = 'message ' + (isUser ? 'user' : 'ai');
    const time = formatTime(timestamp ? new Date(timestamp) : new Date());
    const label = isUser ? originText(origin) : '';
    if (label) {
      msg.innerHTML = '<div class="user-stack">' +
        '<span class="origin-label" data-origin="' + escapeHtml(origin) + '">' +
        escapeHtml(label) + '</span>' +
        '<div class="bubble">' + escapeHtml(text) +
        '<span class="time">' + time + '</span></div></div>';
    } else if (isUser) {
      msg.innerHTML = '<div class="bubble">' + escapeHtml(text) +
        '<span class="time">' + time + '</span></div>';
    } else {
      msg.innerHTML =
        '<div class="ai-icon">' + ROBOT_SVG + '</div>' +
        '<div class="bubble">' + renderMarkdown(text) +
        '<span class="time">' + time + '</span></div>';
    }
    messagesEl.appendChild(msg);
    enhanceCodeBlocks(msg);
    scrollToBottom();
  }

  function balanceMarkdownForStreaming(text) {
    if (!text) return '';
    const fenceMatches = text.match(/(^|\n)```/g);
    const count = fenceMatches ? fenceMatches.length : 0;
    if (count % 2 === 1) text = text + '\n```';
    return text;
  }

  function ensureStreamingBubble(mid, segmentIndex) {
    if (
      streamingMessageId === mid
      && streamingSegmentIndex === segmentIndex
      && streamingMessageEl
      && streamingMessageEl.isConnected
    ) {
      return streamingMessageEl;
    }
    if (welcomeEl) welcomeEl.style.display = 'none';
    streamingMessageId = mid;
    streamingSegmentIndex = segmentIndex;
    const msg = document.createElement('div');
    msg.className = 'message ai streaming';
    msg.dataset.segment = String(segmentIndex);
    msg.innerHTML =
      '<div class="ai-icon">' + ROBOT_SVG + '</div>' +
      '<div class="bubble">' +
        '<div class="stream-content"></div>' +
        '<span class="stream-cursor"></span>' +
      '</div>';
    messagesEl.appendChild(msg);
    streamingMessageEl = msg;
    return msg;
  }

  // Fige la bulle de streaming courante (sans la déplacer dans le DOM)
  // pour qu'elle reste visible quand on passe au segment suivant ou à la
  // fin de la génération.
  function promoteCurrentStreamingBubble(timestamp) {
    if (!streamingMessageEl) return;
    streamingMessageEl.classList.remove('streaming');
    const cursor = streamingMessageEl.querySelector('.stream-cursor');
    if (cursor) cursor.remove();
    const bubble = streamingMessageEl.querySelector('.bubble');
    if (bubble && !bubble.querySelector('.time')) {
      const time = formatTime(timestamp ? new Date(timestamp) : new Date());
      const timeEl = document.createElement('span');
      timeEl.className = 'time';
      timeEl.textContent = time;
      bubble.appendChild(timeEl);
    }
  }

  function updateStreamingBubble(mid, text, segmentIndex) {
    if (typeof segmentIndex !== 'number') segmentIndex = 0;
    const trimmedText = (text || '').trim();
    // Détection d'un nouveau segment (= nouvelle itération LLM) : on
    // promeut la bulle courante en bulle "finie" et on en crée une
    // nouvelle, qui apparaîtra APRÈS les cartes d'outils déjà insérées
    // entre les deux segments. C'est ce qui donne l'ordre :
    // texte → outils → texte → outils → ...
    if (
      streamingMessageId === mid
      && streamingMessageEl
      && streamingSegmentIndex !== null
      && streamingSegmentIndex !== segmentIndex
    ) {
      // Si le segment précédent est resté vide (LLM n'a émis qu'un
      // tool_use sans texte autour), on retire carrément sa bulle pour
      // ne pas afficher un robot orphelin sans contenu.
      const prevContent = streamingMessageEl.querySelector('.stream-content');
      const prevText = prevContent ? prevContent.textContent.trim() : '';
      if (!prevText) {
        streamingMessageEl.remove();
      } else {
        promoteCurrentStreamingBubble(null);
      }
      streamingMessageEl = null;
    }
    // Ne pas créer de bulle tant qu'il n'y a pas de contenu visible :
    // évite les bulles fantômes pour les segments où le LLM n'émet que
    // des balises <tool_use> (déjà strippées côté hôte).
    if (!trimmedText) {
      // On enregistre quand même le segment courant pour détecter la
      // prochaine transition.
      streamingMessageId = mid;
      streamingSegmentIndex = segmentIndex;
      return;
    }
    const bubble = ensureStreamingBubble(mid, segmentIndex);
    const content = bubble.querySelector('.stream-content');
    if (content) {
      content.innerHTML = renderMarkdown(balanceMarkdownForStreaming(text));
      enhanceCodeBlocks(content);
    }
    scrollToBottomStream();
  }

  function finalizeStreaming(mid, finalText, timestamp) {
    if (streamingMessageId !== mid) {
      // Le streaming n'a jamais commencé pour ce message : afficher la
      // réponse finale d'un coup.
      if (finalText !== null && finalText !== undefined) {
        addMessage(finalText, false, timestamp);
      }
      return;
    }
    // En mode segmenté, la bulle de streaming actuelle contient le DERNIER
    // segment (pas la réponse complète). On la promeut sans toucher à son
    // contenu : tous les segments précédents sont déjà des bulles figées
    // au-dessus, intercalées avec les cartes d'outils. Le finalText reçu
    // dans le message `response` est la concaténation de tous les segments
    // (utile si le streaming a été manqué, mais redondant sinon).
    if (streamingMessageEl) {
      // Si la bulle de streaming est restée vide (dernier segment sans
      // texte), on l'efface et on bascule sur le finalText pour que
      // l'utilisateur voie au moins la réponse complète une fois.
      const content = streamingMessageEl.querySelector('.stream-content');
      const currentText = content ? content.textContent.trim() : '';
      if (!currentText && finalText && finalText.trim()) {
        streamingMessageEl.remove();
        addMessage(finalText, false, timestamp);
      } else {
        promoteCurrentStreamingBubble(timestamp);
      }
    } else if (finalText !== null && finalText !== undefined && finalText.trim()) {
      // Streaming vide (jamais reçu de chunk visible) → afficher la réponse.
      addMessage(finalText, false, timestamp);
    }
    streamingMessageEl = null;
    streamingMessageId = null;
    streamingSegmentIndex = null;
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

  function clearChat() {
    // Vider le chat pendant une génération l'arrête, sinon la réponse
    // continuerait de s'écrire dans le chat vidé. Le bouton reste en mode
    // stop jusqu'à la réponse « interrompue » de l'hôte.
    if (isWaiting) {
      stopGeneration();
      discardingReply = true;
    }
    removeTyping();
    Array.from(messagesEl.children).forEach((c) => {
      if (c !== welcomeEl) c.remove();
    });
    if (welcomeEl) welcomeEl.style.display = 'flex';
    renderedMessageIds.clear();
    streamingMessageId = null;
    streamingMessageEl = null;
    streamingSegmentIndex = null;
    toolCardEls.clear();
    toolCardEvents.clear();
  }

  function scrollToBottom() {
    requestAnimationFrame(() => {
      messagesEl.scrollTop = messagesEl.scrollHeight;
    });
  }

  function scrollToBottomStream() {
    if (!userPinnedToBottom) return;
    messagesEl.scrollTop = messagesEl.scrollHeight;
    requestAnimationFrame(() => {
      if (!userPinnedToBottom) return;
      messagesEl.scrollTop = messagesEl.scrollHeight;
    });
  }

  // ── CODE BLOCK ACTIONS ───────────────────────────────
  function enhanceCodeBlocks(root) {
    root.querySelectorAll('pre').forEach((pre) => {
      if (pre.parentElement && pre.parentElement.classList.contains('code-block-wrapper')) {
        return;
      }
      const wrapper = document.createElement('div');
      wrapper.className = 'code-block-wrapper';
      pre.parentNode.insertBefore(wrapper, pre);
      wrapper.appendChild(pre);

      const actions = document.createElement('div');
      actions.className = 'code-actions';

      const copyBtn = document.createElement('button');
      copyBtn.className = 'code-action';
      copyBtn.dataset.action = 'copy';
      copyBtn.textContent = t('webview.code.copy');
      actions.appendChild(copyBtn);

      const insertBtn = document.createElement('button');
      insertBtn.className = 'code-action';
      insertBtn.dataset.action = 'insert';
      insertBtn.textContent = t('webview.code.insert');
      actions.appendChild(insertBtn);

      wrapper.appendChild(actions);
    });
  }

  // ── MARKDOWN (light) ─────────────────────────────────
  function renderMarkdown(text) {
    if (!text) return '';
    let html = escapeHtml(text);

    html = html.replace(/```(\w*)\n([\s\S]*?)```/g, (_, _lang, code) => {
      return '<pre><code>' + code.trim() + '</code></pre>';
    });

    html = html.replace(/`([^`]+)`/g, '<code>$1</code>');

    // Horizontal rule: a line containing only 3+ identical chars among - _ *
    // (matches "---", "___", "***", with optional surrounding whitespace).
    // Must run BEFORE the list transform so that "---" is not interpreted as a bullet.
    html = html.replace(/^[ \t]*([-_*])\1{2,}[ \t]*$/gm, '<hr>');

    html = html.replace(/^(#{1,6}) (.+)$/gm, (_, hashes, content) => {
      const lvl = hashes.length;
      return '<h' + lvl + '>' + content + '</h' + lvl + '>';
    });

    html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
    html = html.replace(/(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)/g, '<em>$1</em>');

    html = html.replace(/((?:^\|[^\n]+\n?)+)/gm, (tableBlock) => {
      const lines = tableBlock.trim().split('\n').filter((l) => l.trim());
      if (lines.length < 2) return tableBlock;
      if (!/^\|[\s:\-|]+\|?$/.test(lines[1].trim())) return tableBlock;
      const parseRow = (line) => line.replace(/^\||\|$/g, '').split('|').map((c) => c.trim());
      const headers = parseRow(lines[0]);
      let out = '<table><thead><tr>';
      headers.forEach((h) => { out += '<th>' + h + '</th>'; });
      out += '</tr></thead><tbody>';
      for (let i = 2; i < lines.length; i++) {
        const row = lines[i].trim();
        if (!row) continue;
        const cells = parseRow(row);
        out += '<tr>';
        cells.forEach((c) => { out += '<td>' + c + '</td>'; });
        out += '</tr>';
      }
      out += '</tbody></table>';
      return out;
    });

    html = html.replace(/^\s*(\d+)[\.)]\s+(.+)$/gm, '<oli>$2</oli>');
    html = html.replace(/^\s*[\-\*]\s+(.+)$/gm, '<uli>$1</uli>');

    html = html.replace(/(?:<oli>[\s\S]*?<\/oli>\n?)+/g, (block) => {
      const items = block.replace(/<oli>/g, '<li>').replace(/<\/oli>/g, '</li>');
      return '<ol>' + items + '</ol>';
    });

    html = html.replace(/(?:<uli>[\s\S]*?<\/uli>\n?)+/g, (block) => {
      const items = block.replace(/<uli>/g, '<li>').replace(/<\/uli>/g, '</li>');
      return '<ul>' + items + '</ul>';
    });

    html = html.replace(/\n\n/g, '</p><p>');
    html = html.replace(/\n/g, '<br>');
    html = '<p>' + html + '</p>';

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

    html = html.replace(/(<\/li>)<br>(<li>)/g, '$1$2');
    html = html.replace(/<ul><br>/g, '<ul>');
    html = html.replace(/<br><\/ul>/g, '</ul>');
    html = html.replace(/<ol><br>/g, '<ol>');
    html = html.replace(/<br><\/ol>/g, '</ol>');

    // <hr>: strip surrounding <br> so the rule stands on its own clean line,
    // then split any wrapping <p>...<hr>...</p> into <p>before</p><hr><p>after</p>
    // so the HTML stays valid (<hr> is a block element and cannot live inside <p>).
    // The negative lookaheads `(?!<\/p>)` / `(?!<p>)` keep the match within a
    // single paragraph so we never swallow neighbouring paragraphs.
    html = html.replace(/<br>\s*<hr>/g, '<hr>');
    html = html.replace(/<hr>\s*<br>/g, '<hr>');
    let _hrIter = 100;
    while (_hrIter-- > 0) {
      const next = html.replace(
        /<p>((?:(?!<\/p>)[^])*?)<hr>((?:(?!<p>)[^])*?)<\/p>/,
        (_m, before, after) => {
          let out = '';
          if (before.trim()) out += '<p>' + before + '</p>';
          out += '<hr>';
          if (after.trim()) out += '<p>' + after + '</p>';
          return out;
        },
      );
      if (next === html) break;
      html = next;
    }
    // Orphan </p> right after <hr> or orphan <p> right before <hr> (left over
    // when the preceding/following block was already stripped of its <p> wrap,
    // e.g. a <ul>...</ul>\n\n<hr> sequence): remove them.
    html = html.replace(/<hr>\s*<\/p>/g, '<hr>');
    html = html.replace(/<p>\s*<hr>/g, '<hr>');

    return html;
  }

  function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }

  function formatTime(date) {
    return date.toLocaleTimeString(timeLocale, { hour: '2-digit', minute: '2-digit' });
  }

  function setStatus(state, label) {
    statusDot.className = 'status-dot ' + (
      state === 'connected' ? '' :
      state === 'connecting' ? 'connecting' : 'offline'
    );
    statusText.textContent = label;
  }

  // Tell the extension we're ready to receive state/history.
  vscode.postMessage({ type: 'webview-ready' });
})();
