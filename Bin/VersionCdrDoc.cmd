@echo off
if %3. == . goto usage
@python -c "import cdr; print cdr.repDoc(('%1','%2'), file='%3', checkIn='Y', ver='Y', val='Y')" 
goto done
:usage
@echo usage: VersionCdrDoc user-id password file-name
:done
