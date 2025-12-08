@echo off
echo ========================================
echo   Vaciando Base de Datos de Materiales
echo ========================================
echo.

cd /d "%~dp0"

REM Eliminar la base de datos
if exist "modulo_material\backend\materials.db" (
    del /f "modulo_material\backend\materials.db"
    echo [OK] Base de datos materials.db eliminada
) else (
    echo [INFO] No existe materials.db
)

REM Eliminar los archivos subidos
if exist "modulo_material\backend\material_files" (
    del /f /q "modulo_material\backend\material_files\*.*" 2>nul
    echo [OK] Archivos de material_files eliminados
) else (
    echo [INFO] No existe la carpeta material_files
)

echo.
echo ========================================
echo   Base de datos vaciada correctamente
echo ========================================
pause
