import * as RadixDialog from '@radix-ui/react-dialog';
import { FolderOpen, SquareArrowOutUpRight, X } from 'lucide-react';

import { openFile, revealPath } from '../../lib/actions';
import { IconButton } from './Button';

interface LightboxProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  /** Lien signé de l'image (null tant qu'il n'est pas connu) */
  url: string | null;
  path: string;
  name: string;
  /** Produite par l'appli : elle s'ouvre aussi dans son application */
  generated: boolean;
}

/** Image en grand, dans la fenêtre de l'appli (clic sur une image générée ou jointe) */
export function Lightbox({ open, onOpenChange, url, path, name, generated }: LightboxProps) {
  return (
    <RadixDialog.Root open={open} onOpenChange={onOpenChange}>
      <RadixDialog.Portal>
        <RadixDialog.Overlay
          className="fixed inset-0 z-40 bg-scrim backdrop-blur-sm"
          style={{ animation: 'fade-in var(--motion) var(--motion-ease)' }}
        />
        <RadixDialog.Content
          className="fixed inset-0 z-50 flex flex-col focus:outline-none"
          style={{ animation: 'fade-in var(--motion) var(--motion-ease)' }}
          onClick={(event) => {
            // Clic à côté de l'image : fermeture
            if (event.target === event.currentTarget) onOpenChange(false);
          }}
        >
          <div className="flex h-14 shrink-0 items-center gap-2 px-4">
            <RadixDialog.Title className="min-w-0 flex-1 truncate text-sm font-medium text-fg">
              {name}
            </RadixDialog.Title>
            <RadixDialog.Description className="sr-only">Image en grand</RadixDialog.Description>
            {generated ? (
              <IconButton label="Ouvrir dans son application" onClick={() => void openFile(path)}>
                <SquareArrowOutUpRight size={16} />
              </IconButton>
            ) : null}
            <IconButton label="Afficher dans l’Explorateur" onClick={() => void revealPath(path)}>
              <FolderOpen size={16} />
            </IconButton>
            <RadixDialog.Close asChild>
              <IconButton label="Fermer" shortcut="Échap">
                <X size={18} />
              </IconButton>
            </RadixDialog.Close>
          </div>
          <div
            className="flex min-h-0 flex-1 items-center justify-center px-6 pb-6"
            onClick={(event) => {
              if (event.target === event.currentTarget) onOpenChange(false);
            }}
          >
            {url ? (
              <img
                src={url}
                alt={name}
                className="max-h-full max-w-full rounded-md object-contain shadow-lg"
                draggable={false}
              />
            ) : null}
          </div>
        </RadixDialog.Content>
      </RadixDialog.Portal>
    </RadixDialog.Root>
  );
}
