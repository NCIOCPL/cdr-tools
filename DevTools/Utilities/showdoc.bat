@REM ==================================================================
@REM Show a CDR document with indenting.
@REM ==================================================================

@echo off
if .%1.==.. goto usage
getcdrdoc %1 | sabcmd indent.xml | less
goto done
:usage
echo usage showdoc docid
:done
