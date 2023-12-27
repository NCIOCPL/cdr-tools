#!/usr/bin/env python3
# ----------------------------------------------------------------------
# Count the nodes in an XML document, report to standard out.
# ----------------------------------------------------------------------
import argparse
import lxml.etree as etree


class Target(object):
    INDENT = "  "

    def __init__(self, counter):
        self.counter = counter
        self.depth = 0

    def start(self, tag, attrib):
        if self.counter.args.text or self.counter.args.attributes:
            spaces = self.depth * self.INDENT
            print(f"{spaces}{tag}")
        self.depth += 1
        self.counter.elem += 1
        self.counter.total += 1
        self.counter.attr += len(attrib)
        self.counter.total += len(attrib)
        if attrib and self.counter.args.attributes:
            spaces = self.depth * self.INDENT
            for name, val in attrib.items():
                print(f"{spaces}@{name}={val}")

    def end(self, tag):
        self.depth -= 1

    def data(self, data):
        if data.isspace():
            self.counter.space += 1
        else:
            self.counter.text += 1
            if self.counter.args.text:
                spaces = self.depth * self.INDENT
                print(f"{spaces}{data}")
        self.counter.total += 1

    def comment(self, text):
        self.counter.comment += 1
        self.counter.total += 1

    def pi(self, name, val):
        self.counter.pi += 1
        self.counter.total += 1

    def close(self):
        print(f"""
Results:
      Element nodes = {self.counter.elem:d}
    Attribute nodes = {self.counter.attr:d}
         Text nodes = {self.counter.text:d}
   Whitespace nodes = {self.counter.space:d}
      Comment nodes = {self.counter.comment:d}
           PI nodes = {self.counter.pi:d}
     -------------------
          Total = {self.counter.total:d}
""")


class Counter:
    def __init__(self):
        self.elem = self.attr = self.text = self.space = self.comment = 0
        self.pi = self.total = 0
        parser = argparse.ArgumentParser()
        parser.add_argument("--text", "-t", action="store_true",
                            help="show non-space text nodes")
        parser.add_argument("--attributes", "-a", action="store_true",
                            help="show attribute values")
        parser.add_argument("path", type=argparse.FileType("r"),
                            help="path to input file")
        self.args = parser.parse_args()

    def count(self):
        parser = etree.XMLParser(target=Target(self))
        etree.parse(self.args.path, parser)


Counter().count()
