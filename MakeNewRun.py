import os
import re
import sys
import json
import math
import shutil
import tarfile
import argparse
from datetime import date
import xml.etree.ElementTree as ET

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

###########################
# ADD TO ARGUMENTS:
# JSON file for command-line arguments, including anything we'd normally prompt for.
###########################

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
new_start = ""
new_end = ""
# TODO: Allow command-line or file-driven entry of dates & times
if use_new_dates:
    start_date = input("Start date (yyyy-mm-dd) = ")
    start_time = input("Start time (24h:min:sec) = ")
    end_date = input("End date (yyyy-mm-dd) = ")
    end_time = input("End time (24h:min:sec) = ")
    new_start = start_date + "T" + start_time + "Z"
    new_end = end_date + "T" + end_time + "Z"
    # TODO: Are any of these in the past? Flag that.

if not os.path.exists(args.filename):
    sys.exit("Filename not found: " + args.filename)
pathname = os.path.dirname(args.filename)

# Make a copy of the tarball for backup purposes
shutil.copy2(args.filename, args.filename[:-7] + "_backup.tar.gz")

# Extract the tarball.
tar = tarfile.open(args.filename)
tar.extractall(pathname)
tar.close()

root_filename = "course/course.xml"
root_text = ""

old_run = ""
new_run = args.run
lti_passports = []
faq_filename = ""
course_name = ""
course_pacing = ""

#########################
# Course base files
#########################

# Change the /course.xml file to point to the new run.
# Open to read
with open(os.path.join(pathname, root_filename), "r") as root_file:
    root_text = root_file.read()

# Open to write
with open(os.path.join(pathname, root_filename), "w") as root_file:
    match_object = re.search('url_name="(.+?)"', root_text)
    old_run = match_object.group(1)
    new_root_text = root_text.replace(old_run, new_run)
    root_file.write(new_root_text)

    # And save the course name for later.
    match_object = re.search('course="(.+?)"', root_text)
    course_name = match_object.group(1)

# Rename the course/course_run.xml file
runfile = os.path.join(pathname, "course", old_run + ".xml")
os.rename(runfile, os.path.join(pathname, new_run + ".xml"))

# Set the start and end dates in xml attributes on course/course_run.xml
run_file = os.path.join(pathname, "course", new_run + ".xml")
tree = ET.parserun_file
root = tree.getroot()
root.set("start", new_start)
root.set("end", new_end)

# Items to track for later:
course_pacing = (
    "self-paced" if root.attrib["self_paced"] == "true" else "instructor-paced"
)

# Write that file, done with it.
tree.write(run_file, encoding="UTF-8", xml_declaration=False)


#########################
# Policies folder
##########################

# Rename the policies/course_run folder
runfolder = os.path.join(pathname, "policies", old_run)
os.rename(runfolder, os.path.join(pathname, "policies", new_run))

# TODO: Existence checks for a lot of these.
# Open policies/course_run/policy.json
data = dict()
with open(os.path.join(pathname, "policies", new_run, "policy.json")) as f:
    data = json.load(f)

    # Set the root to "course/new_run"
    data["course/" + new_run] = data["course/" + old_run]
    del data["course/" + old_run]
    # Clear any discussion blackouts.
    data["course/" + new_run]["discussion_blackouts"] = []
    # Set the start and end dates
    data["course/" + new_run]["start"] = new_start
    data["course/" + new_run]["end"] = new_end
    # Set the xml_attributes:filename using new_run
    data["xml_attributes"]["filename"] = ["course/" + new_run]
    # A few other default settings
    data["days_early_for_beta"] = 100.0

    # Items to handle later
    lti_passports = data["lti_passports"]
    faq_filename = [x["url_slug"] for x in tabs if "FAQ" in x["name"]][0]
    display_name = data["display_name"]


################################
# Open Response Assessments
################################

# Update ORAs to use flexible grading.
# Shift deadlines for ORAs to match new start date.

################################
# Boilerplate Updates
################################

# Update "Related Courses" page to use new edX search terms.
# Update the FAQ page.
# Pull new version of hx.js and update

# Find all instances of course_run in XML and HTML files,
# and replace them with the new one.

################################
# Chapter scraping
################################

# Open everything in the chapter/ folder
# How many chapters have weekly highlights set?

################################
# Vertical scraping
################################

# Open everything in the vertical/ folder
# Count the number of all the component types in the course.
# Especially need: ORA, LTI, discussion

################################
# Video scraping
################################

# Open everything in the video/ folder
# Are any videos still pointing to YouTube?
# What % of videos are downloadable?

################################
# Problem scraping
################################

# Open everything in the problem/ folder
# Count the number of problems of each assignment type
# What % of content is gated?

################################
# HTML scraping
################################

# Open everything in the html/ folder
# How many iframes?
# Any Flash?
# Any javascript that targets the top tabs?
# Any links to the discussion boards?
# For all of these, if so, where?


# Re-tar

################################
# High-level summary
################################

# Create high-level summary of course as takeaway file.
with open(os.path.join(pathname, course_name + "_" + new_run + ".txt"), a) as summary:
    txt = ""
    txt += "Course Summary\n--------------\n\n"
    txt += "Identifier: " + display_name + " " + new_run + "\n"
    txt += "New Start: " + new_start
    txt += "New End: " + new_end
    txt += "Pacing: " + course_pacing

    # N weeks have highlights set
    # What percentage of content is gated?
    # What percentage of videos and transcripts are not downloadable?

    # Summarize LTI tools & keys
    # TODO: better formatting
    txt += lti_passports

    # Number of ORA
    # Do we still have Flash in this course?
    # Do we have javascript that tries to access the top tabs?
    # How many discussion components are there?
    # Also, list all links to the forums and where they appear in the course.

    print(txt)
    summary.write(txt)

# Anything else?

# Post or e-mail this somewhere so we keep a record.
