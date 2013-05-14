@echo off
if %2. == . goto usage
perl CdrQuery.pl %1 %2 "CdrAttr/Term/TermPrimaryType = 'gene'" | CdrCmd  | SabCmd filters/TermFilter.xsl | CdrCmd | sed -f filters/StripCdata.sed | SabCmd filters/ShowTerms.xsl > output\GeneTerms.html
echo bring up output\GeneTerms.html in your favorite browser
goto done
:usage
echo usage: GeneTerms user-id password
:done
