import { Bot } from 'lucide-react';

/** Page Agents : construite à la phase 4 (grille, canvas, exécutions, débat) */
export function AgentsPage() {
  return (
    <div className="flex flex-1 flex-col items-center justify-center gap-3 px-6 text-center">
      <Bot size={40} className="text-fg-3" />
      <p className="text-lg font-semibold text-fg">Page Agents</p>
      <p className="max-w-sm text-sm text-fg-2">
        Elle arrive à la phase 4 de la migration. En attendant, la page Agents de l'interface Tk
        reste disponible avec <code className="font-mono text-fg">--ui tk</code>.
      </p>
    </div>
  );
}
