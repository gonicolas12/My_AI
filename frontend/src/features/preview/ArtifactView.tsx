/*
 * Bloc HTML ou SVG d'une réponse : sa page isolée (onglet Aperçu) ou son code
 * (onglet Code). Partagé par le volet de droite du chat (PreviewPane) et la
 * fenêtre au premier plan (AttachmentPreviewDialog, page Agents).
 *
 * La page s'affiche dans une iframe isolée, sans allow-same-origin : elle ne
 * peut ni lire l'appli ni appeler son API (cf. interfaces/desktop/previews.py).
 */

import { LoaderCircle } from 'lucide-react';

import { useT } from '../../i18n';
import type { Artifact } from '../../lib/artifacts';
import { cn } from '../../lib/cn';
import type { PreviewTab } from '../../stores/preview';
import { CodeBlock } from '../chat/markdown/CodeBlock';
import { usePreviewPage } from './usePreviewPage';

/** Iframe d'un artefact : scripts, formulaires, fenêtres (navigateur du système) */
const ARTIFACT_SANDBOX = 'allow-scripts allow-forms allow-modals allow-popups';

export function ArtifactView({
  artifact,
  tab,
  hidden,
}: {
  artifact: Artifact;
  tab: PreviewTab;
  /** Volet ou fenêtre en mouvement : la page ne prend pas les clics */
  hidden: boolean;
}) {
  const t = useT();
  const { view, error } = usePreviewPage(artifact);

  if (tab === 'code' && artifact.kind !== 'document') {
    return (
      <div className="md h-full overflow-auto p-3">
        <CodeBlock code={artifact.code} lang={artifact.language || artifact.kind} />
      </div>
    );
  }
  if (error) {
    return (
      <div className="flex h-full flex-col items-center justify-center gap-3 px-6 text-center text-sm text-fg-2">
        <span>{error}</span>
      </div>
    );
  }
  if (!view) {
    return (
      <div className="flex h-full items-center justify-center gap-2 text-sm text-fg-2">
        <LoaderCircle size={16} className="spin text-accent" />
        {t('preview.opening')}
      </div>
    );
  }
  return (
    <iframe
      key={view.id}
      src={view.url}
      title={view.title}
      // Pas d'allow-same-origin : la page ne peut ni lire l'appli ni appeler son API
      sandbox={ARTIFACT_SANDBOX}
      referrerPolicy="no-referrer"
      className={cn('h-full w-full border-0', hidden && 'pointer-events-none')}
    />
  );
}
