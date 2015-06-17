@echo off
if %3. == . goto usage
@python -c "import cdr; print cdr.addDoc(('%1','%~2'), file='%3')"
goto done
:usage
@echo usage: AddCdrDoc user-id password file-name
:done
