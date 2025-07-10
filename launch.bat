@echo off
chcp 65001 >nul
REM ====================================
REM My Personal AI - Lanceur Universal
REM ====================================

echo.
echo MY PERSONAL AI - Lanceur Universal
echo ================================
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
echo 1. Lancer l'interface graphique (GUI)
echo 2. Lancer l'interface ligne de commande (CLI)
echo 3. Executer la demonstration
echo 4. Verifier le statut du systeme
echo 5. Installer toutes les dependances
echo.
set /p choice="Votre choix (1-5, ou Entree pour GUI): "

if "%choice%"=="" set choice=1
if "%choice%"=="1" goto gui
if "%choice%"=="2" goto cli
if "%choice%"=="3" goto demo
if "%choice%"=="4" goto status
if "%choice%"=="5" goto install

REM Gestion des choix invalides
echo.
echo [ERROR] Choix invalide : "%choice%"
echo Veuillez choisir un numero entre 1 et 5.
echo.
goto menu

:gui
echo [INFO] Lancement GUI...
python launcher.py gui
goto end

:cli
echo [INFO] Lancement CLI...
python launcher.py cli
goto end

:demo
echo [INFO] Lancement demo...
python launcher.py demo
goto end

:status
echo [INFO] Verification statut...
python launcher.py status
python diagnostic.py
goto end

:install
echo [INFO] Installation complete...
pip install --user -r requirements.txt
echo [OK] Installation terminee
goto end

:end
if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Une erreur s'est produite
    echo [AIDE] Essayez: python diagnostic.py
    pause
)
echo.
echo Au revoir !
pause
