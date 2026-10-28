/*
 * Page Code : la conversation de l'extension VS Code, ouverte du bouton « Code »
 * de la barre latérale. Les messages envoyés et reçus dans VS Code y sont, ceux
 * du téléphone aussi ; un message tapé ici part à l'extension, qui agit dans
 * son workspace (lecture, écriture, commandes), réponse en streaming. Même
 * interface que le chat, adaptée au code : appels d'outils de VS Code, leurs
 * approbations, dossier ouvert dans VS Code. Des fichiers déposés sur la page
 * deviennent des pièces jointes du prochain message.
 */

import { CodeXml, TriangleAlert } from 'lucide-react';
import { useEffect } from 'react';

import { Button } from '../../components/ui/Button';
import { useT } from '../../i18n';
import { useApp } from '../../stores/app';
import {
  addCodePaths,
  loadCode,
  setCodeDropping,
  uploadCodeFiles,
  useCode,
} from '../../stores/code';
import { openPanel } from '../../stores/panels';
import { type DropTarget, useFileDrop } from '../chat/useFileDrop';
import { CodeComposer } from './CodeComposer';
import { CodeThread } from './CodeThread';

const CODE_DROP: DropTarget = {
  onPaths: (paths) => void addCodePaths(paths),
  onFiles: (files) => void uploadCodeFiles(files),
  setDropping: setCodeDropping,
};

/** VS Code absent : pourquoi rien ne part, et comment le connecter */
function VscodeBanner() {
  const t = useT();
  const vscode = useCode((state) => state.state.vscode);
  const relayRunning = useApp((state) => Boolean(state.relay?.running));
  if (vscode) return null;
  return (
    <div className="mx-auto mt-2 flex w-full max-w-[var(--chat-column)] items-start gap-2 rounded-md border border-warning/40 bg-warning-soft px-3 py-2 text-sm text-fg">
      <TriangleAlert size={16} className="mt-0.5 shrink-0 text-warning" />
      <div className="min-w-0 flex-1">
        <p className="font-medium">
          {relayRunning ? t('code.vscodeOffline') : t('code.relayStopped')}
        </p>
        <p className="mt-0.5 text-fg-2">{t('code.vscodeOfflineHint')}</p>
      </div>
      {!relayRunning ? (
        <Button size="sm" variant="secondary" onClick={() => openPanel('relay')}>
          {t('code.openRelay')}
        </Button>
      ) : null}
    </div>
  );
}

function CodeHome() {
  const t = useT();
  return (
    <div className="flex min-h-0 flex-1 flex-col items-center justify-center overflow-y-auto px-6 pb-[12vh]">
      <div
        className="flex w-full flex-col items-center"
        style={{ animation: 'rise-in var(--motion) var(--motion-ease)' }}
      >
        <CodeXml size={72} strokeWidth={1.6} className="text-accent" aria-hidden />
        <h1 className="mt-4 text-display leading-none font-bold tracking-tight text-fg">
          {t('code.title')}
        </h1>
        <p className="mt-3 mb-8 max-w-[var(--chat-column)] text-center text-sm text-fg-2">
          {t('code.subtitle')}
        </p>
        <CodeComposer variant="home" />
      </div>
    </div>
  );
}

export function CodePage() {
  const drop = useFileDrop('code', CODE_DROP);
  const loaded = useCode((state) => state.loaded);
  const empty = useCode((state) => state.messages.length === 0);

  // À chaque ouverture : la conversation telle qu'elle est (VS Code, téléphone)
  useEffect(() => {
    void loadCode();
  }, []);

  return (
    <div className="flex min-h-0 flex-1 flex-col" {...drop}>
      <VscodeBanner />
      {!loaded ? null : empty ? (
        <CodeHome />
      ) : (
        <>
          <CodeThread />
          <CodeComposer variant="dock" />
        </>
      )}
    </div>
  );
}
