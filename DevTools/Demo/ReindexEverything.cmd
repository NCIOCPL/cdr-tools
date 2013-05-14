now >> ReindexEverything.out
perl CdrQuery.pl "CdrCtl/DocType ne ''" | CdrCmd  | SabCmd filters/ReindexDocs.xsl | CdrCmd >> output\ReindexEverything.out
now >> ReindexEverything.out
less output/ReindexEverything.out
