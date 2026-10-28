# Changelog

All notable changes to the **My_AI Relay** VS Code extension are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/).

## [1.6.1] — 2026-10-28

Cleaner replies, drawn like on the phone.

### Changed
- **One bubble per reply.** A reply used to be a bubble, then a stack of
  tool cards, then a new bubble. It is now a single bubble: the text of
  each pass of the model and, after it, its tool calls grouped one line
  each (*Reading src/app.py*, *Command: npm test*… in My_AI's language),
  then the text that follows. A line's icon gives its state; a click
  shows its input and output; the approval buttons sit under the call.
  The bottom of the bubble says when the reply was stopped or failed,
  with its time and how long it took.
- **Same rendering as the phone.** The Code view of the phone draws its
  replies with the same files (`media/markdown.js`, `media/turn.js`,
  `media/thread.css`): both look the same.
- **Code blocks** show their language, and their **Copy** and **Insert**
  buttons stay visible in their header (they only showed on hover, over
  the code).

### Fixed
- **Gray bands behind the code.** VS Code's default webview styles gave
  every `<code>` a gray background: in a code block, one band per line.
- **Markdown**: a blank line after each heading, nested lists flattened,
  a numbered list restarting at 1 after a sub-list or a code block,
  quotes, links, strikethrough and task lists left as raw text, inline
  code styled differently in lists and tables. The streaming cursor now
  follows the last character, instead of sitting alone on the next line.
- A message on several lines (or with attachments) showed on one line.
- The view stops following a streaming reply only when you scroll up, not
  when a long passage grows below the screen.

## [1.6.0] — 2026-10-28

The VS Code conversation is shared with My_AI on the PC and on the phone,
and kept apart from their regular chat. The extension speaks the 12
languages of My_AI.

### Added
- **One conversation, three places.** The chat also shows on the new
  **Code** page of My_AI on the host PC (button at the top of its sidebar)
  and in the **Code** view of its phone page (`</>` button left of
  **Chat**). A message typed there lands here and acts in your workspace;
  the reply streams everywhere, tool cards included. Messages typed
  elsewhere show where they come from, with the names of their
  attachments: a message from the PC can carry documents, code and
  images, read by the model on the host.
- **Approvals from anywhere.** For a message typed on the PC or the phone,
  a write or a shell command asks for approval with buttons in its tool
  card — here, on the PC and on the phone — and the first answer counts;
  the tool waits without timing out. A message typed in VS Code still asks
  in the modal dialog.
- **12 languages.** The chat, notifications and prompts speak the language
  chosen in My_AI (French, English, Spanish, German, Italian, Portuguese,
  Dutch, Russian, Chinese, Japanese, Korean, and Arabic, right to left):
  the Relay gives it on connection and when it changes, and the extension
  remembers it. Before the first connection: VS Code's language if My_AI
  speaks it, English otherwise. Command titles and setting descriptions
  follow VS Code's display language, now in these languages too.

### Changed
- **Clear** starts a new conversation in VS Code, on the PC and on the
  phone, and stops a reply in progress. It used to clear this view only.
- **Memory.** The conversation, and the model's context, live on the host:
  they survive reconnections and restarts of My_AI. Past the model's
  context window, the oldest exchanges are dropped.
- **Stop** stops the reply in progress wherever its message was typed.

### Fixed
- **Replies of the phone's chat showed in VS Code**, and its history
  loaded into the view on connection. They no longer do.
- **The last words of a reply could be missing** (the host dropped the end
  of a streamed passage). Replies now arrive whole.
- **"Send selection" and "Send active file"**: the message now shows in
  the chat, with the typing indicator.
- **Tool cards** were labelled in French whatever the language.
- **A failed send** no longer leaves the Stop button stuck.
- **A modal approval answered after Stop** no longer runs the tool.

### Notes
- With a host from before this version, the extension works as before,
  without the shared conversation: it no longer loads the phone's chat
  history there.

## [1.5.2] — 2026-10-26

Marketplace listing only: no change to how the extension works.

### Changed
- **Keywords.** The extension now shows up in Marketplace searches for
  `ollama`, `local-llm`, `agent`, `offline` and `privacy`.

## [1.5.1] — 2026-10-24

Wording update, released with a change to the host's Relay panel: no change
to how the extension works.

### Changed
- **Where to copy the connection string.** The connect prompt, the welcome
  text and the README point to the **Copier** button next to the link in
  the host's Relay panel. My_AI no longer has a separate "Copier pour
  l'extension VS Code" button: it copied the same link, the QR code's.
  Before a tunnel answers, that field shows the host's local address,
  which the extension can't use, and the panel says so.
- **README.** The Relay button is at the bottom of the host's sidebar (or
  Ctrl+R), not at the top-left.

