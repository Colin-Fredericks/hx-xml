import os
import re
import sys
import json
import math
import shutil
import tarfile
import argparse
import datetime
from statistics import median
from collections import OrderedDict
from xml.etree import ElementTree as ET

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


######################
# Utility Functions
######################


def edxDateToPython(date_string):
    # date_string is in edx's format: 2030-01-01T00:00:00+00:00
    # split on -, T, :, and +
    # Resulting list is year, month, day, 24hours, minutes,seconds, something something.
    date_list_str = re.split("-|T|:|\+", date_string)
    date_list = [int(x.replace('"', "").replace("'", "")) for x in date_list_str]
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
        date_list_full.append(d if len(d) > 1 else "0" + d)

    date_string = ""
    date_string += date_list_full[0] + "-"
    date_string += date_list_full[1] + "-"
    date_string += date_list_full[2] + "T"
    date_string += date_list_full[3] + ":"
    date_string += date_list_full[4] + ":"
    date_string += date_list_full[5] + "+"
    date_string += "00:00"

    return date_string


# Converts from seconds to hh:mm:ss,msec format
# Used to convert video duration
def secondsToHMS(time):
    # Round it to an integer.
    time = int(round(float(time), 0))

    # Downconvert through hours.
    seconds = int(time % 60)
    time -= seconds
    minutes = int((time / 60) % 60)
    time -= minutes * 60
    hours = int((time / 3600) % 24)

    # Make sure we get enough zeroes.
    if int(seconds) == 0:
        seconds = "00"
    elif int(seconds) < 10:
        seconds = "0" + str(seconds)
    if int(minutes) == 0:
        minutes = "00"
    elif int(minutes) < 10:
        minutes = "0" + str(minutes)
    if int(hours) == 0:
        hours = "00"
    elif int(hours) < 10:
        hours = "0" + str(hours)

    # Send back a string
    return str(hours) + ":" + str(minutes) + ":" + str(seconds)


# Space out text to a particular number of characters wide
def spaceOut(s, n, rl="left"):
    while len(s) < n:
        s = s + " " if rl == "left" else " " + s
    return s


#########################
# Command Line Args
#########################


def getCommandLineArgs():

    # Read in the filename and options
    parser = argparse.ArgumentParser(usage=instructions, add_help=False)
    parser.add_argument("filename", default="course.tar.gz")
    parser.add_argument("run", default=None)
    parser.add_argument("-h", "--help", action="store_true")
    parser.add_argument("-d", "--dates", action="store_true")

    ###########################
    # TODO: Handle input from JSON file
    ###########################
    # parser.add_argument("file", action="store")

    args = parser.parse_args()
    if args.help:
        sys.exit(instructions)

    if not os.path.exists(args.filename):
        sys.exit("Filename not found: " + args.filename)
    pathname = os.path.dirname(args.filename)

    # Make a copy of the tarball for backup purposes
    shutil.copy2(args.filename, args.filename[:-7] + "_backup.tar.gz")

    # Extract the tarball.
    tar = tarfile.open(args.filename)
    tar.extractall(pathname)
    tar.close()

    args.root_filename = "course/course.xml"

    return args


#########################
# Dates
#########################


def getDates(use_new_dates):
    # TODO: replace the placeholder values below
    dates = {
        "new_start_py": datetime.date.today(),
        "new_end_py": datetime.date.today(),
        "new_start_edx": "",
        "new_end_edx": "",
    }

    dates["new_start_edx"] = pythonDateToEdx(
        new_start_py, datetime.datetime.now().time()
    )
    dates["new_end_edx"] = pythonDateToEdx(new_end_py, datetime.datetime.now().time())

    # TODO: Allow command-line or file-driven entry of dates & times
    if use_new_dates:
        start_date = input("Start date (yyyy-mm-dd) = ")
        start_time = input("Start time (24h:min:sec) = ")
        end_date = input("End date (yyyy-mm-dd) = ")
        end_time = input("End time (24h:min:sec) = ")
        dates["new_start_edx"] = start_date + "T" + start_time + "Z"
        dates["new_end_edx"] = end_date + "T" + end_time + "Z"

        # Are any of these in the past? Flag that.
        dates["new_start_py"] = edxDateToPython(dates["new_start_edx"])["date"]
        dates["new_end_py"] = edxDateToPython(dates["new_end_edx"])["date"]

    starts_in_past = dates["new_start_py"] < datetime.date.today()
    ends_in_past = dates["new_end_py"] < datetime.date.today()
    if starts_in_past:
        sys.exit("WARNING: Your start date is in the past.")
    if ends_in_past:
        sys.exit("WARNING: Your end date is in the past.")

    return dates


