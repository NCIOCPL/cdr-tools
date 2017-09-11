@echo off
if %3. == . goto usage
@python -c "import cdr; print cdr.repDoc(('%1','%2'), file='%3', val='Y', ver='Y', checkIn='Y', verPublishable='Y', showWarnings=1, comment='Replaced by programmer')" 
goto done
:usage
@echo Replaces a checked out doc with a new, publishable version
@echo Adds comment 'Replaced by programmer'
@echo usage: ReplaceCdrPubDoc user-id password file-name
:done
