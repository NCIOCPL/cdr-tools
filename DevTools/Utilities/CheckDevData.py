import sys, glob, os

class Tables:
    def __init__(self, directory):
        self.directory = directory
        self.usr = self.load_table("usr")
        
def fix(line, table):
    row = eval(line)
    if table == "usr":
        return tuple(row[:-3])
    return tuple(row)

def compare(dev, prod):
    if set(dev.cols) != set(prod.cols):
        print "-------- TABLE STRUCTURE MISMATCH --------"
        print "< %s" % repr(dev.cols)
        print "> %s" % repr(prod.cols)
    if True: # else
        dev_set = set(dev.data)
        prod_set = set(prod.data)
        dev_only = [(row, "<") for row in (dev_set - prod_set)]
        prod_only = [(row, ">") for row in (prod_set - dev_set)]
        deltas = dev_only + prod_only
        for row, direction in sorted(deltas):
            print direction, row

class Table(object):
    def __init__(self, fp, name):
        self.name = name
        self.lines = fp.readlines()
        self.cols = eval(self.lines[0])
        self.data = [tuple(eval(line)) for line in self.lines[1:]]
class Usr(Table):
    def __init__(self, fp, name):
        super(Usr, self).__init__(fp, name)
        data = []
        for row in self.data:
            cols = dict(zip(self.cols, row))
            data.append((cols["id"], cols["name"], cols["created"],
                         cols["fullname"], cols["office"], cols["email"],
                         cols["phone"], cols["expired"], cols["comment"]))
        self.data = data

dev, prod = sys.argv[1:]
for path in glob.glob("%s/tables/*" % dev):
    name = os.path.basename(path)
    print "{:*^60}".format(" %s " % name)
    try:
        fp = open("%s/tables/%s" % (prod, name))
    except:
        print "-> TABLE NOT ON PROD"
        continue
    classes = { "usr": Usr }
    prod_data = classes.get(name, Table)(fp, name)
    #prod_data = collect_rows(fp, name)[fix(line, name) for line in fp]
    fp.close()
    #dev_data = [fix(line, name) for line in open(path)]
    dev_data = classes.get(name, Table)(open(path), name)
    compare(dev_data, prod_data)

for path in glob.glob("%s/*" % dev):
    doc_type = os.path.basename(path)
    if doc_type != "tables":
        prod_docs = {}
        for doc_path in glob.glob("%s/%s/*.cdr" % (prod, doc_type)):
            doc = eval(open(doc_path).read())
            title = doc[1].lower().strip()
            if title in prod_docs:
                raise Exception("too many %s docs with title %s" % (doc_type,
                                                                    doc[1]))
            prod_docs[title] = doc
        print "loaded %d %s documents from PROD" % (len(prod_docs), doc_type)
        for doc_path in glob.glob("%s/%s/*.cdr" % (dev, doc_type)):
            doc_id, doc_title, doc_xml = eval(open(doc_path).read())
            key = doc_title.lower().strip()
            if key not in prod_docs:
                print "no %s doc with title %s on PROD" % (doc_type, doc_title)
            elif doc_xml != prod_docs[key][2]:
                print "%s document %s changed" % (doc_type, doc_title)
