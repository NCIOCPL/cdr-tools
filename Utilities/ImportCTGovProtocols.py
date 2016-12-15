#----------------------------------------------------------------------
#
# $Id$
#
# BZIssue::4667
# BZIssue::4689
# BZIssue::4697 (copy citations from transferred InScopeProtocol)
# BZIssue::4942
# JIRA::OCECTS-113
# JIRA::OCECTS-120
# JIRA::OCECDR-4044
#
#----------------------------------------------------------------------
import cdr
import cdrdb
import sys
import re
import cdrcgi
import time
import lxml.etree as etree

#----------------------------------------------------------------------
# Determine whether the clinical center at the main NIH campus is
# (or is about to be) actively participating in this trial.
# See Request #4689.
# Modifications for JIRA request OCECTS-120.
# Modification made at Erika's request 2016-03-07: use zip code (OCECDR-4044).
#----------------------------------------------------------------------
def hasActiveMagnusonSite(tree):
    for node in tree.findall("Location/Facility/PostalAddress/PostalCode_ZIP"):
        if node.text is not None:
            code = node.text.strip()
            if code.startswith("20892"):
                return True
    return False

#----------------------------------------------------------------------
# Determine whether the trial document already has at least one
# ProtocolSpecialCategory block with SpecialCategory containing the
# value "NIH Clinical Center trial" (see Request #4689).
#----------------------------------------------------------------------
def hasNihCctBlock(tree):
    path = "PDQAdminInfo/ProtocolSpecialCategory/SpecialCategory"
    for node in tree.findall(path):
        if node.text == u"NIH Clinical Center trial":
            return True
    return False

#----------------------------------------------------------------------
# Adjust the PDQAdminInfo block, ensuring that it contains at least one
# ProtocolSpecialCategory block with SpecialCategory child set to
# 'NIH Clinical Center trial' if and only if the clinical center at
# the main NIH campus is (or is about to be) actively participating
# in the trial. See request #4689. The docXml argument is encoded as
# utf-8, as is the return value.
#----------------------------------------------------------------------
def fixSpecialCategory(docXml):
    tree = etree.XML(docXml)
    activeMagnusonSite = hasActiveMagnusonSite(tree)
    nihCctBlock = hasNihCctBlock(tree)
    filt = None
    parm = []
    if activeMagnusonSite:
        if not nihCctBlock:
            filt = ['name:NIH CCT Block Inserter']
            parm.append(['cmt', 'Inserted by CT.gov import program'])
    else:
        if nihCctBlock:
            filt = ['name:NIH CCT Block Stripper']
    if filt:
        cdr.logwrite("applying filter '%s'" % filt[0], LOGFILE)
        response = cdr.filterDoc('guest', filt, doc=docXml, parm=parm)
        if isinstance(response, basestring):
            raise Exception(response)
        return response[0]
    return docXml

#----------------------------------------------------------------------
# Keep track of the settings for the trial document currently being
# processed.
#
#   isNew             - "Y" if we've never imported it before; otherwise
#                       "N" (CIAT will need to provide PDQ indexing for
#                       new trials)
#   needsReview       - "Y" if significant changes possibly requiring
#                       modifications to the PDQ indexing have occurred
#                       since the last import; otherwise "N"
#   pubVersionCreated - "Y" if this import created a publishable version;
#                       otherwise "N"
#   locked            - True if we were unable to modify the CDR
#                       document because another user has it checked out
#----------------------------------------------------------------------
class Flags:
    def __init__(self):
        self.clear()
    def clear(self):
        self.isNew = 'N'
        self.needsReview = 'N'
        self.pubVersionCreated = 'N'
        self.locked = False

#----------------------------------------------------------------------
# Gather a list of email recipients for reports.
#----------------------------------------------------------------------
def getEmailRecipients(cursor, includeDeveloper = False):
    developer = '***REMOVED***'
    try:
        cursor.execute("""\
            SELECT u.email
              FROM usr u
              JOIN grp_usr gu
                ON gu.usr = u.id
              JOIN grp g
                ON g.id = gu.grp
             WHERE g.name = 'CTGov Publishers'
               AND u.expired IS NULL
               AND u.email IS NOT NULL
               AND u.email <> ''""")
        recips = [row[0] for row in cursor.fetchall()]
        if includeDeveloper and developer not in recips:
            recips.append(developer)
        return recips
    except:
        if includeDeveloper:
            return [developer]

