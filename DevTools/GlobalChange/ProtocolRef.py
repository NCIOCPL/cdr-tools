"""
One-off global change job to convert all ExternalRef elements
pointing to a NCT protocol ID to a ProtocolRef element.

Uses the lxml.etree parser to perform the document modifications.
"""

from argparse import ArgumentParser
from lxml import etree
from ModifyDocs import Job
from cdrapi import db as cdrdb
import re
import sys


class OneOffGlobal(Job):
    """
    Derived class for a specific document transformation job
    """

    COMMENT = "Convert ExternalRef elements to ProtocolRef. OCECDR-4551"


    def __init__(self, doc_ids, **opts):
        """
        Capture control settings for job

        Invoke the base class constructor with the user's options,
        then remember the list of documents to be transformed.
        """

        Job.__init__(self, **opts)
        self.__doc_ids = doc_ids


    def select(self):
        """
        Return the sequence of CDR document IDs for this job

        Looking for all ExternalRef elements within a Summary
        containing an xref attribute pointing to CT.gov and
        including a NCT-ID indicated by 'NCTxxxxxxxx'
        """

        # SQL query to select all summary documents with
        # ExternalRef element
        # ----------------------------------------------------
        qry = """
            SELECT DISTINCT d.id AS "CDR-ID"
              FROM document d
              JOIN doc_type dt
                ON d.doc_type = dt.id
              JOIN pub_proc_cg cg
                ON d.id = cg.id
              JOIN query_term_pub q
                ON q.doc_id = d.id
             WHERE dt.name = 'Summary'
               AND q.path LIKE  '/Summary%ExternalRef/@cdr:xref'
               AND value LIKE 'https://clinicaltrials.gov/%NCT________%'
             ORDER by d.id
        """

        # Connecting to the DB and executing the query
        # ----------------------------------------------------
        try:
            conn = cdrdb.connect(tier=opts.tier)
            cursor = conn.cursor()
            cursor.execute(qry)
            rows = cursor.fetchall()
            cursor.close()
        except cdrdb.Error as info:
            print(qry)
            sys.exit('*** ProtocolRef.py: Error connecting to DB ***')

        # Creating the list of doc IDs
        # ----------------------------------------------------
        self.__doc_ids = [row[0] for row in rows]
        #self.__doc_ids = [ 62902, 62707 ]

        return self.__doc_ids


    def transform(self, doc):
        """
        - Find all ExternalRef element within the document
        - Create a new ProtocolRef element with the information
          from the ExternalRef element
        - Replace the ExternalRef with the ProtocolRef elements

        Note: The ExternalRef is an inline element and therefore
              the findall() function includes a tail of the
              element that needs to be added to the ProtocolRef

        Pass:
          doc - reference to `cdr.Doc` object for document to be modified

        Return:
          serialized transformed document XML, encoded as UTF-8
        """

        root = etree.fromstring(doc.xml)

        # Search for all ExternalRef elements
        #   Not all will point to a NCT protocol
        # ------------------------------------------------------
        for node in root.findall(".//ExternalRef"):
            #print("------------------")
            #print(repr(node.text))
            attribs = node.attrib
            url = attribs['{cips.nci.nih.gov/cdr}xref']
            urlSub = re.search('NCT(........)', url)

            # For those links including a NCT-ID create a
            # replacement element
            # --------------------------------------------------
            if urlSub:
                nctId = urlSub.group(1)
                prot = etree.Element('ProtocolRef')
                prot.text = node.text
                prot.tail = node.tail
                prot.set('nct_id', 'NCT%s' % nctId)
                prot.set('comment', 'Converted from ExternalRef')
                #node.getparent().insert(0, prot)
                #node.getparent().remove(node)
                node.getparent().replace(node, prot)

        return etree.tostring(root, encoding="utf-8")


if __name__ == "__main__":
    """
    Collect the command-line options, create the job, and run it
    """

    parser = ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--session")
    group.add_argument("--user")
    parser.add_argument("--mode", default="test")
    parser.add_argument("--tier")
    opts = parser.parse_args()
    docs = 444444, 555555, 666666
    job = OneOffGlobal(docs, **vars(opts))
    job.run()
