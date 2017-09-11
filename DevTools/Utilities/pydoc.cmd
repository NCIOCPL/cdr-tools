@echo off
if %1. == . goto usage
@python d:/python/lib/pydoc.py %*
goto done
:usage
@echo usage: pydoc module-name
:done
