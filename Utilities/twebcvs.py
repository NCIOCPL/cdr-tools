#!/usr/bin/python

#----------------------------------------------------------------------
#
# $Id: twebcvs.py,v 1.1 2009-07-21 19:54:51 bkline Exp $
#
# Demonstration of python code to retrieve filter document from
# cvs using anonymous http interface.
#
#----------------------------------------------------------------------
import urllib2, sys

host   = 'verdi.nci.nih.gov'
app    = 'cgi-bin/cdr/cvsweb.cgi/~checkout~/cdr/Filters'
docId  = len(sys.argv) > 1 and int(sys.argv[1]) or 134
rev    = len(sys.argv) > 2 and sys.argv[2] or '1.32'
parms  = 'CDR%010d.xml?rev=%s;content-type=application/xml' % (docId, rev)
url    = 'http://%s/%s/%s' % (host, app, parms)
reader = urllib2.urlopen(url)
doc    = reader.read()
print doc
