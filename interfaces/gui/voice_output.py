"""Lecture vocale : relais de l'interface Tk.

La lecture vocale est dans interfaces/desktop/voice_output.py, partagée avec
l'interface web ; ce relais disparaît avec l'interface Tk (phase 5 de la
migration web).
"""

from interfaces.desktop.voice_output import VoiceOutput, clean_for_speech  # noqa: F401
