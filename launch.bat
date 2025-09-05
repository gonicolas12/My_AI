@echo off
chcp 65001 >nul
REM ====================================
REM My Personal AI ULTRA - Lanceur v5.0
REM ====================================

echo.
echo MY PERSONAL AI v5.0
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
echo 1. Interface Graphique Moderne - RECOMMANDE
echo 2. Menu de demarrage interactif
echo 3. Test complet de tous les modules
echo 4. Audit et validation du systeme
echo.
set /p choice="Votre choix (1-4, ou Entree pour ULTRA): "

if "%choice%"=="" set choice=1
if "%choice%"=="1" goto ultra
if "%choice%"=="2" goto menu_interactif
if "%choice%"=="3" goto test_complet
if "%choice%"=="4" goto audit

REM Gestion des choix invalides
echo.
echo [ERROR] Choix invalide : "%choice%"
echo Veuillez choisir un numero entre 1 et 5.
echo.
goto menu

:ultra
echo [INFO] Lancement Interface UNIFIEE (CustomAI avec 1M tokens)...
echo [CONFIG] Configuration unifiee activee
python launch_unified.py
goto end

:menu_interactif
echo [INFO] Menu de demarrage interactif...
python start_ultra.py
goto end

:test_complet
echo [INFO] Test complet de tous les modules...
python test_final_ultra.py
goto end

:audit
echo [INFO] Audit et validation...
python audit.py
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