##################################################################################

#########################
# Course base files
#########################


def handleBaseFiles(new_run, dates):
    root_text = ""
    course_name = ""
    course_pacing = ""
    run = {
        "old": "",
        "new": new_run,
        "id": "",
        "old_start_edx": "",
        "pacing": "instructor-paced",
    }

    # Open the course root file
    root_file = os.path.join(pathname, "course", "course", new_run + ".xml")
    rooty_root = ET.parse(run_file)

    # Get course ID
    course_id = rooty_root.attrib.get("course", "unknown")
    # Change the /course.xml file to point to the new run.
    run["old"] = rooty_root.attrib.get("url_name", "unknown")
    rooty_root.set("url_name", run["new"])

    # Close course root.
    tree.write(run_file, encoding="UTF-8", xml_declaration=False)

    # Rename the course/course_run.xml file
    run_file = os.path.join(pathname, "course", "course", run["old"] + ".xml")
    new_runfile = os.path.join(pathname, "course", "course", run["new"] + ".xml")
    os.rename(run_file, new_runfile)

    # Open the course/course_run.xml file.
    tree = ET.parse(new_runfile)
    root = tree.getroot()
    # Set the start and end dates in xml attributes
    root.set("start", dates["new_start_edx"])
    root.set("end", dates["new_end_edx"])
    # Get the old start date too. We'll need it to update the ORAs later.
    run["old_start_edx"] = root.attrib["start"]

    if root.attrib["self_paced"] == "true":
        run["pacing"] = "self-paced"

    # Convert old_start_date to a Python datetime object for later manipulation
    old_start_py = edxDateToPython(old_start_edx)["date"]
    date_delta = new_start_py - old_start_py

    # Write that file, done with it.
    tree.write(run_file, encoding="UTF-8", xml_declaration=False)

    return run


#########################
# Policies folder
##########################


def handlePolicies(run):
    # Rename the policies/course_run folder
    runfolder = os.path.join(pathname, "course", "policies", run["old"])
    newfolder = os.path.join(pathname, "course", "policies", run["new"])
    if os.path.exists(newfolder):
        shutil.rmtree(newfolder)
    os.rename(runfolder, newfolder)

    # TODO: Existence checks for a lot of these.
    # TODO: Blackout dates
    # Open policies/course_run/policy.json
    data = dict()
    with open(
        os.path.join(pathname, "course", "policies", new_run, "policy.json")
    ) as f:
        data = json.load(f)

        # Set the root to "course/new_run"
        data["course/" + new_run] = data["course/" + old_run]
        del data["course/" + old_run]
        # Clear any discussion blackouts.
        data["course/" + new_run]["discussion_blackouts"] = []
        # Set the start and end dates
        data["course/" + new_run]["start"] = new_start_edx
        data["course/" + new_run]["end"] = new_end_edx
        # Set the xml_attributes:filename using new_run
        data["course/" + new_run]["xml_attributes"]["filename"] = ["course/" + new_run]
        # A few other default settings
        data["course/" + new_run]["days_early_for_beta"] = 100.0

        # TODO: Wipe all the old LTI keys and secrets.

        # Items to handle later
        lti_passports = data["course/" + new_run].get("lti_passports", [])

        tabs = [x for x in data["course/" + new_run]["tabs"]]
        faq_search = [x for x in tabs if "FAQ" in x["name"]]
        if len(faq_search) > 0:
            faq_filename = faq_slug[0]["url_slug"]
        display_name = data["course/" + new_run]["display_name"]


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
def scrapeChapters():
    # How many chapters have weekly highlights set?
    # Open everything in the chapter/ folder
    num_highlights = 0
    num_chapters = 0
    for dirpath, dirnames, filenames in os.walk(
        os.path.join(pathname, "course", "chapter")
    ):
        for eachfile in filenames:

            # Get the XML for each file
            tree = ET.parse(os.path.join(dirpath, eachfile))
            root = tree.getroot()

            # If there's a highlights attribute set, then there are highlights.
            # If not, then no.
            if root.attrib.get("highlights", False):
                num_highlights += 1

            num_chapters += 1


