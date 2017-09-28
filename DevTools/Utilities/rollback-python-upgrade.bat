@REM ======================================================================
@REM Undo upgrade of Python from 2.7.10 to 2.7.13.
@REM (Used for testing the upgrade script).
@REM ======================================================================

@echo off
setlocal
CALL :progress Roll back Python upgrade (takes about 13-15 minutes)
cd \tmp\python-upgrade
CALL :progress Remove 2.7.13
start /wait MsiExec.exe /qr /log \tmp\u.log /x {4E514478-E395-496B-AB86-A752E9CE3810}
CALL :progress Install 2.7.10
rmdir /q /s \Python
start /wait msiexec /I ActivePython-2.7.10.12-win64-x64.msi INSTALLDIR=C:\Python /qr
call :progress Done
exit /B 0

@REM ======================================================================
@REM Show the current time and where we are in the processing.
@REM ======================================================================
:progress
\cygwin\bin\date.exe +'%%F %%T %*'
exit /B 0
