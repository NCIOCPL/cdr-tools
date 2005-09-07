#----------------------------------------------------------------------
#
# $Id: LoadZipCodes.py,v 1.3 2005-09-07 19:11:51 venglisc Exp $
#
# Utility to drop, re-create, and load the zipcode validation table.
# Required command-line argument is path to comma-delimited ASCII
# file from ZIPInfo (ZIPList5).
#
# $Log: not supported by cvs2svn $
# Revision 1.2  2005/03/16 18:44:22  venglisc
# Made changes to the program to address a version change of the CSV module
# (Bug 1457).
#
# Revision 1.1  2003/09/09 15:09:56  bkline
# Script to create and populate zipcode table.
#
#----------------------------------------------------------------------
import cdrdb, sys
import csv   #http://www.object-craft.com.au/projects/csv/

file   = open(sys.argv[1])
conn   = cdrdb.connect()
cursor = conn.cursor()
reader = csv.reader(file)
added  = 0
header = 0
try:
    cursor.execute("DROP TABLE zipcode")
    conn.commit()
except:
    pass # OK if it doesn't exist yet.
cursor.execute("""\
    CREATE TABLE zipcode
           (city VARCHAR(28) NOT NULL,
              st CHAR(2)     NOT NULL,
             zip CHAR(5)     NOT NULL,
       area_code CHAR(5)     NOT NULL,
     county_fips CHAR(5)     NOT NULL,
     county_name VARCHAR(25) NOT NULL,
       preferred CHAR(1)     NOT NULL CHECK (preferred IN ('P', 'A', 'N')),
   zip_code_type CHAR(1)     NOT NULL CHECK (zip_code_type IN ('P',
                                                               'U',
                                                               'M',
                                                               ' ')))""")
conn.commit()
cursor.execute("GRANT select ON zipcode TO CdrGuest")
conn.commit()
for row in reader:
    if header > 1:
        if len(row) == 16:
            zipInfo = [row[0], row[1], row[2], row[3], 
                       row[4], row[5], row[6], row[15]]
            cursor.execute("""\
            INSERT INTO zipcode (city, st, zip, area_code, county_fips,
                                 county_name, preferred, zip_code_type)
                  VALUES(?, ?, ?, ?, ?, ?, ?, ?)""", zipInfo)
            conn.commit()
            added += 1
            print "added %d rows" % added
        else:
            print "invalid line: %s" % row
    header += 1
file.close()
