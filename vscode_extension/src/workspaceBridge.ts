import * as path from 'path';
import * as vscode from 'vscode';
import { ConnectionManager } from './connectionManager';

const AUTO_ATTACH_KEY = 'myaiRelay.autoAttachActiveFile';
const MAX_FILE_BYTES = 25 * 1024 * 1024;

const TEXT_EXTENSIONS = new Set([
  '.txt', '.md', '.py', '.js', '.ts', '.tsx', '.jsx', '.html', '.css',
  '.json', '.xml', '.yaml', '.yml', '.csv', '.ini', '.toml', '.sh',
  '.bat', '.ps1', '.c', '.cpp', '.h', '.hpp', '.java', '.kt', '.go',
  '.rs', '.rb', '.php', '.sql',
]);

const SUPPORTED_BINARY_EXTENSIONS = new Set([
  '.pdf', '.docx', '.doc', '.xlsx', '.xls',
  '.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp', '.tiff', '.tif',
]);

export class WorkspaceBridge {
  private context: vscode.ExtensionContext;
  private manager: ConnectionManager;

  constructor(context: vscode.ExtensionContext, manager: ConnectionManager) {
    this.context = context;
    this.manager = manager;
  }

  isAutoAttachEnabled(): boolean {
    return this.context.workspaceState.get<boolean>(AUTO_ATTACH_KEY, false);
  }

  async setAutoAttach(value: boolean): Promise<void> {
    await this.context.workspaceState.update(AUTO_ATTACH_KEY, value);
  }

  async toggleAutoAttach(): Promise<boolean> {
    const next = !this.isAutoAttachEnabled();
    await this.setAutoAttach(next);
    return next;
  }

  /**
   * Reads the active editor file (or any document) and uploads it via the
   * Relay /api/upload endpoint. Returns the resolved file_id and metadata.
   *
   * `silentSizeReject` controls whether oversized files surface a UI error
   * (true for explicit user actions, false for silent auto-attach).
   */
  async attachDocument(
    document: vscode.TextDocument,
    options: { silentSizeReject?: boolean } = {},
  ): Promise<{ fileId: string; filename: string; isImage: boolean } | null> {
    const filename = path.basename(document.fileName) || 'untitled.txt';
    const ext = path.extname(filename).toLowerCase();
    const looksTextual = TEXT_EXTENSIONS.has(ext) || ext === '';

    let bytes: Uint8Array;
    if (looksTextual) {
      bytes = new TextEncoder().encode(document.getText());
    } else if (SUPPORTED_BINARY_EXTENSIONS.has(ext)) {
      try {
        const raw = await vscode.workspace.fs.readFile(document.uri);
        bytes = new Uint8Array(raw);
      } catch (err) {
        vscode.window.showErrorMessage(
          vscode.l10n.t('My_AI Relay: cannot read file: {0}', (err as Error).message),
        );
        return null;
      }
    } else {
      vscode.window.showWarningMessage(
        vscode.l10n.t('My_AI Relay: unsupported extension "{0}".', ext || 'unknown'),
      );
      return null;
    }

    if (bytes.length > MAX_FILE_BYTES) {
      if (!options.silentSizeReject) {
        vscode.window.showErrorMessage(
          vscode.l10n.t(
            'My_AI Relay: file too large ({0} MB > 25 MB).',
            String(Math.round(bytes.length / 1024 / 1024)),
          ),
        );
      }
      return null;
    }

    const result = await this.manager.uploadFile(filename, bytes);
    return {
      fileId: result.fileId,
      filename: result.filename,
      isImage: result.isImage,
    };
  }

  /**
   * Send the active editor's selection (or full file) as a chat message,
   * with the file attached so the model has full context.
   */
  async sendSelection(): Promise<void> {
    const editor = vscode.window.activeTextEditor;
    if (!editor) {
      vscode.window.showWarningMessage(vscode.l10n.t('My_AI Relay: no active editor.'));
      return;
    }
    const sel = editor.selection;
    const selectionText = sel.isEmpty ? '' : editor.document.getText(sel);
    const filename = path.basename(editor.document.fileName) || 'snippet';

    const language = editor.document.languageId || '';
    const fence = '```' + language;
    const message = selectionText
      ? `${vscode.l10n.t('Here is a snippet from `{0}`:', filename)}\n${fence}\n${selectionText}\n\`\`\``
      : vscode.l10n.t('Please look at `{0}`.', filename);

    await vscode.commands.executeCommand('myai-relay.focusChat');
    await this.manager.sendChat(message);
  }

  async sendActiveFile(): Promise<void> {
    const editor = vscode.window.activeTextEditor;
    if (!editor) {
      vscode.window.showWarningMessage(vscode.l10n.t('My_AI Relay: no active editor.'));
      return;
    }
    const attached = await this.attachDocument(editor.document);
    if (!attached) {
      return;
    }
    await vscode.commands.executeCommand('myai-relay.focusChat');
    await this.manager.sendChat(
      vscode.l10n.t('Please review the attached file `{0}`.', attached.filename),
      [attached.fileId],
    );
  }

  async insertAtCursor(code: string): Promise<void> {
    const editor = vscode.window.activeTextEditor;
    if (!editor) {
      vscode.window.showWarningMessage(
        vscode.l10n.t('My_AI Relay: no active editor — open a file to insert code into.'),
      );
      return;
    }
    await editor.edit((edit) => {
      edit.replace(editor.selection, code);
    });
  }

  /**
   * Helper used by the chat view: when the user submits a message and
   * auto-attach is on, upload the active file first and prepend its file_id.
   */
  async maybeAutoAttachActiveFile(): Promise<string[]> {
    if (!this.isAutoAttachEnabled()) {
      return [];
    }
    const editor = vscode.window.activeTextEditor;
    if (!editor) {
      return [];
    }
    try {
      const attached = await this.attachDocument(editor.document, {
        silentSizeReject: true,
      });
      return attached ? [attached.fileId] : [];
    } catch (err) {
      vscode.window.showWarningMessage(
        vscode.l10n.t('My_AI Relay: auto-attach failed: {0}', (err as Error).message),
      );
      return [];
    }
  }
}
