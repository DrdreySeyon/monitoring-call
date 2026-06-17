@echo off
cd /d "%~dp0API"
where python >nul 2>nul
if %errorlevel%==0 (
  python -m uvicorn main:app --host 127.0.0.1 --port 8090
  goto :eof
)

where py >nul 2>nul
if %errorlevel%==0 (
  py -m uvicorn main:app --host 127.0.0.1 --port 8090
  goto :eof
)

echo Python introuvable. Installe Python ou ajoute-le au PATH.
pause
