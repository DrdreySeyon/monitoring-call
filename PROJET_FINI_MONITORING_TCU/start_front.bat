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
    set "BUNDLED_PYTHON=%USERPROFILE%\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
    if exist "%BUNDLED_PYTHON%" (
      set "PYTHON_CMD=%BUNDLED_PYTHON%"
    ) else (
      echo [ERREUR] Python est introuvable dans le PATH.
      echo Ouvre sinon directement FRONT\index.html dans le navigateur.
      pause
      exit /b 1
    )
  )
)

echo [INFO] Front disponible sur http://127.0.0.1:8080
%PYTHON_CMD% -m http.server 8080

endlocal
