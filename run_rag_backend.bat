@echo off
echo ========================================
echo   Iniciando RAG Backend (Python)
echo ========================================

cd /d "%~dp0modulo_rag\backend"

REM Activar el entorno virtual
call venv\Scripts\activate.bat

REM Ejecutar el servidor
echo Iniciando servidor en http://localhost:8001
python main.py

pause
