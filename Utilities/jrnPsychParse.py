############################################################
# $Id$
#
# Parse a PsychINFO journal list and output a text list suitable for
# comparisons to Pubmed.
#
# Author: AHM
#   Date: June 2010
#
# BZIssue::4858
#############################################################

import sys, xml.sax.handler

class Journal:
    """
    Data for one journal.
    We only work on one of these at a time, so we just use a global singleton.
    """
    def __init__(self):
        self.clear()

    def clear(self):
        self.title  = u""
        self.issn   = None
        self.eissn  = None
        self.colcnt = 0
        self.text   = u""

    def __repr__(self):
        """
        Format for output.
        """
        tmp = self.title.replace(u"\n", u"")
        tmp = u"%s\t%s\t%s" % (self.issn, self.eissn, tmp)
        utf = tmp.encode("utf-8")
        return utf

class Nbsp(xml.sax.handler.EntityResolver):
    def resolveEntity(self, publicId, systemId):
        print("pubicId=%s systemId=%s" % publicId, systemId)
        return " "

class Parser(xml.sax.handler.ContentHandler):

    def startElement(self, name, attributes):
        global jrnl

        # All journal entries begin with a table row
        if name == "tr":
            jrnl.clear()

        # All text is in table columns
        # Clear the accumulator for the next column of text
        if name == "td":
            jrnl.text = u""

    def endElement(self, name):
        global jrnl

        # All interesting info is in first 3 columns
        if name == "td":
            jrnl.colcnt += 1

            if jrnl.colcnt == 1:
                jrnl.title = jrnl.text
            if jrnl.colcnt == 2:
                jrnl.issn = jrnl.text
            elif jrnl.colcnt == 3:
                jrnl.eissn = jrnl.text

        # At end of row, output the journal to stdout
        if name == "tr":
            # Skip lines that just have a single letter of the alphabet
            if jrnl.colcnt > 2:
                print(jrnl)

        # Nothing else matters

    def characters(self, content):
        global jrnl

        # Accumulate text
        jrnl.text += content

    def processingInstruction(self, target, data):
        pass


if __name__ == "__main__":

    # usage
    if len(sys.argv) != 2:
        sys.stderr.write("""
usage: jrnPsychINFOParse.py filename
  Converts PsychINFO journal title list to normalized form for comparison
  Normal form is:
    ISSN<tab>eISSN<tab>Title
  Output is UTF-8 to stdout.

Input filename names an HTML file containing the entire list of PsychINFO
    journals.
    Currently, this list can be found at:
      http://apa.org/pubs/databases/psycinfo/coverage.aspx#list
    If the format of that file changes, this program must be rewritten.

Input file preparation:
    Delete everything from before the <tr> for the first journal.
    Delete everything from after the </tr> for the last journal.
    Global search and replace "&nbsp;" with "         " (9 spaces).
        """)
        sys.exit(1)

    # Global Journal object, re-used for each journal
    jrnl = Journal()

    # Create the parser
    parser = Parser()
    # p = Parser()
    # parser = xml.sax.make_parser()
    # parser.setContentHandler(p)
    # parser.setEntityResolver(Nbsp())

    # Parse and output the file
    inf = open(sys.argv[1], "r").read()

    xml.sax.parseString(inf, parser)