### Notes
- Works with every host: older ones still show both buttons, and their
  **Copier** copies the same link once a tunnel is active.

## [1.5.0] — 2026-10-23

Asks for the Relay **access code**: the connection string alone no longer
connects.

### Added
- **Access code.** After you paste the connection string, the extension
  asks for the 6-digit code shown under the QR code in the host's Relay
  panel. The host only serves the chat, history, uploads and tools to a
  session opened with that code, and the code isn't in the connection
  string: a string that leaks (clipboard history, synced notes, a pasted
  message) is useless on its own. The code travels inside the AES-GCM
  envelope. Five wrong codes lock the Relay until it restarts (new
  connection string, new code).
- The session is saved with the credentials in SecretStorage: reloading
  VS Code doesn't ask for the code again while the Relay keeps running.

### Fixed
- **French translations.** The **@codebase** messages (folder picker,
  indexing progress, result and errors) stayed in English in a French
  VS Code.

### Notes
- Needs the access code on the host (My_AI with this change). Hosts that
  predate it don't ask for a code, and this version still connects to them
  without one.
- Older versions of the extension can't connect to an updated host: the
  host refuses a connection without the code.

## [1.4.0] — 2026-10-19

Documentation update, released with host-side fixes to the tunnels: no
change to how the extension works.

### Changed
- **README.** Describes the **Stop** and **Clear** buttons, lists the tunnels
  the host starts by default (cloudflared and localhost.run), and no longer
  claims that your host's IP address is always hidden: serveo, now off by
  default, puts your network's public IP address in its tunnel names.

### Notes
- On the host, the SSH tunnels now forward to `127.0.0.1`. localhost.run
  used to answer "502 no tunnel" to every request: Windows' OpenSSH tried
  `::1`, where the Relay doesn't listen. With localhost.run working again,
  the QR code is ready in a few seconds. serveo is no longer started by
  default, and the Relay no longer lists its tunnels to callers without a
  token. These changes ship with My_AI and apply to every extension version.

## [1.3.9] — 2026-10-19

Fixes **Stop** and **Clear** while a reply is being written.

### Fixed
- **A stopped reply no longer writes into a cleared chat.** After **Stop**
  then **Clear**, the rest of the stopped reply kept appearing in the
  emptied chat, and the send button could not stop it. Text that arrives
  after a reply has ended or been stopped is now ignored, even after
  **Clear**, and the reply freezes as soon as you click **Stop**.
- **Clear now stops a reply in progress.** The reply used to keep writing
  into the emptied chat. The send button stays in stop mode until the host
  confirms, and nothing more of that reply is shown.
- **No tool runs after Stop.** A tool call that left the host just before
  you clicked **Stop** is no longer run, so no approval prompt for a file
  write pops up afterwards. A tool still running when you click **Clear**
  no longer brings its card back into the emptied chat.

### Notes
- On the host, **Stop** now really stops the model: the stream from Ollama
  is cut instead of running to the end in the background, which also
  delayed the next message. **Stop** also always gets an answer, so the
  button no longer stays stuck in stop mode when a reconnect lost the
  reply. These changes ship with My_AI and apply to every extension
  version.

## [1.3.8] — 2026-10-16

New logo, shared with the My_AI desktop app: no change to how the extension works.

