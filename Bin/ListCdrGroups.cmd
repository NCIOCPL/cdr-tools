@echo off
if %2. == . goto usage
@python -c "import cdr; print cdr.sendCommands(cdr.wrapCommand('<CdrListGrps/>', ('%1','%2')))"
goto done
:usage
@echo usage: ListCdrGroups user-id password
:done
