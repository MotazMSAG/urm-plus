@echo off
rem URMPLUS_VERSION=@@URMPLUS_VERSION@@
setlocal disabledelayedexpansion enableextensions

rem ==========================================================================
rem  URM_fix.bat - installs Multiversal Ren'Py Mod (MRM) into Ren'Py games.
rem
rem  Put this file in the game folder, next to the game's .exe, and
rem  double-click it. A menu will walk you through the rest.
rem
rem  You can also drag a game folder onto this file.
rem
rem  Everything below the PAYLOAD marker at the end is the Python half; it is
rem  read straight out of this file and run with the game's own
rem  interpreter. The game's interpreter is required - the decryption key
rem  lives inside the game's native module and nothing else can read it.
rem
rem  No delayed expansion anywhere: with it on, every "!" in a folder name is
rem  eaten, and a game in "Game!" is looked for in "Game".
rem ==========================================================================

title MRM installer

set "GAME=%~1"
if not defined GAME for %%I in ("%~dp0.") do set "GAME=%%~fI"

if not exist "%GAME%\game\" (
    echo.
    echo   "%GAME%"
    echo   has no game\ folder in it, so it is not a Ren'Py game folder.
    echo.
    echo   Put this file next to the game's .exe and run it again, or drag
    echo   the game folder onto this file.
    goto :finish
)

set "PY="
rem Whatever interpreter the game ships: py3-windows-*, py2-windows-* (Ren'Py 7.4+),
rem windows-* (Ren'Py 7.3 and older), or lib\python.exe. 64-bit first.
for /d %%D in ("%GAME%\lib\*x86_64*") do if not defined PY if exist "%%~D\python.exe" set "PY=%%~D\python.exe"
for /d %%D in ("%GAME%\lib\*") do if not defined PY if exist "%%~D\python.exe" set "PY=%%~D\python.exe"
if not defined PY if exist "%GAME%\lib\python.exe" set "PY=%GAME%\lib\python.exe"

if not defined PY (
    echo.
    echo   Could not find the game's bundled Python under
    echo   "%GAME%\lib".
    echo.
    echo   Is this the folder with the game's .exe in it? URM_fix needs the
    echo   game's own copy of Python to install MRM.
    goto :finish
)

rem Ren'Py 7.3 and older keep the standard library beside the interpreter
rem rather than inside it, and native modules beside the interpreter.
rem Their library is .pyo files only, which Python 2 loads only with -O.
set "PYFLAGS=-s"
for %%F in ("%PY%\..") do set "PYDIR=%%~fF"
for %%F in ("%PYDIR%") do set "PYKIND=%%~nxF"
if /i "%PYKIND:~0,3%"=="py3" set "PYFLAGS=-I"
set "PYTHONHOME="
set "PYTHONPATH="
set "PYLIB="
for /d %%D in ("%GAME%\lib\pythonlib*") do set "PYLIB=%%~D"
if defined PYLIB set "PYTHONPATH=%PYLIB%;%PYDIR%"
if defined PYLIB set "PYFLAGS=-O -s"

rem The Python half is read straight out of this file and run - no copy is
rem written. It gets the game folder, this file and
rem the optional "install" argument.
"%PY%" %PYFLAGS% -c "import sys;f=open(sys.argv[1],'rb');s=f.read().decode('utf-8').replace('\r\n','\n');f.close();sys.argv=['urmfix',sys.argv[2],sys.argv[1]]+sys.argv[3:];exec(compile(s.split('\nrem PAYLOAD_BEGIN\n',1)[1],'urmfix.py','exec'),{'__name__':'__main__'})" "%~f0" "%GAME%" %2
set "RESULT=%ERRORLEVEL%"
if /i "%~2"=="install" exit /b %RESULT%

:finish
if /i "%~2"=="install" exit /b 1
echo.
pause
endlocal
exit /b
