#----------------------------------------------------------------------
#
# $Id: Request1992.py,v 1.1 2006-02-16 23:22:14 ameyer Exp $
#
# One off program to delete ExternalRef elements from Term documents
# containing the text "See a list of clinical trials using this agent".
# Done for Bugzilla Request 1992.
#
# $Log: not supported by cvs2svn $
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
        cursor.execute("""\
         SELECT distinct doc_id FROM query_term
          WHERE path='/Term/Definition/DefinitionText/ExternalRef/@cdr:xref'
          ORDER BY doc_id
        """)
        # Return list of first element of each row
        return [row[0] for row in cursor.fetchall()]


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
 <xsl:template             match =
                            '/Term/Definition/DefinitionText/ExternalRef'>

   <!-- Does it have the text we want to delete? -->
   <xsl:choose>
     <xsl:when              test =
             "contains(., 'See a list of clinical trials using this agent')">
       <!-- Do nothing for this element.  It won't be copied.
            But tell transformer that document has been changed.  -->
     </xsl:when>
     <xsl:otherwise>
       <!-- Copy it to the output record -->
       <xsl:copy>
        <xsl:apply-templates  select = "@*|comment()|*|
                                        processing-instruction()|text()"/>
       </xsl:copy>
     </xsl:otherwise>
   </xsl:choose>
 </xsl:template>
</xsl:transform>
"""
        response = cdr.filterDoc('guest', filter, doc = docObj.xml, inline = 1)
        if type(response) in (type(""), type(u"")):
            raise Exception("Failure in transformation Filter: %s" % response)

        # Return the possibly changed doc
        # ModifyDocs will do the right thing, only saving it if changed.
        return response[0]

# To run with real database update, pass userid, pw, 'run' on cmd line
if len(sys.argv) < 3:
    sys.stderr.write("usage: Request1992.py userid pw {'run' - for non-test}\n")
    sys.exit(1)

testMode = True
if len(sys.argv) > 3:
    if sys.argv[3] == 'run':
        testMode = False
job = ModifyDocs.Job(sys.argv[1], sys.argv[2], Filter(), Transform(),
 "Global change deleting ExternalRefs seeing list of trials (request #1792).",
 testMode=testMode)
job.run()
