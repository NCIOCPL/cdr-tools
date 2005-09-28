# Count the nodes in an XML document, report to standard out
#
# $Id: countNodes.py,v 1.1 2005-09-28 01:37:20 ameyer Exp $
# $Log: not supported by cvs2svn $
#
import sys, xml.dom.minidom

# Ignore comments and PIs
elemCnt = 0
attrCnt = 0
textCnt = 0
spceCnt = 0
cmntCnt = 0
pinsCnt = 0
cdatCnt = 0
totlCnt = 0

if len(sys.argv) != 2:
    sys.stderr.write("usage: countNodes.py xmlfilename\n")
    sys.exit(1)

def countem(nodeList):
    global elemCnt, attrCnt, textCnt, spceCnt, cmntCnt, pinsCnt, \
           cdatCnt, totlCnt

    for i in range(len(nodeList)):
        n = nodeList[i]
        if n.nodeType == xml.dom.minidom.Node.COMMENT_NODE:
            cmntCnt += 1
        elif n.nodeType == xml.dom.minidom.Node.PROCESSING_INSTRUCTION_NODE:
            pinsCnt += 1
        elif n.nodeType == xml.dom.minidom.Node.CDATA_SECTION_NODE:
            cdatCnt += 1
        elif n.nodeType == xml.dom.minidom.Node.TEXT_NODE:
            if(n.nodeValue.isspace()):
                spceCnt += 1
            else:
                textCnt += 1
        elif n.nodeType == xml.dom.minidom.Node.ELEMENT_NODE:
            elemCnt += 1
            attrCnt += len(n.attributes)
            totlCnt += len(n.attributes)
            countem(n.childNodes)

        totlCnt += 1

# Parse file fail if not found
try:
    d = xml.dom.minidom.parse(sys.argv[1])
except Exception, info:
    sys.stderr.write(str(info))
    sys.exit(1)

# Count
countem(d.childNodes)

# Report
print """
Results:
      Element nodes = %d
    Attribute nodes = %d
         Text nodes = %d
   Whitespace nodes = %d
      Comment nodes = %d
           PI nodes = %d
        CDATA nodes = %d
     -------------------
          Total = %d
""" % (elemCnt, attrCnt, textCnt, spceCnt, cmntCnt, pinsCnt, cdatCnt, totlCnt)
