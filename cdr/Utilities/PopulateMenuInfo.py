#----------------------------------------------------------------------
#
# $Id: PopulateMenuInfo.py,v 1.2 2003-03-31 16:11:57 bkline Exp $
#
# Populate the CDR Term documents with MenuInformation elements.
#
# $Log: not supported by cvs2svn $
# Revision 1.1  2003/03/31 15:25:26  bkline
# Program to automatically insert MenuInformation elements to CDR Term
# documents.
#
#----------------------------------------------------------------------
import cdr, cdrdb, sys, time, re, os

#----------------------------------------------------------------------
# Log processing/error information with a timestamp.
#----------------------------------------------------------------------
def log(what):
    what = "%s: %s\n" % (time.strftime("%Y-%m-%d %H:%M:%S"), what)
    logFile.write(what)
    sys.stderr.write(what)
    
#----------------------------------------------------------------------
# Invoke the CdrRepDoc command.
#----------------------------------------------------------------------
def saveDoc(id, doc, verPublishable, checkIn):
    log("saveDoc(%d, pub='%s', checkIn='%s')" % (id, verPublishable, checkIn))
    #return 1
    comment = "Populating Term document with menu information"
    response = cdr.repDoc(session, doc = doc, ver = 'Y', val = 'Y',
                          verPublishable = verPublishable,
                          reason = comment, comment = comment,
                          showWarnings = 'Y')
    if not response[0]:
        log("Failure versioning latest changes for CDR%010d: %s" %
            (id, response[1]))
        return 0
    if response[1]:
        log("Warnings for CDR%010d: %s" % (id, response[1]))
    return 1

#----------------------------------------------------------------------
# Show the number of rows for a table we just populated.
#----------------------------------------------------------------------
def countRows(tableName):
    cursor.execute("SELECT COUNT(*) FROM %s" % tableName)
    log("populated %d rows for table %s" % (cursor.fetchone()[0], tableName))

#----------------------------------------------------------------------
# Prepare a string for becoming part of an XML document.
#----------------------------------------------------------------------
def escape(term):
    return term.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

