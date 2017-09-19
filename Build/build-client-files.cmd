@REM ----------------------------------------------------------------------
@REM Build the CDR client files for deployment.
@REM ----------------------------------------------------------------------

@ECHO OFF
SETLOCAL
SET SCRIPTNAME=%0
@REM Invoke each subscript, exit /B 1 inside any of them causes abort
CALL :init %*           || EXIT /B 1
CALL :pull_github_files || EXIT /B 1
CALL :build_loader      || EXIT /B 1
CALL :build_dll         || EXIT /B 1
CALL :build_dtds        || EXIT /B 1
CALL :build_manifest    || EXIT /B 1
CALL :cleanup           || EXIT /B 1
EXIT /B 0

REM ----------------------------------------------------------------------
REM Verify options, set local variables, and create the directory.
REM ----------------------------------------------------------------------
:init
IF "%4." == "." (
    ECHO Usage: CALL %SCRIPTNAME% BRANCH OUTPUT-BASE CDR-DRIVE TIMESTAMP
    ECHO  e.g.: CALL %SCRIPTNAME% fermi d:\tmp\fermi D 20170918132844
    EXiT /B 1
)
SET BRANCH=%1
SET TARGET=%2
SET DRIVE=%3
SET STAMP=%4
SET NCIOCPL=https://github.com/NCIOCPL
SET CLIENTFILES=%TARGET%\ClientFiles
SET LOADER=CdrClient-%STAMP%.exe
MKDIR %CLIENTFILES% || ECHO Failed creating %CLIENTFILES% && EXIT /B 1
%DRIVE%:\bin\vsvars32.bat || ECHO Failed Visual Studio Init && EXIT /B 1
EXIT /B 0

REM ----------------------------------------------------------------------
REM Pull what we need from GitHub.
REM ----------------------------------------------------------------------
:pull_github_files
CHDIR /D %CLIENTFILES%
SET URL=%NCIOCPL%/cdr-client/branches/%BRANCH%/XMetaL
SET BUILD=%NCIOCPL%/cdr-tools/branches/%BRANCH%/Build
SET EXP=svn export -q
%EXP% %URL%/Display   || ECHO Failure exporting Display   && EXIT /B 1
%EXP% %URL%/Forms     || ECHO Failure exporting Forms     && EXIT /B 1
%EXP% %URL%/Icons     || ECHO Failure exporting Icons     && EXIT /B 1
%EXP% %URL%/Macros    || ECHO Failure exporting Macros    && EXIT /B 1
%EXP% %URL%/Rules     || ECHO Failure exporting Rules     && EXIT /B 1
%EXP% %URL%/Template  || ECHO Failure exporting Template  && EXIT /B 1
MKDIR tmp-build       || ECHO Failure creating tmp-build  && EXIT /B 1
CHDIR tmp-build       || ECHO Failure entering tmp-build  && EXIT /B 1
%EXP% %URL%/CdrClient || ECHO Failure exporting CdrClient && EXIT /B 1
%EXP% %URL%/DLL       || ECHO Failure exporting DLL       && EXIT /B 1
%EXP% %BUILD%         || ECHO Failure exporting Build     && EXIT /B 1
EXIT /B 0

REM ----------------------------------------------------------------------
REM Build the program which launches XMetaL.
REM ----------------------------------------------------------------------
:build_loader
CHDIR /D %CLIENTFILES%\tmp-build\CdrClient
nmake > nmake.log 2>nmake.err || ECHO Failed building loader && EXIT /B 1
COPY Release\CdrClient.exe %CLIENTFILES%\%LOADER% > NUL 2>&1
IF ERRORLEVEL 1 ECHO Failed copying CdrClient.exe && EXIT /B 1
CHDIR /D %CLIENTFILES%
SET SCRIPT=tmp-build\Build\make-cdr-loader-scripts.py
python %SCRIPT% %LOADER% || ECHO Failed building loader scripts && EXIT /B 1
EXIT /B 0

REM ----------------------------------------------------------------------
REM Build the DLL used by the XMetaL client.
REM ----------------------------------------------------------------------
:build_dll
CHDIR /D %CLIENTFILES%\tmp-build\DLL
nmake > nmake.log 2>nmake.err || ECHO DLL build failure && EXIT /B 1
MKDIR %CLIENTFILES%\Cdr
COPY ReleaseUMinDependency\Cdr.dll %CLIENTFILES%\Cdr\Cdr.dll > NUL 2>&1
IF ERRORLEVEL 1 ECHO Failed copying Cdr.dll && EXIT /B 1
EXIT /B 0

REM ----------------------------------------------------------------------
REM Generate the DTDs from the repository's schemas.
REM ----------------------------------------------------------------------
:build_dtds
CHDIR /D %CLIENTFILES%\tmp-build\Build
python CheckDtds.py %CLIENTFILES% >CheckDtds.log 2>CheckDtds.err
IF ERRORLEVEL 1 ECHO Failure generating DTDs && EXIT /B 1
EXIT /B 0

REM ----------------------------------------------------------------------
REM Generate the manifest for the client files.
REM ----------------------------------------------------------------------
:build_manifest
CHDIR /D %CLIENTFILES%\tmp-build\Build
python RefreshManifest.py %CLIENTFILES% >RefreshManifest.err 2>&1
IF ERRORLEVEL 1 ECHO Failure building manifest && EXIT /B 1
EXIT /B 0

REM ----------------------------------------------------------------------
REM Drop our working intermediate files.
REM ----------------------------------------------------------------------
:cleanup
CHDIR %CLIENTFILES%
RMDIR /S /Q tmp-build || ECHO Cleanup failure && EXIT /B 1
ECHO Build complete.
EXIT /B 0
