@echo off
setlocal enabledelayedexpansion

rem Installs URM into a Ren'Py game that encrypts its script cache.
rem
rem Put this folder inside the game folder - the one with the .exe - and
rem double-click this file. You can also drag a game folder onto it.

title Install URM

set "HERE=%~dp0"
if "%HERE:~-1%"=="\" set "HERE=%HERE:~0,-1%"

if not "%~1"=="" (
    set "GAME=%~1"
) else (
    for %%D in ("%HERE%\..") do set "GAME=%%~fD"
)

echo.
echo   Game folder: !GAME!
echo.

if not exist "!GAME!\game" (
    echo   That folder has no game\ directory in it, so it is not a Ren'Py
    echo   game folder.
    echo.
    echo   Put this folder next to the game's .exe and run it again, or drag
    echo   the game folder onto this file.
    goto :done
)

set "PY="
for %%P in (
    "lib\py3-windows-x86_64\python.exe"
    "lib\py3-windows-i686\python.exe"
    "lib\windows-x86_64\python.exe"
    "lib\windows-i686\python.exe"
) do (
    if not defined PY if exist "!GAME!\%%~P" set "PY=!GAME!\%%~P"
)

if not defined PY (
    echo   Could not find the game's bundled Python under !GAME!\lib.
    echo.
    echo   This has to run with the game's own interpreter, because the
    echo   encryption key lives inside the game's native module.
    goto :done
)

"!PY!" "%HERE%\repack.py" "!GAME!"

if errorlevel 1 (
    echo.
    echo   Something went wrong - see the message above.
    echo.
    echo   If it says the archive could not be read, check that
    echo   0x52_URM.rpa is sitting next to this .bat file.
) else (
    echo.
    echo   Done. Start the game normally.
)

:done
echo.
pause
endlocal
