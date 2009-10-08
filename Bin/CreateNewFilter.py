#----------------------------------------------------------------------
#
# $Id$
#
# Creates a new stub filter document on Bach.  A file is created in the
# current working directory containing the XML content for the stub
# document under the name CDR9999999999.xml (where 9999999999 is replaced
# by the actual 10-digit version of the newly created document's CDR ID).
# This document can be edited and installed in the version control
# system.  See the usage() function below for invocation details.
#
#----------------------------------------------------------------------
import cdr, getopt, sys

def usage():
    sys.stderr.write("""\
usage: %s [options]

options:
    -t "T"              title of new filter [required; must be unique]
    -u U                CDR user ID [required]
    -p P                CDR account password [required]
    -s S                optional server name [for testing only]
    --title "T"         title of new filter [required]
    --userid U          CDR user ID [required]
    --password P        CDR account password [required]
    --server S          optional server name [for testing only]
    --usage             print this message
""" % sys.argv[0])
    sys.exit(1)

def checkForProblems(response):
    errors = cdr.getErrors(response, errorsExpected = False, asSequence = True)
    if errors:
        for error in errors:
            sys.stderr.write("%s\n" % error)
        usage()

def main():
    uid = pwd = title = None
    server = "bach.nci.nih.gov"
    try:
        longopts = ["title", "userid", "password", "server"]
        opts, args = getopt.getopt(sys.argv[1:], "u:p:t:s:", longopts)
    except getopt.GetoptError, e:
        usage()
    for o, a in opts:
        if o in ('-t', '--title'):
            title = a
        elif o in ('-u', '--userid'):
            uid = a
        elif o in ('-p', '--password'):
            pwd = a
        elif o in ('-s', '--server'):
            server = a
        else:
            usage()
    if args:
        usage()
    if not uid or not pwd or not title:
        usage()
    session = cdr.login(uid, pwd, server)
    checkForProblems(session)
    stub = """\
<?xml version='1.0' encoding='utf-8'?>
<!-- $Id$ -->
<!-- Filter title: %s -->
<xsl:transform               xmlns:xsl = 'http://www.w3.org/1999/XSL/Transform'
                             xmlns:cdr = 'cips.nci.nih.gov/cdr'
                               version = '1.0'>

 <xsl:output                    method = 'xml'
                              encoding = 'utf-8'/>

 <xsl:param                       name = 'sample-param'
                                select = '"default-value"'/>

 <!-- Sample template -->
 <xsl:template                   match = '@*|node()'>
  <xsl:copy>
   <xsl:apply-templates         select = '@*|node()'/>
  </xsl:copy>
 </xsl:template>

</xsl:transform>
""" % title
    docObj = cdr.Doc(stub, 'Filter', { 'DocTitle': title })
    doc = str(docObj)
    cdrId = cdr.addDoc(session, doc = doc, host = server)
    checkForProblems(cdrId)
    response = cdr.unlock(session, cdrId)
    checkForProblems(response)
    name = cdrId + ".xml"
    fp = open(name, "w")
    fp.write(stub)
    fp.close()
    print "Created %s" % name

if __name__ == '__main__':
    main()
