@echo off
D:
if x%1 == x goto usage
echo backing up CDR sources to /cdr/zips/%1
zip -r -@ /cdr/zips/%1 < \cdr\bin\cdr-backup.lst
goto done
:usage
echo usage: backup-cdr zipfile-name
:done
