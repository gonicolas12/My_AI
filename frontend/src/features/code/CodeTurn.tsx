import { CircleAlert, CodeXml, OctagonX, Smartphone } from 'lucide-react';
import { memo } from 'react';

import { useT } from '../../i18n';
import type { CodeAssistantMessage, CodeUserMessage } from '../../lib/events';
import { formatDuration, formatTime } from '../../lib/format';
import { Activity } from '../chat/AssistantMessage';
import { Markdown } from '../chat/markdown/Markdown';
import { CopyButton, MessageActions } from '../chat/MessageActions';
import { CodeToolRow } from './CodeToolRow';

const OPEN_TOOL = new Set(['requested', 'running', 'awaiting-approval']);

/**
 * Message de l'utilisateur. Celui tapé dans VS Code ou sur le téléphone porte
 * sa provenance, comme un message du téléphone dans le chat.
 */
export const CodeUserBubble = memo(function CodeUserBubble({
  message,
}: {
  message: CodeUserMessage;
}) {
  const t = useT();
  const body = [message.text, ...message.attachments.map((name) => `📎 ${name}`)]
    .filter(Boolean)
    .join('\n');
  return (
    <div className="group/msg flex flex-col items-end py-3">
      {message.origin !== 'desktop' ? (
        <span className="mb-1.5 inline-flex items-center gap-1 rounded-full border border-line px-2 py-0.5 text-2xs font-medium text-fg-2">
          {message.origin === 'mobile' ? <Smartphone size={11} /> : <CodeXml size={11} />}
          {t(message.origin === 'mobile' ? 'chat.queue.mobile' : 'code.origin.vscode')}
        </span>
      ) : null}
      <div className="max-w-[85%] rounded-xl rounded-ee-sm bg-user px-4 py-2.5 text-chat leading-relaxed break-words whitespace-pre-wrap text-on-user">
        {body}
      </div>
      <MessageActions align="end" meta={formatTime(message.timestamp)}>
        <CopyButton text={message.text} label={t('chat.message.copyUser')} />
      </MessageActions>
    </div>
  );
});

/**
 * Réponse : le texte de chaque passe du modèle, avec entre elles les appels
 * d'outils que l'extension exécute dans VS Code, dans l'ordre.
 */
export const CodeReply = memo(function CodeReply({
  message,
  isLast,
}: {
  message: CodeAssistantMessage;
  isLast: boolean;
}) {
  const t = useT();
  const streaming = message.status === 'streaming';
  const { parts } = message;
  const texts = parts.filter((part) => part.kind === 'text');
  const last = parts[parts.length - 1];
  // Réponse terminée sans texte en streaming : son texte final
  const finalText = !texts.length && message.status === 'done' ? message.text : '';
  // Rien ne bouge à l'écran (début, entre deux outils) : le robot s'anime
  const working = streaming && (!last || (last.kind === 'tool' && !OPEN_TOOL.has(last.status)));
  const copied = texts.map((part) => part.text).join('\n\n') || finalText;
  const meta = [
    formatTime(message.timestamp),
    message.duration_ms ? formatDuration(message.duration_ms) : '',
  ]
    .filter(Boolean)
    .join(' · ');

  return (
    <article className="group/msg py-3" aria-busy={streaming}>
      {parts.map((part, index) =>
        part.kind === 'text' ? (
          <Markdown
            key={`t${part.segment}`}
            text={part.text}
            streaming={streaming && index === parts.length - 1}
          />
        ) : (
          <CodeToolRow key={part.call_id} tool={part} />
        ),
      )}
      {finalText ? <Markdown text={finalText} /> : null}
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
