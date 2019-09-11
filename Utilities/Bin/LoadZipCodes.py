#----------------------------------------------------------------------
# Utility to drop, re-create, and load the zipcode validation table.
# Required command-line argument is path to comma-delimited ASCII
# file from ZIPInfo (ZIPList5).
# ---------------------------------------------------------------------
# OCECDR-3848: Automate Quarterly ZIP Code Updates
#----------------------------------------------------------------------
import cdrdb, sys
import csv   #http://www.object-craft.com.au/projects/csv/

file   = open(sys.argv[1])
conn   = cdrdb.connect()
cursor = conn.cursor()
reader = csv.reader(file)
added  = 0
header = 0

# Create a backup of the current zipcode table
# --------------------------------------------
try:
    cursor.execute("TRUNCATE TABLE zipcode_backup")
    conn.commit()
except:
    print("Error:  Unable to truncate zipcode_backup")
    sys.exit(1)

try:
    cursor.execute("""INSERT INTO zipcode_backup
                    SELECT *
                      FROM zipcode""")
    conn.commit()
except:
    print("Error:  Unable to populate zipcode_backup")
    sys.exit(1)

# Drop the zipcode table and recreate it with proper permissions
# --------------------------------------------------------------
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
errCount = 0

# Load the ZIP code data
# ----------------------
for row in reader:
    if header > 1:
        if len(row) == 19:
            zipInfo = [row[0], row[1], row[2], row[3],
                       row[4], row[5], row[6], row[15]]
            cursor.execute("""\
            INSERT INTO zipcode (city, st, zip, area_code, county_fips,
                                 county_name, preferred, zip_code_type)
                  VALUES(?, ?, ?, ?, ?, ?, ?, ?)""", zipInfo)
            conn.commit()
            added += 1
            if not added % 2500: print("added %d rows" % added)
        elif len(row) > 19:
            print("Data format change!!!  Adjust data columns.")
            sys.exit(1)
        else:
            errCount += 1
            print("invalid line: %s" % row)
            if errCount > 50:
                print("ERROR: Too many errors detected!!!")
                sys.exit(1)
    header += 1
print("\nTotal number of rows loaded: %d" % added)
file.close()
