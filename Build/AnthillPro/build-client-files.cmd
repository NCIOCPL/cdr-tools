@REM ----------------------------------------------------------------------
@REM $Id$
@REM ----------------------------------------------------------------------

@ECHO OFF
SETLOCAL
SET SCRIPTNAME=%0
@REM Invoke each subscript, exit /B 1 inside any of them causes abort
CALL :init %*           || EXIT /B 1
CALL :pull_svn_files    || EXIT /B 1
CALL :build_tools       || EXIT /B 1
CALL :build_loader      || EXIT /B 1
CALL :build_dll         || EXIT /B 1
CALL :build_dtds        || EXIT /B 1
CALL :build_manifest    || EXIT /B 1
CALL :export_schemas    || EXIT /B 1
CALL :cleanup           || EXIT /B 1
EXIT /B 0

REM ----------------------------------------------------------------------
REM Create work spaces and set environment variables.
REM ----------------------------------------------------------------------
:init
ECHO Building CDR Client Files.
IF "%1." == "." (
    ECHO Usage: CALL %SCRIPTNAME% branch-path [svn-pwd [svn-uid]]
    ECHO  e.g.: CALL %SCRIPTNAME% branches/patch-2.3
    EXIT /B 1
)

REM Establish defaults for all CDRBUILD_ environment variables
CALL init-build-envvars.cmd

REM Create command to export from svn
IF "%2." == "." (
    SET SVNEXP=%CYGSVN% export %CDRBUILD_SVNOPTS%
) ELSE IF "%3." == "." (
    SET SVNEXP=%CYGSVN% export %CDRBUILD_SVNOPTS% --password %2
) ELSE (
    SET SVNEXP=%CYGSVN% export %CDRBUILD_SVNOPTS% --username %3 --password %2
)

REM Output data to a directory name found in the env or created here
IF "%CDRBUILD_BASEPATH%." == "." (
  SET CLIENTFILES_TMP=%CDRBUILD_DRIVE%\tmp\ClientFiles
) ELSE (
  SET CLIENTFILES_TMP=%CDRBUILD_BASEPATH%\ClientFiles
)
SET CLIENTFILES=%CLIENTFILES_TMP:/=\%

SET SVNBRANCH=%CDRBUILD_SVNBASEURL%/%1
SET CYGDATE=%CDRBUILD_CYGBIN%\date.exe
SET STAMP=
FOR /F %%s IN ('%CYGDATE% +%%Y%%m%%d%%H%%M%%S') DO SET STAMP=%%s
IF NOT DEFINED STAMP ECHO %CYGDATE% failure && EXIT /B 1
SET WORKDIR=%CDRBUILD_DRIVE%\tmp\client-%STAMP%
SET CDRLOADER=CdrClient-%STAMP%.exe
MKDIR %WORKDIR% || ECHO Failure creating %WORKDIR% && EXIT /B 1
CD %WORKDIR%
ECHO Created working directory.
%SVNEXP% %SVNBRANCH%/Build/AnthillPro || ECHO Failed export && EXIT /B 1
ECHO Build tools successfully fetched into working directory.
CALL %CDRBUILD_DRIVE%\bin\vcvars32.bat > NUL 2>&1 || ECHO Failed Visual C++ Init (vcvars32) && EXIT /B 1
ECHO Compiler successfully initialized.
IF EXIST %CLIENTFILES% (
  RMDIR /S /Q %CLIENTFILES%
)
MKDIR %CLIENTFILES% || ECHO Failed creating %CLIENTFILES% && EXIT /B 1
ECHO Environment successfully initialized.
EXIT /B 0

REM ----------------------------------------------------------------------
REM Get the files which can be pulled directly from version control.
REM ----------------------------------------------------------------------
:pull_svn_files
ECHO Exporting files from Subversion.
CD %CLIENTFILES%
%SVNEXP% %SVNBRANCH%/XMetaL/Display   || ECHO Failed export && EXIT /B 1
%SVNEXP% %SVNBRANCH%/XMetaL/Forms     || ECHO Failed export && EXIT /B 1
%SVNEXP% %SVNBRANCH%/XMetaL/Icons     || ECHO Failed export && EXIT /B 1
%SVNEXP% %SVNBRANCH%/XMetaL/Macros    || ECHO Failed export && EXIT /B 1
%SVNEXP% %SVNBRANCH%/XMetaL/Rules     || ECHO Failed export && EXIT /B 1
%SVNEXP% %SVNBRANCH%/XMetaL/Template  || ECHO Failed export && EXIT /B 1
ECHO Client configuration files pulled successfully from Subversion.
EXIT /B 0