#----------------------------------------------------------------------
# Make one of these for every term used by the CDR menus.
#----------------------------------------------------------------------
class Term:

    def __init__(self, id, title, lastv, lastp, lastvDate, lastpDate,
                 lastSaveDate, done = 0):
        self.id           = id
        self.title        = title
        self.displays     = []
        self.parents      = []
        self.lastv        = lastv
        self.lastp        = lastp
        self.lastvDate    = lastvDate
        self.lastpDate    = lastpDate
        self.lastSaveDate = lastSaveDate
        self.done         = done

    #------------------------------------------------------------------
    # Create new versions of the Term document with menu info added.
    #------------------------------------------------------------------
    def update(self):
        """
        Versioning logic:
        
        Let PV  = publishable version
        Let LPV = latest publishable version
        Let NPV = non-publishable version
        Let CWD = copy of current working document when processing job begins

        If last numbered version == current working version:
           If most recent version is publishable:
              Apply change to CWD and save as new PV
           Else
              If any PV exists:
                 Apply change to LPV and save as new PV
              Apply change to CWD and save as new NPV
        Else:
           Create a new NPV using the unmodified CWD
           If any PV exists:
              Apply change to LPV and save as new PV
           Apply change to CWD and save as new NPV
        """

        # Get last published version if not the same as current working doc.
        if self.lastpDate and self.lastSaveDate != self.lastpDate:
            lpv = cdr.getDoc(session, self.id, version = str(self.lastp))
            if lpv.startswith("<Err"):
                log("Failure retrieving version %d for CDR%010d: %s" %
                    (self.lastp, lpv))
                return 0
            file = open("SavedTerms/CDR%010d-LPV.xml" % self.id, "wb")
            file.write(lpv)
            file.close

            # Apply the changes.
            lpvModified = self.insertMenuInfo(lpv)
            if not lpvModified:
                return 0
            file = open("SavedTerms/CDR%010d-LPV-MOD.xml" % self.id, "wb")
            file.write(lpvModified)
            file.close()
                
        # Check out the document.
        cwd = cdr.getDoc(session, self.id, 'Y')
        if cwd.startswith("<Err"):
            log("Failure checking out CDR%010d: %s" % (self.id, cwd))
            return 0
        file = open("SavedTerms/CDR%010d-CWD.xml" % self.id, "wb")
        file.write(cwd)
        file.close

        # Apply the changes.
        cwdModified = self.insertMenuInfo(cwd)
        if not cwdModified:
            return 0
        file = open("SavedTerms/CDR%010d-CWD-MOD.xml" % self.id, "wb")
        file.write(cwdModified)
        file.close()

        # Is the last numbered version the same as the current working doc?
        if self.lastvDate == self.lastSaveDate:

            # Is it publishable?
            if self.lastpDate == self.lastSaveDate:
                return saveDoc(self.id, cwdModified, 'Y', 'Y')

            # Has there ever been a publishable version?
            elif self.lastpDate:
                if not saveDoc(self.id, lpvModified, 'Y', 'N'):
                    return 0

            # Overlay the publishable version with an updated NPV.
            return saveDoc(self.id, cwdModified, 'N', 'Y')
        
        # Version the unversioned changes.
        if not saveDoc(self.id, cwd, 'N', self.lastpDate and 'N' or 'Y'):
            return 0

        # Save a modified publishable version if appropriate.
        if self.lastpDate:
            if not saveDoc(self.id, lpvModified, 'Y', 'N'):
                return 0

        # Save the modified CWD as a new NPV.
        return saveDoc(self.id, cwdModified, 'N', 'Y')

    #------------------------------------------------------------------
    # Create a new MenuInformation element and insert it into the Term.
    #------------------------------------------------------------------
    def insertMenuInfo(self, oldDoc):
        parents   = ""
        menuItems = ""
        for parent in self.parents:
            parents += """
   <MenuParent cdr:ref='CDR%010d'>%s</MenuParent>""" % (parent,
                                                        terms[parent].title)
        if self.displays:
            if len(self.displays) > 1:
                log("%d display strings for %d" % (len(self.displays),
                                                   self.id))
            itemWithNoDisplayName = 0
            for display in self.displays:
                dispName = ""
                if display and self.title != display:
                    dispName = """
   <DisplayName>%s</DisplayName>""" % escape(display)
                elif itemWithNoDisplayName:
                    continue
                else:
                    itemWithNoDisplayName = 1
                menuItems += """\
  <MenuItem>
   <MenuType>Clinical Trials--CancerType</MenuType>%s%s
   <MenuStatus>Online</MenuStatus>
   <EnteredBy>%s</EnteredBy>
   <EntryDate>%s</EntryDate>
   <Comment>Automatic conversion from Cancer.gov info.</Comment>
  </MenuItem>
""" % (parents, dispName, sys.argv[1], time.strftime("%Y-%m-%d"))
        else:
            menuItems += """\
  <MenuItem>
   <MenuType>Clinical Trials--CancerType</MenuType>%s
   <MenuStatus>Online</MenuStatus>
   <EnteredBy>%s</EnteredBy>
   <EntryDate>%s</EntryDate>
   <Comment>Automatic conversion from Cancer.gov info.</Comment>
  </MenuItem>
""" % (parents, sys.argv[1], time.strftime("%Y-%m-%d"))
        if not menuItems:
            raise Exception, "Internal error: no menuItems (can't happen!)"
        menuInfo = """
 <MenuInformation>
%s </MenuInformation>""" % menuItems
        position = oldDoc.find("</TermStatus>")
        if position == -1:
            log("</TermStatus> not found in term %d: %s" % (self.id, oldDoc))
            return None
        position += len("</TermStatus>")
        while position < len(oldDoc) and oldDoc[position] in ' \t\r':
            position += 1
        return oldDoc[:position] + menuInfo + oldDoc[position:]

#----------------------------------------------------------------------
# Main processing starts here.
#----------------------------------------------------------------------
try:
    os.mkdir("SavedTerms")
except:
    pass
logFile = open("SavedTerms/PopulateMenuInfo.log", "a")
if not len(sys.argv) == 3:
    sys.stderr.write("usage: PopulateMenuInfo uid pwd\n")
    sys.exit(1)
session = cdr.login(sys.argv[1], sys.argv[2])
if session.find("<Err") != -1:
    log("Login failure: %s\n" % session)
    sys.exit(1)

terms    = {}
conn     = cdrdb.connect()
cursor   = conn.cursor()
log("Connected to database ...")
cursor.execute("""\
    SELECT doc_id
      FROM query_term
     WHERE value = 'cancer'
       AND path = '/Term/PreferredName'""")
rows = cursor.fetchall()
if len(rows) != 1:
    raise Exception, "%d term documents found for cancer" % len(rows)
cancerId = rows[0][0]
log("doc id for cancer term is %d" % cancerId)

#----------------------------------------------------------------------
# Set up the table for the cancer types on the Cancer.gov menus.
#----------------------------------------------------------------------
cursor.execute("""\
   CREATE TABLE #CancerType
   (
       id INTEGER NOT NULL,
       display VARCHAR(256) NOT NULL
   )""")
conn.commit()
log("Created temp table #CancerType")
pattern = re.compile(r'<option (selected="selected" )?'
                     r'value=".*%3b(\d*)">([^<]*)</option>')
