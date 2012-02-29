@echo off
rem ========================================================================
rem When running command on test server the cluster group will need to be
rem moved manually with these commands:
rem cluster /cluster:cdrc1  group "Cluster Group" /moveto:mahler
rem cluster /cluster:cdrc1  group "Cluster Group" /moveto:bach
rem python ArchiveCmdDbgLogs.py --lastdate #14 --quiet --outdir D:\Backup\cdr\CommandDebugLogs move|copy >> d:\cdr\log\HistoryArchive_error.log 2>&1
rem 
rem Because Franck is a member of the cluster we can only write to the 
rem R-drive after the cluster has been moved to FRANCK.  That's no good 
rem when testing.  Setting the output location to the V-drive for FRANCK
rem ========================================================================
@echo on
if %1. == . goto usage
set _drive=R:
if [%1] == [Franck] set _drive=V:
d:\cdr\utilities\ArchiveCmdDbgLogs.py --lastdate #14 --quiet --outdir %_drive%\DB_Backup\%1\cdr\CommandDebugLogs move 
goto done
:usage
@echo usage: ArchiveCmdDbgLogs.cmd hostname
:done