#----------------------------------------------------------------------
# Split paragraph text into multiple paragraphs and/or itemized lists.
# The sub-parts ("chunks" below) are delimited in the original document
# by two or more consecutive newline characters (ignoring carriage
# returns). Itemized list items are marked by a space-hyphen-space
# sequence at the beginning of a line. Chunks which don't begin with
# this sequence are regular paragraphs. Note that we have to prepend
# a dummy line to the string for an itemized list because the newline
# character is part of the delimiter on which the items are split.
# The dummy line is dropped after the split by the [1:] slice operator.
# If the original paragraph is empty, return a single Para element
# with no text content.
#----------------------------------------------------------------------
def parsePara(node):
    elements = []
    text = node.text
    if text is not None:
        text = text.replace(u"\r", u"")
        if text:
            chunks = re.split(u"\n\n+", text)
            for chunk in chunks:
                if re.match(r"\s+-\s", chunk):
                    n = 0
                    items = etree.Element("ItemizedList")
                    for item in re.split(r"\n\s+-\s", u"dummy\n" + chunk)[1:]:
                        t = item.strip()
                        if t:
                            etree.SubElement(items, "ListItem").text = t
                            n += 1
                    if n:
                        elements.append(items)
                else:
                    t = chunk.strip()
                    if t:
                        para = etree.Element("Para")
                        para.text = t
                        elements.append(para)
    if not elements:
        elements.append(etree.Element("Para"))
    return elements

#----------------------------------------------------------------------
# The original documents use text formatting to mark up paragraphs
# and itemized lists withing a single element. We parse the original
# to create true XML markup.
#----------------------------------------------------------------------
def parseParas(doc):
    tree = etree.XML(doc)
    paras = [node for node in tree.iter("Para")]
    for para in paras:
        elements = parsePara(para)
        current = elements[0]
        para.getparent().replace(para, current)
        for next in elements[1:]:
            current.addnext(next)
            current = next
    return etree.tostring(tree, xml_declaration=True, encoding="utf-8")

#----------------------------------------------------------------------
# Record processing progress, including errors.
#----------------------------------------------------------------------
def log(msg, cdrErrors=None, tback=False):
    if cdrErrors:
        errors = cdr.getErrors(cdrErrors, asSequence=True)
        if not errors:
            cdr.logwrite(msg, LOGFILE, tback)
        elif len(errors) == 1:
            cdr.logwrite("%s: %s" % (msg, errors[0]), LOGFILE, tback)
        else:
            cdr.logwrite(msg, LOGFILE, tback)
            cdr.logwrite(errors, LOGFILE)
    else:
        cdr.logwrite(msg, LOGFILE, tback)

#----------------------------------------------------------------------
# Extract any error messages from a CDR Server response.
#----------------------------------------------------------------------
def checkResponse(resp):
    if not resp[0]:
        errors = cdr.getErrors(resp[1], errorsExpected=True,
                               asSequence=False)
        raise Exception(errors)
    if resp[1]:
        errors = cdr.getErrors(resp[1], errorsExpected=False,
                               asSequence=True)
        return errors

#----------------------------------------------------------------------
# Extract the portions of the trial document which are used for PDQ
# indexing.
#----------------------------------------------------------------------
def extractDocSubset(cdrId, docVer=None):
    filt = ['name:Extract Significant CTGovProtocol Elements']
    response = cdr.filterDoc(session, filt, cdrId, docVer=docVer)
    if not response[0]:
        raise Exception(response[1])
    return response[0]

#----------------------------------------------------------------------
# Compare the old and new versions of the portions of the trial document
# which are used for PDQ indexing to determine whether those portions
# have changed.
#----------------------------------------------------------------------
def hasMajorDiffs(cdrId, version, newSubset):
    oldSubset = extractDocSubset(cdrId, version)
    return newSubset != oldSubset

#----------------------------------------------------------------------
# When we extract document fragments using the CDR namespace using
# the lxml etree parser we'll get superfluous namespace declarations.
# Remove them.
#----------------------------------------------------------------------
def stripNamespaceDecl(xml):
    return re.sub(" xmlns:cdr=[\"']cips.nci.nih.gov/cdr['\"]", "", xml)

