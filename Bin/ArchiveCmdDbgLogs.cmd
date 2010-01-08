@echo off
rem ========================================================================
rem When running command on test server the cluster group will need to be
rem moved manually with these commands:
rem cluster /cluster:cdrc1  group "Cluster Group" /moveto:mahler
rem cluster /cluster:cdrc1  group "Cluster Group" /moveto:bach
rem python ArchiveCmdDbgLogs.py --lastdate #14 --quiet --outdir D:\Backup\cdr\CommandDebugLogs move|copy >> d:\cdr\log\HistoryArchive_error.log 2>&1
rem ========================================================================
@echo on
if %1. == . goto usage
d:\cdr\utilities\ArchiveCmdDbgLogs.py --lastdate #14 --quiet --outdir R:\DB_Backup\%1\cdr\CommandDebugLogs move 
goto done
:usage
@echo usage: ArchiveCmdDbgLogs.cmd hostname
:done
