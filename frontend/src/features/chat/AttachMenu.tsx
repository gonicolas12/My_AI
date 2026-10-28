/*
 * Menu « + » de la zone de saisie : les entrées de l'interface Tk (PDF, DOCX,
 * Excel / CSV, PowerPoint, Code, Image, Dossier). Il s'ouvre vers le haut.
 * Les fichiers choisis deviennent des pièces jointes du chat, ou de la page
 * qui fournit les siens (page Code).
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
  /** Entrée Dossier (codebase) ; sans elle, le menu n'en a pas */
  onAttachFolder?: (() => void) | undefined;
  /** Fichiers choisis dans le dialogue du système (défaut : pièces jointes du chat) */
  onPaths?: (paths: string[], kind: AttachKind) => void;
  /** Fichiers choisis dans un navigateur, sans chemin (défaut : pièces jointes du chat) */
  onFiles?: (files: File[]) => void;
}

export function AttachMenu({
  onAttachFolder,
  onPaths = (paths, kind) => void attachPaths(paths, kind),
  onFiles = (files) => void uploadFiles(files),
}: AttachMenuProps) {
  const t = useT();
  const input = useRef<HTMLInputElement>(null);

  const choose = (kind: AttachKind) => {
    if (shell.canPickFiles()) {
      void shell.pickFiles(kind).then((paths) => onPaths(paths, kind));
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
          {onAttachFolder ? (
            <>
              <MenuSeparator />
              <MenuItem icon={<FolderOpen size={15} />} onSelect={onAttachFolder}>
                {t('chat.attach.folder')}
              </MenuItem>
            </>
          ) : null}
        </MenuContent>
      </Menu>
      <input
        ref={input}
        type="file"
        hidden
        onChange={(event) => {
          const files = Array.from(event.target.files ?? []);
          event.target.value = '';
          onFiles(files);
        }}
      />
    </>
  );
}
