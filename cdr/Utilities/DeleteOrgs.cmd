perl perl CdrQuery.pl rmk ***REDACTED*** "CdrCtl/DocType = 'Organization' and not(CdrCtl/Title begins 'Test Org ')" | CdrCmd  | SabCmd filters/DeleteDocs.xsl | CdrCmd >> output\DeleteOrgs.out
less output/DeleteOrgs.out
