@echo off
setlocal
set PYTHONUTF8=1
cd /d "%~dp0"
where py >nul 2>nul
if not errorlevel 1 (
    py -3 lancer.py
) else (
    where python >nul 2>nul
    if errorlevel 1 (
        echo Python est introuvable. Installez Python 3.10 ou plus recent.
        echo Puis relancez ce fichier.
    ) else (
        python lancer.py
    )
)
echo.
pause
