#!/usr/bin/env python
# ---------------------------------------------------------------------
# File Name: makePub.py
#            ==========
# This script extracts a set of documents (by doctype) from the 
# database and makes the current working document publishable if it has
# changed since the last document version had been saved.
#
# Input:  userid, passwd
# ---------------------------------------------------------------------
import sys, cdr, cdrdb

if len(sys.argv) < 2:
   print 'usage: makePub.py userid passwd'
   sys.exit(1)

#----------------------------------------------------------------------
# Extract arguments from the command-line.
#----------------------------------------------------------------------
if len(sys.argv) > 1: userid   = sys.argv[1]
if len(sys.argv) > 2: passwd   = sys.argv[2]
if len(sys.argv) > 3: doctype  = sys.argv[3]

session = cdr.login(userid, passwd)
l  = cdr.Log('makePubVersions.log')
l.write('makePubVersions.py - Started')

#----------------------------------------------------------------------
# Set up a database connection and cursor.
#----------------------------------------------------------------------
try:
    conn = cdrdb.connect()
    cursor = conn.cursor()
except cdrdb.Error, info:
    cdrcgi.bail('Database connection failure: %s' % info[1][0])

#----------------------------------------------------------------------
# Query to find the publishable documents of a given docType
#----------------------------------------------------------------------
cursor.execute("""\
    SELECT id
      FROM document
     WHERE doc_type = 26
       AND active_status = 'A'
       AND xml like '%<SpanishTerm%'
     ORDER BY id""", timeout = 300)

#       AND val_status = 'V'
rows = cursor.fetchall()

# print rows[:6]

# -------------------------------------------------------------
# Walk through the list of documents and check which ones have
# changed and need to be versioned.
# lastVersion() returns three values:
#   latest Version number, latest publishable version number, 
#   Y/N indicator if CWD is different from latest version
# -------------------------------------------------------------
irow   = 0
allrow = 0
#for row in rows[:6]:
for row in rows:
    allrow += 1
    doc = ''
    showVersion = cdr.lastVersions(session, 'CDR' + str(row[0]))
    print "CDR-ID, Versions: ", row[0], showVersion
    l.write('CDR-ID: %s  Versions(last, pub, changed): %s' % (row[0],
                                                              showVersion))

    # -----------------------------------------------------
    # Documents that have changes will need to be versioned
    # -----------------------------------------------------
    if showVersion[2] == 'Y':
       doc = cdr.getDoc ((userid, passwd), row[0], checkout = 'Y',
                                      version = 'Current', xml = 'Y')

       # doc is either an object or a string of errors
       # ---------------------------------------------
       try:
           (repId, repErrs) = cdr.repDoc (session, doc=str(doc),
                             ver="Y", verPublishable='Y',
                             val='Y', checkIn='Y', showWarnings = 1,
                             comment="Create pub version, 2007-03-19, VE")
           irow += 1
           print repId, repErrs
           l.write('%s: %s' % (repId, repErrs))
       except:
           print "Document already checked out"
           l.write('Document already checked out')

print '*** Documents versioned, total: ', irow, allrow
l.write('makePubVersions.py - Documents versioned: %d' % irow)
l.write('makePubVersions.py - Documents total:     %d' % allrow)
l.write('makePubVersions.py - Completed')
