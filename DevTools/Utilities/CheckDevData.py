#!/usr/bin/python

import cdrdb, sys, glob, os, cgi, re, lxml.etree as etree, difflib

PROLOG = """\
<!DOCTYPE html>
<html>
 <head>
  <meta charset="utf-8">
  <title>DEV CDR Refresh Report</title>
  <style>
  * { font-family: Arial, sans-serif }
  h1 { color: maroon; font-size: 22pt; }
  h2 { font-size: 20pt; color: green; }
  h3 { background-color: green; color: white; padding: 5px; }
  p.ok { font-size: 16pt; padding-left: 30px; }
  pre.fixed, pre.fixed span { font-family: monospace; font-size: 9pt; }
  </style>
 </head>
 <body>
  <h1>DEV CDR Refresh Report</h1>"""
EPILOG = """\
 </body>
</html>"""

class Table:
    def __init__(self, name, source):
        self.name = name
        self.path = self.cols = self.values = self.map = self.names = None
        if type(source) is str:
            path = "%s/tables/%s" % (source, name)
            self.values = [tuple(eval(row)) for row in open(path)]
            self.cols = self.values.pop(0)
        else:
            source.execute("SELECT * FROM %s" % name)
            self.cols = tuple([col[0] for col in source.description])
            self.values = [tuple(row) for row in source.fetchall()]
        self.rows = [self.row_dict(row) for row in self.values]
        if "name" in self.cols:
            names = [row["name"] for row in self.rows]
            self.names = dict(zip(names, self.rows))
            if "id" in self.cols:
                ids = [row["id"] for row in self.rows]
                self.map = dict(zip(ids, names))
        if name == "query_term_def":
            paths = [row["path"] for row in self.rows]
            self.names = dict(zip(paths, self.rows))
    def row_dict(self, row):
        d = dict(zip(self.cols, row))
        if self.name == "filter_set" and d["notes"] == u"None":
            d["notes"] = u""
        return d

def fix_para(p):
    p = cgi.escape(p).replace("\r", "").replace("\n", "<br>")
    return (u"<pre class='fixed'>%s</pre>" % p).encode("utf-8")

def compare_table(name, old, new):
    items = []
    ot = old.tables[name]
    nt = new.tables[name]
    if set(ot.cols) != set(nt.cols):
        items.append("TABLE STRUCTURE MISMATCH"
                     "<li>old: %s</li><li>new: %s</li></ul>" %
                     (repr(ot.cols), repr(nt.cols)))
    if ot.names:
        for key in sorted(ot.names):
            display = "<b>%s</b>" % cgi.escape(key)
            if key not in nt.names:
                items.append("row for %s lost" % display)
                continue
            old_row = ot.names[key].copy()
            new_row = nt.names[key].copy()
            if "id" in old_row:
                old_row.pop("id")
                new_row.pop("id")
            if old_row != new_row:
                change = ["row for %s changed<ul>" % display]
                for col in old_row:
                    ov = old_row[col]
                    nv = new_row[col]
                    if ov != nv:
                        if name == "query" and col == "value":
                            ov = fix_para(ov)
                            nv = fix_para(nv)
                        else:
                            ov = repr(ov)
                            nv = repr(nv)
                        change.append("<li>'%s' column changed" % col)
                        if col not in ("hashedpw", "password"):
                            change.append("<ul><li>old: %s</li>" % ov)
                            change.append("<li>new: %s</li></ul>" % nv)
                        change.append("</li>")
                change.append("</ul>")
                items.append("".join(change))
    elif name in ("grp_action", "grp_usr"):
        old_rows = [getattr(old, name)(row) for row in ot.rows]
        new_rows = [getattr(new, name)(row) for row in nt.rows]
        for row in sorted(set(old_rows) - set(new_rows)):
            items.append((u"row for %s lost" % row).encode("utf-8"))
    else:
        if name in dir(old):
            old_rows = set([getattr(old, name)(row) for row in ot.rows])
            new_rows = set([getattr(new, name)(row) for row in nt.rows])
        else:
            old_rows = set(ot.rows)
            new_rows = set(nt.rows)
        old_only = [(row, "lost") for row in (old_rows - new_rows)]
        new_only = [(row, "added") for row in (new_rows - old_rows)]
        deltas = old_only + new_only
        for row, which_set in sorted(deltas):
            items.append("%s: %s" % (which_set, row))
    if not items:
        print """<p class="ok">&#x2713;</p>"""
    else:
        print "  <ul>\n   "
        print "\n   ".join(["<li>%s</li>" % i for i in items])
        print "\n  </ul>"

class DocType:
    def __init__(self, name, source):
        self.name = name
        self.docs = {}
        self.map = {}
        if type(source) is str:
            for doc_path in glob.glob("%s/%s/*.cdr" % (source, name)):
                doc = eval(open(doc_path).read())
                key = doc[1].lower().strip()
                if key in self.docs:
                    raise Exception("too many %s docs with title %s" %
                                    (name, doc[1]))
                self.docs[key] = tuple(doc)
                self.map[doc[0]] = doc[1]
        else:
            source.execute("""\
SELECT d.id, d.title, d.xml
  FROM document d
  JOIN doc_type t
    ON t.id = d.doc_type
 WHERE t.name = ?""", name)
            row = cursor.fetchone()
            while row:
                doc_id, doc_title, doc_xml = row
                key = doc_title.lower().strip()
                if key in self.docs:
                    raise Exception("too many %s docs with title %s " 
                                    "in database" % (name, doc_title))
                self.docs[key] = tuple(row)
                self.map[doc_id] = doc_title
                row = cursor.fetchone()

