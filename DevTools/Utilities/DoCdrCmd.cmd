@REM ==================================================================
@REM Wrap and send CDR XML command string to CDR server (low level tool)
@REM ==================================================================
@echo off
if %3. == . goto usage
@python -c "import cdr; print cdr.sendCommands(cdr.wrapCommand('%3', ('%1','%~2')))"
goto done
:usage
@echo usage: DoCdrCmd user-id password "command-xml-string"
:done
