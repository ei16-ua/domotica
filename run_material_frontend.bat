@echo off
echo ========================================
echo   Iniciando Material Frontend (Vite)
echo ========================================

cd /d "%~dp0modulo_material\frontend\app"

REM Instalar dependencias si es necesario
if not exist node_modules (
    echo Instalando dependencias...
    npm install
)

REM Ejecutar el servidor de desarrollo
echo Iniciando servidor en http://localhost:5174
npm run dev

pause
