#----------------------------------------------------------------------
#
# $Id: CheckDtds.py,v 1.2 2002-06-27 19:30:36 bkline Exp $
#
# Utility to reparse the schemas and determine which DTDs are out of
# date in the manifest for the client.
#
# $Log: not supported by cvs2svn $
# Revision 1.1  2002/06/06 15:44:00  bkline
# Utility to bring client DTDs up to date.
#
#----------------------------------------------------------------------

import cdr, sys

if len(sys.argv) != 2:
    sys.stderr.write("usage: CheckDtds webserver-base-path\n" \
                     " e.g.: CheckDtds d:/InetPub/wwwroot\n")
    sys.exit(1)

dir = sys.argv[1] + '/cgi-bin/Ticket/ClientFiles/Display'
session = cdr.login('rmk', '***REDACTED***')
docTypes = cdr.getDoctypes(session)
for docType in docTypes:
    try:
        path = "%s/%s.dtd" % (dir, docType)
        #sys.stderr.write("checking %s\n" % path)
        current = open(path).read()
        #sys.stderr.write("old DTD read\n")
        start = current.find('<!ELEMENT')
        if start == -1:
            sys.stderr.write("Malformed DTD: %s.dtd\n" % docType)
            continue
        #sys.stderr.write("old start is at %d\n" % start)
        current = current[start:]
        dtInfo = cdr.getDoctype(session, docType)
        #sys.stderr.write("new DTD retrieved\n")
        if not dtInfo.dtd:
            sys.stderr.write("Can't get new DTD for %s\n" % docType)
            continue
        start = dtInfo.dtd.find("<!ELEMENT")
        #sys.stderr.write("new start is at %d\n" % start)
        if start == -1:
            sys.stderr.write("Malformed DTD for %s type\n" % docType)
            #print dtInfo.dtd
            continue
        newDtd = dtInfo.dtd[start:]
        if newDtd == current: print "DTD for %s is current" % docType
        else: 
            print "DTD for %s has changed" % docType
            open(path, "w").write(dtInfo.dtd)
    except:
        pass
