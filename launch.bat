@echo off
chcp 65001 >nul
REM ====================================
REM My Personal AI ULTRA - Lanceur v5.7.0
REM ====================================

echo.
echo MY PERSONAL AI v5.7.0
echo ======================
echo.

REM Verifier Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python non trouve. Installez Python depuis python.org
    pause
    exit /b 1
)

REM Activer l'environnement virtuel s'il existe
if exist "venv\Scripts\activate.bat" (
    echo [INFO] Activation environnement virtuel...
    call venv\Scripts\activate.bat
    echo [OK] Environnement virtuel active
) else (
    echo [INFO] Mode installation globale
)

REM Verifier/installer dependances critiques
echo [INFO] Verification des dependances...
python -c "import click, yaml, rich" 2>nul
if %errorlevel% neq 0 (
    echo [INFO] Installation des dependances critiques...
    pip install --user click pyyaml rich
    if %errorlevel% neq 0 (
        echo [ERROR] Echec installation dependances
        pause
        exit /b 1
    )
)

REM Menu de choix
:menu
echo.
echo Que voulez-vous faire ?
echo 1. Interface Graphique Moderne
echo 2. Benchmark 1M tokens
echo 3. RAG Pipeline Test
echo 4. Test des imports
echo.
set /p choice="Votre choix (1-4, ou Entree pour ULTRA): "

if "%choice%"=="" set choice=1
if "%choice%"=="1" goto ultra
if "%choice%"=="2" goto benchmark
if "%choice%"=="3" goto rag_pipeline
if "%choice%"=="4" goto test_imports

REM Gestion des choix invalides
echo.
echo [ERROR] Choix invalide : "%choice%"
echo Veuillez choisir un numero entre 1 et 3.
echo.
goto menu

:ultra
echo [INFO] Lancement Interface UNIFIEE (CustomAI avec 1M tokens)...
echo [CONFIG] Configuration unifiee activee
python launch_unified.py
goto end

:benchmark
echo [INFO] Benchmark 1M tokens...
python tests/test_real_1m_tokens.py
goto end

:rag_pipeline
echo [INFO] RAG Pipeline Test...
python tests/rag_pipeline.py
goto end

:test_imports
echo [INFO] Test de tous les imports...
python tests/test_imports.py
goto end

:end
if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Une erreur s'est produite
    echo [AIDE] Essayez: python main.py
    pause
)
echo.
echo Au revoir !
pause
