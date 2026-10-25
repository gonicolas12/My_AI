/*
 * Menu « + » de la zone de saisie : les entrées de l'interface Tk (PDF, DOCX,
 * Excel / CSV, PowerPoint, Code, Image, Dossier). Il s'ouvre vers le haut.
 */

import { FolderOpen, Plus } from 'lucide-react';
import { useRef } from 'react';

import { IconButton } from '../../components/ui/Button';
import { Menu, MenuContent, MenuItem, MenuSeparator, MenuTrigger } from '../../components/ui/Menu';
import { useT } from '../../i18n';
import { type AttachKind, shell } from '../../lib/shell';
import { ACCEPT, attachPaths, uploadFiles } from './attach';
import { ATTACH_ENTRIES } from './attachKinds';

interface AttachMenuProps {
  /** Dossier (codebase) : section « Dossiers du projet » de la barre latérale */
  onAttachFolder?: (() => void) | undefined;
}

export function AttachMenu({ onAttachFolder }: AttachMenuProps) {
  const t = useT();
  const input = useRef<HTMLInputElement>(null);

  const choose = (kind: AttachKind) => {
    if (shell.canPickFiles()) {
      void shell.pickFiles(kind).then((paths) => attachPaths(paths, kind));
      return;
    }
    // Navigateur (repli sans pywebview) : sélecteur de fichiers de la page
    const element = input.current;
    if (!element) return;
    element.accept = ACCEPT[kind];
    element.multiple = kind !== 'Image';
    element.click();
  };

  return (
    <>
      <Menu>
        <MenuTrigger asChild>
          <IconButton label={t('chat.attach.button')} tooltipSide="top">
            <Plus size={18} />
          </IconButton>
        </MenuTrigger>
        <MenuContent side="top" label={t('chat.attach.menu')}>
          {ATTACH_ENTRIES.map(({ kind, label, icon: Icon }) => (
            <MenuItem key={kind} icon={<Icon size={15} />} onSelect={() => choose(kind)}>
              {t(label)}
            </MenuItem>
          ))}
          <MenuSeparator />
          <MenuItem
            icon={<FolderOpen size={15} />}
            disabled={!onAttachFolder}
            onSelect={() => onAttachFolder?.()}
          >
            {t('chat.attach.folder')}
          </MenuItem>
        </MenuContent>
      </Menu>
      <input
        ref={input}
        type="file"
        hidden
        onChange={(event) => {
          const files = Array.from(event.target.files ?? []);
          event.target.value = '';
          void uploadFiles(files);
        }}
      />
    </>
  );
}
