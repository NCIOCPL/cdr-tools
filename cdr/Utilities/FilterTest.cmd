perl perl CdrQuery.pl ahm ***REDACTED*** "CdrCtl/DocType = 'Term' and CdrCtl/Title begins 'advanced'" | CdrCmd  | SabCmd filters/TermFilter.xsl | CdrCmd | sed -f filters/StripCdata.sed | SabCmd filters/ShowTerms.xsl > output\Terms.html
@echo bring up output\Terms.html in your favorite browser
