@echo off
if %3. == . goto usage
@python -c "import cdr; print cdr.sendCommands(cdr.wrapCommand('<CdrGetUsr><UserName>%3</UserName></CdrGetUsr>', ('%1','%2')))"
goto done
:usage
@echo usage: GetCdrUser your-user-id password target-user-id
:done
