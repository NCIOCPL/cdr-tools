#----------------------------------------------------------------------
#
# $Id: CheckDtds.py,v 1.1 2002-06-06 15:44:00 bkline Exp $
#
# Utility to reparse the schemas and determine which DTDs are out of
# date in the manifest for the client.
#
# $Log: not supported by cvs2svn $
#----------------------------------------------------------------------

import cdr, sys

dir = '/Inetpub/wwwtest/cgi-bin/Ticket/ClientFiles/Rules'
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
