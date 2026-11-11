@echo off
rem Abre o Painel DP (se já estiver rodando, só abre o navegador)
set PY=%LOCALAPPDATA%\Programs\Python\Python312\pythonw.exe
if not exist "%PY%" set PY=pythonw
start "" "%PY%" "%~dp0painel.py"
