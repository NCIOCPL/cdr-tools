@REM ----------------------------------------------------------------------
@REM Pull the files for a CDR directory from version control.
@REM ----------------------------------------------------------------------

@ECHO OFF
SETLOCAL
SET SCRIPTNAME=%0
CALL :init %* || EXIT /B 1
CALL :pull    || EXIT /B 1
ENDLOCAL
EXIT /B 0

REM ----------------------------------------------------------------------
REM Create work spaces and create environment variables.
REM ----------------------------------------------------------------------
:init
IF "%3." == "." (
    SET URL=https://github.com/NCIOCPL/cdr-lib/branches/fermi
    SET LOC=d:\tmp\fermi
    ECHO Usage: CALL %SCRIPTNAME% URL LOCATION DIRECTORY
    ECHO  e.g.: CALL %SCRIPTNAME% %URL% %LOC% lib
    EXIT /B 1
)
SET URL=%1
SET LOC=%2
SET DIR=%3
EXIT /B 0

REM ----------------------------------------------------------------------
REM Pull the files from GitHub.
REM ----------------------------------------------------------------------
:pull
CD /D %LOC%
ECHO Pulling %DIR% from %URL%
svn export -q %URL% %DIR% || ECHO Failure exporting %URL% && EXIT /B 1
EXIT /B 0
