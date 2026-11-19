import { useEffect } from 'react';

import { useCode } from '../../stores/code';
import { closePagePreview } from '../../stores/preview';

/**
 * Conversation Code effacée (ici, dans VS Code ou sur le téléphone) : ce que
 * montrait le volet de la page n'y est plus, il se ferme
 */
export function usePaneReset(): void {
  useEffect(
    () =>
      useCode.subscribe((state, previous) => {
        if (previous.messages.length && !state.messages.length) closePagePreview('code');
      }),
    [],
  );
}
