#----------------------------------------------------------------------
# $Id$
# Strip Compact attributes from CDR documents.
# OCECDR-3820
#----------------------------------------------------------------------
import lxml.etree as etree
import cdrdb
import cdr
import ModifyDocs
import sys

LOGFILE = "%s/strip-compact-attribute.log" % cdr.DEFAULT_LOGDIR

# Keep everything execpt the @Compact attributes on list elements.
FILTER = """\
<xsl:transform            xmlns:xsl = "http://www.w3.org/1999/XSL/Transform"
                            version = "1.0">
 <xsl:output                 method = "xml"
                           encoding = "utf-8"/>
 <xsl:template                match = "OrderedList/@Compact"/>
 <xsl:template                match = "ItemizedList/@Compact"/>
 <xsl:template                match = "@*|node()">
  <xsl:copy>
   <xsl:apply-templates      select = "@*|node()"/>
  </xsl:copy>
 </xsl:template>
</xsl:transform>
"""

# Generated from the output of `grep -l Compact d:/cdr/ClientFiles/Rules/*.dtd`
DOCTYPES = (
    "Citation",
    "Documentation",
    "DocumentationToC",
    "DrugInformationSummary",
    "GlossaryTerm",
    "GlossaryTermConcept",
    "GlossaryTermName",
    "InScopeProtocol",
    "Media",
    "MiscellaneousDocument",
    "Organization",
    "OutOfScopeProtocol",
    "ScientificProtocolInfo",
    "Summary",
    "Term"
)

#----------------------------------------------------------------------
# Job control object. Implements the interface used by the ModifyDocs
# module, returning the list of IDs for the documents to be modified,
# and performing the actual document modifications.
#----------------------------------------------------------------------
class StripCompact:

    def getDocIds(self):
        query = cdrdb.Query("document d", "d.id", "d.xml")
        query.join("doc_type t", "t.id = d.doc_type")
        query.where(query.Condition("t.name", DOCTYPES, "IN"))
        query.where(query.Condition("d.xml", "%edList%Compact%", "LIKE"))
        cursor = query.timeout(1000).execute()
        doc_ids = []
        row = cursor.fetchone()
        while row:
            doc_id, xml = row
            if StripCompact.wanted(xml):
                doc_ids.append(doc_id)
            row = cursor.fetchone()
        return sorted(doc_ids)

    def run(self, doc_obj):
        "Strip out the obsolete Compact attribute instances"
        response = cdr.filterDoc("guest", FILTER, doc=doc_obj.xml, inline=True)
        error = cdr.checkErr(response)
        if error:
            sys.stderr.write("%s: %s\n" % (doc_obj.id, repr(error)))
            return doc_obj.xml
        else:
            return response[0]

    @staticmethod
    def wanted(xml):
        "Find out if the document needs to be processed"
        tree = etree.XML(xml.encode("utf-8"))
        if tree.xpath("//OrderedList[@Compact]"):
            return True
        if tree.xpath("//ItemizedList[@Compact]"):
            return True
        return False

if len(sys.argv) != 4 or sys.argv[3].lower() not in ("test", "live"):
    sys.stderr.write("usage: strip-compact.py UID PWD test|live\n")
    sys.exit(1)
uid, pwd, mode = sys.argv[1:]
test = mode.lower() != "live"
obj = StripCompact()
comment = "global change job to strip Compact attributes (OCECDR-3820)"
job = ModifyDocs.Job(uid, pwd, obj, obj, comment, validate=True,
                     testMode=test, logFile=LOGFILE)
job.run()
