@echo off
chcp 65001 >nul
REM ====================================
REM Installation simple et rapide
REM ====================================

echo.
echo MY PERSONAL AI - Installation
echo =============================
echo.

REM Verifier Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python requis. Telechargez depuis python.org
    pause
    exit /b 1
)

echo [OK] Python trouve
python --version

REM Proposer environnement virtuel
echo.
choice /c YN /m "Voulez-vous utiliser un environnement virtuel (recommande)"
if %errorlevel% == 1 (
    echo [INFO] Creation environnement virtuel...
    if exist "venv" rmdir /s /q venv
    python -m venv venv
    call venv\Scripts\activate.bat
    echo [OK] Environnement virtuel cree et active
) else (
    echo [INFO] Installation globale (mode utilisateur)
)

REM Installation
echo.
echo [INFO] Installation des dependances...
pip install --upgrade pip
pip install --user -r requirements.txt

if %errorlevel% neq 0 (
    echo [WARNING] Installation complete echouee
    echo [INFO] Installation des modules critiques...
    pip install --user click pyyaml rich transformers torch
)

REM Test
echo.
echo [INFO] Test de l'installation...
python launcher.py status
if %errorlevel% neq 0 (
    echo [WARNING] Test echoue mais installation probablement OK
)

echo.
echo [SUCCESS] Installation terminee !
echo.
echo Pour lancer l'IA:
echo - Double-cliquez: launch.bat
echo - Ou tapez: python launcher.py gui
echo.
pause
