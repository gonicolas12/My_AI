import { CircleAlert, CodeXml, OctagonX, Smartphone } from 'lucide-react';
import { memo, useCallback, useMemo } from 'react';

import { useLocale, useT } from '../../i18n';
import { fileArtifact, messageArtifacts } from '../../lib/artifacts';
import type { CodeAssistantMessage, CodeUserMessage } from '../../lib/events';
import { formatDuration, formatTime } from '../../lib/format';
import { openPreview } from '../../stores/preview';
import { Activity } from '../chat/AssistantMessage';
import { CodePreview } from '../chat/markdown/codePreview';
import { buildChatLinks } from '../chat/markdown/links';
import { Markdown } from '../chat/markdown/Markdown';
import { CopyButton, MessageActions } from '../chat/MessageActions';
import { SentAttachment } from '../chat/SentAttachment';
import { CodeToolRow } from './CodeToolRow';

const OPEN_TOOL = new Set(['requested', 'running', 'awaiting-approval']);

/**
 * Message de l'utilisateur. Celui tapé dans VS Code ou sur le téléphone porte
 * sa provenance, comme un message du téléphone dans le chat. Ses pièces
 * jointes s'ouvrent dans le volet de la page, comme celles du chat ; celles
 * d'une conversation d'avant leur aperçu (sans chemin) restent des noms.
 */
export const CodeUserBubble = memo(function CodeUserBubble({
  message,
}: {
  message: CodeUserMessage;
}) {
  const t = useT();
  const files = message.files ?? [];
  const named = files.length ? [] : message.attachments.map((name) => `📎 ${name}`);
  const body = [message.text, ...named].filter(Boolean).join('\n');
  return (
    <div className="group/msg flex flex-col items-end py-3">
      {message.origin !== 'desktop' ? (
        <span className="mb-1.5 inline-flex items-center gap-1 rounded-full border border-line px-2 py-0.5 text-2xs font-medium text-fg-2">
          {message.origin === 'mobile' ? <Smartphone size={11} /> : <CodeXml size={11} />}
          {t(message.origin === 'mobile' ? 'chat.queue.mobile' : 'code.origin.vscode')}
        </span>
      ) : null}
      {body ? (
        <div className="max-w-[85%] rounded-xl rounded-ee-sm bg-user px-4 py-2.5 text-chat leading-relaxed break-words whitespace-pre-wrap text-on-user">
          {body}
        </div>
      ) : null}
      {files.length ? (
        <div className="mt-1.5 flex max-w-[85%] flex-wrap justify-end gap-1.5">
          {files.map((file, index) => (
            <SentAttachment
              key={`${index}:${file.path}`}
              attachment={{ path: file.path, name: file.name, type: file.type ?? '' }}
              onOpen={() =>
                openPreview(
                  message.message_id,
                  files.map((item, at) => fileArtifact(item.path, false, at)),
                  index,
                )
              }
            />
          ))}
        </div>
      ) : null}
      <MessageActions align="end" meta={formatTime(message.timestamp)}>
        <CopyButton text={message.text} label={t('chat.message.copyUser')} />
      </MessageActions>
    </div>
  );
});

/**
 * Réponse : le texte de chaque passe du modèle, avec entre elles les appels
 * d'outils que l'extension exécute dans VS Code, dans l'ordre. Une fois
 * terminée, comme dans le chat : les fichiers qu'elle cite ou nomme
 * (« src/app.ts », « shell.ts ») s'ouvrent dans le volet de la page, et ses
 * blocs HTML ou SVG ont leur bouton « Aperçu ».
 */
export const CodeReply = memo(function CodeReply({
  message,
  isLast,
}: {
  message: CodeAssistantMessage;
  isLast: boolean;
}) {
  const t = useT();
  const locale = useLocale();
  const streaming = message.status === 'streaming';
  const { parts, paths } = message;
  const texts = parts.filter((part) => part.kind === 'text');
  const last = parts[parts.length - 1];
  // Réponse terminée sans texte en streaming : son texte final
  const finalText = !texts.length && message.status === 'done' ? message.text : '';
  // Rien ne bouge à l'écran (début, entre deux outils) : le robot s'anime
  const working = streaming && (!last || (last.kind === 'tool' && !OPEN_TOOL.has(last.status)));
  const copied = texts.map((part) => part.text).join('\n\n') || finalText;

  const links = useMemo(() => buildChatLinks('', paths), [paths]);
  // Blocs HTML ou SVG, une fois la réponse écrite ; leurs titres par défaut suivent la langue
  const artifacts = useMemo(
    () => (streaming || message.status === 'error' ? [] : messageArtifacts(copied, [])),
    // eslint-disable-next-line react-hooks/exhaustive-deps -- titres traduits
    [streaming, message.status, copied, locale],
  );
  // Son bouton « Aperçu » ouvre le volet sur lui (les autres blocs s'y suivent, ‹ k/n ›)
  const findPreview = useCallback(
    (code: string) => {
      const wanted = code.trim();
      const index = artifacts.findIndex(
        (artifact) => artifact.kind !== 'document' && artifact.code === wanted,
      );
      return index >= 0 ? () => openPreview(message.message_id, artifacts, index) : null;
    },
    [artifacts, message.message_id],
  );
  const meta = [
    formatTime(message.timestamp),
    message.duration_ms ? formatDuration(message.duration_ms) : '',
  ]
    .filter(Boolean)
    .join(' · ');

  return (
    <article className="group/msg py-3" aria-busy={streaming}>
      <CodePreview.Provider value={artifacts.length ? findPreview : null}>
        {parts.map((part, index) =>
          part.kind === 'text' ? (
            <Markdown
              key={`t${part.segment}`}
              text={part.text}
              streaming={streaming && index === parts.length - 1}
              links={links}
            />
          ) : (
            <CodeToolRow key={part.call_id} tool={part} />
          ),
        )}
        {finalText ? <Markdown text={finalText} links={links} /> : null}
      </CodePreview.Provider>
      {working ? <Activity label={t('code.activity.working')} /> : null}
      {message.status === 'error' ? (
        <div className="mt-1 flex items-start gap-2 rounded-md border border-error/40 bg-error-soft px-3 py-2 text-sm text-fg">
          <CircleAlert size={16} className="mt-0.5 shrink-0 text-error" />
          <span className="whitespace-pre-wrap">{message.text.replace(/^❌\s*/u, '')}</span>
        </div>
      ) : null}
      {message.status === 'stopped' ? (
        <div className="mt-1 inline-flex items-center gap-1.5 text-xs text-warning">
          <OctagonX size={13} />
          {t('chat.message.interrupted')}
        </div>
      ) : null}
      {!streaming && copied ? (
        <MessageActions meta={meta} pinned={isLast}>
          <CopyButton text={copied} label={t('chat.message.copyAnswer')} />
        </MessageActions>
      ) : null}
    </article>
  );
});
