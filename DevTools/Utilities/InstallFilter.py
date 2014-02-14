#--------------------------------------------------------------
# $Id$
#
# Script for installing a filter on a development or test server that
# has already been created on the production server but has not yet
# appeared on the server on which it will be installed now.
#
# The program will add the filter as a new document, with a new ID, using
# the title stored in the document on disk and in the production database.
#
# BZIssue::4652
# JIRA::OCECDR-3694
#--------------------------------------------------------------
import sys, optparse, cdr, cdrdb, re
etree = cdr.importEtree()

EXPECTED_ROOT = "{http://www.w3.org/1999/XSL/Transform}transform"

def fatal(msg, parser=None):
    """
    Write message and quit.

    Pass:
        msg    - Message to write
        parser - If not None, invoke parser.print_help()
    """
    sys.stderr.write("Fatal error.\n")
    sys.stderr.write(msg)
    sys.stderr.write("\n\n")
    if parser:
        parser.print_help()
    sys.exit(1)

def createOptionParser():
    """
    Create an option parser and associated usage, help, etc.
    """
    parser = optparse.OptionParser(
      usage = """%prog userid password filterfile

  args:
    userid     = CDR user id.
    password   = CDR password.
    filterfile = Name of filter, must be in CDRnnnnnnnnn.xml format.""",
      description = """Install a filter on a test or development server
for the first time.  Filter must already have been created on the production
server.  Filter will be installed on the requested server using the existing
name/title from production, and (almost certainly) a new CDR ID.

""")

    return parser

class DocDesc:
    """
    Hold information parsed from the filter file on disk.
    """
    def __init__(self, filename):
        """
        Load filter from disk.
        Locate relevant parts.

        Pass:
            Name of file on disk containing XML for filter.
        """

        # Initial values.
        self.cdrIdNum = self.xml = self.title = None

        # Parse filename to get CDR ID
        if not re.match("^CDR\\d{10}.xml$", filename):
            fatal("File name must be in the form CDRnnnnnnnnnn.xml")
        self.cdrIdNum = int(re.sub("[^\\d]+", "", filename))

        # Load file
        self.xml = None
        try:
            # Translate line ends if needed to plain linefeed
            fp = open(filename, "r")
            self.xml = fp.read()
            fp.close()
        except IOError, info:
            fatal("Error opening/reading/closing file: %s" % info)

        # Parse.  Since we're creating the filters from our own
        # templates, we expect transform as the root element,
        # not stylesheet (which is also valid in the wild).
        try:
            root = etree.fromstring(self.xml)
            if root.tag != EXPECTED_ROOT:
                fatal("%s is not a CDR XSL/T filter" % filename)
        except SyntaxError, info:
            fatal("Error parsing contents of %s:\n%s" % (filename, info))
        except:
            raise

        # Extract the filter title.
        match = re.search("<!--\\s*filter title:(.*?)-->", self.xml, re.I)
        if not match:
            fatal("Filter title comment not found in %s" % filename)
        self.title = match.group(1).strip()
        if not self.title:
            fatal("Filter title comment in %s is empty" % filename)

    def checkTargetTitle(self):
        """
        Make sure the document is not already installed in the target
        server.  This check is actually redundant, as the CDR server
        will enforce the assumption.  Can't hurt to check twice, though.

        Return:
            Void.
            Exits with fatal error if filter already installed.
        """
        try:
            conn = cdrdb.connect("CdrGuest")
            cursor = conn.cursor()
            cursor.execute("""
SELECT d.id
  FROM document d
  JOIN doc_type t
    ON d.doc_type = t.id
 WHERE title = ?
   AND t.name = 'Filter'
""", self.title)
            rows = cursor.fetchall()
            cursor.close()
        except cdrdb.Error, info:
            fatal("Database error checking title in database: %s" % info)
        if rows:
            ids = ", ".join([str(row[0]) for row in rows])
            fatal("%s already present (%s) in the CDR" % (self.title, ids))

#----------------------------------------------------------
# Main
#----------------------------------------------------------
if __name__ == "__main__":

    # Args
    op = createOptionParser()
    (options, args) = op.parse_args()

    if len(args) != 3:
        op.print_help()
        op.exit(2)

    userid = args[0]
    passwd = args[1]
    fname  = args[2]

    # Make sure we're not on the production server.
    if cdr.isProdHost():
        fatal("""
This program can only be used to install a filter on the development or
  test server, not production.
Use CreateFilter.py to create the filter in the production database, then
  use InstallFilter.py to install it in test or development with the same
  title/name and (almost certainly) a different local CDR ID.
""")

    # Load the document
    doc = DocDesc(fname)

    # Make sure the filter isn't already installed
    doc.checkTargetTitle()

    # All checks passed.  Add the document
    docObj = cdr.Doc(doc.xml, 'Filter', {'DocTitle': doc.title},
                     encoding='utf-8')
    wrappedXml = str(docObj)

    session = cdr.login(userid, passwd)
    if session.find("<Err") != -1:
        fatal("Error logging in to CDR: %s" % session)
    # DEBUG
    # sys.exit(0)
    comment = 'New filter install'
    newCdrId = cdr.addDoc(session, doc=wrappedXml, comment=comment)

    # Display result, doc ID or error message
    print(newCdrId)
