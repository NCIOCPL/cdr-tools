#!/usr/bin/python

import glob
import lxml.etree as etree
import re
import sys
import time

#----------------------------------------------------------------------
# Object representing a transformed clinical trial document.
# The transformation is performed in two parts. The first part
# uses an XSL/T filter to map the elements from NLM's structure
# into the structure used in the CDR. The second part parses the
# text content of each Para element found in the result of the
# first step. An original Para element's text can represent a
# sequence of paragraphs and itemized lists, separated by a blank
# line. Itemized lists start with the sequence:
#       WHITESPACE HYPHEN WHITESPACE
# and each item in the list is marked off by that sequence.
#----------------------------------------------------------------------
class Trial:

    # Class member, used to transform NLM's structure into CDR's.
    transform = etree.XSLT(etree.parse("CDR0000349690.xml"))

    # Transform the document
    def __init__(self, path):

        # Get a parsed tree for the original document
        tree = etree.parse(path)

        # Run the base XSL/T transformation on the document.
        self.doc = self.transform(tree)

        # Find all of the Para elements in the result.
        for para in self.doc.getroot().iter("Para"):

            # Break down the paragraph's formatted text into separate
            # Para and ItemizedList elements.
            elements = Trial.parse_para(para)

            # Leave the Para element alone unless we have replacements.
            if elements:

                # Replace the original Para element with the first
                # of the parsed elements.
                para.getparent().replace(para, elements[0])

                # Append remaining parsed elements as siblings of the first.
                prev = elements[0]
                for next in elements[1:]:
                    prev.addnext(next)
                    prev = next

    @staticmethod
    def parse_para(para):

        # Start with an empty list for the return value.
        elements = []

        # Eliminate carriage return characters introduced on Windows.
        text = para.text.replace(u"\r", "")

        # Don't do anything if the text content is empty.
        if text:

            # Break the incoming text content at blank lines.
            for chunk in re.split(u"\n\n+", text):

                # Lists start with the sequence WHITESPACE HYPHEN WHITESPACE.
                if re.match(r"\s+-\s", chunk):

                    # Assemble the items in the list.
                    items = []

                    # We stick a dummy line at the front to make regex
                    # parsing simpler, then throw that line away (with
                    # the [1:] slice).
                    for item in re.split(r"\n\s+-\s", u"dummy\n" + chunk)[1:]:

                        # Grab the text, strip it, add it to the list.
                        item_text = item.strip()

                        # Skip empty items.
                        if item_text:

                            # Wrap the item in a ListItem element.
                            item_node = etree.Element("ListItem")

                            # Set the text content.
                            item_node.text = item_text

                            # Add the new element to our list of items.
                            items.append(item_node)

                    # If the list has any items, wrap them in an
                    # ItemizedList parent, and tack that onto the return
                    # list.
                    if items:
                        list_node = etree.Element("ItemizedList")
                        for item in items:
                            list_node.append(item)
                        elements.append(list_node)

                else:

                    # This is a paragraph, not a list.
                    para_text = chunk.strip()
                    if para_text:
                        para_node = etree.Element("Para")
                        para_node.text = para_text
                        elements.append(para_node)
        return elements

def main():
    counter = 0
    start = time.time()
    ctrp_dir = len(sys.argv) > 1 and sys.argv[1] or "ctrp"
    for path in glob.glob("%s/*.xml" % ctrp_dir):
        trial = Trial(path)
        counter += 1
    elapsed = time.time() - start
    print("transformed %d trials in %.3f seconds" % (counter, elapsed))

if __name__ == "__main__":
    main()