REM ----------------------------------------------------------------------
REM Build any troubleshooting tools used on the client machine.
REM ----------------------------------------------------------------------
:build_tools
ECHO Building client diagnostic tools.
CD %WORKDIR%
%SVNEXP% %SVNBRANCH%/XMetaL/Tools || ECHO Failed export && EXIT /B 1
CD Tools
nmake > nmake.log 2>nmake.err || ECHO Tools Build Failed && EXIT /B 1
COPY *.exe %CLIENTFILES%\ > NUL 2>&1
ECHO Tools built successfully.
EXIT /B 0

REM ----------------------------------------------------------------------
REM Build the program which launches XMetaL.
REM ----------------------------------------------------------------------
:build_loader
ECHO Building Client CDR Loader.
CD %WORKDIR%
%SVNEXP% %SVNBRANCH%/XMetaL/CdrClient || ECHO Failed export && EXIT /B 1
CD CdrClient
nmake > nmake.log 2>nmake.err || ECHO Failed building loader && EXIT /B 1
COPY Release\CdrClient.exe %CLIENTFILES%\%CDRLOADER% > NUL 2>&1
CD %CLIENTFILES%
python %WORKDIR%\AnthillPro\make-cdr-loader-scripts.py %CDRLOADER%
ECHO Loader successfully built.
EXIT /B 0

REM ----------------------------------------------------------------------
REM Build the DLL used by the XMetaL client.
REM ----------------------------------------------------------------------
:build_dll
ECHO Building Client DLL.
CD %WORKDIR%
%SVNEXP% %SVNBRANCH%/XMetaL/DLL || ECHO Failed export && EXIT /B 1
CD DLL
nmake > nmake.log 2>nmake.err || ECHO DLL build failure, check nmake.log && EXIT /B 1
MKDIR %CLIENTFILES%\Cdr
COPY ReleaseUMinDependency\Cdr.dll %CLIENTFILES%\Cdr\Cdr.dll > NUL 2>&1
ECHO DLL successfully built.
EXIT /B 0

REM ----------------------------------------------------------------------
REM Generate the DTDs from the repository's schemas.
REM ----------------------------------------------------------------------
:build_dtds
ECHO Building DTDs.
CD %WORKDIR%\AnthillPro
python CheckDtds.py %CLIENTFILES% >CheckDtds.log 2>CheckDtds.err
IF ERRORLEVEL 1 ECHO Failure generating DTDs && EXIT /B 1
ECHO DTDs successfully generated.
EXIT /B 0

REM ----------------------------------------------------------------------
REM Generate the manifest for the client files.
REM ----------------------------------------------------------------------
:build_manifest
ECHO Building fresh manifest file.
CD %WORKDIR%\AnthillPro
python RefreshManifest.py %CLIENTFILES% >RefreshManifest.err 2>&1
IF ERRORLEVEL 1 ECHO Failure building manifest && EXIT /B 1
ECHO Manifest successfully built.
EXIT /B 0

REM ----------------------------------------------------------------------
REM Export the current schemas for later deployment
REM ----------------------------------------------------------------------
:export_schemas
ECHO Exporting current schemas from version control

REM Output path
IF "%CDRBUILD_BASEPATH%." == "." (
  SET SCHEMAFILES_TMP=%CDRBUILD_DRIVE%\tmp
) ELSE (
  SET SCHEMAFILES_TMP=%CDRBUILD_BASEPATH%
)
SET SCHEMAFILES=%SCHEMAFILES_TMP:/=\%
CD %SCHEMAFILES%
%SVNEXP% %SVNBRANCH%/Schemas || ECHO Failed Schemas export && EXIT /B 1
ECHO Schemas exported successfully.
EXIT /B 0

REM ----------------------------------------------------------------------
REM Set file permissions and drop our working intermediate files.
REM ----------------------------------------------------------------------
:cleanup
ECHO Setting file permssions.
CD %CLIENTFILES%
echo DEBUG
echo CLIENTFILES=%CLIENTFILES%
%CDRBUILD_CYGBIN%\pwd
%CDRBUILD_CYGBIN%\chmod -R 777 * || ECHO Can't set permissions && EXIT /B 1
ECHO File permissions successfully set.
ECHO Cleaning up temporary files.
CD \
RMDIR /S /Q %WORKDIR% || ECHO Cleanup failure && EXIT /B 1
ECHO Build complete.
EXIT /B 0
