@echo off
rem Faz o Painel DP ligar sozinho (em segundo plano) quando o Windows iniciar,
rem para ler os e-mails mesmo antes de você abrir o painel.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0ferramentas\criar_atalhos.ps1" -Inicializacao
pause
