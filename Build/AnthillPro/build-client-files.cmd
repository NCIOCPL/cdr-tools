@ECHO OFF
ECHO Building CDR Client Files.
SETLOCAL

REM ----------------------------------------------------------------------
REM Make Microsoft's compiler available.
REM ----------------------------------------------------------------------
CALL d:\bin\vcvars32.bat > NUL 2>&1

REM ----------------------------------------------------------------------
REM Create the target localtion.
REM ----------------------------------------------------------------------
SET CLIENTFILES=d:\tmp\ClientFiles
RMDIR /S /Q %CLIENTFILES%
MKDIR %CLIENTFILES%

SET SVNBRANCH=https://ncisvn.nci.nih.gov/svn/oce_cdr/trunk
SET CYGDATE=d:\cygwin\bin\date.exe
CALL :pull_svn_files
CALL :make_working_dir
CALL :build_tools
CALL :build_loader
IF %ERRORLEVEL% GEQ 1 @exit /b 1
@CALL :build_dll
IF %ERRORLEVEL% GEQ 1 @exit /b 1
CD %WORKDIR%\AnthillPro
python CheckDtds.py %CLIENTFILES% >CheckDtds.log 2>CheckDtds.err
ECHO DTDs successfully generated.
python RefreshManifest.py %CLIENTFILES% >RefreshManifest.err 2>&1
ECHO Manifest successfully built.
CD %CLIENTFILES%
d:\cygwin\bin\chmod -R 777 *
ECHO Build complete.
EXIT /B 0

REM ----------------------------------------------------------------------
REM Build any troubleshooting tools used on the client machine.
REM ----------------------------------------------------------------------
:build_tools
ECHO Building client diagnostic tools.
CD %WORKDIR%
svn export -q %SVNBRANCH%/XMetaL/Tools
CD Tools
nmake > nmake.log 2>nmake.err
IF NOT EXIST ShowTimestamp.exe (
    ECHO Tools Build Failed
    EXIT /B 1
)
COPY *.exe %CLIENTFILES%\ > NUL 2>&1
ECHO Tools built successfully.
EXIT /B 0

REM ----------------------------------------------------------------------
REM Get the files which can be pulled directly from version control.
REM ----------------------------------------------------------------------
:pull_svn_files
ECHO Exporting files from Subversion.
CD %CLIENTFILES%
svn export -q %SVNBRANCH%/XMetaL/Display
svn export -q %SVNBRANCH%/XMetaL/Forms
svn export -q %SVNBRANCH%/XMetaL/Icons
svn export -q %SVNBRANCH%/XMetaL/Macros
svn export -q %SVNBRANCH%/XMetaL/Rules
svn export -q %SVNBRANCH%/XMetaL/Template
ECHO Client configuration files pulled from Subversion.
EXIT /B 0

REM ----------------------------------------------------------------------
REM Build a working directory based on current date/time.
REM ----------------------------------------------------------------------
:make_working_dir
D:
SET WORKDIR=
FOR /F %%i IN ('%CYGDATE% +d:\tmp\client-%%Y%%m%%d%%H%%M%%S') DO (
    SET WORKDIR=%%i
)
MKDIR %WORKDIR%
CD %WORKDIR%
svn export -q %SVNBRANCH%/Build/AnthillPro
ECHO Created working directory.
EXIT /B 0

REM ----------------------------------------------------------------------
REM Build the DLL used by the XMetaL client.
REM ----------------------------------------------------------------------
:build_dll
CD %WORKDIR%
ECHO Building Client DLL.
svn export -q %SVNBRANCH%/XMetaL/DLL
CD DLL
nmake > nmake.log 2>nmake.err
IF NOT EXIST ReleaseUMinDependency\Cdr.dll (
    ECHO DLL Build Failed.
    EXIT /B 1
)
MKDIR %CLIENTFILES%\Cdr
COPY ReleaseUMinDependency\Cdr.dll %CLIENTFILES%\Cdr\Cdr.dll > NUL 2>&1
ECHO DLL successfully built.
EXIT /B 0

REM ----------------------------------------------------------------------
REM Build the program which launches XMetaL.
REM ----------------------------------------------------------------------
:build_loader
CD %WORKDIR%
ECHO Building Client CDR Loader.
svn export -q %SVNBRANCH%/XMetaL/CdrClient
CD CdrClient
nmake > nmake.log 2>nmake.err
IF NOT EXIST Release\CdrClient.exe (
    ECHO Loader Build Failed.
    EXIT /B 1
)
FOR /F %%i IN ('%CYGDATE% +CdrClient-%%Y%%m%%d%%H%%M%%S.exe') DO (
    SET CDRLOADER=%%i
)
COPY Release\CdrClient.exe %CLIENTFILES%\%CDRLOADER% > NUL 2>&1
CD %CLIENTFILES%
python %WORKDIR%\AnthillPro\make-cdr-loader-scripts.py %CDRLOADER%
ECHO Loader successfully built.
EXIT /B 0
