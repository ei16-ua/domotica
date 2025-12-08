@echo off
echo ========================================
echo   Iniciando Material Backend (Go)
echo ========================================

cd /d "%~dp0modulo_material\backend"

REM Compilar y ejecutar
echo Compilando y ejecutando el servidor...
go run main.go

pause
