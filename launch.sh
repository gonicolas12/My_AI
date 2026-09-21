#!/usr/bin/env bash
# ====================================
# My Personal AI ULTRA - Lanceur v8.0.0 (macOS / Linux)
# Équivalent POSIX de launch.bat
# ====================================

set -u

cd "$(dirname "$0")" || exit 1

ORANGE=$'\033[38;2;255;136;0m'
WHITE=$'\033[97m'
RESET=$'\033[0m'
BOLD=$'\033[1m'

printf '\n'
printf '%s    __  ___          ___    ____ %s\n' "$ORANGE$BOLD" "$RESET"
printf '%s   /  |/  /_  __    /   |  /  _/ %s\n' "$ORANGE$BOLD" "$RESET"
printf '%s  / /|_/ / / / /   / /| |  / /   %s\n' "$ORANGE$BOLD" "$RESET"
printf '%s / /  / / /_/ /   / ___ |_/ /    %s\n' "$ORANGE$BOLD" "$RESET"
printf '%s/_/  /_/\\__, /___/_/  |_/___/   %s\n' "$ORANGE$BOLD" "$RESET"
printf '%s       /____/                  %s\n' "$ORANGE$BOLD" "$RESET"
printf '\n'
printf '%s====================================%s\n' "$ORANGE" "$RESET"
printf '%s           Version 8.0.0%s\n' "$BOLD" "$RESET"
printf '%s====================================%s\n' "$ORANGE" "$RESET"
printf '\n'

# Verifier Python
PYTHON=""
for candidate in python3 python; do
    if command -v "$candidate" >/dev/null 2>&1; then
        PYTHON="$candidate"
        break
    fi
done
if [ -z "$PYTHON" ]; then
    echo "[ERROR] Python non trouve. Installez Python depuis python.org"
    exit 1
fi

# Activer l'environnement virtuel s'il existe
if [ -f "venv/bin/activate" ]; then
    echo "[INFO] Activation environnement virtuel..."
    # shellcheck disable=SC1091
    . venv/bin/activate
    PYTHON="python"
    echo "[OK] Environnement virtuel active"
else
    echo "[INFO] Mode installation globale"
fi

# tkinter n'est pas systematiquement fourni avec Python sur macOS/Linux :
# sans lui, la GUI ne peut pas demarrer et l'erreur est peu explicite.
if ! "$PYTHON" -c "import tkinter" >/dev/null 2>&1; then
    echo "[ERROR] Le module tkinter est absent de cette installation Python."
    case "$(uname -s)" in
        Darwin) echo "[AIDE]  Installez Python depuis python.org (tkinter inclus),"
                echo "        ou via Homebrew : brew install python-tk" ;;
        *)      echo "[AIDE]  Debian/Ubuntu : sudo apt install python3-tk" ;;
    esac
    exit 1
fi

# Verifier/installer dependances critiques
echo "[INFO] Verification des dependances..."
if ! "$PYTHON" -c "import click, yaml, rich" >/dev/null 2>&1; then
    echo "[INFO] Installation des dependances critiques..."
    if ! "$PYTHON" -m pip install --user click pyyaml rich; then
        echo "[ERROR] Echec installation dependances"
        exit 1
    fi
fi

# Menu de choix
while true; do
    printf '\n'
    printf '%sQue voulez-vous faire ?%s\n' "$WHITE$BOLD" "$RESET"
    printf '\n'
    echo "1. Interface Graphique Moderne"
    echo "2. Benchmark memoire vectorielle"
    echo "3. Benchmark 10M tokens"
    echo "4. RAG Pipeline Test"
    echo "5. Test des imports"
    printf '\n'
    printf '%sVotre choix (1-5, ou Entree pour l'"'"'interface graphique): %s' "$WHITE$BOLD" "$RESET"
    read -r choice
    [ -z "$choice" ] && choice=1

    case "$choice" in
        1)
            printf '\n'
            echo "[INFO] Lancement Interface (CustomAI avec 10M tokens)..."
            echo "[CONFIG] Configuration activee"
            printf '\n'
            printf '%s====================================%s\n' "$ORANGE" "$RESET"
            printf '\n'
            "$PYTHON" launch_unified.py
            break
            ;;
        2) echo "[INFO] Benchmark memoire vectorielle..."; "$PYTHON" tests/test_real_1m_tokens.py; break ;;
        3) echo "[INFO] Benchmark 10M tokens..."; "$PYTHON" tests/benchmark_10m_tokens.py; break ;;
        4) echo "[INFO] RAG Pipeline Test..."; "$PYTHON" tests/rag_pipeline.py; break ;;
        5) echo "[INFO] Test de tous les imports..."; "$PYTHON" tests/test_imports.py; break ;;
        *)
            printf '\n'
            echo "[ERROR] Choix invalide : \"$choice\""
            echo "Veuillez choisir un numero entre 1 et 5."
            ;;
    esac
done

status=$?
if [ "$status" -ne 0 ]; then
    printf '\n'
    echo "[ERROR] Une erreur s'est produite"
    echo "[AIDE] Essayez: $PYTHON main.py"
fi
printf '\n'
echo "Au revoir !"
