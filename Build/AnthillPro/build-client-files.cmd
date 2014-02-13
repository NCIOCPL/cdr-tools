@REM ----------------------------------------------------------------------
@REM $Id$
@REM ----------------------------------------------------------------------

@ECHO OFF
SETLOCAL
SET SCRIPTNAME=%0
CALL :init %*           || EXIT /B
CALL :pull_svn_files    || EXIT /B
CALL :build_tools       || EXIT /B
CALL :build_loader      || EXIT /B
CALL :build_dll         || EXIT /B
CALL :build_dtds        || EXIT /B
CALL :build_manifest    || EXIT /B
CALL :cleanup           || EXIT /B
EXIT /B 0

REM ----------------------------------------------------------------------
REM Create work spaces and set environment variables.
REM ----------------------------------------------------------------------
:init
ECHO Building CDR Client Files.
IF "%1." == "." (
    ECHO Usage: CALL %SCRIPTNAME% branch-path [svn-pwd [svn-uid]]
    ECHO  e.g.: CALL %SCRIPTNAME% branches/patch-2.3
    EXiT /B 1
)
IF "%2." == "." (
    SET SVNEXP=svn export -q
) ELSE IF "%3." == "." (
    SET SVNEXP=svn export -q --password %2
) ELSE (
    SET SVNEXP=svn export -q --username %3 --password %2
)
D:
SET CLIENTFILES=d:\tmp\ClientFiles
SET SVNBRANCH=https://ncisvn.nci.nih.gov/svn/oce_cdr/%1
SET CYGDATE=d:\cygwin\bin\date.exe
SET STAMP=
FOR /F %%s IN ('%CYGDATE% +%%Y%%m%%d%%H%%M%%S') DO SET STAMP=%%s
IF NOT DEFINED STAMP ECHO %CYGDATE% failure && EXIT /B 1
SET WORKDIR=d:\tmp\client-%STAMP%
SET CDRLOADER=CdrClient-%STAMP%.exe
MKDIR %WORKDIR% || ECHO Failure creating %WORKDIR% && EXIT /B 1
CD %WORKDIR%
ECHO Created working directory.
%SVNEXP% %SVNBRANCH%/Build/AnthillPro || ECHO Failed export && EXIT /B 1
ECHO AnthillPro tools successfully fetched.
CALL d:\bin\vcvars32.bat > NUL 2>&1 || ECHO Failed VC Init && EXIT /B 1
ECHO Compiler successfully initialized.
RMDIR /S /Q %CLIENTFILES%
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
nmake > nmake.log 2>nmake.err || ECHO DLL build failure && EXIT /B 1
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
REM Set file permissions and drop our working intermediate files.
REM ----------------------------------------------------------------------
:cleanup
ECHO Setting file permssions.
CD %CLIENTFILES%
d:\cygwin\bin\chmod -R 777 * || ECHO Can't set permissions && EXIT /B 1
ECHO File permissions successfully set.
ECHO Cleaning up temporary files.
CD \
RMDIR /S /Q %WORKDIR% || ECHO Cleanup failure && EXIT /B 1
ECHO Build complete.
EXIT /B 0
