now >> ReindexEverything.out
perl perl CdrQuery.pl rmk ***REDACTED*** "CdrCtl/DocType ne ''" | CdrCmd  | SabCmd filters/ReindexDocs.xsl | CdrCmd >> output\ReindexEverything.out
now >> ReindexEverything.out
less output/ReindexEverything.out
