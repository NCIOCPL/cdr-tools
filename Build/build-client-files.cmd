@REM ----------------------------------------------------------------------
@REM Build the CDR client files for deployment.
@REM ----------------------------------------------------------------------

@ECHO OFF
SETLOCAL
SET SCRIPTNAME=%0

@REM Invoke each subscript, exit /B 1 inside any of them causes abort
CALL :init %*           || EXIT /B 1
CALL :move_dirs         || EXIT /B 1
CALL :build_dtds        || EXIT /B 1
CALL :build_manifest    || EXIT /B 1
EXIT /B 0

REM ----------------------------------------------------------------------
REM Verify options, set local variables, and create the directory.
REM ----------------------------------------------------------------------
:init
IF "%1." == "." (
    ECHO Usage: CALL %SCRIPTNAME% BASE-DIR
    ECHO  e.g.: CALL %SCRIPTNAME% d:\tmp\fermi
    EXIT /B 1
)
SET BASE=%1
SET BRANCH=%BASE%\branch
SET BUILD=%BRANCH%\tools\Build
SET XMETAL=%BRANCH%\client\XMetaL
SET LOADER=%XMETAL%\Loader
SET CLIENTFILES=%BASE%\ClientFiles
MKDIR %CLIENTFILES% || ECHO Failed creating %CLIENTFILES% && EXIT /B 1
EXIT /B 0

REM ----------------------------------------------------------------------
REM Move in the directories (and a couple of files) we pulled from GitHub.
REM ----------------------------------------------------------------------
:move_dirs
CHDIR /D %CLIENTFILES%
MOVE %XMETAL%\Display  . || ECHO Failure moving Display  && EXIT /B 1
MOVE %XMETAL%\Forms    . || ECHO Failure moving Forms    && EXIT /B 1
MOVE %XMETAL%\Icons    . || ECHO Failure moving Icons    && EXIT /B 1
MOVE %XMETAL%\Macros   . || ECHO Failure moving Macros   && EXIT /B 1
MOVE %XMETAL%\Rules    . || ECHO Failure moving Rules    && EXIT /B 1
MOVE %XMETAL%\Template . || ECHO Failure moving Template && EXIT /B 1
MOVE %LOADER%\cdr.ico .  || ECHO Failure moving CDR icon && EXIT /B 1
MOVE %LOADER%\cdr-loader.pyw . || ECHO Failure moving loader && EXIT /B 1
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
