perl perl CdrQuery.pl rmk ***REDACTED*** "CdrAttr/Term/TermPrimaryType = 'glossary term'" | CdrCmd  | SabCmd filters/TermFilter.xsl | CdrCmd | sed -f filters/StripCdata.sed | SabCmd filters/ShowTerms.xsl > output\GlossaryTerms.html
@echo bring up output\GlossaryTerms.html in your favorite browser
