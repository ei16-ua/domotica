@echo off
echo ========================================
echo   Iniciando Chatbot Backend (Python)
echo ========================================

cd /d "%~dp0modulo_chatbot\backend"

REM Activar el entorno virtual
call venv\Scripts\activate.bat

REM Ejecutar el servidor
echo Iniciando servidor en http://localhost:8000
python main.py

pause