### Changed
- **Logo.** The orange robot of the My_AI desktop window replaces the robot
  emoji at the top left of the chat view, on the welcome screen and next to
  each reply. The Marketplace icon uses it too; the activity bar already did.

## [1.3.7] — 2026-10-06

Documentation release: no change to how the extension works.

### Changed
- **README and changelog** now describe the extension on its own terms,
  without comparing it to another tool.

### Notes
- On the host, the agent system prompt now introduces the model as My_AI
  only. That change ships with My_AI and applies to every extension version.

## [1.3.6] — 2026-09-25

Accepts PowerPoint files as attachments.

### Added
- **PowerPoint attachments.** `.pptx` presentations and `.potx` templates can
  now be picked with the **+** button (they were missing from the file picker)
  or sent as the active file. The host reads them — titles, bullets with their
  level, tables, speaker notes — like Word and PDF documents.

### Notes
- Requires **My_AI 8.1.0** or later on the host: older hosts refuse the upload
  (`Format non supporté : .pptx`).

## [1.3.5] — 2026-06-26

Improves the `@` menu: browse into folders, attach single files reliably, and
keep one shared context per VS Code project.

### Added
- **Folder navigation in `@`.** Selecting a folder now *enters* it and lists its
  contents (sub-folders + files) instead of attaching the whole folder
  immediately. An explicit **📎 attach this folder** entry attaches it as
  @codebase. You can also type a path like `@src/utils/` to drill in, or just
  type a file name to fuzzy-find it anywhere in the workspace.

### Changed
- **`@` file attach now uses the indexing channel.** Picking a file via `@`
  indexes it on the host (same reliable WebSocket path as folders) instead of an
  HTTP upload — this fixes the `… · fetch failed` errors and matches the
  "attach to the workspace context" model. (The **+** button still uploads a
  one-shot attachment.)
- **One shared @codebase context per VS Code project.** Every file/folder you
  attach from the same VS Code workspace now goes into a single host workspace
  (keyed by the workspace root), so the assistant sees one coherent project
  context instead of a separate one per attachment.

## [1.3.4] — 2026-06-26

Adds an `@` mention menu to attach workspace files/folders, and fixes the file
picker labels showing untranslated keys.

### Added
- **`@` mentions.** Typing `@` in the chat opens an autocomplete menu listing the
  files and folders of the current VS Code workspace (like Copilot/Claude `@`).
  Picking a **file** attaches it to your next message; picking a **folder**
  attaches it as a persistent **@codebase** context (indexed on the host), so the
  assistant keeps that project in scope for every question. Heavy directories
  (`node_modules`, `.git`, `dist`, `.venv`, …) are excluded.

### Fixed
- **File picker labels.** The native "+" open dialog showed raw keys
  (`openDialog.openLabel`, `openDialog.filter.allSupported`) instead of localized
  text. The Open button and filter name are now translated to the user's VS Code
  language (e.g. « Envoyer à My_AI », « Tous les formats pris en charge »). Two
  other notifications (auto-attach / send failures) had the same issue and are
  fixed too.

## [1.3.3] — 2026-06-26

Adds folder attachment as persistent `@codebase` context.

### Added
- **Attach a folder as @codebase.** New commands *Attach Folder as @codebase* and
  *Re-index @codebase Folder* (Command Palette + right-click a folder in the
  Explorer). The host indexes the folder incrementally (respects `.gitignore`,
  excludes `node_modules`/`.git`/…) and keeps it available as RAG context for all
  questions of that workspace — no need to re-attach files each time. A progress
  notification reports the indexed file/excerpt counts.

## [1.3.2] — 2026-06-25

Adds a Stop button to interrupt a running generation.

### Added
- **Stop button.** While the assistant is generating, the send button turns into
  a Stop button (black square on white), identical in place and style to the My_AI
  Relay mobile chat. Clicking it aborts everything for that turn on the host — the
  LLM generation **and** the agentic tool loop (pending tool calls included) — and
  the chat unblocks with an "interrupted" notice.

## [1.3.1] — 2026-06-25

