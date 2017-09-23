@REM ----------------------------------------------------------------------
@REM Build the contents of the /cdr/Bin directory for deployment.
@REM ----------------------------------------------------------------------

@ECHO OFF
SETLOCAL
SET SCRIPTNAME=%0
CALL :init %*           || EXIT /B 1
CALL :pull_msvc_dlls    || EXIT /B 1
CALL :build CdrServer   || EXIT /B 1
CALL :build CdrService  || EXIT /B 1
CALL :build ShutdownCdr || EXIT /B 1
EXIT /B 0

REM ----------------------------------------------------------------------
REM Verify options, set local variables, and initialize the Bin directory.
REM ----------------------------------------------------------------------
:init
IF "%2." == "." (
    ECHO Usage: CALL %SCRIPTNAME% BASE-DIR CDR-DRIVE
    ECHO  e.g.: CALL %SCRIPTNAME% d:\tmp\build\fermi-20170909140358 D
    EXIT /B 1
)
SET BASE=%1
SET DRIVE=%2
SET BIN=%BASE%\Bin
SET SRC=%BASE%\branch\tools\Bin
MOVE %SRC% %BASE%\ || ECHO Failed moving Bin && EXIT /B 1
%DRIVE%:\bin\vsvars32.bat || ECHO Failed Visual Studio Init && EXIT /B 1
EXIT /B 0

REM ----------------------------------------------------------------------
REM Grab a copy of Microsoft's runtime DLLs.
REM ----------------------------------------------------------------------
:pull_msvc_dlls
SET DLLS=%DRIVE%:\cdr\Bin\msvc*.dll
COPY %DLLS% %BIN%\ > NUL 2>&1 || ECHO Unable to copy MSVC DLLs && EXIT /B 1
EXIT /B 0

REM ----------------------------------------------------------------------
REM Build an compiled and linked executable program.
REM ----------------------------------------------------------------------
:build
SET EXE=%1.exe
CD /D %BASE%\branch\server\Server
nmake DRV=%DRIVE%: %EXE% >>log 2>>err || ECHO Build %EXE% failed && EXIT /B 1
COPY %EXE% %BIN%\ > NUL 2>&1 || ECHO Copy %EXE failed && EXIT /B 1
EXIT /B 0