def preserveElement(tagName, newXml, root):
    """
    Extract a specified node from the XML tree for a CDR document
    and insert the serialized form of that node into the string
    for a CTGovProtocol document, replacing the placeholder inserted
    by the 'Import CT.gov Protocol' filter.

    Pass:
        tagName    - unqualified element name for the node to
                     extract from the tree for the CDR document;
                     there will be at most one occurrence of
                     the node
        newXml     - string representation of a CTGovProtocol
                     document, containing a placeholder of the
                     form '@@' + tagName + '@@' which will be
                     replaced with the serialized form of the
                     node we're looking for if we find it, or
                     with an empty string if the node is not
                     present; the string is encoded as utf-8
        root       - object representing the CDR document from
                     which we will extract the node to be
                     preserved

    Return:
        Modified utf-8 string representing the CTGovProtocol
        document with information from a previous version of
        the corresponding CDR document inserted.
    """
    oldXml = [etree.tostring(node,
                             encoding="utf-8") for node in root.iter(tagName)]
    oldXml = stripNamespaceDecl("\n".join(oldXml))
    placeholder = "@@%s@@" % tagName
    return newXml.replace(placeholder, oldXml)

def mergeVersion(newDoc, cdrId, docObject, docVer):
    """
    Merge information added by CIAT in a previous copy of the CDR document
    into the new document we just got from CTRP.

    Pass:
        newDoc     - new document received from CTRP, after being run
                     through the XSL/T filter 'Import CT.gov Protocol';
                     encoded as utf-8
        cdrId      - identifier for our own document
        docObject  - object which will be capable of serializing itself
                     into the form ready for passing into the CdrRepDoc
                     command, after we have modified the newDoc string
                     to restore the PDQ information created by CIAT
                     and plugged that modified string into this object
                     as the 'xml' attribute
        docVer     - version of the CDR document from which we will
                     retrieve the PDQ information to preserve

    Return:
        Serialized CdrDoc object, ready to be passed to the CdrRepDoc
        command (encoded as utf-8).
    """

    response = cdr.getDoc('guest', cdrId, version=docVer, getObject=True)
    if isinstance(response, basestring):
        errors = cdr.getErrors(response, errorsExpected=False, asSequence=True)
        raise Exception(errors)
    root   = etree.XML(response.xml)
    newDoc = preserveElement('PDQIndexing', newDoc, root)
    newDoc = preserveElement('PDQAdminInfo', newDoc, root)
    newDoc = preserveElement('ProtocolProcessingDetails', newDoc, root)
    newDoc = fixSpecialCategory(newDoc)
    docObject.xml = newDoc
    return str(docObject)

