@echo off
REM Script pour supprimer les dossiers __pycache__ et le dossier logs

REM Suppression des dossiers __pycache__ partout dans le projet
for /d /r %%i in (__pycache__) do if exist "%%i" rd /s /q "%%i"

REM Suppression du dossier logs à la racine
if exist "logs" rd /s /q "logs"

echo Projet maintenant clean !
