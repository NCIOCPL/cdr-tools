perl CdrQuery.pl "CdrCtl/DocType = 'GeographicEntity'" | CdrCmd  | SabCmd filters/DeleteDocsRmk.xsl | CdrCmd >> output\DeleteGEs.out
less output/DeleteGEs.out
