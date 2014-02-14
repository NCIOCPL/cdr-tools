@echo off
if %3. == . goto usage
@python -c "import cdr; print cdr.getDoc(('%1','%2'), '%3','Y')" 
goto done
:usage
@echo usage: CheckoutCdrDoc user-id password file-name
:done
