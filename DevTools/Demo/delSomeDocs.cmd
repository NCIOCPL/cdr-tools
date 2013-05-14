if "%1." == "." goto usage
d:\bin\perl.exe CdrQuery.pl "CdrCtl/DocType = '%1'" | CdrCmd  | SabCmd filters/DeleteDocsRmk.xsl | CdrCmd >> output\DelSomeDocs.out
goto done
:usage
echo usage: delSomeDocs DOCTYPE-NAME
:done
