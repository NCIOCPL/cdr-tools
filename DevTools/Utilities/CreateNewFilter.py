#!/usr/bin/env python
"""
Create a new stub filter document in the CDR

See CreateNewFilter.py --help for details.
"""

import argparse
import getpass
import cdr

# Support Python 3
try:
    unicode
    from cgi import escape
except:
    unicode = str
    from html import escape

def create_parser():
    """
    Create the object which collects the run-time arguments.
    """

    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description="""\
This program creates a new stub filter document in the CDR.  The
program runs on the production server to get the CDR ID to be used for
the filter's version control file name.  A file is created in the
current working directory containing the XML content for the stub
document under the name CDR9999999999.xml (where 9999999999 is
replaced by the actual 10-digit version of the newly created
document's CDR ID).  This document can be edited and installed in the
version control system.

Enclose the title argument in double quote marks if it contains any
embedded spaces (which it almost certainly will).  The filter title
will be included in the document as an XML comment, and therefore
cannot contain the substring --.

SEE ALSO
  `InstallFilter.py` (adding new filter to another tier)
  `UpdateFilter.py` (modifying existing filter on any tier)
  `ModifyFilterTitle.py` (changing filter title)""")
    parser.add_argument("title")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--session")
    group.add_argument("--user")
    return parser

def main():
    parser = create_parser()
    opts = parser.parse_args()
    title = opts.title
    if not title:
        parser.error("empty title argument")
    if not isinstance(title, unicode):
        title = unicode(title.strip(), "latin-1")
    if "--" in title:
        parser.error("filter title cannot contain --")
    if not opts.session:
        password = getpass.getpass()
        session = cdr.login(opts.user, password, tier="PROD")
        error = cdr.checkErr(session)
        if error:
            parser.error(error)
    else:
        session = opts.session
    stub = u"""\
<?xml version="1.0" encoding="utf-8"?>
<!-- Filter title: {} -->
<xsl:transform               xmlns:xsl = "http://www.w3.org/1999/XSL/Transform"
                             xmlns:cdr = "cips.nci.nih.gov/cdr"
                               version = "1.0">

 <xsl:output                    method = "xml"
                              encoding = "utf-8"/>

 <xsl:param                       name = "sample-param"
                                select = "'default-value'"/>

 <!-- Sample template -->
 <xsl:template                   match = "@*|node()">
  <xsl:copy>
   <xsl:apply-templates         select = "@*|node()"/>
  </xsl:copy>
 </xsl:template>

</xsl:transform>
""".format(escape(title)).encode("utf-8")
    title = title.encode("utf-8")
    ctrl = dict(DocTitle=title)
    doc_opts = dict(doctype="Filter", ctrl=ctrl, encoding="utf-8")
    doc = cdr.Doc(stub, **doc_opts)
    cdr_id = cdr.addDoc(session, doc=str(doc), tier="PROD")
    error = cdr.checkErr(cdr_id)
    if error:
        parser.error(error)
    response = cdr.unlock(session, cdr_id, tier="PROD")
    error = cdr.checkErr(response)
    if error:
        parser.error(error)
    name = cdr_id + ".xml"
    with open(name, "wb") as fp:
        fp.write(stub)
    print("Created {}".format(name))
    if not opts.session:
        cdr.logout(session, tier="PROD")

if __name__ == '__main__':
    main()