Slash commands are now prompt-engineering wrappers instead of plain
text completion.

### Changed
- **Slash commands expand at send time.** Selecting a command in the autocomplete
  menu now inserts just `/command `; you then type your own text — e.g.
  `/code a tic-tac-toe game`. At send time the desktop host substitutes your text
  into the template's `{arguments}` placeholder and sends the resulting detailed
  prompt to the AI, while the chat bubble keeps showing the short command. A short
  command therefore yields a well-engineered prompt. (Previously the full template
  text was inserted inline into the message box.)

## [1.3.0] — 2026-06-25

Adds slash command autocompletion and reusable prompt templates to the chat.

### Added
- **Slash commands.** Typing `/` at the start of the message box opens an
  autocomplete menu listing the prompt templates defined in My_AI (fetched from
  the desktop app over the existing end-to-end-encrypted Relay channel via the new
  `GET /api/prompts` endpoint). Navigate the menu with ↑/↓, accept with Enter/Tab,
  dismiss with Escape.

## [1.2.2] — 2026-05-13

Documentation hotfix. Fixes the French README link on the Marketplace
listing, which resolved to `https://github.com/gonicolas12/My_AI/blob/HEAD/README.fr.md`
(repo root) instead of the actual file under `vscode_extension/`. The
Marketplace rewrites relative links from the repo root rather than from
the extension subdirectory, so `./README.fr.md` was 404-ing for anyone
clicking the language switcher from the listing.

### Fixed
- **Marketplace language switcher.** `README.md` and `README.fr.md` now
  use absolute GitHub URLs (`blob/main/vscode_extension/...`) for the
  English/Français toggle so the link works from both the Marketplace
  listing and the in-repo view.

## [1.2.1] — 2026-05-07

Hotfix on top of 1.2.0. Fixes a **critical deadlock** that made every tool
call time out at 120 s after upgrade testing — the entire agentic loop was
returning `[Timeout]` on every read_file/grep/edit and the model was
spinning trying alternative approaches against a tool surface that never
actually responded. Also cleans up two visible UX glitches.

### Fixed
- **Tool call deadlock (CRITICAL).** The Relay's WebSocket handler was
  awaiting `_handle_vscode_chat` directly inside its `while
  receive_text()` loop. The chat handler in turn awaited `tool_result`
  Futures that could only be resolved by the **same** loop's next
  iteration. Result: every tool call sent a `tool_use` to the extension,
  the extension executed it and sent the `tool_result` back, but the
  message stayed queued forever because the receive loop was blocked
  waiting on the Future. Fixed by spawning the chat handler with
  `asyncio.create_task` so the receive loop can keep pumping
  `tool_result` messages while the agentic loop runs in parallel.
  Pending tasks are cancelled cleanly when the WebSocket closes.
- **Empty assistant bubbles** for iterations where the LLM only emitted
  a `<tool_use>` block with no surrounding text. The webview now skips
  bubble creation when the segment text is empty, and removes any leftover
  empty bubble when the next segment arrives.

### Changed
- **`grep --max-count`** raised from 50 to 100. More matches per file in
  workspace searches, in line with what the user saw as a useful default.
- **`read_file` truncation footer.** When the requested window is
  smaller than the file, the result now ends with an explicit
  `[Fichier tronqué : N ligne(s) restante(s). Pour lire la suite,
  rappelle read_file avec offset=…]` block. Small models (qwen3.5:2b,
  llama3.2:3b…) didn't reliably interpret the `(showing lines …)`
  header alone — they now have a directive instruction to follow up.
- **Tool description for `read_file`** in the agent system prompt
  now tells the model to keep calling `read_file` with growing offsets
  until the truncation footer disappears, so long files are read in full.

## [1.2.0] — 2026-05-07

Polish pass on the agentic mode introduced in 1.1.0. Focuses on **streaming
correctness, transport stability, and chat UX** — the agentic loop now
renders in narration order (text → tool card → text → tool card → final
answer), no longer leaks raw `<tool_use>` JSON during streaming, and stops
spinning on repeated tool calls.

