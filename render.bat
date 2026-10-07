@echo off
REM ============================================================
REM  Experiment FM 105.9 - OFFLINE QWEN RENDER
REM  Cara 3h + Junior 1h (normal shift), 4h total, pause/resume.
REM
REM  Usage:
REM    render.bat              <- default: 4h, cara+junior, normal shift
REM    render.bat --minutes 10 <- quick test
REM
REM  Pause / resume / stop while running:
REM    edit render_control.json -> {"action":"pause"} | "run" | "stop"
REM ============================================================
cd /d "%~dp0"

if "%~1"=="" (
  echo {"action":"run"}> render_control.json
  "C:\sourceCode\Qwen3-TTS\.venv\Scripts\python.exe" render_offline.py ^
    --hours 4 --djs cara,junior --normal-shift
) else (
  echo {"action":"run"}> render_control.json
  "C:\sourceCode\Qwen3-TTS\.venv\Scripts\python.exe" render_offline.py %*
)

echo.
echo [render.bat] finished. Output in recordings\
pause
