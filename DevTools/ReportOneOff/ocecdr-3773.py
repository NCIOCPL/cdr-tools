#----------------------------------------------------------------------
#
# $Id$
#
# As we discussed today, we would like to get an estimated word count of
# the text content (excluding references) for all of the English HP
# summaries.
#
# As decided in our meeting, Bob will use the vendor output of the
# summaries and determine the word count including each of the text
# elements with the exception of the reference sections. He will create
# an Excel spreadsheet including the Summary Type, CDR ID, and Word
# Count for each summary. Thanks!
#
# JIRA::OCECDR-3773
#
#----------------------------------------------------------------------

import cdrdb
import lxml.etree as etree
import re
import sys

class Summary:
    def __init__(self, doc_id, summary_type):
        self.doc_id = doc_id
        self.summary_type = summary_type
        self.count = 0
        self.count_words()
    def count_words(self, node=None):
        if node is None:
            cursor.execute("SELECT xml FROM pub_proc_cg WHERE id = ?",
                           self.doc_id)
            doc_xml = cursor.fetchall()[0][0]
            node = etree.XML(doc_xml.encode("utf-8"))
        if node.tag != "ReferenceSection":
            content = node.text
            if content is not None:
                content = re.sub("[-/]+", " ", content)
                content = re.sub("[0-9]", "", content)
                content = content.strip()
                if content:
                    words = content.split()
                    self.count += len(words)
            for child in node:
                self.count_words(child)

cursor = cdrdb.connect("CdrGuest").cursor()
cursor.execute("""\
  SELECT t.doc_id, t.value
    FROM query_term_pub t
    JOIN query_term_pub a
      ON a.doc_id = t.doc_id
    JOIN query_term_pub l
      ON l.doc_id = t.doc_id
    JOIN pub_proc_cg c on id = t.doc_id
   WHERE t.path = '/Summary/SummaryMetaData/SummaryType'
     AND a.path = '/Summary/SummaryMetaData/SummaryAudience'
     AND l.path = '/Summary/SummaryMetaData/SummaryLanguage'
     AND l.value = 'English'
     AND a.value = 'Health professionals'
ORDER BY 2, 1""")
rows = cursor.fetchall()
count = 0
for doc_id, summary_type in rows:
    summary = Summary(doc_id, summary_type)
    print "%s\t%s\t%s" % (summary_type, doc_id, summary.count)
    count += 1
    sys.stderr.write("\r%d of %d" % (count, len(rows)))
