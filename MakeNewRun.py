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
# All the things we need to track
#########################
def setUpDetails(args):
    details = {
        # For all of these, if so, where?
        "trouble": {
            "discussion_links": [],  # Any links to the discussion boards?
            "flash_links": [],  # Any Flash?
            "top_tab_js": [],  # Any javascript that targets the top tabs?
            "iframes": [],  # Any iframes?
        },
        "run": {
            "old": "",
            "new": args.run,
            "id": "",
            "old_start_edx": "",
            "pacing": "instructor-paced",
            "course_name": "",
            "pathname": os.path.dirname(args.filename),
            "lti_passports": [],
            "display_name": "",
        },
        # TODO: replace the placeholder values below
        "dates": {
            "new_start_py": datetime.date.today(),
            "new_end_py": datetime.date.today(),
            "new_start_edx": "",
            "new_end_edx": "",
            "old_start_edx": "",
            "old_end_edx": "",
            "date_delta": "",
        },
        "chapters": {"num_chapters": 0, "num_highlights": 0},
        "verticals": {"component_count": OrderedDict()},
        "problems": {
            "total": 0,
            "ungated": 0,
            "choiceresponse": 0,
            "customresponse": 0,
            "optioninput": 0,
            "numericalresponse": 0,
            "multiplechoiceresponse": 0,
            "stringresponse": 0,
            "formularesponse": 0,
        },
        "videos": {
            "num_videos": 0,
            "youtube_videos": 0,
            "num_videos": 0,
            "num_downloadable_videos": 0,
            "num_downloadable_transcripts": 0,
            "lengths": [],
            "max_length": "",
            "median_length": "",
            "min_length": "",
            "total_length": "",
        },
    }
    return details


# Updating the trouble or run data appropriately
def updateDetails(new_info, category, details):
    # "level 1" here is the category string.
    # TODO: This was written like shit. Rewrite the whole thing.
    for level2 in details[category]:
        for item in new_info:
            if level2 == item:
                if type(details[category][level2]) == list:
                    for element in item:
                        details[category][level2].append(element)
                elif type(details[category][level2]) == int:
                    details[category][level2] += new_info[level2]
                else:
                    details[category][level2] = new_info[level2]
    return details


#########################
# Command Line Args
#########################
def getCommandLineArgs(args):

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
    args.pathname = os.path.dirname(args.filename)

    args.root_filename = "course/course.xml"

    return args


#########################
# Dates
#########################
def getDates(args, details):
    use_new_dates = args.dates
    dates = details["dates"]

    dates["new_start_edx"] = pythonDateToEdx(
        dates["new_start_py"], datetime.datetime.now().time()
    )
    dates["new_end_edx"] = pythonDateToEdx(
        dates["new_end_py"], datetime.datetime.now().time()
    )

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

    details = updateDetails(dates, "dates", details)
    return details


#########################
# TODO: Update FAQ file
#########################
def updateFAQ(filename):
    pass


#########################
# TODO: Update Related Course file
#########################
def updateRelated(filename):
    pass


#########################
# Course base files
#########################
def handleBaseFiles(details):
    run = details["run"]
    pathname = run["pathname"]
    date = details["dates"]

    # Open the course root file
    root_file = os.path.join(pathname, "course", "course.xml")
    root_tree = ET.parse(root_file)
    root_root = root_tree.getroot()

    # Get course ID
    course_id = root_root.attrib.get("course", "unknown")
    # Change the /course.xml file to point to the new run.
    run["old"] = root_root.attrib.get("url_name", "unknown")
    root_root.set("url_name", run["new"])

    # Close course root.
    root_tree.write(root_file, encoding="UTF-8", xml_declaration=False)

    # Rename the course/course_run.xml file
    run_file = os.path.join(pathname, "course", "course", run["old"] + ".xml")
    new_runfile = os.path.join(pathname, "course", "course", run["new"] + ".xml")
    os.rename(run_file, new_runfile)

    # Open the course/course_run.xml file.
    tree = ET.parse(new_runfile)
    root = tree.getroot()
    # Get the old start date. We'll need it to update the ORAs later.
    date["old_start_edx"] = root.attrib["start"]
    # Set the start and end dates in xml attributes
    root.set("start", date["new_start_edx"])
    root.set("end", date["new_end_edx"])

    if root.attrib["self_paced"] == "true":
        run["pacing"] = "self-paced"

    # Write that file, done with it.
    tree.write(run_file, encoding="UTF-8", xml_declaration=False)

    # Convert old_start_date to a Python datetime object for later manipulation
    date["old_start_py"] = edxDateToPython(date["old_start_edx"])["date"]
    date["date_delta"] = date["new_start_py"] - date["old_start_py"]

    details = updateDetails(run, "run", details)
    details = updateDetails(date, "dates", details)
    return details


