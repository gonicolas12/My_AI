@echo off
echo Creation du modele personnalise My_AI...
ollama create my_ai -f Modelfile
if %ERRORLEVEL% EQU 0 (
    echo.
    echo [SUCCES] Le modele 'my_ai' a ete cree avec succes !
    echo Vous pouvez maintenant l'utiliser dans votre projet.
) else (
    echo.
    echo [ERREUR] Echec de la creation du modele. Assurez-vous qu'Ollama est lance.
)
pause
