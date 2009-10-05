@echo off
if %2. == . goto usage
perl CdrQuery.pl %1 %2 "CdrCtl/DocType = 'Organization' and not(CdrCtl/Title begins 'Test Org ')" | CdrCmd  | SabCmd filters/DeleteDocs.xsl | CdrCmd >> output\DeleteOrgs.out
less output/DeleteOrgs.out
goto done
:usage
echo usage: DeleteOrgs user-id password
:done
