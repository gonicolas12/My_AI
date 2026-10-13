import { Button } from '../../components/ui/Button';
import { Dialog } from '../../components/ui/Dialog';
import { answerConfirm } from '../../lib/actions';
import { useChat } from '../../stores/chat';

/**
 * Suppression d'un fichier demandée par un outil (on_delete_confirm) : le
 * moteur attend la réponse. Échap ou fermeture valent un refus, comme dans Tk.
 */
export function ConfirmDeleteDialog() {
  const confirm = useChat((state) => state.confirm);
  if (!confirm) return null;
  const answer = (accepted: boolean) => void answerConfirm(confirm.confirm_id, accepted);
  return (
    <Dialog
      open
      onOpenChange={(open) => {
        if (!open) answer(false);
      }}
      title="Confirmation de suppression"
      description="L'IA souhaite supprimer ce fichier :"
      footer={
        <>
          <Button variant="secondary" onClick={() => answer(false)} autoFocus>
            Non, annuler
          </Button>
          <Button variant="danger" onClick={() => answer(true)}>
            Oui, supprimer
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
