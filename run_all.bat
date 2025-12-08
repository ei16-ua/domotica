@echo off
echo ========================================
echo   Iniciando TODOS los modulos
echo ========================================

REM Iniciar cada modulo en una ventana separada
start "Chatbot Backend" cmd /k "%~dp0run_chatbot_backend.bat"
timeout /t 2 /nobreak >nul

start "Chatbot Frontend" cmd /k "%~dp0run_chatbot_frontend.bat"
timeout /t 2 /nobreak >nul

start "Material Backend" cmd /k "%~dp0run_material_backend.bat"
timeout /t 2 /nobreak >nul

start "Material Frontend" cmd /k "%~dp0run_material_frontend.bat"
timeout /t 2 /nobreak >nul

start "RAG Backend" cmd /k "%~dp0run_rag_backend.bat"

echo.
echo ========================================
echo   Todos los modulos han sido iniciados
echo ========================================
echo.
echo Puertos:
echo   - Chatbot Backend:  http://localhost:8000
echo   - Chatbot Frontend: http://localhost:5173
echo   - Material Backend: http://localhost:8080
echo   - Material Frontend: http://localhost:5174
echo   - RAG Backend:      http://localhost:8001
echo.
pause
