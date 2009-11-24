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
#--------------------------------------------------------------
import sys, optparse, cdr, cdrdb
etree = cdr.importEtree()

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
      usage = """%prog {--server} userid password filterfile

  args:
    userid     = CDR user id.
    password   = CDR password.
    filterfile = Name of filter, must be in CDRnnnnnnnnn.xml format.""",
      description = """Install a filter on a test or development server
for the first time.  Filter must already have been created on the production
server.  Filter will be installed on the requested server using the existing
name/title from production, and (almost certainly) a new CDR ID.

""")
    parser.add_option("-s", "--server", dest="server", metavar="server",
                      help="install filter on this server, default=%default")
    parser.set_defaults(server="localhost")

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
            Name of file on disk containing file in CdrDoc format.
        """
        # Parse filename to get CDR ID
        self.cdrIdTxt = filename[:13]
        try:
            self.cdrIdNum = cdr.exNormalize(self.cdrIdTxt)[1]
        except Exception, info:
            fatal("Bad CDR ID in name: %s" % info)
        if filename[13:] != ".xml":
            fatal('Expecting filename CDRnnnnnnnnnn.xml, ".xml" missing')

        # Load file
        self.xml = None
        try:
            # Translate line ends if needed to plain linefeed
            fp = open(filename, "r")
            self.xml = fp.read()
            fp.close()
        except IOError, info:
            fatal("Error opening/reading/closing file: %s" % info)

        # Parse
        tree = None
        try:
            tree = etree.fromstring(self.xml)
        except SyntaxError, info:
            fatal("Error parsing contents of %s:\n%s" % (filename, info))
        except:
            raise

        # Accept CdrDoc format, but convert it
        if tree.tag == 'CdrDoc':
            sys.stderr.write(
               "Discarding CdrDoc wrapper.  Getting CDATA content\n")
            self.xml = cdr.getCDATA(self.xml)

            # Parse it, just to check filter syntax
            try:
                tree = etree.fromstring(self.xml)
            except SyntaxError, info:
                fatal("""
Error parsing CDATA/Filter content of %s:
%s
NOTE: Transform line numbers are relative to start of CDATA section.
""" % (filename, info))
            except:
                raise


    def getProdTitle(self):
        """
        Get the title stored on the production server.
        Store it and return it.

        Return:
            Title
            Fatal error if the match is wrong.
        """
        try:
            conn = cdrdb.connect(dataSource=cdr.PROD_NAME)
            cursor = conn.cursor()
            cursor.execute(
                "SELECT title FROM document WHERE id = %d" % self.cdrIdNum)
            row = cursor.fetchone()
            cursor.close()
        except cdrdb.Error, info:
            fatal("Database error verifying title in production database: %s"
                   % info)
        if not row:
            fatal("Could not find CDR ID=%d in production database" %
                   self.cdrIdNum)
        self.title = row[0]

        return self.title

    def checkTargetTitle(self, server):
        """
        Make sure the document is not already installed in the target
        server.

        Pass:
            Server name.

        Return:
            Void.
            Exits with fatal error if filter already installed.
        """
        try:
            conn = cdrdb.connect(dataSource=server)
            cursor = conn.cursor()
            cursor.execute("""
SELECT d.id
  FROM document d
  JOIN doc_type t
    ON d.doc_type = t.id
 WHERE title = ?
   AND t.name = 'Filter'
""", self.title)
            row = cursor.fetchone()
            cursor.close()
        except cdrdb.Error, info:
            fatal("Database error checking title in %s database: %s"
                   % (server, info))
        if row:
            fatal("""
A filter with CDR ID = %d already exists in the database with title:
  "%s"
Use UpdateFilter.py, not InstallFilter.py, to update it.
""" % (row[0], self.title))

#----------------------------------------------------------
# Main
#----------------------------------------------------------
if __name__ == "__main__":

    # Args
    op = createOptionParser()
    (options, args) = op.parse_args()

    if len(args) != 3:
        fatal("Missing required args", op)

    userid = args[0]
    passwd = args[1]
    fname  = args[2]
    server = options.server

    # Can only use this program for installing on development or test servers
    if server.lower() == cdr.PROD_NAME.lower():
        fatal("""
This program can only be used to install a filter on the development or
  test server, not production.
Use CreateFilter.py to create the filter in the production database, then
  use InstallFilter.py to install it in test or development with the same
  title/name and (almost certainly) a different local CDR ID.
""")

    # Load the document
    doc = DocDesc(fname)

    # Check it on the production server, exits on failure
    title = doc.getProdTitle()

    # Check it on target server
    doc.checkTargetTitle(server)

    # All checks passed.   Add the document
    docObj     = cdr.Doc(doc.xml, 'Filter', {'DocTitle': title},
                         encoding='utf-8')
    wrappedXml = str(docObj)

    session = cdr.login(userid, passwd, host=server)
    if session.find("<Err") != -1:
        fatal("Error logging in to %s: %s" % (server, session))
    # DEBUG
    # sys.exit(0)
    newCdrId = cdr.addDoc(session, doc=wrappedXml,
                          comment='New filter install',
                          host=server)

    # Display result, doc ID or error message
    print(newCdrId)