file = open("//mahler/d$/home/bkline/MenuTerms/CancerTypes.html")
for line in file.readlines():
    match = pattern.search(line)
    if match:
        try:
            id = int(match.group(2))
            cursor.execute("INSERT INTO #CancerType(id, display) VALUES(?,?)",
                           (id, match.group(3).replace("&amp;", "&")))
            conn.commit()
        except:
            log("failure inserting row into #CancerType for %s (%s)" %
                (match.group(2), match.group(3)))
    else:
        log("no match for line [%s]" % line.strip())
file.close()
countRows("#CancerType")

#----------------------------------------------------------------------
# Create a temporary table with all of the cancer stage terms.
#----------------------------------------------------------------------
cursor.execute("""\
    CREATE TABLE #CancerStage
    (
              id INTEGER NOT NULL,
            name NVARCHAR(255)
    )""")
conn.commit()
log("Created temp table #CancerStage")
cursor.execute("""\
    INSERT INTO #CancerStage(id, name)
    SELECT DISTINCT n.doc_id, n.value
               FROM query_term n
               JOIN query_term t
                 ON t.doc_id = n.doc_id
               JOIN query_term s
                 ON s.doc_id = t.int_val
              WHERE s.value = 'Cancer stage'
                AND n.path = '/Term/PreferredName'
                AND t.path = '/Term/SemanticType/@cdr:ref'
                AND s.path = '/Term/PreferredName'""")
conn.commit()
countRows("#CancerStage")

#----------------------------------------------------------------------
# Find all of these stages which are linked to one of the cancer types
# on the Cancer.gov menu.  This is a two-step process.  First we seed
# the list with the direct children, then we recursively look for all
# descendants.
#----------------------------------------------------------------------
cursor.execute("""\
    CREATE TABLE #CancerTypeDescendant
    (
     cancer_type INT,
      descendant INT
    )""")
conn.commit()
log("Created temp table #CancerTypeDescendant")
cursor.execute("""\
    INSERT INTO #CancerTypeDescendant(cancer_type, descendant)
    SELECT DISTINCT p.id, c.doc_id
               FROM #CancerType p
               JOIN query_term c
                 ON c.int_val = p.id
              WHERE c.path = '/Term/TermRelationship/ParentTerm' +
                             '/TermId/@cdr:ref'""")
conn.commit()
countRows("#CancerTypeDescendant")
more = 1
while more:
    cursor.execute("""\
    INSERT INTO #CancerTypeDescendant(cancer_type, descendant)
    SELECT DISTINCT a.cancer_type, d.doc_id
               FROM #CancerTypeDescendant a
               JOIN query_term d
                 ON d.int_val = a.descendant
              WHERE d.path = '/Term/TermRelationship/ParentTerm' +
                             '/TermId/@cdr:ref'
                AND NOT EXISTS (SELECT *
                                  FROM #CancerTypeDescendant
                                 WHERE cancer_type = a.cancer_type
                                   AND descendant = d.doc_id)""")
    more = cursor.rowcount > 0 and 1 or 0
    log("%d additional rows inserted" % cursor.rowcount)
    conn.commit()
    countRows("#CancerTypeDescendant")

#----------------------------------------------------------------------
# Set up the table which knows about the versions of these terms.
#----------------------------------------------------------------------
cursor.execute("""\
    CREATE TABLE #TermVersions
    (
        id         INTEGER  NOT NULL,
        lastv      INTEGER      NULL,
        lastv_date DATETIME     NULL, 
        lastp      INTEGER      NULL,
        lastp_date DATETIME     NULL,
        cwv_date   DATETIME NOT NULL
    )""")
conn.commit()
log("Created temp table #TermVersions")
cursor.execute("""\
     INSERT INTO #TermVersions(id, lastv, lastp, cwv_date)
 SELECT DISTINCT lastv.id, MAX(lastv.num), MAX(lastp.num), MAX(a.dt)
            FROM audit_trail a
 LEFT OUTER JOIN doc_version lastv
              ON a.document = lastv.id
 LEFT OUTER JOIN doc_version lastp
              ON lastv.id = lastp.id
             AND lastp.publishable = 'Y'
           WHERE a.document IN (SELECT DISTINCT descendant
                                           FROM #CancerTypeDescendant
                                          UNION
                                         SELECT id FROM #CancerType)
              OR a.document = %d
        GROUP BY lastv.id""" % cancerId)
conn.commit()
countRows("#TermVersions")
cursor.execute("""\
    UPDATE #TermVersions 
       SET lastv_date = v.updated_dt
      FROM #TermVersions tv, doc_version v
     WHERE v.id = tv.id
       AND v.num = tv.lastv""")
conn.commit()
log("updated lastv_date in #TermVersions")
cursor.execute("""\
    UPDATE #TermVersions 
       SET lastp_date = v.updated_dt
      FROM #TermVersions tv, doc_version v
     WHERE v.id = tv.id
       AND v.num = tv.lastp""")
