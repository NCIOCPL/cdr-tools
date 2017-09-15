@REM ----------------------------------------------------------------------
@REM Assemble a set of publishing software files for deployment.
@REM ----------------------------------------------------------------------

@ECHO OFF
SETLOCAL
CALL :init              || EXIT /B 1
CALL :pull_svn_files    || EXIT /B 1
CALL :cleanup           || EXIT /B 1
EXIT /B 0

REM ----------------------------------------------------------------------
REM Create work spaces and set environment variables.
REM ----------------------------------------------------------------------
:init
ECHO Extracting Publishing Files

REM Establish defaults for all CDRBUILD_ environment variables
CALL init-build-envvars.cmd

%CDRBUILD_DRIVE%
SET PUBFILES=%CDRBUILD_DRIVE%\tmp\Publishing
SET TMP=%CDRBUILD_DRIVE%\tmp
SET SVNBRANCH=https://ncisvn.nci.nih.gov/svn/oce_cdr/trunk
SET CYGDATE=%CDRBUILD_CYGBIN%\date.exe
RMDIR /S /Q %PUBFILES%
ECHO Environment successfully initialized.
EXIT /B 0

REM ----------------------------------------------------------------------
REM Get the files which can be pulled directly from version control.
REM ----------------------------------------------------------------------
:pull_svn_files
ECHO Exporting files from Subversion.
CD %TMP%
%CYGSVN% export -q %SVNBRANCH%/Publishing   || ECHO Failed export && EXIT /B 1
ECHO Publishing files pulled successfully from Subversion.
EXIT /B 0

REM ----------------------------------------------------------------------
REM Set file permissions and drop our working intermediate files.
REM ----------------------------------------------------------------------
:cleanup
ECHO Setting file permssions.
CD %PUBFILES%
%CDRBUILD_CYGBIN%\chmod -R 777 * || ECHO Can't set permissions && EXIT /B 1
ECHO File permissions successfully set.
ECHO Build complete.
EXIT /B 0
