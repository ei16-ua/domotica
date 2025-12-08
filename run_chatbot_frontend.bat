@echo off
echo ========================================
echo   Iniciando Chatbot Frontend (Vite)
echo ========================================

cd /d "%~dp0modulo_chatbot\frontend\app"

REM Instalar dependencias si es necesario
if not exist node_modules (
    echo Instalando dependencias...
    npm install
)

REM Ejecutar el servidor de desarrollo
echo Iniciando servidor en http://localhost:5173
npm run dev

pause
