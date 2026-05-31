@echo off
setlocal

cd /d "%~dp0FRONT"

where python >nul 2>nul
if %ERRORLEVEL% EQU 0 (
  set "PYTHON_CMD=python"
) else (
  where py >nul 2>nul
  if %ERRORLEVEL% EQU 0 (
    set "PYTHON_CMD=py"
  ) else (
    echo [ERREUR] Python est introuvable dans le PATH.
    echo Ouvre sinon directement FRONT\index.html dans le navigateur.
    pause
    exit /b 1
  )
)

echo [INFO] Front disponible sur http://127.0.0.1:8080
%PYTHON_CMD% -m http.server 8080

endlocal
