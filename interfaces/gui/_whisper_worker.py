"""Worker de transcription Whisper, isolé dans son propre process.

⚠️ **Ce fichier doit être lancé PAR CHEMIN** (``python .../_whisper_worker.py``),
jamais via ``python -m interfaces.gui._whisper_worker`` : le second exécuterait
``interfaces/gui/__init__.py``, qui importe toute la pile applicative — donc
torch — et réintroduirait exactement le conflit que ce worker existe pour éviter.

Pourquoi ce process séparé
--------------------------
Sur macOS, la saisie vocale segfaulte dans le process applicatif : plusieurs
runtimes OpenMP y cohabitent, et le pool de threads de ctranslate2 meurt sur un
``EXC_BAD_ACCESS`` dans ``__kmp_fork_barrier``. Le message ``OMP: Error #15``
n'apparaît pas, car sklearn et threadpoolctl posent ``KMP_DUPLICATE_LIB_OK=True``
à l'import : l'abort explicite est remplacé par un crash muet.

Ce que ce worker évite exactement — et ce qu'il n'évite pas :

- ``ctranslate2`` **importe lui-même torch et transformers**. Un process
  « sans torch » est donc impossible avec cette pile : le worker charge, comme
  l'application, deux copies du runtime Intel (``libiomp5``), celle de
  ctranslate2 et celle de torch.
- Ce qu'il n'importe pas, c'est ``scikit-learn``, que l'application charge via
  sentence-transformers et qui apporte un **troisième** runtime, ``libomp``
  (LLVM). C'est ce mélange Intel + LLVM qui fait tomber le process.

Autrement dit : le worker reproduit la configuration où la transcription a été
observée stable, et Whisper y tourne à pleine vitesse (pas de ``cpu_threads=1``).
Si le crash survenait malgré tout, le parent le détecte — réponse vide — et se
replie sur une transcription mono-thread en process.

Protocole (stdin/stdout binaires, stderr pour les diagnostics)
-------------------------------------------------------------
Requête  : une ligne JSON ``{"n": <nb_échantillons>}`` puis ``n*4`` octets
           float32 little-endian (audio mono 16 kHz).
Réponse  : une ligne JSON ``{"text", "language", "language_probability"}``
           ou ``{"error": "..."}``.
Arrêt    : EOF sur stdin.
"""

import json
import sys


def _log(msg: str) -> None:
    """Diagnostics sur stderr : stdout est réservé au protocole."""
    print(f"[whisper-worker] {msg}", file=sys.stderr, flush=True)


def main() -> int:
    model_size = sys.argv[1] if len(sys.argv) > 1 else "small"
    compute_type = sys.argv[2] if len(sys.argv) > 2 else "int8"

    try:
        import numpy as np
        from faster_whisper import WhisperModel
    except Exception as exc:
        # Pas de modèle => on signale l'échec au parent et on sort proprement.
        sys.stdout.write(json.dumps({"error": f"import: {exc}"}) + "\n")
        sys.stdout.flush()
        return 1

    model = None
    stdin = sys.stdin.buffer
    stdout = sys.stdout

    while True:
        header = stdin.readline()
        if not header:
            break  # EOF : le parent a fermé le tube
        try:
            meta = json.loads(header.decode("utf-8"))
        except Exception as exc:
            _log(f"en-tête illisible : {exc}")
            continue

        n = int(meta.get("n", 0))
        raw = b""
        remaining = n * 4
        while remaining > 0:
            chunk = stdin.read(remaining)
            if not chunk:
                return 1  # tube coupé en plein transfert
            raw += chunk
            remaining -= len(chunk)

        try:
            if model is None:
                _log(f"chargement du modèle '{model_size}' ({compute_type})…")
                model = WhisperModel(model_size, device="cpu", compute_type=compute_type)
                _log("modèle prêt")

            audio = np.frombuffer(raw, dtype=np.float32)
            segments, info = model.transcribe(
                audio,
                language=None,  # auto-détection
                vad_filter=True,
                beam_size=1,
            )
            text = " ".join(seg.text.strip() for seg in segments).strip()
            reply = {
                "text": text,
                "language": info.language,
                "language_probability": info.language_probability,
            }
        except Exception as exc:
            reply = {"error": str(exc)}

        stdout.write(json.dumps(reply) + "\n")
        stdout.flush()

    return 0


if __name__ == "__main__":
    sys.exit(main())
