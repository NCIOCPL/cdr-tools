@echo off
if %3. == . goto usage
@python -c "import cdr, string; print cdr.sendCommands(cdr.wrapCommand('<CdrGetGrp><GrpName>%%s</GrpName></CdrGetGrp>' %% string.strip('%3 %4 %5 %6 %7 %8'), ('%1','%2')))"
goto done
:usage
@echo usage: GetCdrGroup user-id password group name
:done