#########################
# Policies folder
##########################
def handlePolicies(details):
    run = details["run"]
    dates = details["dates"]
    pathname = run["pathname"]
    runpath = "course/" + run["new"]

    # Rename the policies/course_run folder
    runfolder = os.path.join(pathname, "course", "policies", run["old"])
    newfolder = os.path.join(pathname, "course", "policies", run["new"])
    if os.path.exists(newfolder):
        shutil.rmtree(newfolder)
    os.rename(runfolder, newfolder)

    # Open policies/course_run/policy.json
    data = dict()
    with open(
        os.path.join(pathname, "course", "policies", run["new"], "policy.json")
    ) as f:
        data = json.load(f)

        # Set the root to "course/new_run"
        data[runpath] = data["course/" + run["old"]]
        del data["course/" + run["old"]]
        # Clear any discussion blackouts.
        data[runpath]["discussion_blackouts"] = []
        # Set the start and end dates
        data[runpath]["start"] = dates["new_start_edx"]
        data[runpath]["end"] = dates["new_end_edx"]
        # Set the xml_attributes:filename using new_run
        data[runpath]["xml_attributes"]["filename"] = [runpath]
        # A few other default settings
        data[runpath]["days_early_for_beta"] = 100.0

        # Items to handle later
        run["lti_passports"] = data[runpath].get("lti_passports", [])
        run["display_name"] = data[runpath]["display_name"]

        # Update some standard tabs
        tabs = [x for x in data[runpath]["tabs"]]
        faq_search = [x for x in tabs if "FAQ" in x["name"]]
        if len(faq_search) > 0:
            updateFAQ(faq_search[0]["url_slug"])
        related_search = [x for x in tabs if "Related Courses" in x["name"]]
        if len(related_search) > 0:
            updateRelated(related_search[0]["related_search"])

    details = updateDetails(run, "run", details)
    return details


################################
# Boilerplate Updates
################################

# Update "Related Courses" page to use new edX search terms.
# Update the FAQ page.
# Pull new version of hx.js and update


################################
# Chapter scraping
################################
def scrapeChapters(details):
    # How many chapters have weekly highlights set?
    # Open everything in the chapter/ folder
    chapters = {"num_chapters": 0, "num_highlights": 0}
    for dirpath, dirnames, filenames in os.walk(
        os.path.join(details["run"]["pathname"], "course", "chapter")
    ):
        for eachfile in filenames:

            # Get the XML for each file
            tree = ET.parse(os.path.join(dirpath, eachfile))
            root = tree.getroot()

            # If there's a highlights attribute set, then there are highlights.
            # If not, then no.
            if root.attrib.get("highlights", False):
                chapters["num_highlights"] += 1

            chapters["num_chapters"] += 1

    details = updateDetails(chapters, "chapters", details)
    return details


