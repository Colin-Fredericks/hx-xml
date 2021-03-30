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

Last update: March 30th 2021
"""


def edxDateToPython(date_string):
    # date_string is in edx's format: 2030-01-01T00:00:00+00:00
    # split on -, T, :, and +
    # Resulting list is year, month, day, 24hours, minutes,seconds, something something.
    date_list_str = re.split("-|T|:|\+", date_string)
    date_list = [int(x) for x in date_list_str]
    return {
        "date": datetime.date(date_list[0], date_list[1], date_list[2]),
        "time": datetime.time(date_list[3], date_list[4], date_list[5]),
    }


def pythonDateToEdx(pydate, pytime):
    # return will be is in edx's format: 2030-01-01T00:00:00+00:00
    date_list = [
        pydate.year,
        pydate.month,
        pydate.day,
        pytime.hour,
        pytime.minute,
        pytime.second,
    ]

    date_list_str = [str(x) for x in date_list]
    date_list_full = []
    for d in date_list_str:
        date_list_full.append(d if len(d) > 0 else "0" + d)

    date_string = ""
    date_string += date_list_full[0] + "-"
    date_string += date_list_full[1] + "-"
    date_string += date_list_full[2] + "T"
    date_string += date_list_full[3] + ":"
    date_string += date_list_full[4] + ":"
    date_string += date_list_full[5] + "+"
    date_string += "+00:00"

    return date_string


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
new_start_edx = ""
new_end_edx = ""
# TODO: Allow command-line or file-driven entry of dates & times
if use_new_dates:
    start_date = input("Start date (yyyy-mm-dd) = ")
    start_time = input("Start time (24h:min:sec) = ")
    end_date = input("End date (yyyy-mm-dd) = ")
    end_time = input("End time (24h:min:sec) = ")
    new_start_edx = start_date + "T" + start_time + "Z"
    new_end_edx = end_date + "T" + end_time + "Z"
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
# Get the old start date too. We'll need it to update the ORAs later.
run_file = os.path.join(pathname, "course", new_run + ".xml")
tree = ET.parserun_file
root = tree.getroot()
old_start_edx = root.attrib["start"]
root.set("start", new_start)
root.set("end", new_end)

# Items to track for later
course_pacing = (
    "self-paced" if root.attrib["self_paced"] == "true" else "instructor-paced"
)
# Convert old_start_date to a Python datetime object for later manipulation
old_start_py = edxDateToPython(old_start_edx)
date_delta = new_start_py - old_start_py

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

    # TODO: Wipe all the old LTI keys and secrets.

    # Items to handle later
    lti_passports = data["lti_passports"]
    faq_filename = [x["url_slug"] for x in tabs if "FAQ" in x["name"]][0]
    display_name = data["display_name"]


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

# How many chapters have weekly highlights set?
# Open everything in the chapter/ folder
num_highlights = 0
num_chapters = 0
for dirpath, dirnames, filenames in os.walk(os.path.join(pathname, "chapter")):
    for eachfile in filenames:

        # Get the XML for each file
        tree = ET.parse(os.path.join(dirpath, eachfile))
        root = tree.getroot()

        # If there's a highlights attribute set, then there are highlights.
        # If not, then no.
        if root.attrib[highlights]:
            num_highlights += 1

        num_chapters += 1


################################
# Vertical scraping
################################

# Count the number of all the component types in the course.
# Especially need: ORA, LTI, discussion
component_count = {}
# Open everything in the vertical/ folder
for dirpath, dirnames, filenames in os.walk(os.path.join(pathname, "vertical")):
    for eachfile in filenames:

        # Get the XML for each file
        tree = ET.parse(os.path.join(dirpath, eachfile))
        root = tree.getroot()

        # get children and count how many we have
        for child in root:
            if component_count[child.tag]:
                component_count[child.tag] = component_count[child.tag] + 1
            else:
                component_count[child.tag] = 1

        ################################
        # Open Response Assessments
        ################################
        # These are all inline in the verticals (hopefully)
        for child in root:
            if child.tag == "openassessment":
                # TODO: Update ORAs to use flexible grading.

                # Shift deadlines for ORAs to match new start date.
                # Sample XML:
                # <openassessment
                #     url_name="0dbe16d48442412d9df17b43daf32bb8"
                #     submission_start="2001-01-01T00:00:00+00:00"
                #     submission_due="2021-07-13T23:30:00+00:00"
                # >
                #   <assessments>
                #     <assessment name="peer-assessment" must_grade="5" must_be_graded_by="3"
                #       start="2001-01-01T00:00:00+00:00" due="2021-07-21T23:25:00+00:00"
                #     />
                #   </assessments>
                # </openassessment>
                pass


################################
# Video scraping
################################

# Are any videos still pointing to YouTube?
# What % of videos are downloadable?

num_videos = 0
youtube_videos = 0
num_videos = 0
num_downloadable_videos = 0
num_downloadable_transcripts = 0
# Open everything in the video/ folder
for dirpath, dirnames, filenames in os.walk(os.path.join(pathname, "video")):
    for eachfile in filenames:

        # Get the XML for each file
        tree = ET.parse(os.path.join(dirpath, eachfile))
        root = tree.getroot()

        if root.attrib["youtube_id_1_0"]:
            if root.attrib["youtube_id_1_0"] != "":
                youtube_videos += 1
        if root.attrib["download_video"]:
            if root.attrib["download_video"] == "true":
                num_downloadable_videos += 1
        if root.attrib["download_track"]:
            if root.attrib["download_track"] == "true":
                num_downloadable_transcripts += 1

        num_videos += 1

percent_downloadable_vid = num_downloadable_videos / num_videos
percent_downloadable_trans = num_downloadable_transcripts / num_videos


################################
# Problem scraping
################################

# Count the number of problems of each assignment type
# What % of content is gated?
num_problems = 0
num_ungated_problems = 0
num_solutions = 0
problem_types = [
    "choiceresponse",
    "customresponse",
    "optioninput",
    "numericalresponse",
    "multiplechoiceresponse",
    "stringresponse",
    "formularesponse",
]
problem_type_count = {
    "choiceresponse": 0,
    "customresponse": 0,
    "optioninput": 0,
    "numericalresponse": 0,
    "multiplechoiceresponse": 0,
    "stringresponse": 0,
    "formularesponse": 0,
}
problem_type_translator = {
    "choiceresponse": "checkbox",
    "customresponse": "custom input",
    "optioninput": "dropdown",
    "numericalresponse": "numerical",
    "multiplechoiceresponse": "multiple-choice",
    "stringresponse": "text",
    "formularesponse": "math formula",
}

# Open everything in the problem/ folder
for dirpath, dirnames, filenames in os.walk(os.path.join(pathname, "problem")):
    for eachfile in filenames:

        # Get the XML for each file
        tree = ET.parse(os.path.join(dirpath, eachfile))
        root = tree.getroot()

        if root.attrib["group_access"]:
            if root.attrib["group_access"] == "{&quot;51&quot;: [1, 2]}":
                num_ungated_problems += 1

        # Check for specific problem types and count them.
        # They won't be at a reliable depth in the problem XML,
        # So we need to dump the full problem file text to get them.
        problem_text = ET.tostring(tree.getroot(), encoding="utf-8", method="text")
        for t in problem_types:
            if t in problem_text:
                problem_type_count[t] = problem_type_count[t] + 1

        num_problems += 1

################################
# HTML scraping
################################

# For all of these, if so, where?
we_got_trouble = {
    "discussion_links": [],  # Any links to the discussion boards?
    "flash_links": [],  # Any Flash?
    "top_tab_js": [],  # Any javascript that targets the top tabs?
    "iframes": [],  # Any iframes?
}

# Open everything in the html/ folder
for dirpath, dirnames, filenames in os.walk(os.path.join(pathname, "html")):
    html_files = [x for x in filenames if x[-5:] == ".html"]
    for eachfile in html_files:

        with open(eachfile, mode="r") as h:
            # Get the whole-file text so we can search it:
            txt = file.read(h)

            if "<iframe" in txt:
                we_got_trouble["iframe"].append(eachfile)
            if ".swf" in txt:
                we_got_trouble["flash_links"].append(eachfile)
            if "/discusison/forum" in txt:
                we_got_trouble["discussion_links"].append(eachfile)
            if (
                "$('.navbar')" in txt
                or "$('.course-tabs')" in txt
                or "$('.navbar-nav')" in txt
                or '$(".navbar")' in txt  # double OR single quotes
                or '$(".course-tabs")' in txt
                or '$(".navbar-nav")' in txt
            ):
                we_got_trouble["top_tab_js"].append(eachfile)

# Re-tar


################################
# High-level summary
################################

# Create high-level summary of course as takeaway file.
with open(os.path.join(pathname, course_name + "_" + new_run + ".txt"), a) as summary:
    txt = ""
    txt += "Course Summary\n"
    txt += "--------------\n"
    txt += "\n"
    txt += "Identifier: " + display_name + " " + new_run + "\n"
    txt += "New Start: " + new_start + "\n"
    txt += "New End: " + new_end + "\n"
    txt += "Pacing: " + course_pacing + "\n"
    txt += "\n"
    txt += "Number of sections: " + num_chapters + "\n"
    txt += "Highlights set for " + num_highlights + " sections" + "\n"
    txt += "\n"
    txt += "Number of videos: " + num_chapters + "\n"
    txt += "Downloadable videos: " + num_downloadable_videos + "\n"
    txt += "Downloadable transcripts: " + num_downloadable_transcripts + "\n"
    txt += "\n"
    txt += "Number of problems: " + num_problems + "\n"
    txt += "Number of ungated problems: " + num_problems + "\n"

    # Types of problems
    # problem_type_count = {
    #     "choiceresponse": 0,
    #     "customresponse": 0,
    #     "optioninput": 0,
    #     "numericalresponse": 0,
    #     "multiplechoiceresponse": 0,
    #     "stringresponse": 0,
    #     "formularesponse": 0,
    # }

    # Trouble section

    # we_got_trouble = {
    #     "discussion_links": [],  # Any links to the discussion boards?
    #     "flash_links": [],  # Any Flash?
    #     "top_tab_js": [],  # Any javascript that targets the top tabs?
    #     "iframes": [],  # Any iframes?
    # }

    # Summarize LTI tools & keys
    # TODO: better formatting
    txt += lti_passports

    # General maintenance items
    # Number of ORA ("openassessment" tag)
    # How many discussion components are there? ("discussion" tag)

    print(txt)
    summary.write(txt)

# Anything else?

# Post or e-mail this somewhere so we keep a record.
