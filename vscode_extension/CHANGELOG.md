# Changelog

All notable changes to the **My_AI Relay** VS Code extension are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/).

## [1.3.1] — 2026-06-25

Slash commands now behave like Claude Code commands (prompt engineering) instead
of plain text completion.

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
  until the truncation footer disappears, matching how Claude Code's
  `Read` tool is used for whole-file reads.

## [1.2.0] — 2026-05-07

Polish pass on the agentic mode introduced in 1.1.0. Focuses on **streaming
correctness, transport stability, and chat UX** — the agentic loop now
renders like Claude Code (text → tool card → text → tool card → final
answer), no longer leaks raw `<tool_use>` JSON during streaming, and stops
spinning on repeated tool calls.

### Added
- **Inline tool-card rendering (Claude-Code parity).** The host now streams
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

Adds an **agentic mode** for the VS Code chat. The extension now behaves like
a Claude-Code-style coding assistant: the local LLM running on the host PC
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
- **Inline tool cards in the chat (Claude-Code style).** Each tool call
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
