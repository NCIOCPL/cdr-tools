@echo off
if %3. == . goto usage
@python -c "import cdr; print cdr.delDoc(('%1','%~2'), '%3')"
goto done
:usage
@echo usage: DelCdrDoc user-id password doc-id
:done
