import { TriangleAlert } from 'lucide-react';

import { useApp } from '../../stores/app';
import { useChat } from '../../stores/chat';
import { isGenerating } from '../../stores/chatReducer';
import { PreviewPane } from '../preview/PreviewPane';
import { useAutoOpenArtifacts } from '../preview/useAutoOpen';
import { Composer } from './Composer';
import { ConfirmDeleteDialog } from './ConfirmDeleteDialog';
import { HomeScreen } from './HomeScreen';
import { Thread } from './Thread';
import { useFileDrop } from './useFileDrop';

const OLLAMA_DOWN = "Ollama n'a pas pu démarrer — lancez l'application Ollama ou « ollama serve »";

function OllamaBanner() {
  const status = useApp((state) => state.status);
  if (!status || status.ollama) return null;
  return (
    <div className="mx-auto mt-2 flex w-full max-w-[var(--chat-column)] items-start gap-2 rounded-md border border-warning/40 bg-warning-soft px-3 py-2 text-sm text-fg">
      <TriangleAlert size={16} className="mt-0.5 shrink-0 text-warning" />
      <span>{status.error ?? OLLAMA_DOWN}</span>
    </div>
  );
}

export function ChatPage() {
  useAutoOpenArtifacts();
  const drop = useFileDrop('chat');
  const empty = useChat((state) => state.messages.length === 0 && !isGenerating(state));
  return (
    <div className="flex min-h-0 flex-1">
      <div className="flex min-w-0 flex-1 flex-col" {...drop}>
        <OllamaBanner />
        {empty ? (
          <HomeScreen />
        ) : (
          <>
            <Thread />
            <Composer variant="dock" />
          </>
        )}
      </div>
      <PreviewPane />
      <ConfirmDeleteDialog />
    </div>
  );
}
