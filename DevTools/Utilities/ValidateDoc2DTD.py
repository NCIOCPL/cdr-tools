#!/usr/bin/env python3
# *************************************************************
# File Name:    validateDoc.py
#               --------------
# Script to validate a single document against a DTD.
# By default, the document is being validated against the
# vendor DTD located in d:/cdr/licensee/pdq.dtd
# Alternatively, the path of the DTD can be provided.
#
# Input:  File name of XML document to be validated
#         Optional location of DTD
# *************************************************************
from argparse import ArgumentParser
from cdr import DEFAULT_DTD
from cdrpub import Control
from lxml import etree


def main():
    parser = ArgumentParser()
    parser.add_argument("filename")
    parser.add_argument("--dtd", default=DEFAULT_DTD)
    opts = parser.parse_args()

    # Parse the document file.
    # -----------------------------------------------------------
    root = etree.parse(opts.filename)

    # Validate the file against the DTD.
    # ------------------------------------------------------------
    results = Control.validate_doc(root, opts.dtd)

    # Print the result of the validation
    # ----------------------------------
    print("\nValidation Errors detected")
    print("==========================")
    if len(results.Errors) > 0:
        for error in results.Errors:
            print(error)
    else:
        print("None")
    print()


main()
