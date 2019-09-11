#!/usr/bin/env python
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
import cdrpub, sys

def main():
   if len(sys.argv) < 2:
      sys.stderr.write("usage: ValidateDoc2DTD.py filename [DTD]\n")
      sys.stderr.write(" e.g.: ValidateDoc2DTD.py abc.xml d:/cdr/pdq.dtd\n")
      sys.exit(1)

   # Read the file or print error message if file does not exist
   # -----------------------------------------------------------
   try:
      input = open(sys.argv[1], "rb")
      doc   = input.read()
      input.close()
   except:
      print("ERROR in main: Unable to read file %s\n" % sys.argv[1])
      sys.exit(2)

   # print doc

   # If an alternate DTD has been specified validate the document
   # against this.  Otherwise use the default.
   # ------------------------------------------------------------
   if len(sys.argv) < 3:
      x = cdrpub.validateDoc(doc, docId = 0)
   else:
      try:
         dtd = open(sys.argv[2], "rb")
      except:
         print("ERROR in main: Unable to read DTD %s\n" % sys.argv[2])
         sys.exit(3)

      x = cdrpub.validateDoc(doc, docId = 0, dtd = sys.argv[2])

   # Print the result of the validation
   # ----------------------------------
   print("\nValidation Errors detected")
   print("==========================")
   if len(x.Errors) > 0:
      for i in range(len(x.Errors)):
         print("%s" % x.Errors[i])
   else:
         print("None")
   print(" ")


main()
