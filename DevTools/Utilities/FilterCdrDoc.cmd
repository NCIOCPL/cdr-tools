@REM ==================================================================
@REM Filter a CDR document through a CDR filter or named filter set.
@REM ==================================================================

@echo off
if %2. == . goto usage
@python -c "import cdr; print cdr.filterDoc('guest',['%1'],'%2')[0]"
goto done
:usage
@echo usage: FilterCdrDoc filter doc-id
:done
