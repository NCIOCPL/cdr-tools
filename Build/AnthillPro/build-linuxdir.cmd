@REM ----------------------------------------------------------------------
@REM Assemble the files needed by one of the CDR Linux servers.
@REM ----------------------------------------------------------------------
@ECHO OFF
SETLOCAL

REM ----------------------------------------------------------------------
REM Set variables based on passed parameters
REM ----------------------------------------------------------------------

REM First three parms are required
IF "%3." == "." (
 ECHO Usage: CALL %SCRIPTNAME% branch output-base, server [svn-pwd [svn-uid]]
 ECHO   branch      = Subversion branch, e.g. "trunk", "branches/Einstein", etc.
 ECHO   output-base = Directory where output goes, e.g., "d:\tmp\cdrbuild"
 ECHO   server      = One of Glossifier, Emailers, FTP
 ECHO   svn-pwd     = Subversion password, if not using cached credentials.
 ECHO   svn-uid     = Subversion userid, if not using cached credentials.
 ECHO Example:
 ECHO   %SCRIPTNAME% branches/Einstein d:\tmp\cdr\2014-04-28-linux FTP
 EXIT /B 1
)

REM Establish defaults for all CDRBUILD_ environment variables
CALL init-build-envvars.cmd

REM Get mandatory arguments
SET SVNBRNCH_TMP=%1
SET BASE_DIR_TMP=%2
SET SVNBRNCH=%SVNBRNCH_TMP:\=/%
SET BASE_DIR=%BASE_DIR_TMP:/=\%
SET LINUX_SERVER=%3
SET BRNCH_URL=%CDRBUILD_SVNBASEURL%/%SVNBRNCH%
SET DEPLOY_SH=%BRNCH_URL%/Build/AnthillPro/deploy-%LINUX_SERVER%.sh
REM Output for the record
ECHO Subversion branch = '%SVNBRNCH%'
ECHO Branch URL        = '%BRNCH_URL%'
ECHO Base directory    = '%BASE_DIR%'
ECHO Linux server      = '%LINUX_SERVER%'
ECHO Deployment script = '%DEPLOY_SH%'

REM ----------------------------------------------------------------------
REM Create work spaces and set variables.
REM ----------------------------------------------------------------------
:init

ECHO Building CDR Linux subdirectory.

REM ----------------------------------------------------------------------
REM Establish defaults for all CDRBUILD_ environment variables
REM ----------------------------------------------------------------------
CALL init-build-envvars.cmd

REM ----------------------------------------------------------------------
REM Subversion parameters
REM ----------------------------------------------------------------------
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

ECHO Environment successfully initialized.

REM ----------------------------------------------------------------------
REM Determine which server we're building for.
REM ----------------------------------------------------------------------
IF %LINUX_SERVER%==Glossifier ( CALL :build_glossifier || EXIT /B 1 )
IF %LINUX_SERVER%==Emailers   ( CALL :build_emailers   || EXIT /B 1 )
IF %LINUX_SERVER%==FTP        ( CALL :build_ftp        || EXIT /B 1 )
ECHO Done exporting %LINUX_SERVER% files.
ENDLOCAL
EXIT /B 0

REM ----------------------------------------------------------------------
REM Assemble the files for the Glossifier server.
REM ----------------------------------------------------------------------
:build_glossifier
ECHO Exporting files for the Glossifier server.
CD /D %BASE_DIR%
MKDIR Glossifier || ECHO Unable to create Glossifier directory && EXIT /B 1
CD Glossifier
%SVNEXP% %BRNCH_URL%/glossifier/cgi-bin   || ECHO Failed export && EXIT /B 1
%SVNEXP% %BRNCH_URL%/glossifier/util      || ECHO Failed export && EXIT /B 1
%SVNEXP% %BRNCH_URL%/lib/Python           || ECHO Failed export && EXIT /B 1
%SVNEXP% %DEPLOY_SH% deploy.sh            || ECHO Failed export && EXIT /B 1
EXIT /B 0

REM ----------------------------------------------------------------------
REM Assemble the files for the Emailers server.
REM ----------------------------------------------------------------------
:build_emailers
ECHO Exporting files for the Emailers server.
CD /D %BASE_DIR%
MKDIR Emailers || ECHO Unable to create Emailers directory && EXIT /B 1
CD Emailers
%SVNEXP% %BRNCH_URL%/gpmailers/cgi-bin    || ECHO Failed export && EXIT /B 1
%SVNEXP% %BRNCH_URL%/gpmailers/util       || ECHO Failed export && EXIT /B 1
%SVNEXP% %BRNCH_URL%/gpmailers/images     || ECHO Failed export && EXIT /B 1
%SVNEXP% %BRNCH_URL%/lib/Python           || ECHO Failed export && EXIT /B 1
%SVNEXP% %DEPLOY_SH% deploy.sh            || ECHO Failed export && EXIT /B 1
EXIT /B 0

REM ----------------------------------------------------------------------
REM Assemble the files for the FTP server, pulling in pdq.dtd from /Licensee
REM ----------------------------------------------------------------------
:build_ftp
ECHO Exporting files for the FTP server.
CD /D %BASE_DIR%
MKDIR FTP  || ECHO Unable to create FTP directory && EXIT /B 1
CD FTP
MKDIR prod || ECHO Unable to create FTP/prod directory && EXIT /B 1
%SVNEXP% %DEPLOY_SH% deploy.sh            || ECHO Failed export && EXIT /B 1
%SVNEXP% %BRNCH_URL%/lib/Python           || ECHO Failed export && EXIT /B 1
CD prod
%SVNEXP% %BRNCH_URL%/Production/prod/bin  || ECHO Failed export && EXIT /B 1
%SVNEXP% %BRNCH_URL%/Production/prod/lib  || ECHO Failed export && EXIT /B 1
%SVNEXP% %BRNCH_URL%/Production/prod/docs || ECHO Failed export && EXIT /B 1
CD docs
%SVNEXP% %BRNCH_URL%/Licensee/pdq.dtd     || ECHO Failed export && EXIT /B 1
EXIT /B 0
