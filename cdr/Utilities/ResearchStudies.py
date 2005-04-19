#----------------------------------------------------------------------
#
# $Id: ResearchStudies.py,v 1.1 2005-04-19 22:14:23 venglisc Exp $ 
#
# Report identifying previously published protocols that should be 
# included in a hotfix.
#
# $Log: not supported by cvs2svn $
#----------------------------------------------------------------------
import cdr, cdrdb, re, sys, time, cdrcgi

path = "d:/cdr/tmp/"
name = "ResearchStudies"

# --------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------
#---------------------------------------------------------------------- 
# Check command-line arguments.
#----------------------------------------------------------------------
if len(sys.argv) != 2:
    sys.stderr.write("usage: ResearchStudies.py report-type\n")
    sys.stderr.write("       report-type = InScopeProtocol|ScientificProtocolInfo\n")
    sys.exit(1)
reportType = sys.argv[1]

# Connecting to the database
# --------------------------------------------------------------------
conn = cdrdb.connect('CdrGuest')
conn.setAutoCommit()
cursor = conn.cursor()

# Aspen wants a simple list of all document IDs
# Creating a CSV document to be written to the cdr/tmp directory
# -----------------------------------------------------------------
query = """\
    SELECT q.doc_id, p.value
      FROM query_term q
      JOIN query_term p
        ON q.doc_id = p.doc_id
       AND p.path = '/%s/ProtocolIDs/PrimaryID/IDString'
     WHERE q.value = 'Research study'
       AND q.path like '/%s%%'
     ORDER BY q.doc_id
""" % (reportType, reportType)
cursor.execute(query, timeout = 300)
 
# Setting output file names 
# -----------------------------------------------------------------
if reportType == 'InScopeProtocol':
    csvFile  = path + name + "_ISP.csv"
    htmlFile = path + name + "_ISP.html"
elif reportType == 'ScientificProtocolInfo':
    csvFile  = path + name + "_SPI.csv"
    htmlFile = path + name + "_SPI.html"
else:
    sys.exit(1)

rows = cursor.fetchall()

open(csvFile, "w").write('"CDR ID","Protocol ID"\n')
for row in rows:
    open(csvFile, "a").write('%s,"%s"\n' % (row[0], row[1]))

# Creating table of all InScopeProtocol documents
# that have been published (and pushed to Cancer.gov)
# We start looking from the last successfull pushing job of the 
# full data set since there may be documents that were dropped
# because of that and did not have a removal record in the 
# pub_proc_doc table
# ------------------------------------------------------------------
query = """\
    SELECT doc_id    
      FROM query_term
     WHERE value = 'Research study'
       AND path like '/%s%%'
     ORDER BY doc_id
""" % reportType
cursor.execute(query, timeout = 300)

rows = cursor.fetchall()

# Create the stylesheet that wraps all of the concatenated 
# Protocol QC reports.
# --------------------------------------------------------------
html = """\
<HTML xmlns:cdr="cips.nci.nih.gov/cdr">
  <HEAD>
    <meta http-equiv="Content-Type" content="text/html; charset=UTF-8">    
    <TITLE>CDR65549: NCCTG-934655</TITLE>
    <STYLE type="text/css">
  h1              { page-break-after: always; }
  b.native        { color: #007000 }
  p.native        { color: #007000; margin-top: 0 }
  p               { font-size: 12pt; }
  dt              { font-size: 12pt; }
  dd              { font-size: 12pt; }
 
  ul.lnone        { list-style: none; }
  ul.disc         { list-style: disc; }
  ul.square       { list-style: square; }
  ol.little-alpha { list-style: lower-alpha; }
  ol.A            { list-style: upper-alpha; }
  ol.little-roman { list-style: lower-roman; }
  ol.I            { list-style: upper-roman; }
  ol.d            { list-style: decimal; }
  ol.none         { list-style: none; }  /* Default if no attribute specified */
  li.org          { vertical-align: top; }
 
 
  ol ol { marginx:0.em; }        /* No space before and after second level */
  ol ul { marginx:0.em; }        /* list                                   */
  ul ol { marginx:0.em; }        /* This white space must be suppressed in */
  ul ul { marginx:0.em; }        /* order to handle the Compact = No       */
  ul    { margin-top:0.em; }
  ol    { margin-top:0.em; }
   
  p.listtitletop { font-style:       italic;  /* Display the first level  */
                   font-weight:      bold;    /* list title               */
                   margin-top:       0.em;
                   margin-bottom:    0.em; }
  p.listtitle    { font-style:       italic;  /* Display para element     */
                   font-weight:      bold;    /* as a list title          */
                   margin-top:       0.em;
                   margin-bottom:    0.em; }
  p.itemtitle    { font-weight:      bold;    /* Display para element     */
                   margin-top:       0.em;    /* as a ListItemTitle       */
                   margin-bottom:    0.em; }
  p.nospace      { margin-top:       0.em;    /* Display a para element   */
                   margin-bottom:    0.em; }  /* without blank lines      */
  li.addspace    { margin-bottom:    1.3em; } /* Add space after listitem */
                                              /* if attribute compact = No*/
  caption        { font-weight:      bold;    /* Display caption left     */
                   text-align:       left; }  /* aligned and bold         */
                    
                    
     ul.term         {margin-left: 16 ; padding-left: 0;}
    </STYLE>
  </HEAD>   
  <BASEFONT FACE="Arial, Helvetica, sans-serif">
  <BODY>
"""
qcReports = ""
for row in rows:
    response = []
    response = cdr.filterDoc('guest', ['set:QC InScopeProtocol HP Set'], row[0])
    qcReports += response[0]

# Insert an H1 element at the end of each individual QC report.
# The CSS has specified to create a page break on these H1 elements.
# ------------------------------------------------------------------
qcReports = re.sub("</BODY>", "<H1></H1></BODY>", qcReports)

# print html + qcReports + "</BODY></HTML>"

open(htmlFile, "w").write(html + qcReports + "</BODY></HTML>\n")
