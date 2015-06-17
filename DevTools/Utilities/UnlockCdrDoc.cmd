@echo off
if %3. == . goto usage
@python -c "import cdr; err = cdr.unlock(('%1','%~2'), '%3'); print err or ('%3' + ' unlocked')"
goto done
:usage
@echo usage: UnlockCdrDoc user-id password cdr-doc-id
:done
