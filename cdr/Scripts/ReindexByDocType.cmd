if "%1x" == "x" goto usage
perl perl CdrQuery.pl rmk ***REDACTED*** "CdrCtl/DocType = '%1'" | CdrCmd  | SabCmd filters/ReindexDocs.xsl | CdrCmd >> output\ReindexByDocType.out
less output/ReindexByDocType.out
goto out
:usage
echo usage: ReindexByDocType DOCTYPENAME
:out
