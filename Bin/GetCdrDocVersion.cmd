@echo off
if %2. == . goto usage
@python -c "import cdr; print cdr.getDoc('guest', '%1', version='%2')"
goto done
:usage
@echo usage: GetCdrDocVersion doc-id which-version
:done