### Added
- **Inline tool-card rendering.** The host now streams
  responses as numbered *segments* (one per LLM iteration) and the chat
  inserts each tool card between the segment that triggered it and the
  segment that consumed its result. Tool cards no longer pile up above the
  whole answer — they appear in narration order.
- **Host-side INFO logging** for the VS Code agentic loop. Each user message
  produces a log line at start (`message_id`, history size), one per
  iteration (segment index, tool count and names), one per tool call
  (`name(input) [call_id]`), one per result (`is_error`, content size), and
  one at end (`%d chars, %.1fs`). Easier to diagnose without attaching a
  debugger.

### Fixed
- **Partial `<tool_use>` blocks no longer leak into the chat.** Until the
  closing tag arrived, the streaming text temporarily showed raw JSON like
  `<tool_use>{"name": "read_file"…`. The host now strips any unfinished
  open tag from the visible chunk on every push.
- **Tunnel keepalive tightened** from 25 s to 15 s. Some public tunnels
  (notably `serveo.net` and `localhost.run` over mobile data) close idle
  WebSockets before the previous interval, causing repeated short-lived
  reconnects. A failed ping now also force-closes the WebSocket so the
  reconnect loop can pick a fresh tunnel instead of holding a zombie
  socket.
- **Anti-loop rules added to the agent system prompt.** Small models would
  sometimes call `read_file` on the same path repeatedly when the previous
  result was already in context. The prompt now forbids re-calling a tool
  with identical arguments, forbids retrying after a `<tool_error>`, and
  requires an explicit stop once all required tool calls have been made.

### Notes
- Wire-protocol change: the `chunk` message now carries an optional
  `segment_index` field. Clients that ignore it (older 1.1.x extensions)
  will see the entire response collapsed into a single bubble — old
  behavior, just less pretty. The host stays backward-compatible with old
  callers via a runtime signature check on `on_chunk`.

## [1.1.0] — 2026-05-06

Adds an **agentic mode** for the VS Code chat. The extension now works as
a coding assistant: the local LLM running on the host PC
can read, edit, and create files, run shell commands, search the workspace,
and inspect the active editor — all delegated to the extension and scoped to
the open VS Code workspace by default. The mobile UI and the desktop GUI on
the host are **strictly unchanged**.

### Added
- **Agentic chat for VS Code clients.** When the extension connects, it
  identifies itself to the Relay (`client_hello { client_kind: "vscode" }`).
  The Relay then routes the conversation through a dedicated agentic loop
  that calls Ollama directly with a tool-aware system prompt. The host's
  GUI/MCP pipeline is reserved for mobile clients and the desktop chat,
  which keep their existing behavior.
- **Nine workspace tools** exposed to the model:
  - `read_file` (with offset/limit pagination), `write_file`, `edit_file`
    (exact-match replace, with optional `replace_all`).
  - `list_dir`, `glob` (workspace `findFiles`), `grep` (ripgrep with JS
    fallback when `rg` is missing).
  - `run_command` (shell exec in the workspace, capped output).
  - `get_active_editor`, `open_file`.
- **Workspace sandbox.** All path arguments are resolved against the first
  workspace folder. Paths that escape the workspace are rejected unless the
  user explicitly approves a one-shot exception via a modal prompt — the
  extension never auto-approves out-of-workspace access.
- **Approval flow for destructive operations.** `write_file`, `edit_file`,
  and `run_command` require explicit user consent before running. The modal
  dialog offers three responses besides denial:
  - *Allow once* — single-call exception.
  - *Allow for this file* — auto-approves further calls of the same tool on
    the same path for the rest of the session.
  - *Allow all <tool> this session* — auto-approves the same tool everywhere
    until disconnect/reconnect.
  Approvals reset on every reconnection.
- **Inline tool cards in the chat.** Each tool call
  renders as a foldable card in the chat with a colored left border that
  reflects status: ⏳ running · 🔒 awaiting approval · ✓ ok · ⚠️ error ·
  🚫 denied. Click to expand the input (JSON) and the captured output
  (stdout/stderr for shell commands).
