perl CdrQuery.pl "CdrCtl/DocType = 'Organization'" | CdrCmd  | SabCmd filters/ReindexDocs.xsl | CdrCmd >> output\ReindexOrgs.out
less output/ReindexOrgs.out
