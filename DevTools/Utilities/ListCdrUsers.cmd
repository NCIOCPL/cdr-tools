@REM ==================================================================
@REM Low-level test of CDR client/server API (fetches CDR users).
@REM ==================================================================

@echo off
if %2. == . goto usage
@python -c "import cdr; print cdr.sendCommands(cdr.wrapCommand('<CdrListUsrs/>', ('%1','%~2')))"
goto done
:usage
@echo usage: ListCdrUsers user-id password
:done