################################
# Vertical scraping
################################
def scrapeVerticals():

    # TODO: Add LTI components

    # Count the number of all the component types in the course.
    # Especially need: ORA, LTI, discussion
    component_count = {}
    # Open everything in the vertical/ folder
    for dirpath, dirnames, filenames in os.walk(
        os.path.join(pathname, "course", "vertical")
    ):
        for eachfile in filenames:

            # Get the XML for each file
            tree = ET.parse(os.path.join(dirpath, eachfile))
            root = tree.getroot()

            # get children and count how many we have
            for child in root:
                if component_count.get(child.tag, False):
                    component_count[child.tag] = component_count[child.tag] + 1
                else:
                    component_count[child.tag] = 1

            ################################
            # LTI components - don't forget old tag style
            ################################

            ################################
            # Open Response Assessments
            ################################
            # These are all inline in the verticals (hopefully)
            for child in root:
                if child.tag == "openassessment":
                    # If there are no child elements (sigh), dig into the url_name.

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

    # Alphabetizing
    component_count_sorted = OrderedDict(sorted(component_count.items()))


################################
# Video scraping
################################


def scrapeVideos():
    # Are any videos still pointing to YouTube?
    # What % of videos are downloadable?

    num_videos = 0
    youtube_videos = 0
    num_videos = 0
    num_downloadable_videos = 0
    num_downloadable_transcripts = 0
    video_lengths = []
    # Open everything in the video/ folder
    for dirpath, dirnames, filenames in os.walk(
        os.path.join(pathname, "course", "video")
    ):
        for eachfile in filenames:

            # Get the XML for each file
            tree = ET.parse(os.path.join(dirpath, eachfile))
            root = tree.getroot()

            if root.attrib.get("youtube_id_1_0", False):
                if root.attrib["youtube_id_1_0"] != "":
                    youtube_videos += 1
            if root.attrib.get("download_video", False):
                if root.attrib["download_video"] == "true":
                    num_downloadable_videos += 1
            if root.attrib.get("download_track", False):
                if root.attrib["download_track"] == "true":
                    num_downloadable_transcripts += 1
            if root.attrib["youtube_id_1_0"] != "":
                youtube_videos += 1

            # Getting video durations
            asset_tag = root.find("video_asset")
            if asset_tag is not None:
                if asset_tag.attrib.get("duration", False):
                    video_lengths.append(float(asset_tag.attrib["duration"]))

            num_videos += 1

    percent_downloadable_vid = num_downloadable_videos / num_videos
    percent_downloadable_trans = num_downloadable_transcripts / num_videos

    video_max_length = ""
    video_median_length = ""
    video_min_length = ""
    video_total_length = ""
    if len(video_lengths) > 0:
        video_max_length = secondsToHMS(max(video_lengths))
        video_median_length = secondsToHMS(median(video_lengths))
        video_min_length = secondsToHMS(min(video_lengths))
        video_total_length = secondsToHMS(sum(video_lengths))
    else:
        video_total_length = "Unknown. Course uses old-style video tags."


################################
# Problem scraping
################################


def scrapeProblems():
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

    # For all of these, if so, where?
    we_got_trouble = {
        "discussion_links": [],  # Any links to the discussion boards?
        "flash_links": [],  # Any Flash?
        "top_tab_js": [],  # Any javascript that targets the top tabs?
        "iframes": [],  # Any iframes?
    }

    # Open everything in the problem/ folder
    for dirpath, dirnames, filenames in os.walk(
        os.path.join(pathname, "course", "problem")
    ):
        for eachfile in filenames:

            # Get the XML for each file
            tree = ET.parse(os.path.join(dirpath, eachfile))
            root = tree.getroot()

            if root.attrib.get("group_access", False):
                if root.attrib["group_access"] == "{&quot;51&quot;: [1, 2]}":
                    num_ungated_problems += 1

            # Check for specific problem types and count them.
            # They won't be at a reliable depth in the problem XML,
            # So we need to dump the full problem file text to get them.
            with open(
                os.path.join(pathname, "course", "problem", eachfile), mode="r"
            ) as p:
                # Get the whole-file text so we can search it:
                problem_text = p.read()

                if "/discusison/forum" in problem_text:
                    we_got_trouble["discussion_links"].append("problem/" + eachfile)
                for t in problem_types:
                    if t in problem_text:
                        problem_type_count[t] = problem_type_count[t] + 1

            num_problems += 1


################################
# HTML and Tab Scraping
################################


def scrapePage(file_contents, filename, folder):
    # Get the whole-file text so we can search it:
    txt = file_contents.read()

    if "<iframe" in txt:
        we_got_trouble["iframes"].append(folder + "/" + filename)
    if ".swf" in txt:
        we_got_trouble["flash_links"].append(folder + "/" + filename)
    if "/discusison/forum" in txt:
        we_got_trouble["discussion_links"].append(folder + "/" + filename)
    if (
        "$('.navbar')" in txt
        or "$('.course-tabs')" in txt
        or "$('.navbar-nav')" in txt
        or '$(".navbar")' in txt  # double OR single quotes
        or '$(".course-tabs")' in txt
        or '$(".navbar-nav")' in txt
    ):
        we_got_trouble["top_tab_js"].append(folder + "/" + filename)


