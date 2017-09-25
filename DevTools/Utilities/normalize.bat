@echo off
if .%1. == .. goto usage
setlocal
for /F %%i in ("%0") do SET XSLT=indent.xml
echo %XSLT%
sabcmd %XSLT% %1
goto done
:usage
echo Normalize indentation and whitespace in an XML file.
echo usage: normalize filename.xml =^> stdout

:done