class Data:
    def __init__(self, source, old=None):
        self.tables = {}
        self.docs = {}
        if old:
            for name in old.tables:
                try:
                    self.tables[name] = Table(name, source)
                except:
                    pass
            for name in old.docs:
                self.docs[name] = DocType(name, source)
        else:
            for path in glob.glob("%s/tables/*" % source):
                name = os.path.basename(path)
                self.tables[name] = Table(name, source)
            for path in glob.glob("%s/*" % source):
                doc_type = os.path.basename(path)
                if doc_type != "tables":
                    self.docs[doc_type] = DocType(doc_type, source)

    def filter_set_member(self, row):
        filter_name = subset = None
        if row["filter"]:
            filter_name = self.docs["Filter"].map[row["filter"]].strip()
        if row["subset"]:
            subset = self.tables["filter_set"].map[row["subset"]].strip()
        filter_set = self.tables["filter_set"].map[row["filter_set"]].strip()
        return (filter_set, filter_name, subset, row["position"])

    def grp_action(self, row):
        group = self.tables["grp"].map[row["grp"]]
        action = self.tables["action"].map[row["action"]]
        doc_type = None
        if row["doc_type"]:
            doc_type = self.tables["doc_type"].map[row["doc_type"]]
        return (group, action, doc_type)

    def grp_usr(self, row):
        group = cgi.escape(self.tables["grp"].map[row["grp"]])
        user = cgi.escape(self.tables["usr"].map[row["usr"]])
        return "%s's membership in group %s" % (user, group)

    def link_properties(self, row):
        return (self.tables["link_type"].map[row["link_id"]],
                self.tables["link_prop_type"].map[row["property_id"]],
                row["value"], row["comment"])

    def link_target(self, row):
        return (self.tables["link_type"].map[row["source_link_type"]],
                self.tables["doc_type"].map[row["target_doc_type"]])

    def link_xml(self, row):
        return (self.tables["doc_type"].map[row["doc_type"]],
                row["element"],
                self.tables["link_type"].map[row["link_id"]])

def compare_tables(old, new):
    print "  <h2>Table Comparisons</h2>"
    for name in sorted(old.tables):
        print "  <h3>%s</h3>" % name
        if name in new.tables:
            compare_table(name, old, new)
        else:
            print "  <ul><li><b>TABLE LOST</b></li></ul>"

def fix_xml(x):
    # This didn't work so well for our XSL/T filters, which have lots of
    # attributes which span multiple lines.
    #x = etree.tostring(etree.XML(x.encode("utf-8")), pretty_print=True)
    lines = x.replace("\r", "").splitlines(1)
    return lines

def addColor(line, color):
    return "<span style='background-color: %s'>%s</span>" % (color, line)

def diff_xml(old, new):
    diffObj = difflib.Differ()
    before = fix_xml(old)
    after = fix_xml(new)
    diffSeq = diffObj.compare(before, after)
    lines = []
    changes = False
    for line in diffSeq:
        line = cgi.escape(line)
        if not line.startswith(' '):
            changes = True
        if line.startswith('-'):
            lines.append(addColor(line, '#FAFAD2')) # Light goldenrod yellow
        elif line.startswith('+'):
            lines.append(addColor(line, '#F0E68C')) # Khaki
        elif line.startswith('?'):
            lines.append(addColor(line, '#87CEFA')) # Light sky blue
        #else: # uncomment these lines if you want a *really* wordy report!
        #    lines.append(line)
    if not changes:
        return None
    return "".join(lines)

def compare_docs(old, new):
    print "  <h2>Document Comparisons</h2>"
    for name in sorted(old.docs):
        print "  <h3>%s Docs</h3>" % name
        new_docs = new.docs[name]
        if not new_docs.docs:
            print "  <ul><li><b>DOCUMENT TYPE LOST</b></li></ul>"
        else:
            old_docs = old.docs[name]
            items = []
            for key in old_docs.docs:
                old_id, old_title, old_xml = old_docs.docs[key]
                if key not in new_docs.docs:
                    items.append("<i>%s</i> lost" % cgi.escape(old_title))
                else:
                    diffs = diff_xml(old_xml, new_docs.docs[key][2])
                    if diffs:
                        show = ["<b>%s</b>" % cgi.escape(old_title)]
                        show.append("<pre class='fixed'>%s</pre>" % diffs)
                        items.append("".join(show))
            if not items:
                print "<p class='ok'>&#x2713;</p>"
            else:
                print "  <ul>"
                print "   " + "\n   ".join(["<li>%s</li>" % i for i in items])
                print "  </ul>"

cursor = cdrdb.connect("CdrGuest").cursor()
old = Data(sys.argv[1])
new = Data(cursor, old)
print PROLOG
compare_tables(old, new)
compare_docs(old, new)
print EPILOG
