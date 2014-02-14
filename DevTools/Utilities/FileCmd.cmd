@echo off
if %3. == . goto usage
@python -c "import cdr; print cdr.sendCommands(cdr.wrapCommand(open('%3', 'r').read(), ('%1','%2')))"
goto done
:usage
@echo usage: FileCmd user-id password file-name
