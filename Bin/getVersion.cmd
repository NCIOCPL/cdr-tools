@echo off
if %4. == . goto usage
@python -c "import cdr; print cdr.getDoc(('%1','%2'), '%3', version='%4')"
goto done
:usage
@echo usage: getVersion user-id password doc-id which-version
:done