def scrapeFolder(folder):
    if folder == "html" or folder == "tabs":
        extension = ".html"
    else:
        extension = ".xml"
    for dirpath, dirnames, filenames in os.walk(
        os.path.join(pathname, "course", folder)
    ):
        html_files = [x for x in filenames if x[-(len(extension)) :] == extension]
        for eachfile in html_files:

            with open(
                os.path.join(pathname, "course", folder, eachfile), mode="r"
            ) as file_contents:
                scrapePage(file_contents, eachfile, folder)


# TODO: Re-tar


################################
# High-level summary
################################


def createSummary():
    # Create high-level summary of course as takeaway file.
    summary_file = os.path.join(pathname, course_name + "_" + new_run + ".txt")
    if os.path.exists(summary_file):
        os.remove(summary_file)
    with open(
        os.path.join(pathname, course_name + "_" + new_run + ".txt"), "a"
    ) as summary:
        txt = ""
        txt += "Course Summary\n"
        txt += "--------------\n"
        txt += "\n"
        txt += "Course name: " + display_name + "\n"
        txt += "Identifier: " + course_id + " " + new_run + "\n"
        txt += "New Start: " + new_start_edx + "\n"
        if starts_in_past:
            print("WARNING: course starts in the past")
        txt += "New End: " + new_end_edx + "\n"
        if ends_in_past:
            print("WARNING: course ends in the past")
        txt += "Pacing: " + course_pacing + "\n"
        txt += "\n"
        txt += "Number of sections: " + str(num_chapters) + "\n"
        txt += "Highlights set for " + str(num_highlights) + " sections" + "\n"
        txt += "\n"
        txt += "Video statistics:\n"
        txt += "  Number of videos: " + str(num_videos) + "\n"
        txt += "  Downloadable videos: " + str(num_downloadable_videos) + "\n"
        txt += "  Downloadable transcripts: " + str(num_downloadable_transcripts) + "\n"
        txt += "  Total duration: " + video_total_length + "\n"
        txt += (
            "  Max: "
            + video_max_length
            + "  Median: "
            + video_median_length
            + "  Min: "
            + video_min_length
            + "\n"
        )
        txt += "\n"
        txt += "Component Count:\n"

        # Types of problems
        for c in component_count_sorted:
            txt += (
                "  "
                + spaceOut(str(component_count_sorted[c]), 4, "right")
                + " "
                + c
                + " components\n"
            )

        txt += "\n"
        txt += "Number of problems: " + str(num_problems) + "\n"
        txt += "Number of ungated problems: " + str(num_problems) + "\n"

        # Types of problems
        for t in problem_type_translator:
            txt += (
                "  "
                + spaceOut(str(problem_type_count[t]), 4, "right")
                + " "
                + problem_type_translator[t]
                + " problems\n"
            )

        # Trouble section
        txt += "\n"
        for troub in we_got_trouble:
            if len(we_got_trouble[troub]) > 0:
                if troub == "discussion_links":
                    txt += "Direct links to discussion boards:\n"
                elif troub == "flash_links":
                    txt += "Links to Flash files (.swf):\n"
                elif troub == "top_tab_js":
                    txt += "Javascript trying to access the top tab bar:\n"
                elif troub == "iframes":
                    txt += "Components with iframes:\n"

                for l in we_got_trouble[troub]:
                    txt += str(l) + "\n"

        # Summarize LTI tools & keys
        txt += "\n"
        if len(lti_passports) > 0:
            txt += "LTI tools:\n"
            for l in lti_passports:
                txt += lti_passports[0] + "\n"
        else:
            txt += "No LTI tools.\n"

        # General maintenance items
        # Number of ORA ("openassessment" tag)
        # How many discussion components are there? ("discussion" tag)

        print(txt)
        summary.write(txt)

    # Anything else?

    # Post or e-mail this somewhere so we keep a record.


#######################
# Main starts here
#######################
def main():

    args = getCommandLineArgs()
    dates = getDates(args.dates)

    lti_passports = []
    faq_filename = ""

    handleBaseFiles(args.run, dates)
    handlePolicies(run)

    scrapeChapters()
    scrapeVerticals()

    scrapeFolder("html")
    scrapeFolder("tabs")
    scrapeFolder("problem")
    scrapeProblems()
    scrapeVideos()

    createSummary(dates)

    createNewTar()


if __name__ == "__main__":
    main()
