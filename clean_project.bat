@echo off
REM Script pour supprimer les dossiers __pycache__, le dossier logs et le fichier code_solutions_cache.db

REM Suppression des dossiers __pycache__ partout dans le projet
for /d /r %%i in (__pycache__) do if exist "%%i" rd /s /q "%%i"

REM Suppression du dossier logs à la racine
if exist "logs" rd /s /q "logs"

REM Suppression du fichier code_solutions_cache.db à la racine
if exist "code_solutions_cache.db" del /q "code_solutions_cache.db"

REM Suppression du fichier ultra_context.db à la racine
if exist "ultra_context.db" del /q "ultra_context.db"

echo Projet maintenant clean !