- **Conversation memory across turns.** The agentic history is preserved for
  the duration of the WebSocket session, so follow-up messages keep context
  (e.g. *"now edit the file you just read"* works).
- **Localized strings (English / French)** for all new modal prompts and
  approval buttons, following the existing l10n bundle conventions.

### Notes
- The model on the host needs to be reachable via Ollama (any model
  works — tool calls are encoded as `<tool_use>{ ... }</tool_use>` tags
  parsed on the host, no native tool-calling API required). Smaller
  models (e.g. `qwen3.5:2b`) work for simple edits; a 4B+ model is
  recommended for multi-file refactors and project scaffolding.
- The mobile chat protocol (chat / response / chunk / ack / resume / ping)
  is untouched. Mobile clients do not send `client_hello`, so they keep
  going through the desktop GUI bridge with full host-side MCPs.

## [1.0.0] — 2026-05-06

First official public release. Stabilizes the `0.1.x` pre-release series after
iteration on localization, view placement, and connection management. The wire
protocol, encryption scheme, and command surface are now considered stable.

### Added (since 0.1.0)
- **Full bilingual UI (English / French)** via VS Code's native localization.
  - `package.nls.json` + `package.nls.fr.json` for manifest strings (display
    name, description, view title, command titles, settings descriptions).
  - `l10n/bundle.l10n.json` + `l10n/bundle.l10n.fr.json` for runtime strings
    consumed by `vscode.l10n.t()` (status bar, prompts, error messages,
    snippet templates, etc.).
  - The webview UI receives a localized strings bundle on startup via
    postMessage, so every label, placeholder, button and tooltip follows
    the active VS Code display language.
- French README (`README.fr.md`) with a language switcher at the top of
  both READMEs.
- **Move Chat to Secondary Side Bar** command — opens the built-in "Move
  View" picker pre-selected on the chat view, so one click places the
  chat on the right side like Copilot Chat.
- First-activation prompt offering to move the chat to the Secondary Side
  Bar automatically. Controlled by the new `myaiRelay.openInSecondarySidebar`
  setting.
- **"New connection" button** in the chat header, always visible. Replaces
  the stored connection string with a fresh one in one click — essential
  when the host PC restarted the Relay (which regenerates the AES key and
  token, leaving the extension stuck in a useless reconnect loop with
  stale credentials).
- Updated marketplace icon (`media/extension_logo.png`).

### Fixed (since 0.1.0)
- View now appears as a proper Activity Bar entry on the left. Earlier
  pre-releases briefly contributed an unsupported `auxiliarybar` entry
  that put the chat inside the Explorer's CHAT section.
- Localization fallback regression where every UI label rendered as a raw
  key string (e.g. `webview.welcome.title` instead of the actual text).
  Root cause: `vscode.l10n.t()` keys must be the **English source strings
  themselves**, not abstract identifiers — when a key is missing from the
  active-locale bundle, VS Code falls back to returning the argument
  verbatim, which exposed our internal keys. All `vscode.l10n.t()` calls
  and l10n bundle entries were refactored to use English source strings
  as keys.

## [0.1.0]

### Added
- Initial release.
- Chat sidebar (Activity Bar → My_AI Relay) that mirrors the mobile Relay UI.
- Connection via the same `router.html#d=…` string used for the mobile QR code.
- AES-256-GCM end-to-end encryption over the public tunnel.
- Multi-tunnel client-side failover (cloudflared, serveo, localhost.run).
- Streaming responses with live token-by-token rendering.
- File uploads (PDF, DOCX, code, images, …) using the same E2EE wire format.
- Auto-attach toggle for the active editor file.
- "Send selection to My_AI" command (Command Palette + editor context menu).
- "Send active file to My_AI" command.
- "Insert at cursor" / "Copy" buttons on every code block in AI replies.
- Status bar item reflecting connection state.
- Credentials stored in VS Code SecretStorage; auto-disconnect when the host
  Relay goes offline; auto-reconnect when it comes back.
