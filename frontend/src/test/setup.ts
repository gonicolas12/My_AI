import '@testing-library/jest-dom/vitest';
import { cleanup } from '@testing-library/react';
import { afterEach } from 'vitest';

// Sans les globales de Vitest, Testing Library ne démonte pas seul le rendu
// d'un test avant le suivant
afterEach(() => {
  cleanup();
});
