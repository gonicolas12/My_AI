/*
 * Zone de tâche de la page Agents (task_input.py, file_handling.py de Tk).
 *
 * Texte de la tâche, pièces jointes en puces au-dessus (menu « + », collage
 * d'une image avec Ctrl+V, fichiers déposés), micro. À droite, un seul bouton
 * primaire, Exécuter, qui devient Arrêter pendant l'exécution ; Créer un
 * agent, Débat et Vider sont des boutons secondaires (§8). Ctrl+Entrée lance
 * aussi l'exécution.
 */

import { Eraser, Play, Plus, Square, Swords, X } from 'lucide-react';
import { createElement, useEffect, useRef, useState } from 'react';

import { Button, IconButton } from '../../components/ui/Button';
import { Menu, MenuContent, MenuItem, MenuTrigger } from '../../components/ui/Menu';
import { Tooltip } from '../../components/ui/Tooltip';
import { cn } from '../../lib/cn';
import { hasFiles, noteDrop, onDroppedPaths } from '../../lib/drops';
import { useFileUrl } from '../../lib/files';
import { type AttachKind, shell } from '../../lib/shell';
import {
  addTaskPaths,
  removeTaskAttachment,
  setTask,
  stopAgentsRun,
  type TaskAttachment,
  uploadTaskFiles,
  useAgents,
} from '../../stores/agents';
import { ACCEPT, CLIPBOARD_IMAGE, clipboardFiles, droppedFiles } from '../chat/attach';
import { ATTACH_ENTRIES, attachmentIcon } from '../chat/attachKinds';
import { MicButton } from '../chat/MessageControls';
import { AgentDialog } from './AgentDialog';
import { clearWorkflow } from './canvas/workflowStore';

const PLACEHOLDER = 'Décrivez la tâche à confier aux agents sélectionnés…';

/** Nom que Chromium donne à une image du presse-papiers (capture d'écran) */
const CHROMIUM_CLIPBOARD_NAME = 'image.png';

function Chip({ item }: { item: TaskAttachment }) {
  const image = item.type === 'Image';
  const url = useFileUrl(image ? item.path : null);
  return (
    <span
      title={item.path}
      className="inline-flex h-9 max-w-60 items-center gap-2 rounded-md border border-line bg-bg-3 pr-1 pl-1 text-xs text-fg-2"
    >
      <span className="flex h-7 w-7 shrink-0 items-center justify-center overflow-hidden rounded-xs bg-bg-2">
        {image && url ? (
          <img src={url} alt="" className="h-full w-full object-cover" draggable={false} />
        ) : (
          createElement(attachmentIcon(item.type), { size: 15 })
        )}
      </span>
      <span className="truncate">{item.name}</span>
      <button
        type="button"
        aria-label={`Retirer ${item.name}`}
        onClick={() => removeTaskAttachment(item.id)}
        className="shrink-0 rounded-xs p-1 text-fg-3 hover:bg-hover hover:text-fg"
      >
        <X size={12} />
      </button>
    </span>
  );
}

/** Menu « + » : les entrées de Tk (PDF, DOCX, Excel / CSV, PowerPoint, Code, Image) */
function AttachButton() {
  const input = useRef<HTMLInputElement>(null);
  const choose = (kind: AttachKind) => {
    if (shell.canPickFiles()) {
      void shell.pickFiles(kind).then((paths) => addTaskPaths(paths));
      return;
    }
    // Navigateur (repli sans pywebview) : sélecteur de fichiers de la page
    const element = input.current;
    if (!element) return;
    element.accept = ACCEPT[kind];
    element.multiple = true;
    element.click();
  };
  return (
    <>
      <Menu>
        <MenuTrigger asChild>
          <IconButton label="Joindre un fichier" tooltipSide="top">
            <Plus size={18} />
          </IconButton>
        </MenuTrigger>
        <MenuContent side="top" label="Joindre">
          {ATTACH_ENTRIES.map(({ kind, label, icon: Icon }) => (
            <MenuItem key={kind} icon={<Icon size={15} />} onSelect={() => choose(kind)}>
              {label}
            </MenuItem>
          ))}
        </MenuContent>
      </Menu>
      <input
        ref={input}
        type="file"
        hidden
        onChange={(event) => {
          const files = Array.from(event.target.files ?? []);
          event.target.value = '';
          void uploadTaskFiles(files);
        }}
      />
    </>
  );
}

interface TaskZoneProps {
  onExecute: () => void;
}

