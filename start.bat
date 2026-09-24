@echo off
rem Starts Legal AI: the LangChain backend (port 8000) and the web UI (port 5173),
rem each in its own window, then opens the browser. Close the two windows to stop.
cd /d "%~dp0"

if not exist ".venv-lc\Scripts\activate.bat" (
  echo The backend environment .venv-lc is missing. Create it once with:
  echo   python -m venv .venv-lc
  echo   .venv-lc\Scripts\pip install -r lc\requirements.txt
  pause
  exit /b 1
)
if not exist "web\node_modules" (
  echo Installing the web UI packages, first run only...
  pushd web && call npm install && popd
)

start "Legal AI backend" cmd /k ".venv-lc\Scripts\activate.bat && uvicorn lc.api:app"
start "Legal AI web" cmd /k "cd web && npm run dev"

rem give both servers a few seconds to come up, then open the app
timeout /t 10 /nobreak >nul
start "" http://localhost:5173