conn.commit()
log("updated lastp_date in #TermVersions")

statPath = "/Term/MenuInformation/MenuItem/MenuStatus"
#----------------------------------------------------------------------
# Create a Term object for the top-level menu term ('cancer').
# Another bug.  Python actually blows up if we try to use a placeholder
# parameter in the WHERE clause below.
#----------------------------------------------------------------------
cursor.execute("""\
    SELECT lastv,
           lastp,
           lastv_date,
           lastp_date,
           cwv_date,
           CASE
               WHEN id IN (SELECT doc_id
                             FROM query_term
                            WHERE path = '%s')
               THEN 1
               ELSE 0
           END AS already_done
      FROM #TermVersions
     WHERE id = %d""" % (statPath, cancerId))
rows = cursor.fetchall()
if len(rows) != 1:
    raise Exception, "found %d rows fetching versions for cancer term doc %d" \
          (len(rows), cancerId)
r = rows[0]
terms[cancerId] = Term(cancerId, "cancer", r[0], r[1], r[2], r[3], r[4],
                       done = r[5])
log("Fetched information for cancer term")

#----------------------------------------------------------------------
# Create Term objects for the cancer type terms.
#----------------------------------------------------------------------
cursor.execute("""\
    SELECT #CancerType.id,
           query_term.value,
           #TermVersions.lastv,
           #TermVersions.lastp,
           #TermVersions.lastv_date,
           #TermVersions.lastp_date,
           #TermVersions.cwv_date,
           #CancerType.display,
           CASE
               WHEN #CancerType.id IN (SELECT doc_id
                                         FROM query_term
                                        WHERE path = '%s')
               THEN 1
               ELSE 0
           END
      FROM #CancerType
      JOIN query_term
        ON query_term.doc_id = #CancerType.id
      JOIN #TermVersions
        ON #TermVersions.id = query_term.doc_id
     WHERE query_term.path = '/Term/PreferredName'""" % statPath)
for r in cursor.fetchall():
    log("type %d (%s...) lastv=%d(%s) lastp=%d(%s) cwd=%s done=%d" %
        (r[0], r[1][:10], r[2], r[4][:10], r[3], r[5][:10], r[6][:10], r[8]))
    if not terms.has_key(r[0]):
        terms[r[0]] = Term(r[0], r[1], r[2], r[3], r[4], r[5], r[6], r[8])
        terms[r[0]].parents.append(cancerId)
    if not r[7] in terms[r[0]].displays:
        terms[r[0]].displays.append(r[7])

##  doc = cdr.getDoc(session, row[0], 'Y')
##  if doc.startswith("<Err"):
##      sys.stderr.write("Failure checking out CDR%010d: %s\n" % (row[0], doc))
##  else:
##      file = open("SavedTerms/%d.xml" % row[0], "wb")
##      file.write(doc)
##      file.close()

#----------------------------------------------------------------------
# Create Term objects for the cancer stage terms.
#----------------------------------------------------------------------
cursor.execute("""\
    SELECT d.descendant,
           s.name,
           v.lastv,
           v.lastp,
           v.lastv_date,
           v.lastp_date,
           v.cwv_date,
           d.cancer_type,
           CASE
               WHEN d.descendant IN (SELECT doc_id
                                       FROM query_term
                                      WHERE path = '%s')
               THEN 1
               ELSE 0
           END
      FROM #CancerTypeDescendant d
      JOIN #CancerStage s
        ON s.id = d.descendant
      JOIN #TermVersions v
        ON v.id = s.id""" % statPath)
for r in cursor.fetchall():
    log("stage %d (%s...) lastv=%d(%s) lastp=%d(%s) cwd=%s parent=%d done=%d" %
        (r[0], r[1][:10], r[2], r[4][:10], r[3], r[5][:10], r[6][:10], r[7],
         r[8]))
    if not terms.has_key(r[7]):
        raise Exception, "doc %d isn't a cancer type!" % r[7]
    if not terms.has_key(r[0]):
        terms[r[0]] = Term(r[0], r[1], r[2], r[3], r[4], r[5], r[6],
                           done = r[8])
##      terms[row[1]] = Term(row[1], row[2])
##      doc = cdr.getDoc(session, row[0], 'Y')
##      if doc.startswith("<Err"):
##          sys.stderr.write("Failure checking out CDR%010d: %s\n" % (row[0],
##                                                                    doc))
##      else:
##          file = open("SavedTerms/%d.xml" % row[0], "wb")
##          file.write(doc)
##          file.close()
    terms[r[0]].parents.append(r[7])
for term in terms:
    if not terms[term].done: # XXX DEBUGGING and terms[term].id == 40694:
        terms[term].update()
