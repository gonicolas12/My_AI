import { setSidebarOpen } from '../../../lib/actions';
import { shell } from '../../../lib/shell';
import { notify } from '../../../stores/app';
import { attachFolder } from '../../../stores/sidebar';

/**
 * Attache un dossier entier (codebase, documents) à la session : choisi dans
 * le dialogue du système, indexé en arrière-plan. Menu « + » (Dossier) et
 * section « Dossiers du projet » : la barre latérale s'ouvre sur sa progression.
 */
export async function attachProjectFolder(): Promise<void> {
  if (!shell.canPickFiles()) {
    notify('info', 'Le choix d’un dossier se fait dans la fenêtre de l’appli.');
    return;
  }
  const path = await shell.pickFolder();
  if (!path) return;
  setSidebarOpen(true);
  await attachFolder(path);
}
