@echo off
if .%1. == .. goto usage

sabcmd \cdr\bin\indent.xml %1
goto done
:usage
echo Normalize indentation and whitespace in an XML file.
echo usage: normalize filename.xml => stdout

:done
