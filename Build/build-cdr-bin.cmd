@REM ----------------------------------------------------------------------
@REM Build the contents of the /cdr/Bin directory for deployment.
@REM ----------------------------------------------------------------------

@ECHO OFF
SETLOCAL
SET SCRIPTNAME=%0
CALL :init %*           || EXIT /B 1
CALL :pull_github_files || EXIT /B 1
CALL :pull_msvc_dlls    || EXIT /B 1
CALL :build_server      || EXIT /B 1
CALL :build_service     || EXIT /B 1
CALL :build_shutdown    || EXIT /B 1
CALL :cleanup           || EXIT /B 1
EXIT /B 0

REM ----------------------------------------------------------------------
REM Verify options and set local variables.
REM ----------------------------------------------------------------------
:init
IF "%3." == "." (
    ECHO Usage: CALL %SCRIPTNAME% BRANCH OUTPUT-BASE CDR-DRIVE
    ECHO  e.g.: CALL %SCRIPTNAME% fermi d:\tmp\fermi D
    EXiT /B 1
)
SET BRANCH=%1
SET TARGET=%2
SET DRIVE=%3
SET NCIOCPL=https://github.com/NCIOCPL
%DRIVE%:\bin\vsvars32.bat || ECHO Failed Visual Studio Init && EXIT /B 1
EXIT /B 0

REM ----------------------------------------------------------------------
REM Pull what we need from GitHub.
REM ----------------------------------------------------------------------
:pull_github_files
CD /D %TARGET%
SET URL=%NCIOCPL%/cdr-tools/branches/%BRANCH%/Bin
svn export -q %URL% || ECHO Failure exporting %URL% && EXIT /B 1
CD Bin
SET URL=%NCIOCPL%/cdr-server/branches/%BRANCH%/Server
svn export -q %URL% tmp-build || ECHO Failure exporting %URL% && EXIT /B 1
EXIT /B 0

REM ----------------------------------------------------------------------
REM Grab a copy of Microsoft's runtime DLLs.
REM ----------------------------------------------------------------------
:pull_msvc_dlls
SET DLLS=%DRIVE%:\cdr\Bin\msvc*.dll
COPY %DLLS% %TARGET%\Bin || ECHO Unable to copy MSVC DLLs && EXIT /B 1
EXIT /B 0

REM ----------------------------------------------------------------------
REM Build the CDR Server.
REM ----------------------------------------------------------------------
:build_server
CD /D %TARGET%\Bin\tmp-build
nmake DRV=%DRIVE%: CdrServer.exe >>log 2>>err || ECHO Build failed && EXIT /B 1
COPY CdrServer.exe .. > NUL 2>&1 || ECHO Copy CdrServer failed && EXIT /B 1
EXIT /B 0

REM ----------------------------------------------------------------------
REM Build the CDR Windows Service executable.
REM ----------------------------------------------------------------------
:build_service
CD /D %TARGET%\Bin\tmp-build
nmake CdrService.exe >>log 2>>err || ECHO Building service failed && EXIT /B 1
COPY CdrService.exe .. > NUL 2>&1 || ECHO Copy CdrService failed && EXIT /B 1
EXIT /B 0

REM ----------------------------------------------------------------------
REM Build the CDR Server shutdown program.
REM ----------------------------------------------------------------------
:build_shutdown
CD /D %TARGET%\Bin\tmp-build
nmake ShutdownCdr.exe >>log 2>>err || ECHO Build Shutdown failure && EXIT /B 1
COPY ShutdownCdr.exe .. > NUL 2>&1 || ECHO Copy ShutdownCdr failed && EXIT /B 1
EXIT /B 0

REM ----------------------------------------------------------------------
REM Cleanup temporary files.
REM ----------------------------------------------------------------------
:cleanup
CD /D %TARGET%\Bin
RMDIR /S /Q tmp-build || ECHO Failure cleaning up build && EXIT /B 1
ECHO Build complete.
EXIT /B 0
