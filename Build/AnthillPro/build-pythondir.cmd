@REM ----------------------------------------------------------------------
@REM BZIssue::None  (JIRA::WEBTEAM-1884)
@REM Despite the name, this is used for more than directories containing
@REM Python scripts (e.g., Licensee).
@REM ----------------------------------------------------------------------
@ECHO OFF
SETLOCAL

REM ----------------------------------------------------------------------
REM Set variables based on passed parameters
REM ----------------------------------------------------------------------

REM First three parms are required
IF "%3." == "." (
 ECHO Usage: CALL %SCRIPTNAME% branch output-base, files-dir [svn-pwd [svn-uid]]
 ECHO   branch      = Subversion branch, e.g., "trunk", "branches/Ampere", etc.
 ECHO   output-base = Directory where output goes, e.g., "d:\tmp\cdrbuild"
 ECHO   files-dir   = Subversion directory to export, "lib", "Utilities", etc.
 ECHO                 ALL-BRANCH gets everything - almost certainly more than
 ECHO                 you really want - and puts it in output-base/branchname.
 ECHO   svn-pwd     = Subversion password, if not using cached credentials.
 ECHO   svn-uid     = Subversion userid, if not using cached credentials.
 ECHO Example:
 ECHO   %SCRIPTNAME% branches/Einstein d:\tmp\cdr\2014-04-28 lib
 EXIT /B 1
)

REM Establish defaults for all CDRBUILD_ environment variables
CALL init-build-envvars.cmd

REM Clear left over variables
REM Get all parameters
SET SVNBRNCH_TMP=%1
SET BASE_DIR_TMP=%2
SET FILES_DIR_TMP=%3
IF %FILES_DIR_TMP%==ALL-BRANCH (
  ECHO Exporting entire branch
  SET SVNEXPORT_POINT_TMP=%CDRBUILD_SVNBASEURL%/%SVNBRNCH_TMP%
  SET OUTPUT_DIR_TMP=%BASE_DIR_TMP%
) ELSE (
  ECHO Exporting just the specified directory: %FILES_DIR_TMP%
  SET SVNEXPORT_POINT_TMP=%CDRBUILD_SVNBASEURL%/%SVNBRNCH_TMP%/%FILES_DIR_TMP%
  SET OUTPUT_DIR_TMP=%BASE_DIR_TMP%\%FILES_DIR_TMP%
)

REM Replace slashes as needed for Windows or Linux
SET SVNBRNCH=%SVNBRNCH_TMP:\=/%
SET BASE_DIR=%BASE_DIR_TMP:/=\%
SET FILES_DIR=%FILES_DIR_TMP:/=\%
SET SVNEXPORT_POINT=%SVNEXPORT_POINT_TMP:\=/%
SET OUTPUT_DIR=%OUTPUT_DIR_TMP:/=\%

REM Output for the record
ECHO Subversion branch = '%SVNBRNCH%'
ECHO Base directory    = '%BASE_DIR%'
ECHO Files collection  = '%FILES_DIR%'
ECHO svn export point  = '%SVNEXPORT_POINT%'
ECHO Output directory  = '%OUTPUT_DIR%'

REM ----------------------------------------------------------------------
REM Invoke the main parts of the script
REM ----------------------------------------------------------------------
SETLOCAL
SET SCRIPTNAME=%0
REM CALL :init              || EXIT /B 1
REM CALL :pull_svn_files    || EXIT /B 1
REM CALL :cleanup           || EXIT /B 1
REM EXIT /B 0

REM ----------------------------------------------------------------------
REM Create work spaces and set variables.
REM ----------------------------------------------------------------------
:init

ECHO Building CDR Python directory.

REM Establish defaults for all CDRBUILD_ environment variables
CALL init-build-envvars.cmd

REM Subversion parameters
IF "%4." == "." (
    SET SVNEXP=%CYGSVN% export %CDRBUILD_SVNOPTS%
) ELSE IF "%5." == "." (
    SET SVNEXP=%CYGSVN% export %CDRBUILD_SVNOPTS% --password %4
) ELSE (
    SET SVNEXP=%CYGSVN% export %CDRBUILD_SVNOPTS% --username %5 --password %4
)

ECHO Creating (or finding) base directory
IF NOT EXIST %BASE_DIR% (
  MKDIR %BASE_DIR%
)
CD /D %BASE_DIR%
DEL %BASE_DIR%\*.* /Q

ECHO Environment successfully initialized.

REM ----------------------------------------------------------------------
REM Get the files which can be pulled directly from version control.
REM ----------------------------------------------------------------------
:pull_svn_files
ECHO Exporting files from Subversion.
ECHO Using: %SVNEXP% %SVNEXPORT_POINT%
CD %BASE_DIR%

%SVNEXP% %SVNEXPORT_POINT% || ECHO Failed export && EXIT /B 1
ECHO Files exported successfully from Subversion.

REM ----------------------------------------------------------------------
REM Set file permissions and drop our working intermediate files.
REM ----------------------------------------------------------------------
:cleanup
ECHO Setting file permssions.
CD %OUTPUT_DIR%
%CDRBUILD_CYGBIN%\chmod -R 777 * || ECHO Can't set permissions && EXIT /B 1
ECHO File permissions successfully set.

ECHO Build complete.
EXIT /B 0
