#----------------------------------------------------------------------
# Show publishing control parameters and options.
#----------------------------------------------------------------------
import glob
import lxml.etree as etree

class Parm:
    parms = {}
    path = "SystemSubset/SubsetParameters/SubsetParameter"
    def __init__(self, node):
        self.name = node.find("ParmName").text
        self.value = node.find("ParmValue").text

class Option:
    options = {}
    path = "SystemSubset/SubsetOptions/SubsetOption"
    def __init__(self, node):
        self.name = node.find("OptionName").text
        self.value = node.find("OptionValue").text

#for name in glob.glob("*.xml"):
for name in ("Primary.xml", "QcFilterSets.xml"):
    tree = etree.parse(name)
    for node in tree.getroot().findall(Parm.path):
        parm = Parm(node)
        if parm.name not in Parm.parms:
            Parm.parms[parm.name] = set()
        Parm.parms[parm.name].add(parm.value)
    for node in tree.getroot().findall(Option.path):
        option = Option(node)
        if option.name not in Option.options:
            Option.options[option.name] = set()
        Option.options[option.name].add(option.value)
for parm in sorted(Parm.parms):
    print parm
    for value in sorted(Parm.parms[parm]):
        print "\t%s" % value
for option in sorted(Option.options):
    print option
    for value in sorted(Option.options[option]):
        print "\t%s" % value
