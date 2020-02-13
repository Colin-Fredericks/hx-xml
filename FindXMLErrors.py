# import XML libraries
import xml.etree.ElementTree as ET
import sys
import os
import argparse

instructions = """
To use:
python3 FindXMLErrors.py path/to/folder -options

Finds problems in XML files (like unmatched tags)
and reports a possible locatino for them.

Options:
  -h   Print this message and exit

Last update: February 13th 2020
"""

parser = argparse.ArgumentParser(usage=instructions, add_help=False)
parser.add_argument("-h", "--help", action="store_true")
parser.add_argument("directory", default=".")

args = parser.parse_args()
if args.help:
    sys.exit(instructions)

if not os.path.exists(args.directory):
    sys.exit("Directory not found: " + args.directory)

numfiles = 0

# Walk through the problems folder
for dirpath, dirnames, filenames in os.walk(args.directory):
    for eachfile in filenames:
        # Get the XML for each file
        try:
            tree = ET.parse(os.path.join(dirpath, eachfile))
            root = tree.getroot()
        except ET.ParseError as e:
            print(eachfile + "  " + str(e))