export function TaskZone({ onExecute }: TaskZoneProps) {
  const task = useAgents((state) => state.task);
  const attachments = useAgents((state) => state.attachments);
  const active = useAgents((state) => state.active);
  const starting = useAgents((state) => state.starting);
  const textarea = useRef<HTMLTextAreaElement>(null);
  const [dropping, setDropping] = useState(false);
  const [creating, setCreating] = useState(false);

  // Fichiers déposés dans la fenêtre de l'appli : leurs chemins arrivent par le serveur
  useEffect(() => onDroppedPaths('agents', (paths) => void addTaskPaths(paths)), []);

  /** Texte dicté : inséré au curseur, une espace devant s'il colle au mot précédent (Tk) */
  const insertDictation = (spoken: string) => {
    const element = textarea.current;
    const current = useAgents.getState().task;
    const at = element ? element.selectionStart : current.length;
    const before = current.slice(0, at);
    const inserted = (before && !/\s$/.test(before) ? ' ' : '') + spoken;
    setTask(before + inserted + current.slice(at));
    requestAnimationFrame(() => {
      if (!element) return;
      element.focus();
      const caret = before.length + inserted.length;
      element.setSelectionRange(caret, caret);
    });
  };

  const onPaste = (event: React.ClipboardEvent<HTMLTextAreaElement>) => {
    const files = clipboardFiles(event);
    // Du texte copié (même depuis Word, qui y joint une image) se colle comme du texte
    if (!files.length || event.clipboardData.getData('text/plain').trim()) return;
    event.preventDefault();
    for (const file of files) {
      const name = file.name === CHROMIUM_CLIPBOARD_NAME ? CLIPBOARD_IMAGE : file.name;
      void uploadTaskFiles([file], name);
    }
  };

  const running = active !== null;
  return (
    <div className="flex gap-3">
      <div
        className={cn(
          'flex min-h-[150px] min-w-0 flex-1 flex-col rounded-xl border bg-bg-2 shadow-sm transition-colors duration-150',
          dropping ? 'border-accent' : 'border-line focus-within:border-line-2',
        )}
        onDragOver={(event) => {
          if (!hasFiles(event)) return;
          event.preventDefault();
          event.dataTransfer.dropEffect = 'copy';
          setDropping(true);
        }}
        onDragLeave={(event) => {
          if (event.currentTarget.contains(event.relatedTarget as Node | null)) return;
          setDropping(false);
        }}
        onDrop={(event) => {
          setDropping(false);
          if (!hasFiles(event)) return;
          event.preventDefault();
          noteDrop('agents');
          // Navigateur : pas de chemin, le contenu part au serveur
          if (!shell.isDesktop()) void uploadTaskFiles(droppedFiles(event.dataTransfer));
        }}
      >
        {attachments.length ? (
          <div className="flex flex-wrap gap-1.5 px-3 pt-3">
            {attachments.map((item) => (
              <Chip key={item.id} item={item} />
            ))}
          </div>
        ) : null}
        <textarea
          ref={textarea}
          value={task}
          onChange={(event) => setTask(event.target.value)}
          onPaste={onPaste}
          onKeyDown={(event) => {
            if (event.key === 'Enter' && (event.ctrlKey || event.metaKey)) {
              event.preventDefault();
              onExecute();
            }
          }}
          placeholder={PLACEHOLDER}
          aria-label="Tâche"
          rows={3}
          className="block max-h-[280px] min-h-20 w-full flex-1 resize-none overflow-y-auto bg-transparent px-4 pt-3 text-chat leading-relaxed text-fg outline-none [field-sizing:content] placeholder:text-fg-3"
        />
        <div className="flex items-center gap-1 px-2.5 pt-1 pb-2">
          <AttachButton />
          <div className="flex-1" />
          <MicButton onTranscript={insertDictation} />
        </div>
      </div>

      <div className="flex w-48 shrink-0 flex-col gap-2">
        {running ? (
          <Tooltip label="Arrêter l’exécution" shortcut="Échap" side="left">
            <button
              type="button"
              onClick={() => void stopAgentsRun()}
              className="flex h-10 items-center justify-center gap-2 rounded-md bg-fg text-sm font-semibold text-bg transition-colors duration-150 hover:bg-fg-2"
            >
              <Square size={12} fill="currentColor" />
              Arrêter
            </button>
          </Tooltip>
        ) : (
          <Tooltip label="Exécuter la tâche" shortcut="Ctrl+Entrée" side="left">
            <button
              type="button"
              disabled={starting}
              onClick={onExecute}
              className="flex h-10 items-center justify-center gap-2 rounded-md bg-accent text-sm font-semibold text-on-accent transition-colors duration-150 hover:bg-accent-hover disabled:opacity-70"
            >
              <Play size={14} fill="currentColor" />
              Exécuter
            </button>
          </Tooltip>
        )}
        <Button variant="secondary" onClick={() => setCreating(true)}>
          <Plus size={15} className="text-fg-2" />
          Créer un agent
        </Button>
        <Tooltip label="Arrive avec la phase 4b de la migration" side="left">
          <span className="flex">
            <Button variant="secondary" disabled className="w-full">
              <Swords size={15} />
              Débat
            </Button>
          </span>
        </Tooltip>
        <Tooltip label="Vider le workflow et le canvas" side="left">
          <Button variant="secondary" onClick={clearWorkflow}>
            <Eraser size={15} className="text-fg-2" />
            Vider
          </Button>
        </Tooltip>
      </div>
      {creating ? <AgentDialog agent={null} onClose={() => setCreating(false)} /> : null}
    </div>
  );
}
