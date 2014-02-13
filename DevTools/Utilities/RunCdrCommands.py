#----------------------------------------------------------------------
# $Id$
#
# Tool to run a set of commands stored in a text XML document file.
# The top-level wrapper element is CdrCommandSets, which in turn
# contains multiple CdrCommandSet elements, each of whose commands
# is submitted synchronously to the CDR Server.  An optional command-
# line argument can specify another port than the standard CDR port.
# A second optional command-line argument can limit the number of
# commands submitted to the number specified.
#
# The format of the input file (read from the standard input) matches
# the output of the GetCdrCommands.py tool (q.v.).
#
# The outcome of each command is written to the standard output,
# including status (success or failure), processing time, command
# name, and any error messages returned.  A briefer version (without
# the error messages) is also written to the standard error stream.
# So typical usage would redirect standard output to a log file,
# allowing standard error to print on the console.
#
# Typically, it is only feasible to replay commands which do not alter
# data in the database.  (It is possible, however, with some serious
# doctoring, to resubmit commands which modify documents, but this would
# typically involve rolling the documents back to the state they were in
# prior to the commands, wrapping commands with login/logoff pairs, and
# taking steps to ensure that documents which need to be changed are not
# locked by another account).
#
# $Log: not supported by cvs2svn $
#----------------------------------------------------------------------

import cdr, sys, xml.dom.minidom, xml.sax.saxutils

port = cdr.DEFAULT_PORT
max  = None
if len(sys.argv) > 1:
    port = int(sys.argv[1])
if len(sys.argv) > 2:
    max = int(sys.argv[2])

def nodeToString(node):
    """
    Serialize an XML node as a string.  This is a simplified version,
    which only cares about elements, attributes, and text content.
    """
    if node.nodeType == node.TEXT_NODE:
        return node.data
    elif node.nodeType == node.ELEMENT_NODE:
        str = "<%s" % node.nodeName
        content = ""
        for child in node.childNodes:
            if child.nodeType == child.ATTRIBUTE_NODE:
                val = xml.sax.saxutils.quoteattr(child.nodeValue)
                str += " %s=%s" % (child.nodeName, val)
            else:
                content += nodeToString(child)
        
        if node.hasAttributes():
            attrs = node.attributes
            for i in range(attrs.length):
                attr = attrs.item(i)
                name = attr.name
                val = xml.sax.saxutils.quoteattr(attr.value)
                str += " %s=%s" % (name, val)
        if not content:
            return str + "/>"
        else:
            return "%s>%s</%s>" % (str, content, node.nodeName)
    elif node.nodeType == node.CDATA_SECTION_NODE:
        return "<![CDATA[%s]]>" % node.data
    else:
        return ""

class Command:
    "Object holding the interesting information about a single CDR command."
    def __init__(self, name):
         self.name   = name
         self.result = None
         self.time   = None
         self.errors = []

def getCommands(node):
    "Returns a list of CdrCommand objects for commands in an XML node."
    cmds = []
    for child in node.childNodes:
        if child.nodeName == "CdrCommand":
            for grandchild in child.childNodes:
                if grandchild.nodeType == node.ELEMENT_NODE:
                    cmds.append(Command(grandchild.nodeName))
    return cmds

def collectErrors(node):
    "Returns a list of Unicode strings, one for each <Err/> child."
    errors = []
    for child in node.childNodes:
        if child.nodeName == "Err":
            errors.append(cdr.getTextContent(child))
    return errors

def extractErrors(node):
    """
    Looks for an <Errors/> element at the child or grandchild level.
    The element will be at the child level only in the case where
    the CDR server couldn't determine which command was being invoked.
    In the normal error case the the immediate child element will be
    the command response top-level element, and <Errors/> will be
    directly under that element.  Returns a list of error strings,
    extracted by collectErrors().
    """
    for child in node.childNodes:
        if child.nodeType == child.ELEMENT_NODE:
            if child.nodeName == "Errors":
                return collectErrors(child)
            for grandchild in child.childNodes:
                if grandchild.nodeName == "Errors":
                   return collectErrors(grandchild)
    return []
         
def parseResponse(resp, cmds):
    "Fills in results in the list of commands, based on the server's response."
    try:
        dom = xml.dom.minidom.parseString(resp)
    except:
        return
    i = 0
    for child in dom.documentElement.childNodes:
        if child.nodeName == "CdrResponse":
            cmds[i].result = child.getAttribute("Status")
            cmds[i].time   = child.getAttribute("Elapsed")
            cmds[i].errors = extractErrors(child)
            i += 1
   
if __name__ == "__main__":

    #----------------------------------------------------------------------
    # Read the commands from the standard input.
    #----------------------------------------------------------------------
    dom = xml.dom.minidom.parse(sys.stdin)

    #----------------------------------------------------------------------
    # Keep going till we run out of commands, or we hit the limit.
    #----------------------------------------------------------------------
    n = 0
    for child in dom.documentElement.childNodes:
        if max and (n > max):
            break
        n += 1
        if child.nodeName == "CdrCommandSet":
            cmds = getCommands(child)
            cmdString = nodeToString(child)

            #---------------------------------------------------------------
            # You can change the following (bogus) test to filter as needed.
            #---------------------------------------------------------------
            if cmdString.find("CdrLastVersionsx") == -1:
                response = cdr.sendCommands(cmdString, port = port)
                parseResponse(response, cmds)

                #-----------------------------------------------------------
                # Report progress to standard output and to standard error.
                #-----------------------------------------------------------
                for cmd in cmds:
                    row = "%20s: %s (%s secs.)" % (cmd.name,
                                                   cmd.result,
                                                   cmd.time)
                    print row
                    sys.stderr.write("%s\n" % row)
                    for err in cmd.errors:
                        print "ERROR: %s" % err
