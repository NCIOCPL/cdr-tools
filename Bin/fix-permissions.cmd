@setlocal
@echo off
if .%1 == . ( set TARGET=. ) else ( set TARGET="%1" )
echo setting permissions for %TARGET% ...
REM icacls %TARGET% /remove:d "NULL SID" /T /C /Q
REM icacls %TARGET% /remove:d "NIH\Domain Users" /T /C /Q
icacls %TARGET% /grant Everyone:(F) /T /C /Q
@endlocal
