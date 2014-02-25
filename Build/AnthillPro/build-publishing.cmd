@REM ----------------------------------------------------------------------
@REM $Id: $
@REM ----------------------------------------------------------------------

@ECHO OFF
SETLOCAL
CALL :init              || EXIT /B
CALL :pull_svn_files    || EXIT /B
CALL :cleanup           || EXIT /B
EXIT /B 0

REM ----------------------------------------------------------------------
REM Create work spaces and set environment variables.
REM ----------------------------------------------------------------------
:init
ECHO Extracting Publishing Files
D:
SET PUBFILES=d:\tmp\Publishing
SET TMP=d:\tmp
SET SVNBRANCH=https://ncisvn.nci.nih.gov/svn/oce_cdr/trunk
SET CYGDATE=d:\cygwin\bin\date.exe
RMDIR /S /Q %PUBFILES%
ECHO Environment successfully initialized.
EXIT /B 0

REM ----------------------------------------------------------------------
REM Get the files which can be pulled directly from version control.
REM ----------------------------------------------------------------------
:pull_svn_files
ECHO Exporting files from Subversion.
CD %TMP%
svn export -q %SVNBRANCH%/Publishing   || ECHO Failed export && EXIT /B 1
ECHO Publishing files pulled successfully from Subversion.
EXIT /B 0

REM ----------------------------------------------------------------------
REM Set file permissions and drop our working intermediate files.
REM ----------------------------------------------------------------------
:cleanup
ECHO Setting file permssions.
CD %PUBFILES%
d:\cygwin\bin\chmod -R 777 * || ECHO Can't set permissions && EXIT /B 1
ECHO File permissions successfully set.
ECHO Build complete.
EXIT /B 0
