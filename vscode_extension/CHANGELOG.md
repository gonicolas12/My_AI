# Changelog

All notable changes to the **My_AI Relay** VS Code extension are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/).

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
