import os
import sys
import math
import tarfile
from datetime import date

instructions = """
To use:
python3 MakeNewRun.py coursefile.tar.gz (run_id) (options)

This script takes an existing course tarball and creates a new one,
named coursefile.new.tar.gz , with hardcoded links, folders, and filenames
updated for the new run.

The run_id will be something like 1T2077.
It defaults to the current quarter and year.

Options:
  -d  Prompt for new dates for start/end of course.
  -h  Print this help message and exit.

Last update: Jan 30th 2021
"""

# Read in the filename

parser = argparse.ArgumentParser(usage=instructions, add_help=False)
parser.add_argument("-h", "--help", action="store_true")
parser.add_argument("-d", "--dates", action="store_true")
parser.add_argument("run", default=None)
parser.add_argument("filename", default="course.tar.gz")

args = parser.parse_args()
if args.help:
    sys.exit(instructions)

# Prompt for start and end dates.
if args.dates:
    start_date = input("Start date (yyyy-mm-dd) = ")
    start_time = input("Start time (24h:min:sec) = ")
    end_date = input("End date (yyyy-mm-dd) = ")
    end_time = input("End time (24h:min:sec) = ")
    course_start = start_date + "T" + start_time + "Z"
    course_end = end_date + "T" + end_time + "Z"

# Use current quarter to set default run identifier.
if args.run is None:
    today = date.today()
    args.run = str(math.ceil(today.month / 3)) + "T" + str(today.year)

if not os.path.exists(args.filename):
    sys.exit("Filename not found: " + args.filename)

# Open the tarball.

# Get the current course_run for future use.

# Change the /course.xml file to point to the new run.

# Rename the courses/course_run.xml file
# Check for optional xml attributes. If they exist...
# Set the start and end dates.

# Rename the policies/course_run folder
# Open policies/course_run/policies.json
# Set the root to "course/current_run"
# Clear any discussion blackouts.
# Set the start and end dates
# Set the xml_attributes:filename

# Find all instances of course_run in XML and HTML files,
# and replace them with the new one.