#----------------------------------------------------------------------
# Create new versions of an existing trial document, folding in the
# changed received from CTRP. The newDoc argument is encoded as utf-8.
#----------------------------------------------------------------------
def mergeChanges(cdrId, newDoc, flags):

    response = cdr.getDoc(session, cdrId, checkout='Y', getObject=True)
    errors   = cdr.getErrors(response, errorsExpected=False,
                             asSequence=True)
    if errors:
        flags.locked = True
        cursor.execute("""\
        INSERT INTO ctgov_import_event (job, nlm_id, locked, new, transferred)
             VALUES (?, ?, 'Y', 'N', 'N')""", (job, nlmId))
        conn.commit()
        raise Exception(errors)
    docObject = response
    originalXml = docObject.xml
    response = cdr.filterDoc(session,
                          ['name:Extract Significant CTGovProtocol Elements'],
                             doc=newDoc)
    if not response[0]:
        raise Exception(response[1])
    newSubset = response[0]
    lastAny, lastPub, isChanged = cdr.lastVersions(session, cdrId)
    newCwd   = mergeVersion(newDoc, cdrId, docObject, "Current")
    isChanged = isChanged == "Y"

    # We only need to save the newCwd once
    # This flag says that we haven't saved it at all yet
    savedNewCwd = False

    # Save the old CWD as a version if appropriate.
    if isChanged:
        comment = 'ImportCTGovProtocols: preserving current working doc'
        response = cdr.repDoc(session, doc=str(docObject), ver='Y',
                              reason=comment, comment=comment,
                              showWarnings=True, verPublishable='N')
        checkResponse(response)


    # Has a publishable CTGovProtocol version ever been saved for this trial?
    if isPublishableCtgovProtocolVersion(cdrId, lastPub):

        # If the differences are not significant, create a new pub. ver.
        if hasMajorDiffs(cdrId, lastPub, newSubset):
            flags.needsReview = 'Y'

        # If the old CWD and the last publishable version are identical
        #   then the newCWD and newPubVer should also be the same
        if not isChanged and lastAny == lastPub:
            newPubVer = newCwd
        else:
            newPubVer = mergeVersion(newDoc, cdrId, docObject, lastPub)
        comment = 'ImportCTGovProtocols: creating new publishable version'
        response = cdr.repDoc(session, doc=newPubVer, ver='Y',
                              verPublishable='Y', val='Y',
                              reason=comment, comment=comment,
                              showWarnings=True)
        errs = checkResponse(response)
        flags.pubVersionCreated = errs and 'N' or 'Y'
        if errs:
            cdr.logwrite("%s: %s" % (cdrId, errs[0]), LOGFILE)

        # If the newCwd and the newPubVer are the same, we've saved both
        if newCwd == newPubVer:
            # They were the same.  Our new CWD was, effectively, saved
            savedNewCwd = True

    elif hasMajorDiffs(cdrId, None, newSubset):
        flags.needsReview = 'Y'

    # Save the new current working document if we haven't done so already.
    if not savedNewCwd:
        comment  = 'ImportCTGovProtocols: creating new CWD'
        response = cdr.repDoc(session, doc=newCwd, showWarnings=True,
                              reason=comment, comment=comment)
        checkResponse(response)

#----------------------------------------------------------------------
# Determine whether the specified version is a publishable version of
# a CTGovProtocol document.
#----------------------------------------------------------------------
def isPublishableCtgovProtocolVersion(cdrId, lastPub):
    docId = cdr.exNormalize(cdrId)[1]
    cursor.execute("""\
        SELECT t.name
          FROM doc_type t
          JOIN doc_version v
            ON v.doc_type = t.id
         WHERE v.publishable = 'Y'
           AND v.id = ?
           AND v.num = ?
           AND t.name = 'CTGovProtocol'""", (docId, lastPub), timeout=600)
    return cursor.fetchall() and True or False

#----------------------------------------------------------------------
# Create the 'reason' string for the unlock action's row in the audit
# trail table.
#----------------------------------------------------------------------
def unlockReason(modifier):
    return "ImportCTGovProtocols: Unlocking %s CTGovProtocol doc" % modifier

#----------------------------------------------------------------------
# Module-scoped data.
#----------------------------------------------------------------------
TESTING = len(sys.argv) > 1 and "TEST" in sys.argv[1].upper()
LOGFILE = cdr.DEFAULT_LOGDIR + "/CTGovImport.log"
flags   = Flags()
conn    = cdrdb.connect()
cursor  = conn.cursor()
session = cdr.login('CTGovImport', '***REMOVED***')
errors  = cdr.getErrors(session, errorsExpected = False, asSequence = True)
if errors:
    cdr.logwrite("Login failure", session)
    sys.stderr.write("Login failure: %s" % str(errors))
    sys.exit(1)
cursor.execute("SELECT id FROM ctgov_disposition WHERE name = 'imported'")
importedDisposition = cursor.fetchall()[0][0]
cursor.execute("""\
    SELECT c.nlm_id, c.cdr_id
      FROM ctgov_import c
      JOIN ctgov_disposition d
        ON d.id = c.disposition
     WHERE d.name = 'import requested'
       AND c.xml IS NOT NULL""")
