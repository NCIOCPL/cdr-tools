@REM ----------------------------------------------------------------------
@REM Fetch specified branch from all of the CDR repositories.
@REM ----------------------------------------------------------------------

@ECHO OFF
SETLOCAL
SET SCRIPTNAME=%0
IF "%2." == "." (
    ECHO Usage: CALL %SCRIPTNAME% BRANCH-NAME OUTPUT-BASE
    ECHO  e.g.: CALL %SCRIPTNAME% fermi D:\tmp\build\fermi-20170909\repos
    EXIT /B 1
)
SET BRANCH=%1
SET BASE=%2
SET NCIOCPL=https://api.github.com/repos/NCIOCPL
CHDIR /D %BASE%

CALL :fetch_repo admin      || EXIT /B 1
CALL :fetch_repo client     || EXIT /B 1
CALL :fetch_repo lib        || EXIT /B 1
CALL :fetch_repo publishing || EXIT /B 1
CALL :fetch_repo scheduler  || EXIT /B 1
CALL :fetch_repo server     || EXIT /B 1
CALL :fetch_repo tools      || EXIT /B 1
EXIT /B 0

:fetch_repo
SET RNAME=%1
SET URL=%NCIOCPL%/cdr-%RNAME%/tarball/%BRANCH%
curl -L -s -k %URL% | tar -xz || ECHO %RNAME% fetch %URL% failed && EXIT /B 1
mv NCIOCPL-cdr-%RNAME%* %RNAME% || ECHO %RNAME% rename failed && EXIT /B 1
EXIT /B 0
