/*
 * Fichier cité dans un texte en Markdown (chemin, nom d'un fichier joint) : ce
 * qui ouvre son aperçu. Dans le chat, le volet de droite ; sur la page Agents,
 * qui n'a pas de volet de droite, la fenêtre au premier plan (ThreadView).
 */

import { createContext } from 'react';

import { openFilePreview } from '../../../stores/preview';

export type OpenFile = (path: string) => void;

export const FileOpener = createContext<OpenFile>((path) => openFilePreview(path));
