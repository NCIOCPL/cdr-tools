#----------------------------------------------------------------------
#
# $Id$
#
# Creates rows to be inserted into the emailer_prot_site table.
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
        self.display     = ""
        locs             = []
        for child in node.childNodes:
            if child.nodeName == "Name":
                self.name = cdr.getTextContent(child)
            elif child.nodeName == "Location":
                locs.append(Location(child))
            elif child.nodeName == "CIPSContact":
                self.cipsContact = cdr.getTextContent(child)
        if locs and self.cipsContact:
            for loc in locs:
                if loc.id == self.cipsContact:
                    self.loc = loc
                    break

        if self.name:
            self.display = self.name
            if self.loc:
                if self.loc.city:
                    self.display += u", %s" % self.loc.city
                if not self.loc.country or self.loc.country.name in ('Canada',
                                                                     'U.S.A.'):
                    if self.loc.state and self.loc.state.name:
                        self.display += u", %s" % self.loc.state.name
                else:
                    if self.loc.country and self.loc.country.name:
                        self.display += u", %s" % self.loc.country.name
                    
#----------------------------------------------------------------------
# Extract the column values from the XML document for the site.
#----------------------------------------------------------------------
def _getSiteRow(siteXml):
    dom = xml.dom.minidom.parseString(siteXml)
    org = Organization(dom.documentElement)
    if org.id and org.display:
        id = org.id
        name = org.name
        display = org.display
        city = org.loc and org.loc.city or None
        state = org.loc and org.loc.state and org.loc.state.id or None
        country = org.loc and org.loc.country and org.loc.country.id or None
        return (id, name, city, state, country, display)
    else:
        sys.stderr.write("Missing id or display in %s\n" % siteXml)

#----------------------------------------------------------------------
# Finds all the participating sites in publishable protocols.
# Returns a tuple containing the table name and list of table rows,
# one row for each site.
#----------------------------------------------------------------------
def load():
    sites  = []
    filter = ['name:Emailer Site Info']
    conn   = cdrdb.connect('CdrGuest')
    cursor = conn.cursor()
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
        id = row[0]
        ver = `row[1]`
        result = cdr.filterDoc('guest', filter, id, docVer = ver)
        if type(result) in (type(""), type(u"")):
            raise Exception(result)
        siteRow = _getSiteRow(result[0])
        if siteRow: sites.append(siteRow)
        rowsDone += 1
        sys.stderr.write("\rProcessed %d of %d organization docs" %
                         (rowsDone, totalRows))
    sys.stderr.write("\n")
    return ('emailer_prot_site', sites)
