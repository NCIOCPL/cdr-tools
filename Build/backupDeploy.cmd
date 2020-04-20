@ECHO OFF
REM Back up all CDR directories that can be replaced in a deploy-all run
IF ".%1%." == ".." (
    ECHO Backing up all CDR directories that can be replaced in a deploy-cdr run
    ECHO Usage: backupDeploy filename
    EXIT /B 1
)
SET ZIPNAME=%1%
zip -r -q %ZIPNAME% d:\Inetpub d:\cdr\Bin d:\cdr\ClientFiles d:\cdr\Database d:\cdr\lib d:\cdr\Mailers d:\cdr\Publishing d:\cdr\Utilities d:\cdr\Licensee d:\cdr\Scheduler d:\cdr\Schemas d:\cdr\Filters d:\cdr\Build d:\cdr\api
