@echo off
setlocal

cd /d "%~dp0API"

if not exist ".env" (
  echo [INFO] Aucun fichier .env detecte. Copie de .env.example vers .env
  copy ".env.example" ".env" >nul
)

where python >nul 2>nul
if %ERRORLEVEL% EQU 0 (
  set "PYTHON_CMD=python"
) else (
  where py >nul 2>nul
  if %ERRORLEVEL% EQU 0 (
    set "PYTHON_CMD=py"
  ) else (
    set "BUNDLED_PYTHON=%USERPROFILE%\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
    if exist "%BUNDLED_PYTHON%" (
      set "PYTHON_CMD=%BUNDLED_PYTHON%"
    ) else (
      echo [ERREUR] Python est introuvable dans le PATH.
      echo Installe Python ou ajoute-le au PATH, puis relance ce script.
      pause
      exit /b 1
    )
  )
)

echo [INFO] Installation/verification des dependances API...
%PYTHON_CMD% -m pip install -r requirements.txt
if %ERRORLEVEL% NEQ 0 (
  echo [ERREUR] Installation des dependances impossible.
  pause
  exit /b 1
)

echo [INFO] Demarrage API sur http://127.0.0.1:8000/api
%PYTHON_CMD% -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload

endlocal
