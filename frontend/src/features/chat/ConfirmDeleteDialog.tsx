import { Button } from '../../components/ui/Button';
import { Dialog } from '../../components/ui/Dialog';
import { useT } from '../../i18n';
import { answerConfirm } from '../../lib/actions';
import { useChat } from '../../stores/chat';

/**
 * Suppression d'un fichier demandée par un outil (on_delete_confirm) : le
 * moteur attend la réponse. Échap ou fermeture valent un refus, comme dans Tk.
 */
export function ConfirmDeleteDialog() {
  const t = useT();
  const confirm = useChat((state) => state.confirm);
  if (!confirm) return null;
  const answer = (accepted: boolean) => void answerConfirm(confirm.confirm_id, accepted);
  return (
    <Dialog
      open
      onOpenChange={(open) => {
        if (!open) answer(false);
      }}
      title={t('chat.confirmDelete.title')}
      description={t('chat.confirmDelete.description')}
      footer={
        <>
          <Button variant="secondary" onClick={() => answer(false)} autoFocus>
            {t('chat.confirmDelete.no')}
          </Button>
          <Button variant="danger" onClick={() => answer(true)}>
            {t('chat.confirmDelete.yes')}
          </Button>
        </>
      }
    >
      <div className="rounded-md border border-line bg-bg px-3 py-2">
        <div className="font-medium text-fg">{confirm.name}</div>
        <div className="mt-0.5 font-mono text-xs break-all text-fg-2">{confirm.path}</div>
      </div>
    </Dialog>
  );
}
