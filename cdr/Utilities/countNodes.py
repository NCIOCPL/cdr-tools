# Count the nodes in an XML document, report to standard out
#
# $Id: countNodes.py,v 1.2 2009-09-23 02:56:33 ameyer Exp $
# $Log: not supported by cvs2svn $
# Revision 1.1  2005/09/28 01:37:20  ameyer
# Initial version
#
#
import sys, getopt, xml.dom.minidom

# Ignore comments and PIs
elemCnt = 0
attrCnt = 0
textCnt = 0
spceCnt = 0
cmntCnt = 0
pinsCnt = 0
cdatCnt = 0
totlCnt = 0

if len(sys.argv) < 2:
    sys.stderr.write("usage: countNodes.py {options} xmlfilename\n")
    sys.stderr.write("  options:\n")
    sys.stderr.write("  -t  = Show element text (not whitespace)\n")
    sys.stderr.write("  -a  = Show attribute text (not whitespace)\n")
    sys.exit(1)

def countem(nodeList, indent):
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
                if showElemText:
                    print("  %s%s" % (indent,
                          n.nodeValue.encode('ascii', 'replace')))

        elif n.nodeType == xml.dom.minidom.Node.ELEMENT_NODE:
            if showElemText or showAttrText:
                print("  %s%s:" % (indent, n.nodeName))

            elemCnt += 1
            if n.hasAttributes():
                attrs = n.attributes
                attrCnt += len(attrs)
                totlCnt += len(attrs)
                if showAttrText:
                    for i in range(attrs.length):
                        attr = attrs.item(i)
                        print("    %s@%s=%s" % (indent, attr.name, attr.value))
            countem(n.childNodes, indent+"  ")

        totlCnt += 1

# Command line
showElemText = False
showAttrText = False
(opts, args) = getopt.getopt(sys.argv[1:], 'ta')
for opt in opts:
    if opt[0] == '-t':
        showElemText = True
    if opt[0] == '-a':
        showAttrText = True

# Parse file fail if not found
try:
    # d = xml.dom.minidom.parse(sys.argv[1])
    d = xml.dom.minidom.parse(args[0])
except Exception, info:
    sys.stderr.write(str(info))
    sys.exit(1)

# Count
countem(d.childNodes, "")

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
