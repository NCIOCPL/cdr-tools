perl perl CdrQuery.pl rmk ***REDACTED*** "CdrAttr/Term/TermPrimaryType = 'gene'" | CdrCmd  | SabCmd filters/TermFilter.xsl | CdrCmd | sed -f filters/StripCdata.sed | SabCmd filters/ShowTerms.xsl > output\GeneTerms.html
@echo bring up output\GeneTerms.html in your favorite browser
