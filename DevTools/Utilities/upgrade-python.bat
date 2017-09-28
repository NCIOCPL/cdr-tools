@ECHO OFF
@REM ======================================================================
@REM Upgrade Python from 2.7.10 to 2.7.13 (OCECDR-4234)
CALL :progress Python upgrade should take under a half hour ...
@REM ======================================================================
SETLOCAL
IF EXIST D:\cdr\lib\Python\cdr.py (
    SET DRIVE=D
    D:
) ELSE (
    SET DRIVE=C
    C:
)
IF EXIST %DRIVE%:\tmp\python-upgrade\upgrade-python.bat (
    SET UPGRADE_DIR=%DRIVE%:\tmp\python-upgrade
) ELSE (
    SET UPGRADE_DIR=\\nciis-p401.nci.nih.gov\cdr_deployments\python-upgrade
)
CALL :progress Installing from %UPGRADE_DIR% ...
SET LOG=\tmp\python-upgrade.log
SET ERR=\tmp\python-upgrade.err
SET SHOWTIME=\cygwin\bin\date.exe +"%%F %%T"
SET MSIEXEC=C:\Windows\SysWOW64\msiexec.exe
SET PY2710={87968C36-E9B2-4318-AF57-CEDF95F6B4E5}
SET PY2713=ActivePython-2.7.13.2716-win64-x64-403203.exe
SET BACKUP=%UPGRADE_DIR%\backup-python.py
SET INSTOPTS=APPDIR=%DRIVE%:\Python /qr /l+ \tmp\install-python-2.7.13.log
SET PIP=python -m pip install
SET WIN32COM=Python\lib\site-packages\win32com

@REM ======================================================================
CALL :progress Stopping services (takes a few seconds) ...
@REM ======================================================================
NET STOP "World Wide Web Publishing Service" >>%LOG% 2>>%ERR%
NET STOP "CDR Scheduler" >>%LOG% 2>>%ERR%
NET STOP Cdr >>%LOG% 2>>%ERR%

@REM ======================================================================
CALL :progress Backing up old Python directory (under a minute) ...
@REM ======================================================================
CHDIR \
python %BACKUP% %DRIVE% 2.7.10 || EXIT /B 1

@REM ======================================================================
CALL :progress Uninstalling Python 2.7.10 (about a minute) ...
@REM
@REM To reinstall the older version to test this script, run
@REM msiexec /I ActivePython-2.7.10.12-win64-x64.msi INSTALLDIR=X:\Python /qr
@REM Note the discrepancy between INSTALLDIR here and APPDIR below (another
@REM reason we're not terribly fond of ActiveState, which we're going to
@REM abandon if at all possible when we upgrade to Python 3).
@REM ======================================================================
@REM ActivePython-<version>.exe /x // /L*v ./uninstall.log
START /WAIT %MSIEXEC% /qr /l+ \tmp\remove-python-2.7.10.log /x %PY2710%
IF EXIST \Python ( RMDIR /Q /S \Python )

@REM ======================================================================
CALL :progress Installing Python 2.7.13 (about 15 minutes) ...
@REM This step takes at least 15 minutes.
@REM NOTE FOR FUTURE WHEN WE UNINSTALL THIS VERSION:
@REM MsiExec.exe /qr /x {4E514478-E395-496B-AB86-A752E9CE3810}
@REM OR ActivePython-<version>.exe /x // /L*v ./uninstall.log
@REM ======================================================================
START /WAIT %UPGRADE_DIR%\%PY2713% %INSTOPTS%

@REM ======================================================================
CALL :progress Installing third-party modules (about 5 minutes) ...
@REM ======================================================================
%PIP% pip==9.0.1 >>%LOG% 2>>%ERR%
%PIP% Pygments==2.2.0 certifi==2017.7.27.1 chardet==3.0.4 colorama==0.3.9 httpie==0.9.9 requests==2.18.4 urllib3==1.22 >>%LOG% 2>>%ERR%
%PIP% asn1crypto==0.23.0 bcrypt==3.1.3 cffi==1.11.0 paramiko==2.3.1 pyasn1==0.3.6 pynacl==1.1.2 six==1.11.0 >>%LOG% 2>>%ERR%
%PIP% astroid==1.5.3 backports.functools-lru-cache==1.4 isort==4.2.15 lazy-object-proxy==1.3.1 mccabe==0.6.1 pylint==1.7.2 wrapt==1.10.11 >>%LOG% 2>>%ERR%
%PIP% suds==0.4 backports-abc==0.5 pycparser==2.18 pyodbc==4.0.17 pymssql==2.1.3 >>%LOG% 2>>%ERR%
%PIP% asn1crypto==0.22.0 cryptography==2.0.3 enum34==1.1.6 idna==2.6 ipaddress==1.0.18 >>%LOG% 2>>%ERR%
%PIP% pillow==4.2.1 pyflakes==1.6.0 setuptools==36.5.0 lxml==4.0.0 >>%LOG% 2>>%ERR%
%PIP% cssselect==1.0.1 cssutils==1.0.2 apns==2.0.1 ecdsa==0.13 xlrd==1.1.0 xlwt==1.3.0 >>%LOG% 2>>%ERR%
%PIP% et-xmlfile==1.0.1 jdcal==1.3 openpyxl==2.5.0a3 openpyxl-templates==0.1.10 >>%LOG% 2>>%ERR%
%PIP% pypyodbc >>%LOG% 2>>%ERR%
%PIP% %UPGRADE_DIR%\ndscheduler-0.1.1-py2-none-any.whl >>%LOG% 2>>%ERR%
%PIP% %UPGRADE_DIR%\mysql_python-1.2.5-cp27-cp27m-win_amd64.whl >>%LOG% 2>>%ERR%

@REM ======================================================================
CALL :progress Adjusting Python file permissions (about 5 minutes) ...
@REM ======================================================================
CALL %UPGRADE_DIR%\fix-permissions.cmd Python >>%LOG% 2>>%ERR%

@REM ======================================================================
CALL :progress Registering COM type libraries (a few seconds) ...
@REM ======================================================================
python %UPGRADE_DIR%\register-typelibs.py >>%LOG% 2>>%ERR%

@REM ======================================================================
CALL :progress Adjusting win32com file permissions (a few seconds) ...
@REM ======================================================================
CALL %UPGRADE_DIR%\fix-permissions.cmd %WIN32COM% >>%LOG% 2>>%ERR%

@REM ======================================================================
CALL :progress Restarting services (a few seconds) ...
@REM ======================================================================
NET START Cdr >>%LOG% 2>>%ERR%
NET START "CDR Scheduler" >>%LOG% 2>>%ERR%
NET START "World Wide Web Publishing Service" >>%LOG% 2>>%ERR%
CALL :progress Python upgrade complete.
ENDLOCAL
PAUSE
EXIT /B 0

@REM ======================================================================
@REM Show the current time and where we are in the processing.
@REM ======================================================================
:progress
\cygwin\bin\date.exe +'%%F %%T %*'
exit /B 0

