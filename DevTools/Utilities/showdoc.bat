@echo off
if .%1.==.. goto usage
getcdrdoc %1 | sabcmd \cdr\bin\indent.xml | less
goto done
:usage
echo usage showdoc docid
:done
