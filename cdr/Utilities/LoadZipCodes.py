#----------------------------------------------------------------------
#
# $Id: LoadZipCodes.py,v 1.1 2003-09-09 15:09:56 bkline Exp $
#
# Utility to drop, re-create, and load the zipcode validation table.
# Required command-line argument is path to comma-delimited ASCII
# file from ZIPInfo (ZIPList5).
#
# $Log: not supported by cvs2svn $
#----------------------------------------------------------------------
import cdrdb, sys
import csv   #http://www.object-craft.com.au/projects/csv/

file   = open(sys.argv[1])
line   = file.readline()   # Skip field names.
line   = file.readline()   # Skip copyright notice.
line   = file.readline()
conn   = cdrdb.connect()
cursor = conn.cursor()
parser = csv.parser()
added  = 0
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
while line:
    fields = parser.parse(line)
    if len(fields) == 8:
        cursor.execute("""\
            INSERT INTO zipcode (city, st, zip, area_code, county_fips,
                                 county_name, preferred, zip_code_type)
                  VALUES(?, ?, ?, ?, ?, ?, ?, ?)""", fields)
        conn.commit()
        added += 1
        print "added %d rows" % added
    else:
        print "invalid line: [%s]" % line.strip()
    line = file.readline()
file.close()
