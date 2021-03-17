import os
import re
import sys
import math
import shutil
import tarfile
import argparse
from datetime import date

instructions = """
To use:
python3 MakeNewRun.py coursefile.tar.gz run_id (options)

This script takes an existing course tarball and creates a new one,
named coursefile.new.tar.gz , with hardcoded links, folders, and filenames
updated for the new run.

The run_id will be something like 1T2077.

Options:
  -d  Prompt for new dates for start/end of course.
  -h  Print this help message and exit.

Last update: Jan 30th 2021
"""

# Read in the filename and options

parser = argparse.ArgumentParser(usage=instructions, add_help=False)
parser.add_argument("filename", default="course.tar.gz")
parser.add_argument("run", default=None)
parser.add_argument("-h", "--help", action="store_true")
parser.add_argument("-d", "--dates", action="store_true")


args = parser.parse_args()
if args.help:
    sys.exit(instructions)

# Prompt for start and end dates.
use_new_dates = args.dates
if use_new_dates:
    start_date = input("Start date (yyyy-mm-dd) = ")
    start_time = input("Start time (24h:min:sec) = ")
    end_date = input("End date (yyyy-mm-dd) = ")
    end_time = input("End time (24h:min:sec) = ")
    course_start = start_date + "T" + start_time + "Z"
    course_end = end_date + "T" + end_time + "Z"
    # Are any of these in the past? Flag that.

if not os.path.exists(args.filename):
    sys.exit("Filename not found: " + args.filename)
pathname = os.path.dirname(args.filename)

# Make a copy of the tarball for backup purposes
shutil.copy2(args.filename, args.filename[:-7] + "_backup.tar.gz")

# Extract the tarball.
tar = tarfile.open(args.filename)
tar.extractall(pathname)
tar.close()

# Get the old course_run for future use.
root_filename = "course/course.xml"

root_text = ""
old_run = ""

with open(os.path.join(pathname, root_filename), "r") as root_file:
    root_text = root_file.read()

# Change the /course.xml file to point to the new run.
with open(os.path.join(pathname, root_filename), "w") as root_file:
    match_object = re.search('url_name="(.+?)"', root_text)
    old_run = match_object.group(1)
    new_root_text = root_text.replace(old_run, args.run)
    root_file.write(new_root_text)


# Rename the course/course_run.xml file
runfile = os.path.join(pathname, "course", old_run + ".xml")
os.rename(runfile, os.path.join(pathname, args.run + ".xml"))

# Check for optional xml attributes on course/course_run.xml. If they exist...
# Set the start and end dates.

# Rename the policies/course_run folder
# Open policies/course_run/policies.json
# Set the root to "course/current_run"
# Clear any discussion blackouts.
# Set the start and end dates
# Set the xml_attributes:filename using new course_run

# Update ORAs to use flexible grading.
# Shift deadlines for ORAs to match new start date.

# Update "Related Courses" page to use new edX search terms.
# Update the FAQ page.
# Pull new version of hx.js and update

# Find all instances of course_run in XML and HTML files,
# and replace them with the new one.

# Re-tar

# Create high-level summary of course:
# New coure run identifier
# New start date is:
# Instructor vs. self-paced
# N weeks have highlights set
# What percentage of content is gated?
# What percentage of videos and transcripts are not downloadable?
# Summarize LTI tools & keys
# Number of ORA
# Do we still have Flash in this course?
# Do we have javascript that tries to access the top tabs?
# How many discussion components are there?
# Also, list all links to the forums and where they appear in the course.
# Anything else?
# Post or e-mail this somewhere so we keep a record.
