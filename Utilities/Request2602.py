#----------------------------------------------------------------------
#
# $Id$
#
# One off program to change other name type from 'NSC code' to 'NSC number'.
#
# BZIssue::2602
#
#----------------------------------------------------------------------

import sys, cdr, cdrdb, ModifyDocs

#----------------------------------------------------------------------
# Filter class for ModifyDocs.Job object.
# getDocIds() retrieves a list of CDR document IDs for # processing.
#
# The list may include many docs that should not be modified, but we
# won't know that until we run the XSLT transform.  We just get all
# of them here.
#----------------------------------------------------------------------
class Filter:
    def getDocIds(self):
        conn = cdrdb.connect('CdrGuest')
        cursor = conn.cursor()
        docIds = set()
        cursor.execute("""\
            SELECT doc_id
              FROM query_term
             WHERE path = '/Term/OtherName/OtherNameType'
               AND value = 'NSC code'""")
        for row in cursor.fetchall():
            docIds.add(row[0])
        cursor.execute("""\
            SELECT doc_id
              FROM query_term_pub
             WHERE path = '/Term/OtherName/OtherNameType'
               AND value = 'NSC code'""")
        for row in cursor.fetchall():
            docIds.add(row[0])
        return list(docIds)

#----------------------------------------------------------------------
# The Transform class is given to the ModifyDocs.Job object, which in
# turn gives it to each ModifyDocs.Doc object.  The run() method of
# this class takes a cdr.Doc object and returns a (possibly) modified
# copy of that object's xml member.
#----------------------------------------------------------------------
class Transform:
    def run(self, docObj):

        filter = """<?xml version='1.0' encoding='UTF-8'?>

<xsl:transform                version = '1.0'
                            xmlns:xsl = 'http://www.w3.org/1999/XSL/Transform'
                            xmlns:cdr = 'cips.nci.nih.gov/cdr'>

 <xsl:output                   method = 'xml'/>

 <!--
 =======================================================================
 Copy almost everything straight through.
 ======================================================================= -->
 <xsl:template             match = '@*|node()|comment()|
                                    processing-instruction()'>
  <xsl:copy>
   <xsl:apply-templates   select = '@*|node()|comment()|text()|
                                    processing-instruction()'/>
  </xsl:copy>
 </xsl:template>

 <!-- Node of interest -->
 <xsl:template             match = '/Term/OtherName/OtherNameType'>

  <!-- Does it have the text we want to modify? -->
  <xsl:choose>
   <xsl:when                test = ". = 'NSC code'">
    <OtherNameType>NSC number</OtherNameType>
   </xsl:when>
   <xsl:otherwise>
    <!-- Copy it to the output record -->
    <xsl:copy>
     <xsl:apply-templates select = "@*|comment()|*|
                                    processing-instruction()|text()"/>
    </xsl:copy>
   </xsl:otherwise>
  </xsl:choose>
 </xsl:template>
</xsl:transform>
"""
        response = cdr.filterDoc('guest', filter, doc = docObj.xml, inline = 1)
        if type(response) in (str, unicode):
            raise Exception(u"Failure in transformation Filter: %s" % response)

        # Return the possibly changed doc
        # ModifyDocs will do the right thing, only saving it if changed.
        return response[0]

if len(sys.argv) != 4 or sys.argv[3] not in ('test', 'live'):
    sys.stderr.write("usage: %s uid pwd test|live\n" % sys.argv[0])
    sys.exit(1)

comment = "Global change of 'NSC code' to 'NSC number' (request #2602)."
job     = ModifyDocs.Job(sys.argv[1], sys.argv[2], Filter(), Transform(),
                         comment, testMode = sys.argv[3] == 'test')
job.run()
