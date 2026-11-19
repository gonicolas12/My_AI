/*
 * A file or folder a reply cites, in the system's file explorer, as on the PC
 * (utils/path_links.reveal_in_file_manager): a folder is opened, a file is
 * selected in its folder (VS Code's « Reveal in File Explorer »). Nothing is
 * ever opened in its application nor run.
 */

import * as vscode from 'vscode';
import { t } from './i18n';

export async function revealInOS(target: unknown): Promise<void> {
  if (typeof target !== 'string' || !target) {
    return;
  }
  const uri = vscode.Uri.file(target);
  let stat: vscode.FileStat;
  try {
    stat = await vscode.workspace.fs.stat(uri);
  } catch {
    vscode.window.showWarningMessage(t('File not found.'));
    return;
  }
  // A folder only: opened by the system like a double-click (a file would run)
  if ((stat.type & vscode.FileType.Directory) && await vscode.env.openExternal(uri)) {
    return;
  }
  await vscode.commands.executeCommand('revealFileInOS', uri);
}
