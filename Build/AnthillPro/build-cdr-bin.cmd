@REM ----------------------------------------------------------------------
@REM $Id$
@REM ----------------------------------------------------------------------

@ECHO OFF
SETLOCAL
SET SCRIPTNAME=%0
CALL :init %*           || EXIT /B
CALL :pull_svn_files    || EXIT /B
CALL :pull_msvc_dlls    || EXIT /B
CALL :build_server      || EXIT /B
CALL :build_service     || EXIT /B
CALL :build_shutdown    || EXIT /B
CALL :cleanup           || EXIT /B
EXIT /B 0

REM ----------------------------------------------------------------------
REM Create work spaces and set environment variables.
REM ----------------------------------------------------------------------
:init
ECHO Building CDR Bin directory.
IF "%1." == "." (
    ECHO Usage: CALL %SCRIPTNAME% branch-path [svn-pwd [svn-uid]]
    ECHO  e.g.: CALL %SCRIPTNAME% branches/patch-2.3
    EXiT /B 1
)
IF "%2." == "." (
    SET SVNEXP=svn export -q
) ELSE IF "%3." == "." (
    SET SVNEXP=svn export -q --password %2
) ELSE (
    SET SVNEXP=svn export -q --username %3 --password %2
)
D:
SET BUILDDIR=d:\tmp\Build
SET BINDIR=%BUILDDIR%\Bin
SET SVNBRANCH=https://ncisvn.nci.nih.gov/svn/oce_cdr/%1
SET CYGDATE=d:\cygwin\bin\date.exe
SET STAMP=
FOR /F %%s IN ('%CYGDATE% +%%Y%%m%%d%%H%%M%%S') DO SET STAMP=%%s
IF NOT DEFINED STAMP ECHO %CYGDATE% failure && EXIT /B 1
SET WORKDIR=d:\tmp\cdr-bin-%STAMP%
MKDIR %WORKDIR% || ECHO Failure creating %WORKDIR% && EXIT /B 1
CD %WORKDIR%
ECHO Created working directory.
CALL d:\bin\vcvars32.bat > NUL 2>&1 || ECHO Failed VC Init && EXIT /B 1
ECHO Compiler successfully initialized.
MKDIR %BUILDDIR% >NUL 2>&1
RMDIR /S /Q %BINDIR% >NUL 2>&1
ECHO Environment successfully initialized.
EXIT /B 0

REM ----------------------------------------------------------------------
REM Get the files which can be pulled directly from version control.
REM This creates the output directory for the AHP artifact, so it
REM must be done early.
REM ----------------------------------------------------------------------
:pull_svn_files
ECHO Exporting scripts from Subversion.
CD %BUILDDIR%
%SVNEXP% %SVNBRANCH%/Bin || ECHO Failed export && EXIT /B 1
ECHO Scripts successfully exported from Subversion.
EXIT /B 0

REM ----------------------------------------------------------------------
REM Get the Microsoft runtime DLLs.
REM ----------------------------------------------------------------------
:pull_msvc_dlls
ECHO Preserving Microsoft runtime DLLs.
COPY d:\cdr\Bin\msvc*.dll %BINDIR% >NUL 2>&1 || ECHO Copy Failed && EXIT /B 1
ECHO Microsoft runtime DLLs successfully fetched.
EXIT /B 0

REM ----------------------------------------------------------------------
REM Build the CDR server executable.
REM ----------------------------------------------------------------------
:build_server
ECHO Building CDR Server
CD %WORKDIR%
%SVNEXP% %SVNBRANCH%/Server || ECHO Failed export && EXIT /B 1
CD Server
nmake CdrServer.exe >>log 2>>err || ECHO Server Build Failed && EXIT /B 1
COPY CdrServer.exe %BINDIR%\ > NUL 2>&1
ECHO Server built successfully.
EXIT /B 0

REM ----------------------------------------------------------------------
REM Build the CDR service executable.  We already have the source.
REM ----------------------------------------------------------------------
:build_service
ECHO Building CDR Windows Service executable.
CD %WORKDIR%\Server
nmake CdrService.exe >>log 2>>err || ECHO Service Build Failed && EXIT /B 1
COPY CdrService.exe %BINDIR% > NUL 2>&1
ECHO Service built successfully.
EXIT /B 0

REM ----------------------------------------------------------------------
REM Build the CDR Server shutdown program.  We already have the source.
REM ----------------------------------------------------------------------
:build_shutdown
ECHO Building CDR Server shutdown program.
CD %WORKDIR%\Server
nmake ShutdownCdr.exe >>log 2>>err || ECHO Shutdown Build Failed && EXIT /B 1
COPY ShutdownCdr.exe %BINDIR% > NUL 2>&1
ECHO Shutdown program built successfully.
EXIT /B 0

REM ----------------------------------------------------------------------
REM Set file permissions and drop our working intermediate files.
REM ----------------------------------------------------------------------
:cleanup
ECHO Setting file permssions.
CD %BINDIR%
d:\cygwin\bin\chmod -R 777 * || ECHO Can't set permissions && EXIT /B 1
ECHO File permissions successfully set.
ECHO Cleaning up temporary files.
CD \
RMDIR /S /Q %WORKDIR% || ECHO Cleanup failure && EXIT /B 1
ECHO Build complete.
EXIT /B 0
