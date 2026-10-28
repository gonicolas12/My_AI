/* ═══════════════════════════════════════════════════ */
/* My_AI — Réponse de la conversation Code               */
/*                                                       */
/* Une réponse, une bulle : le texte de chaque passe du  */
/* modèle et, entre deux passes, ses appels d'outils     */
/* (une ligne chacun, regroupés), dans l'ordre ; en bas, */
/* l'attente, l'arrêt ou l'erreur, puis l'heure.         */
/*                                                       */
/* Même rendu pour la vue Code du téléphone (code.js) et */
/* la vue de l'extension VS Code (chat.js) : ce fichier  */
/* est copié tel quel dans relay/static/ et              */
/* vscode_extension/media/ (tests/test_web_assets.py     */
/* vérifie qu'ils sont identiques). Le texte passe par   */
/* markdown.js.                                          */
/*                                                       */
/* Réponse (relay/code_hub.py) : { status (streaming,    */
/* done, stopped, error), parts, text, timestamp,        */
/* duration_ms } ; un morceau : { kind: 'text', segment, */
/* text } ou { kind: 'tool', call_id, name, input,       */
/* status, output, options }.                            */
/* ═══════════════════════════════════════════════════ */

(function (root) {
  'use strict';

  // Icônes lucide, celles de la page Code de la fenêtre du PC
  var ICONS = {
    'file-text': '<path d="M6 22a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h8a2.4 2.4 0 0 1 1.704.706l3.588 3.588A2.4 2.4 0 0 1 20 8v12a2 2 0 0 1-2 2z"/><path d="M14 2v5a1 1 0 0 0 1 1h5"/><path d="M10 9H8"/><path d="M16 13H8"/><path d="M16 17H8"/>',
    'file-plus': '<path d="M6 22a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h8a2.4 2.4 0 0 1 1.704.706l3.588 3.588A2.4 2.4 0 0 1 20 8v12a2 2 0 0 1-2 2z"/><path d="M14 2v5a1 1 0 0 0 1 1h5"/><path d="M9 15h6"/><path d="M12 18v-6"/>',
    'file-pen': '<path d="M12.659 22H18a2 2 0 0 0 2-2V8a2.4 2.4 0 0 0-.706-1.706l-3.588-3.588A2.4 2.4 0 0 0 14 2H6a2 2 0 0 0-2 2v9.34"/><path d="M14 2v5a1 1 0 0 0 1 1h5"/><path d="M10.378 12.622a1 1 0 0 1 3 3.003L8.36 20.637a2 2 0 0 1-.854.506l-2.867.837a.5.5 0 0 1-.62-.62l.836-2.869a2 2 0 0 1 .506-.853z"/>',
    'folder-open': '<path d="m6 14 1.5-2.9A2 2 0 0 1 9.24 10H20a2 2 0 0 1 1.94 2.5l-1.54 6a2 2 0 0 1-1.95 1.5H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h3.9a2 2 0 0 1 1.69.9l.81 1.2a2 2 0 0 0 1.67.9H18a2 2 0 0 1 2 2v2"/>',
    'file-search': '<path d="M6 22a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h8a2.4 2.4 0 0 1 1.704.706l3.588 3.588A2.4 2.4 0 0 1 20 8v12a2 2 0 0 1-2 2z"/><path d="M14 2v5a1 1 0 0 0 1 1h5"/><circle cx="11.5" cy="14.5" r="2.5"/><path d="M13.3 16.3 15 18"/>',
    'search': '<path d="m21 21-4.34-4.34"/><circle cx="11" cy="11" r="8"/>',
    'square-terminal': '<path d="m7 11 2-2-2-2"/><path d="M11 13h4"/><rect width="18" height="18" x="3" y="3" rx="2" ry="2"/>',
    'file-code-2': '<path d="M4 12.15V4a2 2 0 0 1 2-2h8a2.4 2.4 0 0 1 1.706.706l3.588 3.588A2.4 2.4 0 0 1 20 8v12a2 2 0 0 1-2 2h-3.35"/><path d="M14 2v5a1 1 0 0 0 1 1h5"/><path d="m5 16-3 3 3 3"/><path d="m9 22 3-3-3-3"/>',
    'external-link': '<path d="M15 3h6v6"/><path d="M10 14 21 3"/><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/>',
    'wrench': '<path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.106-3.105c.32-.322.863-.22.983.218a6 6 0 0 1-8.259 7.057l-7.91 7.91a1 1 0 0 1-2.999-3l7.91-7.91a6 6 0 0 1 7.057-8.259c.438.12.54.662.219.984z"/>',
    'loader-circle': '<path d="M21 12a9 9 0 1 1-6.219-8.56"/>',
    'lock': '<rect width="18" height="11" x="3" y="11" rx="2" ry="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/>',
    'circle-alert': '<circle cx="12" cy="12" r="10"/><line x1="12" x2="12" y1="8" y2="12"/><line x1="12" x2="12.01" y1="16" y2="16"/>',
    'ban': '<circle cx="12" cy="12" r="10"/><path d="M4.929 4.929 19.07 19.071"/>',
    'octagon-x': '<path d="m15 9-6 6"/><path d="M2.586 16.726A2 2 0 0 1 2 15.312V8.688a2 2 0 0 1 .586-1.414l4.688-4.688A2 2 0 0 1 8.688 2h6.624a2 2 0 0 1 1.414.586l4.688 4.688A2 2 0 0 1 22 8.688v6.624a2 2 0 0 1-.586 1.414l-4.688 4.688a2 2 0 0 1-1.414.586H8.688a2 2 0 0 1-1.414-.586z"/><path d="m9 9 6 6"/>',
    'chevron-right': '<path d="m9 18 6-6-6-6"/>',
  };

  // Outils de l'extension (AGENT_TOOLS de core/agentic_executor.py)
  var TOOLS = {
    read_file: { icon: 'file-text', label: 'code.tool.read_file' },
    write_file: { icon: 'file-plus', label: 'code.tool.write_file' },
    edit_file: { icon: 'file-pen', label: 'code.tool.edit_file' },
    list_dir: { icon: 'folder-open', label: 'code.tool.list_dir' },
    glob: { icon: 'file-search', label: 'code.tool.glob' },
    grep: { icon: 'search', label: 'code.tool.grep' },
    run_command: { icon: 'square-terminal', label: 'code.tool.run_command' },
    get_active_editor: { icon: 'file-code-2', label: 'code.tool.get_active_editor' },
    open_file: { icon: 'external-link', label: 'code.tool.open_file' },
  };
  // Appel qui ne s'est pas simplement terminé : son état, à côté du libellé
  var STATUS_TEXTS = {
    'awaiting-approval': 'code.toolStatus.awaiting',
    failed: 'code.toolStatus.failed',
    denied: 'code.toolStatus.denied',
    stopped: 'code.toolStatus.stopped',
  };
  var STATUS_ICONS = {
    requested: 'loader-circle', running: 'loader-circle', 'awaiting-approval': 'lock',
    failed: 'circle-alert', denied: 'ban', stopped: 'octagon-x',
  };
  var DECISIONS = {
    'allow-once': 'code.approval.allowOnce',
    'allow-target': 'code.approval.allowTarget',
    'allow-tool': 'code.approval.allowTool',
    deny: 'code.approval.deny',
  };
  var OPEN = { requested: true, running: true, 'awaiting-approval': true };
  // Longueur d'une commande ou d'un motif dans le libellé
  var TARGET_LENGTH = 80;

  function svg(name) {
    return '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" ' +
      'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">' + ICONS[name] + '</svg>';
  }

  function element(tag, cls, html) {
    var node = document.createElement(tag);
    if (cls) node.className = cls;
    if (html) node.innerHTML = html;
    return node;
  }

  // Ce que vise l'appel, sur une ligne : chemin, motif ou commande
  function target(part) {
    var input = part.input || {};
    var value = part.name === 'run_command' ? input.command
      : (part.name === 'glob' || part.name === 'grep') ? input.pattern
        : (input.path || (part.name === 'list_dir' ? '.' : ''));
    var line = String(value || '').replace(/\s+/g, ' ').trim();
    return line.length > TARGET_LENGTH ? line.slice(0, TARGET_LENGTH) + '…' : line;
  }

  // Arguments montrés dans le détail : la commande telle quelle, sinon le JSON
  function inputText(part) {
    var input = part.input || {};
    if (part.name === 'run_command' && typeof input.command === 'string') return input.command;
    try {
      return JSON.stringify(input, null, 2);
    } catch (e) {
      return String(input);
    }
  }

  function partKey(part) {
    return part.kind === 'text' ? 't' + part.segment : 'x' + part.call_id;
  }

  // Ce qui change l'affichage d'un morceau
  function signature(part, cursor) {
    if (part.kind === 'text') return (cursor ? '1' : '0') + part.text;
    return [part.status, part.name, typeof part.output === 'string' ? part.output : '-',
      (part.options || []).join(','), JSON.stringify(part.input || {})].join('\u0001');
  }

  // Durée « 8 s », « 1 min 5 s », dans la langue de la page
  function formatDuration(ms, locale) {
    if (!(ms >= 1000)) return '';
    var seconds = Math.round(ms / 1000);
    function unit(name, value) {
      try {
        return new Intl.NumberFormat(locale, { style: 'unit', unit: name, unitDisplay: 'short' })
          .format(value);
      } catch (e) {
        return value + (name === 'minute' ? ' min' : ' s');
      }
    }
    if (seconds < 60) return unit('second', seconds);
    return unit('minute', Math.floor(seconds / 60)) + ' ' + unit('second', seconds % 60);
  }

  function detailBlock(label, text) {
    var block = element('div', 'tool-block');
    var title = element('div', 'tool-block-label');
    title.textContent = label;
    var pre = element('pre');
    pre.dir = 'ltr';
    pre.textContent = text;
    block.appendChild(title);
    block.appendChild(pre);
    return block;
  }

  /**
   * options :
   *   t(key, params)             textes (clés code.*)
   *   approve(callId, decision)  réponse à une demande d'approbation
   *   robotSvg                   logo de My_AI, à côté de la bulle
   *   formatTime(date)           heure « 14:19 »
   *   locale                     langue de la durée
   *   codeActions                boutons des blocs de code (markdown.js)
   *   approvalNote               approbation demandée sans boutons (message
   *                              tapé dans VS Code) : le dire, sous l'appel
   */
  function Turn(reply, options) {
    this.options = options || {};
    this.shown = [];
    this.el = element('div', 'message ai turn');
    this.el.innerHTML = '<div class="ai-icon">' + (this.options.robotSvg || '') + '</div>';
    this.bubble = element('div', 'bubble');
    this.body = element('div', 'turn-body');
    this.tail = element('div', 'turn-tail',
      '<div class="typing-indicator"><div class="typing-dot"></div>' +
      '<div class="typing-dot"></div><div class="typing-dot"></div></div>');
    this.note = element('div', 'turn-note');
    this.error = element('div', 'turn-error');
    this.time = element('span', 'time');
    [this.body, this.tail, this.note, this.error, this.time].forEach(function (node) {
      this.bubble.appendChild(node);
    }, this);
    this.el.appendChild(this.bubble);
    this.update(reply);
  }

  Turn.prototype.t = function (key, params) {
    return this.options.t ? this.options.t(key, params) : key;
  };

  // Réponse changée (texte reçu, appel d'outil, fin) : seuls les morceaux qui
  // ont changé sont refaits, les nouveaux s'ajoutent à la suite
  Turn.prototype.update = function (reply) {
    var streaming = reply.status === 'streaming';
    var parts = (reply.parts || []).filter(function (part) {
      return part && (part.kind === 'tool' || (part.kind === 'text' && part.text));
    });
    var hasText = parts.some(function (part) { return part.kind === 'text'; });
    // Réponse finie sans texte reçu en streaming : son texte final
    if (reply.status === 'done' && !hasText && reply.text) {
      parts = parts.concat([{ kind: 'text', segment: 'final', text: reply.text }]);
    }
    var last = parts[parts.length - 1];
    var aligned = this.shown.every(function (node, index) {
      return parts[index] && partKey(parts[index]) === node.key;
    });
    if (!aligned) {
      this.body.innerHTML = '';
      this.shown = [];
    }
    for (var i = 0; i < parts.length; i++) {
      var part = parts[i];
      var cursor = streaming && part === last && part.kind === 'text';
      var sig = signature(part, cursor);
      var node = this.shown[i];
      if (!node) {
        node = { key: partKey(part), sig: '', open: false, el: null };
        this.place(node, part);
        this.shown.push(node);
      }
      if (node.sig !== sig) {
        node.sig = sig;
        this.fill(node, part, cursor);
      }
    }

    // Rien ne bouge à l'écran (début, entre deux outils) : les trois points
    var waiting = streaming && (!last || (last.kind === 'tool' && !OPEN[last.status]));
    this.tail.style.display = waiting ? '' : 'none';
    var stopped = reply.status === 'stopped';
    this.note.style.display = stopped ? '' : 'none';
    if (stopped && !this.note.firstChild) {
      this.note.innerHTML = svg('octagon-x') + '<span></span>';
      this.note.lastChild.textContent = this.t('code.stopped');
    }
    var failure = reply.status === 'error' ? String(reply.text || '').replace(/^❌\s*/, '') : '';
    this.error.style.display = failure ? '' : 'none';
    if (failure) {
      this.error.innerHTML = svg('circle-alert') + '<span></span>';
      this.error.lastChild.textContent = failure;
    }
    var meta = [];
    if (!streaming && this.options.formatTime) {
      meta.push(this.options.formatTime(reply.timestamp ? new Date(reply.timestamp) : new Date()));
      var duration = formatDuration(reply.duration_ms, this.options.locale);
      if (duration) meta.push(duration);
    }
    this.time.textContent = meta.join(' · ');
    this.time.style.display = meta.length ? '' : 'none';
    // Outils et code prennent toute la largeur, la bulle ne change plus de taille
    this.bubble.classList.toggle('wide', parts.some(function (p) {
      return p.kind === 'tool' || p.text.indexOf('```') !== -1 || p.text.indexOf('~~~') !== -1;
    }));
    this.el.style.display = parts.length || streaming || stopped || failure ? '' : 'none';
  };

  // Textes de la page changés (langue) : la réponse est refaite, détails
  // ouverts gardés
  Turn.prototype.refresh = function (reply) {
    this.shown.forEach(function (node) { node.sig = ''; });
    this.note.innerHTML = '';
    this.update(reply);
  };

  // Nouveau morceau, à la fin : un texte, ou un appel ajouté au groupe d'outils
  // qui le précède (ou à un nouveau groupe)
  Turn.prototype.place = function (node, part) {
    if (part.kind === 'text') {
      node.el = element('div', 'turn-text md');
      node.el.dir = 'auto';
      this.body.appendChild(node.el);
      return;
    }
    var group = this.body.lastElementChild;
    if (!group || !group.classList.contains('tool-group')) {
      group = element('div', 'tool-group');
      this.body.appendChild(group);
    }
    node.el = element('div', 'tool-row');
    group.appendChild(node.el);
  };

  Turn.prototype.fill = function (node, part, cursor) {
    if (part.kind === 'text') {
      node.el.innerHTML = root.MyAIMarkdown.render(part.text, {
        cursor: cursor, codeActions: this.options.codeActions,
      });
      return;
    }
    var row = this.toolRow(node, part);
    node.el.parentNode.replaceChild(row, node.el);
    node.el = row;
  };

  // Appel d'outil : une ligne (icône, libellé, état), son détail au clic ;
  // les boutons d'approbation dessous quand elle est demandée
  Turn.prototype.toolRow = function (node, part) {
    var self = this;
    var status = part.status || 'requested';
    var known = TOOLS[part.name];
    var label = known ? this.t(known.label, { target: target(part) }) : String(part.name || '');
    // Approbation demandée : ses boutons (ou la note) le disent déjà, le libellé garde la place
    var approval = status === 'awaiting-approval' ? this.approval(part) : null;
    var state = STATUS_TEXTS[status] && !approval ? this.t(STATUS_TEXTS[status]) : '';
    var row = element('div', 'tool-row ' + status + (node.open ? ' open' : ''));
    var head = element('button', 'tool-head',
      '<span class="tool-icon">' + svg(STATUS_ICONS[status] || (known ? known.icon : 'wrench')) + '</span>' +
      '<span class="tool-label"></span>' + (state ? '<span class="tool-state"></span>' : '') +
      '<span class="tool-chev">' + svg('chevron-right') + '</span>');
    head.type = 'button';
    head.title = label;
    head.setAttribute('aria-expanded', node.open ? 'true' : 'false');
    this.fillLabel(head.querySelector('.tool-label'), part, known);
    if (state) head.querySelector('.tool-state').textContent = state;
    row.appendChild(head);
    if (approval) row.appendChild(approval);

    var details = element('div', 'tool-details');
    details.style.display = node.open ? '' : 'none';
    details.appendChild(detailBlock(this.t('code.tool.input'), inputText(part)));
    if (typeof part.output === 'string') {
      details.appendChild(detailBlock(this.t('code.tool.output'), part.output || this.t('code.tool.empty')));
    }
    row.appendChild(details);
    head.addEventListener('click', function () {
      node.open = !node.open;
      details.style.display = node.open ? '' : 'none';
      row.classList.toggle('open', node.open);
      head.setAttribute('aria-expanded', node.open ? 'true' : 'false');
      if (self.options.onToggle) self.options.onToggle(row, node.open);
    });
    return row;
  };

  // Libellé d'un appel, sa cible (chemin, motif, commande) isolée dans un
  // <bdi> : elle garde son sens de lecture dans une phrase en arabe
  Turn.prototype.fillLabel = function (el, part, known) {
    if (!known) {
      el.textContent = String(part.name || '');
      return;
    }
    var pieces = this.t(known.label, { target: '\u0001' }).split('\u0001');
    el.appendChild(document.createTextNode(pieces[0]));
    if (pieces.length > 1) {
      var bdi = document.createElement('bdi');
      bdi.textContent = target(part);
      el.appendChild(bdi);
      el.appendChild(document.createTextNode(pieces.slice(1).join('')));
    }
  };

  // Écriture ou commande d'un message du PC ou du téléphone : la première
  // réponse donnée (ici, dans VS Code, sur le PC ou le téléphone) compte
  Turn.prototype.approval = function (part) {
    var self = this;
    var options = (Array.isArray(part.options) ? part.options : []).filter(function (decision) {
      return DECISIONS[decision];
    });
    if (!options.length) {
      if (!this.options.approvalNote) return null;
      var note = element('div', 'tool-approval-note');
      note.textContent = this.t('code.approval.inVscode');
      return note;
    }
    var box = element('div', 'tool-approval');
    var prompt = element('div', 'tool-approval-prompt');
    prompt.textContent = this.t('code.approval.prompt');
    var buttons = element('div', 'tool-approval-buttons');
    options.forEach(function (decision, index) {
      var button = element('button', 'tool-approval-btn' + (index === 0 ? ' primary' : '') +
        (decision === 'deny' ? ' deny' : ''));
      button.type = 'button';
      button.textContent = self.t(DECISIONS[decision], { tool: part.name });
      button.addEventListener('click', function () {
        buttons.querySelectorAll('button').forEach(function (b) { b.disabled = true; });
        if (self.options.approve) self.options.approve(part.call_id, decision);
      });
      buttons.appendChild(button);
    });
    box.appendChild(prompt);
    box.appendChild(buttons);
    return box;
  };

  root.MyAITurn = {
    create: function (reply, options) { return new Turn(reply, options); },
    formatDuration: formatDuration,
  };
})(typeof window !== 'undefined' ? window : globalThis);
