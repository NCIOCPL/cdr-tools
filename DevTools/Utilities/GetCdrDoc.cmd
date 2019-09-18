@REM ==================================================================
@REM Fetch current working version of a CDR document.
@REM ==================================================================

@echo off
if %1. == . goto usage
@python -c "import cdr; print(cdr.getDoc('guest', '%1'))"
goto done
:usage
@echo usage: GetCdrDoc doc-id
:done
