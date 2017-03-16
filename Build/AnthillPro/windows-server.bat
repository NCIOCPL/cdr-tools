@echo off
setlocal

rem ======================================================================
rem This is the template for the master deployment script for the CDR
rem Windows server on a given tier. Here's what you do with it:
rem   1. copy it to the release directory in the root of the cdr_deployments
rem      share (e.g., \\nciis-p401.nci.nih.gov\cdr_deployments\einstein)
rem   2. replace REPLACEME below to set the variable RELEASE to the
rem      name of that directory
rem   3. (optionally) add any extra steps needed for this specific
rem      release on the Windows server (e.g., add new DB tables)
rem
rem (cf. https://collaborate.nci.nih.gov/display/OCECTBWIKI/CDR+Release+Deployment+How-To)
rem ======================================================================

rem ----------------------------------------------------------------------
rem This is the part which *MUST* be customized for each release.
rem e.g., set RELEASE=einstein
rem ----------------------------------------------------------------------
set RELEASE=REPLACEME

rem ----------------------------------------------------------------------
rem Set the rest of the variables.
rem ----------------------------------------------------------------------
set CDR_DEPLOYMENTS=\\nciis-p401.nci.nih.gov\cdr_deployments
set RELEASE_DIR=%CDR_DEPLOYMENTS%\%RELEASE%\windows
set PYTHON=D:\Python\python.exe
set DEPLOY_ALL=%CDR_DEPLOYMENTS%\Scripts\deploy-all.py
set DEPLOY_OPTS=--live %RELEASE_DIR% d:\cdr

rem ----------------------------------------------------------------------
rem Make sure the share is reachable, and we really have a release there.
rem ----------------------------------------------------------------------
if not exist %RELEASE_DIR%\Licensee\pdq.dtd (
    echo .
    echo ********************   SCRIPT ERROR   *****************************
    echo %RELEASE_DIR% is not reachable
    echo or does not contain the files for a complete CDR release.
    echo Please resolve this problem and try again.
    echo ********************   SCRIPT ERROR   *****************************
    echo .
    goto END
)

rem ----------------------------------------------------------------------
rem Make sure we're actually running on a CDR server.
rem ----------------------------------------------------------------------
if not exist D:\cdr\Bin\CdrServer.exe (
    echo .
    echo ********************   SCRIPT ERROR   *****************************
    echo Unable to find CdrServer.exe binary. This does not appear to be
    echo running on a CDR Windows server. Please log into the CDR Windows
    echo app server and run this script there.
    echo ********************   SCRIPT ERROR   *****************************
    echo .
    goto END
)

rem ----------------------------------------------------------------------
rem This is the part where we actually do the deployment.
rem ----------------------------------------------------------------------
cd /D D:\
%PYTHON% %DEPLOY_ALL% %DEPLOY_OPTS%

rem ----------------------------------------------------------------------
rem You might need to add commands here for things which aren't taken
rem care of by the deploy-all script. For example:
rem %PYTHON% D:\cdr\Database\add-tables-for-ocecdr-9999.py
rem
rem For some edge cases, you might need to add an extra command *before*
rem the deploy-all script runs. For example, for one release we needed
rem to set some obsolete document types as inactive before the build-all
rem script generated fresh DTDs for the CDR client for the active document
rem types.
rem ----------------------------------------------------------------------

echo .
echo *******************************************************************
echo                   Deployment script completed
echo *******************************************************************
echo .
:END
pause