################################
# Vertical scraping
################################
def scrapeVerticals(details):

    # TODO: Add LTI components

    # Count the number of all the component types in the course.
    # Especially need: ORA, LTI, discussion
    component_count = {}
    # Open everything in the vertical/ folder
    for dirpath, dirnames, filenames in os.walk(
        os.path.join(details["run"]["pathname"], "course", "vertical")
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
    verticals = {"component_count": component_count_sorted}

    details = updateDetails(verticals, "verticals", details)
    return details


################################
# Video scraping
################################
def scrapeVideos(details):
    # Are any videos still pointing to YouTube?
    # What % of videos are downloadable?

    videos = {
        "num_videos": 0,
        "youtube_videos": 0,
        "num_videos": 0,
        "num_downloadable_videos": 0,
        "num_downloadable_transcripts": 0,
        "lengths": [],
        "max_length": "",
        "median_length": "",
        "min_length": "",
        "total_length": "",
    }
    # Open everything in the video/ folder
    for dirpath, dirnames, filenames in os.walk(
        os.path.join(details["run"]["pathname"], "course", "video")
    ):
        for eachfile in filenames:

            # Get the XML for each file
            tree = ET.parse(os.path.join(dirpath, eachfile))
            root = tree.getroot()

            if root.attrib.get("youtube_id_1_0", False):
                if root.attrib["youtube_id_1_0"] != "":
                    videos["youtube_videos"] += 1
            if root.attrib.get("download_video", False):
                if root.attrib["download_video"] == "true":
                    videos["num_downloadable_videos"] += 1
            if root.attrib.get("download_track", False):
                if root.attrib["download_track"] == "true":
                    videos["num_downloadable_transcripts"] += 1

            # Getting video durations
            asset_tag = root.find("video_asset")
            if asset_tag is not None:
                if asset_tag.attrib.get("duration", False):
                    videos["lengths"].append(float(asset_tag.attrib["duration"]))

            videos["num_videos"] += 1

    if len(videos["lengths"]) > 0:
        videos["max_length"] = secondsToHMS(max(videos["lengths"]))
        videos["median_length"] = secondsToHMS(median(videos["lengths"]))
        videos["min_length"] = secondsToHMS(min(videos["lengths"]))
        videos["total_length"] = secondsToHMS(sum(videos["lengths"]))
    else:
        videos["total_length"] = "Unknown. Course uses old-style video tags."

    details = updateDetails(videos, "videos", details)
    return details


################################
# Problem scraping
################################
def scrapeProblems(details):
    # Count the number of problems of each assignment type
    # What % of content is gated?
    problems = {"total": 0, "ungated": 0, "solutions": 0}
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
    trouble = {}

    # Open everything in the problem/ folder
    for dirpath, dirnames, filenames in os.walk(
        os.path.join(details["run"]["pathname"], "course", "problem")
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
                os.path.join(details["run"]["pathname"], "course", "problem", eachfile),
                mode="r",
            ) as p:
                # Get the whole-file text so we can search it.
                problem_text = p.read()

                if "/discusison/forum" in problem_text:
                    trouble["discussion_links"].append("problem/" + eachfile)
                # TODO: Can we replace this with a ET.find() command?
                if "<solution" in problem_text:
                    problems["solutions"] += 1
                # TODO: Can we replace this with a ET.find() command?
                for t in problem_types:
                    if t in problem_text:
                        problem_type_count[t] = problem_type_count[t] + 1

            num_problems += 1

    details = updateDetails(problem_type_count, "problems", details)
    details = updateDetails(trouble, "trouble", details)
    return details


################################
# HTML and Tab Scraping
################################
def scrapePage(file_contents, filename, folder, details):
    trouble = {}
    run = details["run"]

    # Get the whole-file text so we can search it:
    txt = file_contents.read()

    if "<iframe" in txt:
        trouble["iframes"].append(folder + "/" + filename)
    if ".swf" in txt:
        trouble["flash_links"].append(folder + "/" + filename)
    if "/discusison/forum" in txt:
        trouble["discussion_links"].append(folder + "/" + filename)
    if (
        "$('.navbar')" in txt
        or "$('.course-tabs')" in txt
        or "$('.navbar-nav')" in txt
        or '$(".navbar")' in txt  # double OR single quotes
        or '$(".course-tabs")' in txt
        or '$(".navbar-nav")' in txt
    ):
        trouble["top_tab_js"].append(folder + "/" + filename)

    # TODO: Update static links
    # Find all instances of course_run in XML and HTML files,
    # and replace them with the new one.

    details = updateDetails(trouble, "trouble", details)
    return details


def scrapeFolder(folder, details):
    pathname = details["run"]["pathname"]
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
                return scrapePage(file_contents, eachfile, folder, details)


# TODO: Re-tar


################################
# High-level summary
################################
def createSummary(details):
    run = details["run"]
    dates = details["dates"]
    videos = details["videos"]
    component_count = details["verticals"]["component_count"]

    # Create high-level summary of course as takeaway file.
    summary_file = os.path.join(run["pathname"], course_name + "_" + new_run + ".txt")
    if os.path.exists(summary_file):
        os.remove(summary_file)
    with open(
        os.path.join(run["pathname"], course_name + "_" + new_run + ".txt"), "a"
    ) as summary:
        txt = ""
        txt += "Course Summary\n"
        txt += "--------------\n"
        txt += "\n"
        txt += "Course name: " + display_name + "\n"
        txt += "Identifier: " + run["id"] + " " + run["new"] + "\n"
        txt += "New Start: " + dates["new_start_edx"] + "\n"
        if starts_in_past:
            print("WARNING: course starts in the past")
        txt += "New End: " + dates["new_end_edx"] + "\n"
        if ends_in_past:
            print("WARNING: course ends in the past")
        txt += "Pacing: " + run["pacing"] + "\n"
        txt += "\n"
        txt += "Number of sections: " + str(num_chapters) + "\n"
        txt += "Highlights set for " + str(num_highlights) + " sections" + "\n"
        txt += "\n"
        txt += "Video statistics:\n"
        txt += "  Number of videos: " + str(videos["num_videos"]) + "\n"
        txt += "  Downloadable videos: " + str(videos["num_downloadable_videos"]) + "\n"
        txt += (
            "  Downloadable transcripts: "
            + str(videos["num_downloadable_transcripts"])
            + "\n"
        )
        txt += "  Total duration: " + videos["total_length"] + "\n"
        txt += (
            "  Max: "
            + videos["max_length"]
            + "  Median: "
            + videos["median_length"]
            + "  Min: "
            + videos["min_length"]
            + "\n"
        )
        txt += "\n"
        txt += "Component Count:\n"

        # Types of problems
        for c in component_count:
            txt += (
                "  "
                + spaceOut(str(component_count[c]), 4, "right")
                + " "
                + c
                + " components\n"
            )

        txt += "\n"
        txt += "Number of problems: " + str(num_problems) + "\n"
        txt += "Number of ungated problems: " + str(num_ungated_problems) + "\n"

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
        for troub in trouble:
            if len(trouble[troub]) > 0:
                if troub == "discussion_links":
                    txt += "Direct links to discussion boards:\n"
                elif troub == "flash_links":
                    txt += "Links to Flash files (.swf):\n"
                elif troub == "top_tab_js":
                    txt += "Javascript trying to access the top tab bar:\n"
                elif troub == "iframes":
                    txt += "Components with iframes:\n"

                for l in trouble[troub]:
                    txt += str(l) + "\n"

        # Summarize LTI tools & keys
        txt += "\n"
        if len(lti_passports) > 0:
            txt += "LTI tools:\n"
            for l in lti_passports:
                txt += lti_passports[0] + "\n"
        else:
            txt += "No LTI tools.\n"

        txt += "\n"
        txt += "Discussion blackout dates removed."

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

    args = getCommandLineArgs(sys.argv)

    # Make a copy of the tarball for backup purposes
    shutil.copy2(args.filename, args.filename[:-7] + "_backup.tar.gz")

    # Extract the tarball.
    tar = tarfile.open(args.filename)
    tar.extractall(args.pathname)
    tar.close()

    details = setUpDetails(args)
    details = getDates(args, details)

    lti_passports = []
    faq_filename = ""

    details = handleBaseFiles(details)
    details = handlePolicies(details)

    details = scrapeChapters(details)
    details = scrapeVerticals(details)

    details = scrapeFolder("html", details)
    details = scrapeFolder("tabs", details)
    details = scrapeFolder("problem", details)
    details = scrapeProblems(details)
    details = scrapeVideos(details)

    createSummary(details)

    createNewTar()


if __name__ == "__main__":
    main()
