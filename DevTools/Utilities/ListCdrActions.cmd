@REM ==================================================================
@REM Low-level test of CDR client/server API (fetches CDR actions).
@REM ==================================================================

@echo off
if %2. == . goto usage
@python -c "import cdr; print cdr.sendCommands(cdr.wrapCommand('<CdrListActions/>', ('%1','%~2')))"
goto done
:usage
@echo usage: ListCdrActions user-id password
:done
