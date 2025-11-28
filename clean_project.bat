@echo off
REM ============================================================================
REM Script de nettoyage du projet My_AI
REM Supprime les caches locaux SANS toucher au cache HuggingFace
REM Le cache HuggingFace contient les modèles ML (ne pas supprimer !)
REM ============================================================================

echo.
echo ========================================
echo            NETTOYAGE DE My_AI
echo ========================================
echo.

REM Suppression des dossiers __pycache__ partout dans le projet
echo [1/9] Suppression des __pycache__...
for /d /r %%i in (__pycache__) do if exist "%%i" rd /s /q "%%i"

REM Suppression du dossier logs à la racine
echo [2/9] Suppression des logs...
if exist "logs" rd /s /q "logs"

REM Suppression du dossier rag_demo_index à la racine
echo [3/9] Suppression de rag_demo_index...
if exist "rag_demo_index" rd /s /q "rag_demo_index"

REM Suppression du dossier .pytest_cache à la racine
echo [4/9] Suppression de .pytest_cache...
if exist ".pytest_cache" rd /s /q ".pytest_cache"

REM Suppression du fichier code_solutions_cache.db
echo [5/9] Suppression de code_solutions_cache.db...
if exist "context_storage\code_solutions_cache.db" del /q "context_storage\code_solutions_cache.db"

REM Suppression du fichier ultra_context.db
echo [6/9] Suppression de ultra_context.db...
if exist "context_storage\ultra_context.db" del /q "context_storage\ultra_context.db"

REM Suppression du fichier code_cache.json
echo [7/9] Suppression de code_cache.json...
if exist "context_storage\code_cache.json" del /q "context_storage\code_cache.json"

REM Suppression du fichier web_search_cache.db
echo [8/9] Suppression de web_search_cache.db...
if exist "context_storage\web_search_cache.db" del /q "context_storage\web_search_cache.db"

REM Suppression du fichier chroma.sqlite3
echo [9/9] Suppression de chroma.sqlite3...
if exist "memory\vector_store\chroma_db\chroma.sqlite3" del /q "memory\vector_store\chroma_db\chroma.sqlite3" 

echo.
echo ========================================
echo           NETTOYAGE TERMINE !
echo ========================================
echo.
echo NOTE: Le cache HuggingFace (modeles ML) n'a PAS ete supprime.
echo       Il se trouve dans: %%USERPROFILE%%\.cache\huggingface
echo       Ne le supprimez pas sinon le demarrage prendra ~10 min.
echo.
