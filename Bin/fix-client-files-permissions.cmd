@setlocal
@echo off
set TARGET=d:\cdr\ClientFiles
icacls %TARGET% /remove:d "NULL SID" /T /C /Q
icacls %TARGET% /remove:d "NIH\Domain Users" /T /C /Q
icacls %TARGET% /grant Everyone:(F) /T /C /Q
@endlocal
