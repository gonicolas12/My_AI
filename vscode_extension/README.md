# My_AI Relay — VS Code Extension

**English** · [Français](https://github.com/gonicolas12/My_AI/blob/main/vscode_extension/README.fr.md)

> **Agentic** chat with your **self-hosted [My_AI](https://github.com/gonicolas12/My_AI) assistant**
> from VS Code, over an end-to-end encrypted tunnel — like Claude Code, but
> running on the local LLM on your own machine.

The extension is a remote client. The LLM, history, and file processing live
on the **PC that hosts My_AI**; the extension delegates filesystem and shell
operations on the workspace side, scoped to your VS Code workspace by
default. This means you can run a beefy LLM on a desktop at home and use it
from any laptop, anywhere — with full read/write/exec parity with Claude
Code's developer experience, and the existing mobile web UI still works
exactly as before.

---

## Highlights

- 🤖 **Agentic mode** — the model can read, edit, and create files, run
  shell commands, and search the workspace via nine built-in tools. Every
  tool call shows up as a Claude-Code-style foldable card **rendered inline
  in narration order** (text → tool card → text → tool card → final
  answer), with status, input, and captured output.
- 🛡️ **Workspace sandbox** — all paths are resolved against the open
  workspace folder. Out-of-workspace access requires an explicit modal
  approval per path, never auto-approvable.
- ✋ **Approval flow** — read-only tools run silently; `write_file`,
  `edit_file`, and `run_command` ask for confirmation, with options to allow
  once, allow for the same file, or allow the tool for the rest of the
  session.
- 🔐 **End-to-end encryption** — AES-256-GCM over the public tunnel. The
  Cloudflare/serveo/localhost.run server only ever sees ciphertext.
- 🌐 **Multi-tunnel failover** — cloudflared, serveo, and localhost.run run in
  parallel on the host; the extension picks the first reachable one and falls
  over automatically when one drops.
- 💾 **Persistent connection** — credentials stay encrypted in VS Code
  SecretStorage. The extension reconnects automatically when the host Relay
  comes back online, and disconnects when it shuts down.
- 🧩 **Workspace integration**
  - Auto-attach the active editor file to every message (toggle).
  - "Send selection to My_AI" (Command Palette and editor context menu).
  - "Send active file to My_AI".
  - One-click **Insert at cursor** / **Copy** on every code block in replies.

## Requirements

- **VS Code** ≥ 1.85.
- A **My_AI host PC** running the Relay (any machine where you can launch
  My_AI). The Relay button is in the GUI's left sidebar.
- An **Internet connection** on both ends (the encrypted tunnel goes
  through Cloudflare / serveo / localhost.run).

## Quick start

### 1. Start the Relay on the host PC

1. Launch My_AI on the PC where the model runs.
2. Click the **Relay** button at the top-left of the sidebar.
3. Wait until at least one tunnel is "active" (status turns green).

### 2. Copy the connection string

In the same Relay popup, click **🧩 Copier pour l'extension VS Code**.
The string copied looks like:

```
https://gonicolas12.github.io/My_AI/router.html#d=…
```

It contains the list of public tunnels, the auth token, and the AES-256-GCM
key — all in the URL fragment, so nothing leaks to the tunnel server. **Treat
it like a password.**

### 3. Connect from VS Code

1. Install the **My_AI Relay** extension.
2. Open the **My_AI Relay** view in the Activity Bar (the small assistant
   icon, by default on the left). On first activation the extension will
   ask if you want to move the chat to the **Secondary Side Bar** (right
   side, like GitHub Copilot Chat) — accept and VS Code will remember the
   placement.
3. Click **Paste connection string…** (or run *My_AI Relay: Connect* from the
   Command Palette) and paste the string from step 2.

The chat is now live. The same conversation is visible on the host's GUI and
on any mobile that has scanned the QR code.

> **Tip — moving the chat later.** VS Code's extension API only allows
> custom views to be contributed to the Activity Bar or Panel; the
> Secondary Side Bar is reserved for user-driven layout. If you missed the
> initial prompt, run *My_AI Relay: Move Chat to Secondary Side Bar* from
> the Command Palette, or right-click the My_AI Relay icon → "Move To" →
> "Secondary Side Bar".

## Agentic mode

When the extension connects, it tells the Relay it is a VS Code client.
From that point on, every prompt goes through an agentic loop on the host:
the local LLM can emit tool calls, the extension executes them inside your
workspace, and the result is fed back to the model until it gives a final
answer.

### Available tools

| Tool | Description |
| --- | --- |
| `read_file` | Read a workspace file (with `offset` / `limit` for big files). |
| `write_file` | Create or overwrite a file. Auto-creates parent folders. ⚠ |
| `edit_file` | Exact-match replace inside an existing file (`replace_all` optional). ⚠ |
| `list_dir` | List the entries of a workspace folder. |
| `glob` | Find files matching a glob (`**/*.ts`, `src/**/index.*`, …). |
| `grep` | Search file contents with ripgrep, falls back to a JS scan. |
| `run_command` | Run a shell command in the workspace. ⚠ |
| `get_active_editor` | Read the currently open file and the user's selection. |
| `open_file` | Open a workspace file in the editor (and reveal an optional line). |

⚠ = requires explicit user approval (modal dialog).

### Sandbox & approvals

- **Workspace-scoped by default.** Any path is resolved against the first
  workspace folder. A path that escapes the root triggers a modal asking
  for one-shot permission — there is no "remember" option for out-of-
  workspace access.
- **Read-only tools** (`read_file`, `list_dir`, `glob`, `grep`,
  `get_active_editor`, `open_file`) run silently.
- **Mutating tools** (`write_file`, `edit_file`, `run_command`) prompt for
  approval. The dialog offers three options besides denial:
  - *Allow once* — single-call exception.
  - *Allow for this file* — auto-approves the same tool on the same path
    for the rest of the session (not available for `run_command`).
  - *Allow all <tool> this session* — auto-approves the tool everywhere
    until disconnect/reconnect.
- Approvals reset on every reconnect.

### Tool cards in the chat

Each tool call renders as a foldable card with a colored left border:

- **Orange** — running.
- **Indigo** — awaiting approval.
- **Green** — completed.
- **Red** — failed.
- **Gray** — denied by the user.

Click the header to expand the input (JSON args) and the output
(stdout/stderr for shell commands, file diffs for edits, etc.).

### Conversation memory

The agentic context is preserved for the whole WebSocket session. You can
say *"now edit the file you just read"* and the model will remember the
previous tool calls. Reconnecting starts a fresh agentic conversation.

## Workspace features

- **Auto-attach active file** — toggle in the chat header. Every message you
  send will silently upload the currently active editor file before delivery.
  Useful when you want the model to keep up with what you're working on.
- **Send selection** — Command Palette → *My_AI Relay: Send Selection to
  My_AI*, or right-click in the editor. Fences the selection with the
  current language for clean rendering.
- **Send active file** — Command Palette → *My_AI Relay: Send Active File to
  My_AI*. Uploads the whole file as an attachment (PDF, DOCX, code, image…).
- **Insert at cursor / Copy** — every code block in an AI reply gets these
  two buttons on hover.

## Commands

| Command | Description |
| --- | --- |
| `My_AI Relay: Connect` | Paste a connection string and start a session. |
| `My_AI Relay: Disconnect` | Close the current session (keeps credentials). |
| `My_AI Relay: Forget Saved Connection` | Delete credentials from SecretStorage. |
| `My_AI Relay: Send Selection to My_AI` | Send the editor selection as a message. |
| `My_AI Relay: Send Active File to My_AI` | Upload and send the current file. |
| `My_AI Relay: Toggle Auto-Attach Active File` | Toggle the auto-attach feature. |
| `My_AI Relay: Open Chat View` | Reveal the chat panel. |
| `My_AI Relay: Move Chat to Secondary Side Bar` | Open VS Code's "Move View" picker pre-selected on the chat view. |

## Settings

| Setting | Default | Description |
| --- | --- | --- |
| `myaiRelay.openInSecondarySidebar` | `true` | On first activation, offer to move the chat to the Secondary Side Bar. |
| `myaiRelay.healthCheckIntervalSeconds` | `10` | Polling interval for tunnel health. |
| `myaiRelay.autoReconnect` | `true` | Reconnect automatically when the host Relay restarts. |
| `myaiRelay.requestTimeoutSeconds` | `15` | Per-request HTTP timeout. |

## Security model

- The connection string contains the AES key. Anyone with it can decrypt
  every message of that Relay session. **Don't share it.**
- Credentials are persisted in VS Code's
  [`SecretStorage`](https://code.visualstudio.com/api/references/vscode-api#SecretStorage)
  — encrypted by the OS keychain, scoped per machine + user.
- The tunnel server (Cloudflare / serveo / localhost.run) sees ciphertext
  only. The IP of your host PC is hidden behind the tunnel.
- Stopping the Relay on the host PC invalidates the encryption key and the
  tunnels. The extension detects this within ~30 s and shows "offline".
- **Workspace isolation.** The agentic mode runs all tools client-side
  inside the VS Code extension. The host's full PC access (the local MCPs
  used by the desktop GUI and the mobile UI) is **not** reachable from the
  VS Code chat. The model can only touch files reachable through the
  workspace tools, which are themselves bounded by the workspace root and
  guarded by the approval flow.

## Troubleshooting

- **"No tunnel reachable"** — the host PC is offline, the Relay was stopped,
  or your local network blocks all three providers. Try restarting the Relay.
- **"E2EE decrypt failed"** — the connection string is from a previous Relay
  session (the AES key is regenerated on every Relay start). Copy a fresh
  string and reconnect.
- **Health check too sensitive** — raise
  `myaiRelay.healthCheckIntervalSeconds` if you have a flaky link.

## Development

```bash
cd vscode_extension
npm install
npm run watch       # esbuild in watch mode
# Press F5 in VS Code to launch an extension host
```

Package a VSIX:

```bash
npm run package
```

## License

[MIT](./LICENSE) © gonicolas12
