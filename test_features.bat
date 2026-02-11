@echo off
setlocal EnableDelayedExpansion
REM Script de test rapide des nouvelles fonctionnalités
REM My_AI - Version 2.0

echo.
echo ============================================================
echo      MY AI - TEST DES FONCTIONNALITES AVANCEES
echo ============================================================
echo.
echo Ce script teste les nouvelles fonctionnalites :
echo   - RLHF Manager
echo   - Training Manager  
echo   - Compression Monitor
echo.
echo [33mNote: Appuyez sur 6 puis Entree pour quitter[0m
echo.

:menu
echo ============================================================
echo                        MENU
echo ============================================================
echo.
echo 1. Lancer TOUS les tests
echo 2. Lancer les exemples complets (demo)
echo 3. Test RLHF Manager uniquement
echo 4. Test Training Manager uniquement
echo 5. Test Compression Monitor uniquement
echo 6. Quitter
echo.
set choice=
set /p choice="Votre choix (1-6): "

REM Gestion des choix vides ou invalides (Ctrl+C)
if "%choice%"=="" goto menu
if "%choice%"=="1" goto all_tests
if "%choice%"=="2" goto demo
if "%choice%"=="3" goto rlhf_only
if "%choice%"=="4" goto training_only
if "%choice%"=="5" goto compression_only
if "%choice%"=="6" goto end

REM Choix invalide
echo.
echo [31mChoix invalide ! Veuillez choisir entre 1 et 6.[0m
timeout /t 2 >nul
goto menu

:all_tests
echo.
echo ============================================================
echo Execution de TOUS les tests...
echo ============================================================
echo.
python tests\test_advanced_features.py
if %ERRORLEVEL% EQU 0 (
    echo.
    echo [32m[SUCCESS] Tous les tests sont passes ![0m
) else (
    echo.
    echo [31m[ERREUR] Certains tests ont echoue[0m
)
echo.
pause
goto menu

:demo
echo.
echo ============================================================
echo Lancement des exemples complets...
echo ============================================================
echo.
python examples\advanced_features_demo.py
echo.
pause
goto menu

:rlhf_only
echo.
echo ============================================================
echo Test RLHF Manager uniquement
echo ============================================================
echo.
python tests\test_advanced_features.py --test rlhf
echo.
pause
goto menu

:training_only
echo.
echo ============================================================
echo Test Training Manager uniquement
echo ============================================================
echo.
python tests\test_advanced_features.py --test training
echo.
pause
goto menu

:compression_only
echo.
echo ============================================================
echo Test Compression Monitor uniquement
echo ============================================================
echo.
python tests\test_advanced_features.py --test compression
echo.
pause
goto menu

:end
echo.
echo ============================================================
echo Merci d'avoir teste My AI !
echo ============================================================
echo.
timeout /t 1 >nul
endlocal
exit /b 0
