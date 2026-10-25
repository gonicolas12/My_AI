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
import { type MessageKey, shortcutLabel, useT } from '../../../i18n';
import { closePanel } from '../../../stores/panels';
import { PanelDialog } from '../PanelDialog';

const SECTIONS: { icon: LucideIcon; title: MessageKey; lines: MessageKey[] }[] = [
  {
    icon: MessageSquare,
    title: 'help.chat.title',
    lines: ['help.chat.1', 'help.chat.2', 'help.chat.3', 'help.chat.4', 'help.chat.5'],
  },
  {
    icon: PenLine,
    title: 'help.edit.title',
    lines: ['help.edit.1', 'help.edit.2', 'help.edit.3'],
  },
  {
    icon: Paperclip,
    title: 'help.attach.title',
    lines: ['help.attach.1', 'help.attach.2', 'help.attach.3', 'help.attach.4'],
  },
  {
    icon: Globe,
    title: 'help.web.title',
    lines: ['help.web.1', 'help.web.2'],
  },
  {
    icon: Bot,
    title: 'help.agents.title',
    lines: ['help.agents.1', 'help.agents.2'],
  },
  {
    icon: Puzzle,
    title: 'help.other.title',
    lines: [
      'help.other.1',
      'help.other.2',
      'help.other.3',
      'help.other.4',
      'help.other.5',
      'help.other.6',
    ],
  },
];

/** Raccourcis (touches en anglais, affichées dans la langue de l'interface) */
const SHORTCUTS: [string, MessageKey][] = [
  ['Ctrl+K', 'help.shortcut.palette'],
  ['Enter', 'help.shortcut.send'],
  ['Shift+Enter', 'help.shortcut.newline'],
  ['Escape', 'help.shortcut.stop'],
  ['Ctrl+N', 'help.shortcut.newConversation'],
  ['Ctrl+S', 'help.shortcut.save'],
  ['Ctrl+B', 'help.shortcut.sidebar'],
  ['Ctrl+R', 'help.shortcut.relay'],
  ['Ctrl+,', 'help.shortcut.settings'],
  ['Ctrl+L', 'help.shortcut.clear'],
  ['F1', 'help.shortcut.help'],
];

export default function HelpPanel() {
  const t = useT();
  return (
    <PanelDialog
      open
      onOpenChange={(open) => {
        if (!open) closePanel();
      }}
      icon={CircleHelp}
      title={t('help.title')}
      description={t('help.description')}
      width={720}
      footer={
        <Button variant="primary" onClick={closePanel}>
          {t('common.close')}
        </Button>
      }
    >
      <div className="space-y-5">
        {SECTIONS.map(({ icon: Icon, title, lines }) => (
          <section key={title}>
            <h3 className="flex items-center gap-2 text-sm font-semibold text-accent">
              <Icon size={16} /> {t(title)}
            </h3>
            <ul className="mt-2 space-y-1 ps-6 text-sm leading-relaxed text-fg">
              {lines.map((line) => (
                <li key={line} className="list-disc marker:text-fg-3">
                  {t(line)}
                </li>
              ))}
            </ul>
          </section>
        ))}
        <section>
          <h3 className="flex items-center gap-2 text-sm font-semibold text-accent">
            <Keyboard size={16} /> {t('help.shortcuts.title')}
          </h3>
          <dl className="mt-2 grid grid-cols-[9rem_1fr] gap-x-4 gap-y-1.5 ps-6 text-sm">
            {SHORTCUTS.map(([keys, label]) => (
              <div key={keys} className="contents">
                <dt>
                  <kbd className="rounded-sm border border-line bg-bg-3 px-1.5 py-0.5 font-mono text-xs font-semibold text-accent">
                    {shortcutLabel(keys, t)}
                  </kbd>
                </dt>
                <dd className="text-fg">{t(label)}</dd>
              </div>
            ))}
          </dl>
        </section>
      </div>
    </PanelDialog>
  );
}
