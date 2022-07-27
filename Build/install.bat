@ECHO off
SETLOCAL

REM ======================================================================
REM This is the template for the master deployment script for the CDR
REM Windows server on a given tier. Here's what you do with it:
REM   1. put the build on a subdirectory of the cdr_deployments share
REM      (ensure that it's world-readable)
REM   2. replace REPLACEME below to set BUILD to that location (we
REM      don't want to put an internal server name into source code
REM      in a public repository)
REM   3. (optionally) add any extra steps needed for this specific
REM      release on the Windows server (e.g., add new DB tables)
REM
REM (cf. https://github.com/NCIOCPL/cdr-tools/tree/master/Build)
REM ======================================================================

REM ----------------------------------------------------------------------
REM This is the part which *MUST* be customized for each release.
REM ----------------------------------------------------------------------
SET BUILD=REPLACEME

REM ----------------------------------------------------------------------
REM Set the rest of the variables.
REM ----------------------------------------------------------------------
SET PYTHON=D:\Python\python.exe
SET DEPLOY=%BUILD%\Build\deploy-cdr.py
SET UPDATE=%BUILD%\Build\install-docset.py %BUILD%
SET LOADER=%BUILD%\Database\Loader
SET INSTALL_LOADER_VALUES=%BUILD%\Build\install-loader-values.py -d %LOADER%

REM ----------------------------------------------------------------------
REM Make sure the share is reachable, and we really have a release there.
REM ----------------------------------------------------------------------
if not exist %BUILD%\Licensee\pdq.dtd (
    ECHO .
    ECHO ********************   SCRIPT ERROR   *****************************
    ECHO %BUILD% is not reachable
    ECHO or does not contain the files for a complete CDR release.
    ECHO Please resolve this problem and try again.
    ECHO ********************   SCRIPT ERROR   *****************************
    ECHO .
    goto END
)

REM ----------------------------------------------------------------------
REM Make sure we're actually running on a CDR server.
REM ----------------------------------------------------------------------
IF NOT EXIST D:\etc\cdrapphosts.rc (
    ECHO .
    ECHO ********************   SCRIPT ERROR   *****************************
    ECHO Unable to find CDR host names file. This does not appear to be
    ECHO running on a CDR Windows server. Please log into the CDR Windows
    ECHO app server and run this script there.
    ECHO ********************   SCRIPT ERROR   *****************************
    ECHO .
    goto END
)

REM ----------------------------------------------------------------------
REM This is the part where we actually do the deployment.
REM ----------------------------------------------------------------------
CHDIR /D D:\
%PYTHON% %DEPLOY% %BUILD% || ECHO Deploy CDR failed && EXIT /B 1
%PYTHON% %UPDATE%\Schemas schema || ECHO Update schemas failed && EXIT /B 1
%PYTHON% %UPDATE%\Filters filter || ECHO Update filters failed && EXIT /B 1
%PYTHON% %INSTALL_LOADER_VALUES% || ECHO Loader values failed && EXIT /B 1

REM ----------------------------------------------------------------------
REM You might need to add commands here for things which aren't taken
REM care of by the deploy-all script. For example:
REM %PYTHON% D:\cdr\Database\add-tables-for-ocecdr-9999.py
REM
REM For some edge cases, you might need to add an extra command *before*
REM the deploy-all script runs. For example, for one release we needed
REM to set some obsolete document types as inactive before the script to
REM generate fresh DTDs for the CDR client for the active document types.
REM ----------------------------------------------------------------------

ECHO .
ECHO *******************************************************************
ECHO                   Deployment script completed
ECHO *******************************************************************
ECHO .
:END
ENDLOCAL
PAUSE
