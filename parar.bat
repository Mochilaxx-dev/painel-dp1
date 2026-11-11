@echo off
rem Encerra o Painel DP que está rodando em segundo plano
set PIDFILE=%~dp0dados\painel.pid
if not exist "%PIDFILE%" (
  echo O Painel DP nao parece estar rodando.
  pause
  exit /b
)
set /p PID=<"%PIDFILE%"
taskkill /PID %PID% /F >nul 2>&1 && echo Painel DP encerrado. || echo O Painel DP ja estava parado.
del "%PIDFILE%" >nul 2>&1
timeout /t 3 >nul
