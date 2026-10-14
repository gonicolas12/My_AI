/*
 * Aide (F1) : le texte de show_help (interfaces/gui/base.py), mis à jour là
 * où l'interface web fait autrement (copie au survol, Échap arrête la réponse,
 * dossier glissé, régénération).
 */

import {
  Bot,
  CircleHelp,
  Globe,
  Keyboard,
  MessageSquare,
  Paperclip,
  PenLine,
  Puzzle,
  type LucideIcon,
} from 'lucide-react';

import { Button } from '../../../components/ui/Button';
import { closePanel } from '../../../stores/panels';
import { PanelDialog } from '../PanelDialog';

const SECTIONS: { icon: LucideIcon; title: string; lines: string[] }[] = [
  {
    icon: MessageSquare,
    title: 'Chat',
    lines: [
      "Tapez votre message et appuyez sur Entrée pour l'envoyer.",
      'Maj+Entrée insère un saut de ligne sans envoyer.',
      'Survolez un message pour le copier, le lire à voix haute ou le modifier.',
      "Notez les réponses de 1 à 5 étoiles pour améliorer l'IA.",
      'Échap ou le bouton Stop arrête la réponse en cours.',
    ],
  },
  {
    icon: PenLine,
    title: 'Éditer & regénérer',
    lines: [
      'Sous chaque message envoyé, « Modifier » réécrit la demande et regénère la réponse.',
      'Sous chaque réponse, « Régénérer » en propose une nouvelle version.',
      "L'ancienne version est conservée : naviguez entre les variantes avec ‹ k/n ›.",
    ],
  },
  {
    icon: Paperclip,
    title: 'Pièces jointes & documents',
    lines: [
      'Bouton « + » : joindre un PDF, DOCX, Excel/CSV, PowerPoint, du code, une image ou un dossier (codebase).',
      'Posez ensuite vos questions sur le contenu attaché (RAG local).',
      'Glisser-déposer de fichiers également pris en charge ; un dossier glissé joint ses fichiers.',
      'Ctrl+V colle une image copiée.',
    ],
  },
  {
    icon: Globe,
    title: 'Recherche web & citations',
    lines: [
      'Ex. « Cherche sur internet les actualités IA ».',
      'Les sources apparaissent numérotées ; cliquez sur un [n] pour ouvrir le lien.',
    ],
  },
  {
    icon: Bot,
    title: 'Agents',
    lines: [
      'Onglet « Agents » : composez des workflows (un ou plusieurs agents).',
      "Une notification système prévient à la fin d'une tâche longue.",
    ],
  },
  {
    icon: Puzzle,
    title: 'Autres fonctions',
    lines: [
      "Relay : accédez à l'assistant depuis votre téléphone.",
      'Prompts : modèles réutilisables (commandes /xxx).',
      'Mémoire : faits et documents mémorisés.',
      'Lecture vocale et saisie vocale.',
      "Génération d'image (« génère une image de … »).",
    ],
  },
];

const SHORTCUTS: [string, string][] = [
  ['Ctrl+K', 'Palette de commandes'],
  ['Entrée', 'Envoyer le message'],
  ['Maj+Entrée', 'Nouvelle ligne'],
  ['Échap', 'Arrêter la réponse en cours'],
  ['Ctrl+N', 'Nouvelle conversation'],
  ['Ctrl+S', 'Sauvegarder la session'],
  ['Ctrl+B', 'Afficher / masquer la barre latérale'],
  ['Ctrl+R', 'Relay (accès mobile)'],
  ['Ctrl+,', 'Réglages'],
  ['Ctrl+L', 'Effacer la conversation'],
  ['F1', 'Cette aide'],
];

export default function HelpPanel() {
  return (
    <PanelDialog
      open
      onOpenChange={(open) => {
        if (!open) closePanel();
      }}
      icon={CircleHelp}
      title="Aide — My_AI"
      description="Assistant IA personnel, 100 % local"
      width={720}
      footer={
        <Button variant="primary" onClick={closePanel}>
          Fermer
        </Button>
      }
    >
      <div className="space-y-5">
        {SECTIONS.map(({ icon: Icon, title, lines }) => (
          <section key={title}>
            <h3 className="flex items-center gap-2 text-sm font-semibold text-accent">
              <Icon size={16} /> {title}
            </h3>
            <ul className="mt-2 space-y-1 pl-6 text-sm leading-relaxed text-fg">
              {lines.map((line) => (
                <li key={line} className="list-disc marker:text-fg-3">
                  {line}
                </li>
              ))}
            </ul>
          </section>
        ))}
        <section>
          <h3 className="flex items-center gap-2 text-sm font-semibold text-accent">
            <Keyboard size={16} /> Raccourcis clavier
          </h3>
          <dl className="mt-2 grid grid-cols-[8rem_1fr] gap-x-4 gap-y-1.5 pl-6 text-sm">
            {SHORTCUTS.map(([keys, label]) => (
              <div key={keys} className="contents">
                <dt>
                  <kbd className="rounded-sm border border-line bg-bg-3 px-1.5 py-0.5 font-mono text-xs font-semibold text-accent">
                    {keys}
                  </kbd>
                </dt>
                <dd className="text-fg">{label}</dd>
              </div>
            ))}
          </dl>
        </section>
      </div>
    </PanelDialog>
  );
}
