@REM ----------------------------------------------------------------------
@REM Build the CDR client files for deployment.
@REM ----------------------------------------------------------------------

@ECHO OFF
SETLOCAL
SET SCRIPTNAME=%0

@REM Invoke each subscript, exit /B 1 inside any of them causes abort
CALL :init %*           || EXIT /B 1
CALL :move_dirs         || EXIT /B 1
CALL :build_loader      || EXIT /B 1
CALL :build_dll         || EXIT /B 1
CALL :build_dtds        || EXIT /B 1
CALL :build_manifest    || EXIT /B 1
EXIT /B 0

REM ----------------------------------------------------------------------
REM Verify options, set local variables, and create the directory.
REM ----------------------------------------------------------------------
:init
IF "%3." == "." (
    ECHO Usage: CALL %SCRIPTNAME% BASE-DIR CDR-DRIVE TIMESTAMP
    ECHO  e.g.: CALL %SCRIPTNAME% d:\tmp\fermi D 20170918132844
    EXIT /B 1
)
SET BASE=%1
SET DRIVE=%2
SET STAMP=%3
SET VSVARS=%DRIVE%:\VisualStudio\VC\Auxiliary\Build\vcvars64.bat
SET BRANCH=%BASE%\branch
SET BUILD=%BRANCH%\tools\Build
SET XMETAL=%BRANCH%\client\XMetaL
SET CLIENTFILES=%BASE%\ClientFiles
SET LOADER=CdrClient-%STAMP%.exe
MKDIR %CLIENTFILES% || ECHO Failed creating %CLIENTFILES% && EXIT /B 1
%VSVARS% || ECHO Failed Visual Studio Init && EXIT /B 1
EXIT /B 0

REM ----------------------------------------------------------------------
REM Move in the directories we pulled from GitHub.
REM ----------------------------------------------------------------------
:move_dirs
CHDIR /D %CLIENTFILES%
MOVE %XMETAL%\Display  . || ECHO Failure moving Display  && EXIT /B 1
MOVE %XMETAL%\Forms    . || ECHO Failure moving Forms    && EXIT /B 1
MOVE %XMETAL%\Icons    . || ECHO Failure moving Icons    && EXIT /B 1
MOVE %XMETAL%\Macros   . || ECHO Failure moving Macros   && EXIT /B 1
MOVE %XMETAL%\Rules    . || ECHO Failure moving Rules    && EXIT /B 1
MOVE %XMETAL%\Template . || ECHO Failure moving Template && EXIT /B 1
EXIT /B 0

REM ----------------------------------------------------------------------
REM Build the program which launches XMetaL.
REM ----------------------------------------------------------------------
:build_loader
CHDIR /D %XMETAL%\CdrClient
nmake > nmake.log 2>nmake.err || ECHO Failed building loader && EXIT /B 1
COPY x64\Release\CdrClient.exe %CLIENTFILES%\%LOADER% > NUL 2>&1
IF ERRORLEVEL 1 ECHO Failed copying CdrClient.exe && EXIT /B 1
CHDIR /D %CLIENTFILES%
SET SCRIPT=%BUILD%\make-cdr-loader-scripts.py
python %SCRIPT% %LOADER% || ECHO Failed building loader scripts && EXIT /B 1
EXIT /B 0

REM ----------------------------------------------------------------------
REM Build the DLL used by the XMetaL client.
REM ----------------------------------------------------------------------
:build_dll
CHDIR /D %XMETAL%\DLL
nmake > nmake.log 2>nmake.err || ECHO DLL build failure && EXIT /B 1
MKDIR %CLIENTFILES%\Cdr || ECHO Failure creating DLL parent && EXIT /B 1
COPY ReleaseUMinDependency\Cdr.dll %CLIENTFILES%\Cdr\Cdr.dll > NUL 2>&1
IF ERRORLEVEL 1 ECHO Failed copying Cdr.dll && EXIT /B 1
EXIT /B 0

REM ----------------------------------------------------------------------
REM Generate the DTDs from the repository's schemas.
REM ----------------------------------------------------------------------
:build_dtds
CHDIR /D %BUILD%
python CheckDtds.py %CLIENTFILES%
IF ERRORLEVEL 1 ECHO Failure generating DTDs && EXIT /B 1
EXIT /B 0

REM ----------------------------------------------------------------------
REM Generate the manifest for the client files.
REM ----------------------------------------------------------------------
:build_manifest
CHDIR /D %BUILD%
python RefreshManifest.py %CLIENTFILES%
IF ERRORLEVEL 1 ECHO Failure building manifest && EXIT /B 1
EXIT /B 0
