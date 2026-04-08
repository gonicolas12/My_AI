@echo off
REM ============================================================================
REM Script de nettoyage du projet My_AI v7.1.0
REM Deux niveaux : leger (caches) ou complet (caches + donnees utilisateur)
REM Le cache HuggingFace n'est JAMAIS supprime (modeles ML).
REM ============================================================================

echo.
echo ========================================
echo            NETTOYAGE DE My_AI
echo ========================================
echo.
echo   [1] Nettoyage LEGER (caches et logs uniquement)
echo       Supprime les fichiers temporaires, caches et logs.
echo       Vos donnees personnelles sont PRESERVEES.
echo.
echo   [2] Nettoyage COMPLET (reset usine)
echo       Supprime TOUT : caches + base de connaissances,
echo       workspaces, historique, exports, memoire vectorielle...
echo       /!\ IRREVERSIBLE : vos donnees seront perdues.
echo.
echo   [3] Annuler
echo.

set /p CHOICE="Votre choix (1/2/3) : "

if "%CHOICE%"=="1" goto LIGHT
if "%CHOICE%"=="2" goto FULL
if "%CHOICE%"=="3" goto CANCEL
echo Choix invalide.
goto CANCEL

REM ============================================================================
:LIGHT
REM ============================================================================
echo.
echo -- Nettoyage LEGER -----------------------
echo.

echo [1/8] Suppression des __pycache__...
for /d /r %%i in (__pycache__) do if exist "%%i" rd /s /q "%%i"

echo [2/8] Suppression des logs...
if exist "logs" rd /s /q "logs"

echo [3/8] Suppression de rag_demo_index...
if exist "rag_demo_index" rd /s /q "rag_demo_index"

echo [4/8] Suppression de .pytest_cache...
if exist ".pytest_cache" rd /s /q ".pytest_cache"

echo [5/8] Suppression de code_solutions_cache.db...
if exist "context_storage\code_solutions_cache.db" del /q "context_storage\code_solutions_cache.db"

echo [6/8] Suppression de ultra_context.db...
if exist "context_storage\ultra_context.db" del /q "context_storage\ultra_context.db"

echo [7/8] Suppression de code_cache.json...
if exist "context_storage\code_cache.json" del /q "context_storage\code_cache.json"

echo [8/8] Suppression du cache web (data\web_cache)...
if exist "data\web_cache" rd /s /q "data\web_cache"

echo.
echo ========================================
echo       NETTOYAGE LEGER TERMINE !
echo ========================================
echo.
echo Vos donnees personnelles ont ete preservees :
echo   - Base de connaissances (data\knowledge_base)
echo   - Workspaces / sessions  (data\workspaces)
echo   - Historique commandes   (data\command_history.db)
echo   - Exports conversations  (outputs\exports)
echo   - Memoire vectorielle    (memory\vector_store\chroma_db)
echo   - Entrainements RLHF     (models\training_runs)
echo.
goto END

REM ============================================================================
:FULL
REM ============================================================================
echo.
echo /!\ ATTENTION : Cette operation supprime TOUTES vos donnees personnelles.
echo     Base de connaissances, workspaces, historique, exports, memoire...
echo.
set /p CONFIRM="Etes-vous sur ? Tapez OUI pour confirmer : "
if /i not "%CONFIRM%"=="OUI" (
    echo Nettoyage complet annule.
    goto END
)

echo.
echo -- Nettoyage COMPLET ---------------------
echo.

REM --- Caches (identique au leger) ---
echo [ 1/15] Suppression des __pycache__...
for /d /r %%i in (__pycache__) do if exist "%%i" rd /s /q "%%i"

echo [ 2/15] Suppression des logs...
if exist "logs" rd /s /q "logs"

echo [ 3/15] Suppression de rag_demo_index...
if exist "rag_demo_index" rd /s /q "rag_demo_index"

echo [ 4/15] Suppression de .pytest_cache...
if exist ".pytest_cache" rd /s /q ".pytest_cache"

echo [ 5/15] Suppression de code_solutions_cache.db...
if exist "context_storage\code_solutions_cache.db" del /q "context_storage\code_solutions_cache.db"

echo [ 6/15] Suppression de ultra_context.db...
if exist "context_storage\ultra_context.db" del /q "context_storage\ultra_context.db"

echo [ 7/15] Suppression de code_cache.json...
if exist "context_storage\code_cache.json" del /q "context_storage\code_cache.json"

echo [ 8/15] Suppression du cache web (data\web_cache)...
if exist "data\web_cache" rd /s /q "data\web_cache"

REM --- Donnees utilisateur ---
echo [ 9/15] Suppression de web_search_cache.db...
if exist "context_storage\web_search_cache.db" del /q "context_storage\web_search_cache.db"

echo [10/15] Suppression de la memoire vectorielle (chroma_db)...
if exist "memory\vector_store\chroma_db\" (
    for /d %%i in ("memory\vector_store\chroma_db\*") do rd /s /q "%%i"
    del /q "memory\vector_store\chroma_db\*" 2>nul
)

echo [11/15] Suppression des entrainements RLHF...
if exist "models\training_runs\" (
    for /d %%i in ("models\training_runs\*") do rd /s /q "%%i"
    for %%f in ("models\training_runs\*") do if /i not "%%~nxf"=="README.md" del /q "%%f"
)

echo [12/15] Suppression de la base de connaissances...
if exist "data\knowledge_base" rd /s /q "data\knowledge_base"

echo [13/15] Suppression de l'historique des commandes...
if exist "data\command_history.db" del /q "data\command_history.db"

echo [14/15] Suppression des workspaces / sessions...
if exist "data\workspaces" rd /s /q "data\workspaces"

echo [15/15] Suppression des exports de conversations...
if exist "outputs\exports" rd /s /q "outputs\exports"

echo.
echo ========================================
echo      NETTOYAGE COMPLET TERMINE !
echo ========================================
echo.
echo Toutes les donnees locales ont ete supprimees.
echo L'application redemarrera comme neuve.
echo.
goto END

REM ============================================================================
:CANCEL
REM ============================================================================
echo.
echo Nettoyage annule. Rien n'a ete modifie.
echo.

:END
echo NOTE: Le cache HuggingFace (modeles ML) n'a PAS ete supprime.
echo       Il se trouve dans: %%USERPROFILE%%\.cache\huggingface
echo       Ne le supprimez pas sinon le demarrage prendra ~10 min.
echo.
pause
