#----------------------------------------------------------------------
#
# $Id: EmailerProtSites.py,v 1.2 2007-01-05 15:25:04 bkline Exp $
#
# Creates rows to be inserted into the emailer_prot_site table.
#
# $Log: not supported by cvs2svn $
# Revision 1.1  2004/11/23 16:45:36  bkline
# Nightly scripts for refreshing emailer lookup tables.
#
#----------------------------------------------------------------------
import cdr, cdrdb, sys, xml.dom.minidom

def extractId(node):
    try:
        id = node.getAttribute("id")
        cdrIds = cdr.exNormalize(id)
        return cdrIds[1]
    except:
        return None

class NameAndID:
    def __init__(self, node):
        self.id   = extractId(node)
        self.name = cdr.getTextContent(node)

class Location:
    def __init__(self, node):
        self.id      = node.getAttribute("id")
        self.city    = ""
        self.state   = None
        self.country = None
        for child in node.childNodes:
            if child.nodeName == "City":
                self.city = cdr.getTextContent(child) or None
            elif child.nodeName == "State":
                self.state = NameAndID(child)
            elif child.nodeName == "Country":
                self.country = NameAndID(child)

class Organization:
    def __init__(self, node):
        self.id          = extractId(node)
        self.name        = None
        self.loc         = None
        self.cipsContact = None
        self.displays    = []
        locs             = []
        otherNames       = []
        for child in node.childNodes:
            if child.nodeName == "Name":
                self.name = cdr.getTextContent(child)
            elif child.nodeName == "OtherName":
                otherNames.append(cdr.getTextContent(child))
            elif child.nodeName == "Location":
                locs.append(Location(child))
            elif child.nodeName == "CIPSContact":
                self.cipsContact = cdr.getTextContent(child)
        if locs and self.cipsContact:
            for loc in locs:
                if loc.id == self.cipsContact:
                    self.loc = loc
                    break

        # Don't do this, according to Lakshmi.
        #if locs:
        #    self.loc = locs[0]
        tail = []
        if self.loc:
            if self.loc.city:
                tail.append(u", %s" % self.loc.city)
            if not self.loc.country or self.loc.country.name in ('Canada',
                                                                 'U.S.A.'):
                if self.loc.state and self.loc.state.name:
                    tail.append(u", %s" % self.loc.state.name)
            else:
                if self.loc.country and self.loc.country.name:
                    tail.append(u", %s" % self.loc.country.name)
        tail = u"".join(tail)
        for name in ([self.name] + otherNames):
            if name:
                self.displays.append(name + tail)
                    
#----------------------------------------------------------------------
# Extract the column values from the XML document for the site.
#----------------------------------------------------------------------
def _getSiteRows(siteXml):
    try:
        dom = xml.dom.minidom.parseString(siteXml)
    except:
        sys.stderr.write("parse failure for %s" % siteXml)
        return (None, [])
    org = Organization(dom.documentElement)
    if org.id and org.name and org.displays:
        orgId = org.id
        name = org.name
        city = org.loc and org.loc.city or None
        state = org.loc and org.loc.state and org.loc.state.id or None
        country = org.loc and org.loc.country and org.loc.country.id or None
        mainTableRow = (orgId, name, city, state, country, org.displays[0])
        displayTableRows = []
        for display in org.displays:
            displayTableRows.append((orgId, display))
        return (mainTableRow, displayTableRows)
    else:
        sys.stderr.write("Missing id or names in %s\n" % siteXml)
        return (None, [])

#----------------------------------------------------------------------
# Finds all the participating sites in publishable protocols.
# Returns a tuple containing the table name and list of table rows,
# one row for each site.
#----------------------------------------------------------------------
def load():
    sites    = []
    displays = []
    filter   = ['name:Emailer Site Info']
    conn     = cdrdb.connect('CdrGuest')
    cursor   = conn.cursor()
    cursor.execute("""
SELECT DISTINCT q.int_val, MAX(v.num)
           FROM query_term q
           JOIN doc_version v
             ON q.int_val = v.id
          WHERE q.path = '/InScopeProtocol/ProtocolAdminInfo/ProtocolLeadOrg'
                       + '/ProtocolSites/OrgSite/OrgSiteID/@cdr:ref'
            AND v.publishable = 'Y'
       GROUP BY q.int_val""", timeout = 300)
    rows = cursor.fetchall()
    rowsDone = 0
    totalRows = len(rows)
    for row in rows:
        docId, docVer = row
        result = cdr.filterDoc('guest', filter, docId, docVer = `docVer`)
        if type(result) in (type(""), type(u"")):
            raise Exception(result)
        if result[0].find("<Name") != -1:
            mainTableRow, displayTableRows = _getSiteRows(result[0])
            if mainTableRow:
                sites.append(mainTableRow)
            for displayTableRow in displayTableRows:
                displays.append(displayTableRow)
        rowsDone += 1
        sys.stderr.write("\rProcessed %d of %d organization docs" %
                         (rowsDone, totalRows))
    sys.stderr.write("\n")
    return (('emailer_prot_site', sites),
            ('emailer_prot_site_search_string', displays))