rows = cursor.fetchall()
cursor.execute("INSERT into ctgov_import_job (dt) VALUES (GETDATE())")
conn.commit()
cursor.execute("SELECT @@IDENTITY")
job = cursor.fetchone()[0]
failures = []
processed = new_docs = updated_docs = 0
try:
    for nlmId, cdrId in rows:
        flags.clear()
        if TESTING:
            if processed >= 10:
                break
            print nlmId, cdrId
        processed += 1
        cursor.execute("SELECT xml FROM ctgov_import WHERE nlm_id = ?", nlmId)
        doc = cursor.fetchone()[0].encode('utf-8')
        parms = [['newDoc', cdrId and 'N' or 'Y'],
                 ['importDateTime', time.strftime("%Y-%m-%dT%H:%M:%S")]]
        resp = cdr.filterDoc('guest', ['name:Import CTGovProtocol'], doc=doc,
                             parm=parms)
        if isinstance(resp, basestring):
            failures.append("Failure converting %s" % nlmId)
            log("Failure converting %s" % nlmId, resp)
            continue
        doc = parseParas(resp[0])

        #------------------------------------------------------------------
        # Add new doc.
        #------------------------------------------------------------------
        if not cdrId:
            flags.isNew = 'Y'
            comment = ('ImportCTGovProtocols: '
                       'Adding imported CTGovProtocol document')
            doc = fixSpecialCategory(doc)
            resp = cdr.addDoc(session, doc="""\
    <CdrDoc Type='CTGovProtocol'>
     <CdrDocCtl>
      <DocComment>%s</DocComment>
     </CdrDocCtl>
     <CdrDocXml><![CDATA[%s]]></CdrDocXml>
    </CdrDoc>
    """ % (comment, doc), showWarnings=True, reason=comment, ver="Y", val="N",
                              verPublishable="N")
            if not resp[0]:
                log("Failure adding %s" % nlmId, resp[1])
                failures.append("Failure adding %s" % nlmId)
            else:
                cdr.unlock(session, resp[0], reason=unlockReason("imported"))
                digits = re.sub(r"[^\d]", "", resp[0])
                cdrId = int(digits)
                cursor.execute("""\
                UPDATE ctgov_import
                   SET disposition = ?,
                       dt = GETDATE(),
                       cdr_id = ?
                 WHERE nlm_id = ?""", (importedDisposition, cdrId, nlmId))
                conn.commit()
                log("Added %s as %s" % (nlmId, resp[0]))
                new_docs += 1

        #------------------------------------------------------------------
        # Merge changes into existing doc.
        #------------------------------------------------------------------
        else:
            try:
                mergeChanges("CDR%d" % cdrId, doc, flags)
                cursor.execute("""\
                UPDATE ctgov_import
                   SET disposition = ?,
                       dt = GETDATE()
                 WHERE nlm_id = ?""", (importedDisposition, nlmId))
                conn.commit()
                log("Updated CDR%d from %s" % (cdrId, nlmId))
                updated_docs += 1
            except Exception, info:
                failures.append("Failure merging changes for %s into %s" %
                                (nlmId, cdrId))
                log("Failure merging changes for %s into %s: %s" %
                    (nlmId, cdrId, str(info)), tback=(not flags.locked))
            if not flags.locked:
                cdr.unlock(session, "CDR%d" % cdrId,
                           reason=unlockReason("updated"))
        if not flags.locked:
            try:
                cursor.execute("""\
     INSERT INTO ctgov_import_event(job, nlm_id, new, needs_review,
                                    pub_version, transferred, locked)
          VALUES (?, ?, ?, ?, ?, 'N', 'N')""", (job,
                                                nlmId,
                                                flags.isNew,
                                                flags.needsReview,
                                                flags.pubVersionCreated))
                conn.commit()
            except Exception, info:
                failures.append("Failure recording import event for %s" %
                                nlmId)
                log("Failure recording import event for %s: %s" %
                    (nlmId, str(info)))
except Exception, e:
    failures.append("Job interrupted: %s" % e)
    log("Job interrupted: %s" % e, tback = True)
if TESTING:
    sys.exit(0)
try:
    if failures:
        recips = getEmailRecipients(cursor, True)
        body = """\
    CT.gov import failures encountered; see logs for more information:

    %s
    """ % "\n".join(failures)
        subject = "CT.gov import failures"
        sender = "cdr@%s" % cdrcgi.WEBSERVER
        cdr.sendMail(sender, recips, subject, body)
except Exception, e:
    log("Failure sending report: %s" % e)
log("Processed %d trials (%d new, %d updated, %d failures)" %
    (processed, new_docs, updated_docs, len(failures)))
