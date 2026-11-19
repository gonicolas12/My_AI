/*
 * Pièce jointe d'un message envoyé, dans le chat et la page Code : son icône
 * (ou sa vignette pour une image) et son nom, qui ouvre son aperçu.
 */

import { createElement } from 'react';

import { useT } from '../../i18n';
import type { AttachmentRef } from '../../lib/events';
import { useFileUrl } from '../../lib/files';
import { attachmentIcon } from './attachKinds';

/**
 * Pièce jointe d'un message envoyé : comme un nom de fichier du chat, elle
 * s'ouvre dans le volet d'aperçu de droite, quel que soit son format (image,
 * code, PDF…) ; les pièces jointes du message s'y suivent (‹ k/n ›). Son type
 * (file_type_for de core/chat_service.py) choisit son icône.
 */
export function SentAttachment({
  attachment,
  onOpen,
}: {
  attachment: AttachmentRef;
  onOpen: () => void;
}) {
  const t = useT();
  const image = attachment.type === 'Image';
  const url = useFileUrl(image ? attachment.path : null);
  return (
    <button
      type="button"
      onClick={onOpen}
      title={t('chat.file.preview', { name: attachment.path })}
      className="group inline-flex h-9 max-w-64 items-center gap-2 rounded-md border border-line bg-bg-2 ps-1 pe-2.5 text-xs text-fg-2 transition-colors duration-150 hover:border-line-2 hover:text-fg"
    >
      <span className="flex h-7 w-7 shrink-0 items-center justify-center overflow-hidden rounded-xs bg-bg-3">
        {image && url ? (
          <img src={url} alt="" className="h-full w-full object-cover" draggable={false} />
        ) : (
          createElement(attachmentIcon(attachment.type), { size: 14 })
        )}
      </span>
      {/*
        Gris comme le reste du message ; bleu souligné sous la souris (ou au clavier).
        Sa couleur à lui, en fondu avec celui du bouton : héritée, elle repassait par
        son blanc de survol après avoir perdu le bleu. Le soulignement est toujours
        là, transparent au repos, pour se fondre lui aussi.
      */}
      <span className="truncate text-fg-2 underline decoration-transparent underline-offset-2 transition-colors duration-150 group-hover:text-link group-hover:decoration-link group-focus-visible:text-link group-focus-visible:decoration-link">
        {attachment.name}
      </span>
    </button>
  );
}
