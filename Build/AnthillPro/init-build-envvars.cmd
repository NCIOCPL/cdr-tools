@ECHO OFF
REM ----------------------------------------------------------------------
REM $Id$
REM Initialize environment variables
REM
REM This should be safe to CALL multiple times, e.g. from each of the
REM build scripts.  It will modify the environment persistently.
REM ----------------------------------------------------------------------

REM ----------------------------------------------------------------------
REM Find drive with cdr installed
REM ----------------------------------------------------------------------
ECHO Establishing drive letter with CDR installed.
IF "%CDRBUILD_DRIVE%." == "." (
  IF EXIST d:\cdr\lib\Python\cdr.py (
    SET CDRBUILD_DRIVE=d:
  ) ELSE IF EXIST c:\cdr\lib\Python\cdr.py (
    SET CDRBUILD_DRIVE=c:
  ) ELSE IF EXIST f:\cdr\lib\Python\cdr.py (
    SET CDRBUILD_DRIVE=f:
  ) ELSE IF EXIST e:\cdr\lib\Python\cdr.py (
    SET CDRBUILD_DRIVE=e:
  ) ELSE (
    ECHO Could not find \cdr\lib\python\cdr.py in d: c: f: e:
    ECHO Can't establish a working drive
    ECHO Aborting!
    EXIT /B 1
  )
)

REM ----------------------------------------------------------------------
REM Find path to cygwin and bin directory within it
REM ----------------------------------------------------------------------
ECHO Establishing path to cygwin
IF "%CDRBUILD_CYGPATH%." == "." (
  IF EXIST %CDRBUILD_DRIVE%\cygwin (
    SET CDRBUILD_CYGPATH=%CDRBUILD_DRIVE%\cygwin
  ) ELSE IF EXIST %CDRBUILD_DRIVE%\cygwin64 (
    SET CDRBUILD_CYGPATH=%CDRBUILD_DRIVE%\cygwin64
  ) ELSE (
    ECHO Can't find cygwin path.
    ECHO Please set env var CDRBUILD_CYGPATH to point to it
    EXIT /B 1
  )
)

SET CDRBUILD_CYGBIN=%CDRBUILD_CYGPATH%\bin
SET CYGSVN=%CDRBUILD_CYGBIN%\svn.exe

REM ----------------------------------------------------------------------
REM Set path to build directory.  Create it if it doesn't exist.
REM ----------------------------------------------------------------------
ECHO Establishing build directory

IF "%CDRBUILD_BASEPATH%." == "." (
  SET CDRBUILD_BASEPATH=%CDRBUILD_DRIVE%\tmp
)

IF NOT EXIST %CDRBUILD_BASEPATH% (
  MKDIR %CDRBUILD_BASEPATH%
  IF NOT EXIST %CDRBUILD_BASEPATH% (
    ECHO Could not find or create %CDRBUILD_BASEPATH%
    ECHO Aborting!
    EXIT /B 1
  )
)

REM ----------------------------------------------------------------------
REM Ensure that python will find needed CDR software
REM ----------------------------------------------------------------------
ECHO Checking PYTHONPATH

IF "%PYTHONPATH%." == "." (
  SET PYTHONPATH=%CDRBUILD_DRIVE%\cdr\lib\Python
)

REM ----------------------------------------------------------------------
REM Can we find Visual Studio if we need it?
REM This only works if command extensions are enabled, which should be true.
REM However, we'll just issue a warning if it fails.
REM ----------------------------------------------------------------------
ECHO Checking accessibility of Visual Studio (via vcvars32)

SET CDRBUILD_VARBAT=%CDRBUILD_DRIVE%\bin\vcvars32.bat
IF NOT EXIST %CDRBUILD_VARBAT% (
  ECHO WARNING! %CDRBUILD_VARBAT% not found
) ELSE (
  ECHO %CDRBUILD_VARBAT% found
)

REM ----------------------------------------------------------------------
REM Set standard subversion options
REM ----------------------------------------------------------------------
ECHO Setting subversion options
IF "%CDRBUILD_SVNBASEURL%." == "." (
  SET CDRBUILD_SVNBASEURL=https://ncisvn.nci.nih.gov/svn/oce_cdr
)

IF "%CDRBUILD_SVNOPTS%." == "." (
  SET CDRBUILD_SVNOPTS=-q --trust-server-cert --non-interactive
)

ECHO Working drive  CDRBUILD_DRIVE      = %CDRBUILD_DRIVE%
ECHO Path to cygwin CDRBUILD_CYGPATH    = %CDRBUILD_CYGPATH%
ECHO To cygwin bin  CDRBUILD_CYGBIN     = %CDRBUILD_CYGBIN%
ECHO Build dir      CDRBUILD_BASEPATH   = %CDRBUILD_BASEPATH%
ECHO svn base url   CDRBUILD_SVNBASEURL = %CDRBUILD_SVNBASEURL%
ECHO svn options    CDRBUILD_SVNOPTS    = %CDRBUILD_SVNOPTS%
ECHO Python path    PYTHONPATH          = %PYTHONPATH%

REM Experimental
SET BISON_SIMPLE=%CDRBUILD_DRIVE%\etc\bison.simple
