import os
import re
import sys
import json
import random
import shutil
import tarfile
import argparse
import datetime
from statistics import median
from collections import OrderedDict
from xml.etree import ElementTree as ET

instructions = """
To use:
python3 MakeNewRun.py coursefile.tar.gz (options)

This script takes an existing course tarball and creates a new one,
named coursefile.new.tar.gz , with hardcoded links, folders, and filenames
updated for the new run. Automatically prompts for new date and run, but
you can feed it a file with -f below.

Auto-copies files from script_directory/file_replacements/ into
the /static/ folder, overwriting any existing versions.

Options:
  -f  Specify a JSON settings file using -f=filename. Overrides other flags.
  -h  Print this help message and exit.

Last update: Feb 22nd, 2022
"""

######################
# Utility Functions
######################
def findDictInList(lst, key, value):
    for i, dic in enumerate(lst):
        try:
            if dic[key] == value:
                return i
        except KeyError:
            pass
    return -1


# 32-character randomized hexadecimal
def getNewEdxFilename():
    f = ""
    for x in range(0, 32):
        f = f + (hex(random.randint(0, 15))[2])
    return f


def edxDateToPython(date_string):
    # date_string is in edx's format: 2030-01-01T00:00:00+00:00
    # sometimes ends with a Z instead of +whatever
    # split on -, T, :, Z, and +
    # Resulting list is year, month, day, 24hours, minutes, seconds, something something.
    date_list_str = re.split("-|/|T|:|\+|Z", date_string)
    date_list = [
        int(x.replace('"', "").replace("'", "")) for x in date_list_str if len(x) > 0
    ]
    return datetime.datetime(
        date_list[0],
        date_list[1],
        date_list[2],
        date_list[3],
        date_list[4],
        date_list[5],
    )


def pythonDateToEdx(moment):
    # return will be is in edx's format: 2030-01-01T00:00:00+00:00
    date_string = ""
    date_string += str(moment.year) + "-"
    date_string += str(moment.month) + "-"
    date_string += str(moment.day) + "T"
    date_string += str(moment.hour) + ":"
    date_string += str(moment.minute) + ":"
    date_string += str(moment.second) + "+"
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
            "youtube_links": [],  # Links or iframes that point to YouTube
            "no_solution": [],  # Problems without written explanations
            "js_files": [],  # A list of all javascript files in /static/
            "replaced_files": [],  # A list of all the files we auto-replaced.
        },
        "run": {
            "old": "",
            "new": args.run,
            "id": "",
            "old_start_edx": "",
            "pacing": "instructor-paced",
            "course_nickname": "",
            "pathname": os.path.dirname(args.tarfile),
            "lti_passports": [],
            "display_name": "",
            "faq_page": "",
            "related_courses_page": "",
        },
        # Note the placeholder values: Course starts today, ends a year from today.
        "dates": {
            "new_start_py": edxDateToPython(args.start),
            "new_end_py": edxDateToPython(args.end),
            "new_start_edx": args.start,
            "new_end_edx": args.end,
            "old_start_edx": "",
            "old_end_edx": "",
            "date_delta": "",
        },
        "chapters": {"num_chapters": 0, "num_highlights": 0},
        "verticals": {"component_count": OrderedDict()},
        "problems": {
            "total": 0,
            "ungated": 0,
            "solutions": 0,
            "choiceresponse": 0,
            "customresponse": 0,
            "optionresponse": 0,
            "numericalresponse": 0,
            "multiplechoiceresponse": 0,
            "stringresponse": 0,
            "formularesponse": 0,
            "compound": 0,
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


#########################
# Updating the details object
# We append to lists, add to integers, and replace everything else.
#########################
def updateDetails(new_info, category, details):
    # "level 1" here is the category string.
    for level2 in details[category]:
        for item in new_info:
            if level2 == item:
                if type(details[category][level2]) == list:
                    for element in new_info[item]:
                        details[category][level2].append(element)
                        details[category][level2] = list(set(details[category][level2]))
                elif type(details[category][level2]) == int:
                    details[category][level2] += new_info[level2]
                else:
                    details[category][level2] = new_info[level2]

    return details


#########################
# Update FAQ file and maybe other tabs
#########################


def updateTabs(details):
    run = details["run"]

    # Get the data from the policy.json file for this course.
    data = dict()
    policy_file = os.path.join(
        run["pathname"], "course", "policies", run["new"], "policy.json"
    )
    with open(policy_file, "r") as policy:
        data = json.load(policy)

    faq_text = """
<p>Course leads: Insert a link to your custom FAQ page below.</p>

<iframe title="Frequently Asked Questions" style="width:100%; height:800px; overflow-y:scroll;" src="FAQ link goes here">
</iframe>

<p>If you can't see the question list above, click this link to <a href="FAQ link goes here" target="_blank">open the FAQ in a new window</a>.</p>
"""

    new_faq_filename = "faq.html"
    new_faq_file = os.path.join(run["pathname"], "course", "tabs", new_faq_filename)
    new_faq_exists = os.path.exists(new_faq_file)

    bak_faq_filename = "faq_backup.html"
    bak_faq_file = os.path.join(run["pathname"], "course", "tabs", bak_faq_filename)
    bak_faq_exists = os.path.exists(bak_faq_file)

    # Is there already a tab that's *probably* the FAQ?
    old_faq_exists = False
    runpath = "course/" + run["new"]
    if not new_faq_exists and not bak_faq_exists:
        tabs = [x for x in data[runpath]["tabs"]]
        faq_search = [x for x in tabs if "faq" in x["name"].lower()]
        if len(faq_search) > 0:
            old_faq_filename = faq_search[0]["url_slug"]
            old_faq_file = os.path.join(
                run["pathname"], "course", "tabs", old_faq_filename
            )
            old_faq_exists = os.path.exists(old_faq_file)
            old_faq_tab = {
                "course_staff_only": True,
                "name": "Old FAQ file",
                "type": "static_tab",
                "url_slug": old_faq_filename,
            }

    new_faq_tab = {
        "course_staff_only": False,
        "name": "FAQ",
        "type": "static_tab",
        "url_slug": new_faq_filename[:-5],
    }
    bak_faq_tab = {
        "course_staff_only": True,
        "name": "FAQ Backup",
        "type": "static_tab",
        "url_slug": bak_faq_filename[:-5],
    }

    # If there's a faq.html file, make a backup copy of that.
    # If not but there's an older faq file with long filename, use that as the backup.
    # Regardless, make the current FAQ page a link to our iframed page.
    run["faq_page"] = "added"
    if new_faq_exists:
        shutil.move(new_faq_file, bak_faq_file)
        run["faq_page"] = "updated"
    elif old_faq_exists:
        shutil.move(old_faq_file, bak_faq_file)
        run["faq_page"] = "updated"
    with open(new_faq_file, "w") as f:
        f.write(faq_text)

    # If we need to add the new and backup faqs to the policy file, do that here.
    has_new_faq = (
        findDictInList(data[runpath]["tabs"], "url_slug", new_faq_filename[:-5]) > -1
    )
    has_backup_faq = (
        findDictInList(data[runpath]["tabs"], "url_slug", bak_faq_filename[:-5]) > -1
    )

    if not has_new_faq:
        data[runpath]["tabs"].append(new_faq_tab)
    if not has_backup_faq:
        data[runpath]["tabs"].append(bak_faq_tab)
        with open(bak_faq_file, "w") as f:
            f.write(faq_text)
    # No need to add tab for old FAQ; that's where we found it in the first place.
    # Just change the visibility.
    if old_faq_exists:
        index = findDictInList(data[runpath]["tabs"], "url_slug", old_faq_filename)
        data[runpath]["tabs"][index]["course_staff_only"] = False
        run["faq_page"] = "updated"

    # Write the policy file and close.
    with open(policy_file, "w") as policy:
        policy.write(json.dumps(data, indent=4))

    details = updateDetails(run, "run", details)
    return details


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
    run["course_nickname"] = root_root.attrib.get("course", "unknown")
    root_root.set("url_name", run["new"])

    # Close and write course root.
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

    if root.attrib.get("self_paced", False) == "true":
        run["pacing"] = "self-paced"

    # Write that file, done with it.
    tree.write(run_file, encoding="UTF-8", xml_declaration=False)

    # Convert old_start_date to a Python datetime object for later manipulation
    date["old_start_py"] = edxDateToPython(date["old_start_edx"])
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
    if run["new"] != run["old"]:
        oldfolder = os.path.join(pathname, "course", "policies", run["old"])
        newfolder = os.path.join(pathname, "course", "policies", run["new"])
        if os.path.exists(newfolder):
            shutil.rmtree(newfolder)
        if os.path.exists(oldfolder):
            os.rename(oldfolder, newfolder)
        else:
            sys.exit("Cannot find policies/" + run["old"] + " folder.")

    # Open policies/course_run/policy.json
    data = dict()
    with open(
        os.path.join(pathname, "course", "policies", run["new"], "policy.json")
    ) as policy_file:
        data = json.load(policy_file)

        # Set the root to "course/new_run"
        if run["new"] != run["old"]:
            data["course/" + run["new"]] = data["course/" + run["old"]]
            del data["course/" + run["old"]]

        # Clear any discussion blackouts.
        data[runpath]["discussion_blackouts"] = []
        # Set the start and end dates
        data[runpath]["start"] = dates["new_start_edx"]
        data[runpath]["end"] = dates["new_end_edx"]
        # Set the xml_attributes:filename using new_run
        data[runpath]["filename"] = runpath
        # A few other default settings
        data[runpath]["days_early_for_beta"] = 100.0

        # Items to handle later
        run["lti_passports"] = data[runpath].get("lti_passports", [])
        # print(run["lti_passports"])
        run["display_name"] = data[runpath]["display_name"]

    with open(
        os.path.join(pathname, "course", "policies", run["new"], "policy.json"), "w"
    ) as policy_file:
        policy_file.write(json.dumps(data, indent=4))

    details = updateDetails(run, "run", details)
    return details


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
# Open Response Assessments
# Shift deadlines and upgrade editor type
################################
def updateORA(child, tree, dirpath, eachfile, details):
    # TODO: If there are no child elements (sigh), dig into the url_name.

    # Use rich text editor. It has fewer input sanitization issues.
    child.attrib["text_response_editor"] = "tinymce"

    # Shift deadlines for ORAs to match new start date.
    course_start = details["dates"]["new_start_edx"]
    course_end = details["dates"]["new_end_edx"]
    submission_end = pythonDateToEdx(
        details["dates"]["new_end_py"] - datetime.timedelta(7)
    )

    # Submissions start at course start and are due a week before course end.
    child.attrib["submission_start"] = course_start
    child.attrib["submission_due"] = submission_end

    # Reviews start at course start and are due at course end.
    # Look for <assessment name="peer-assessment" ...>
    # Assume there's only one peer-assessment tag, maybe none.
    peer_grading = child.findall(".//assessment[@name='peer-assessment']")
    if len(peer_grading) > 0:
        peer_grading[0].attrib["start"] = course_start
        peer_grading[0].attrib["due"] = course_end

    # Same for self-grading components
    s_grading = child.findall(".//assessment[@name='self-assessment']")
    if len(s_grading) > 0:
        s_grading[0].attrib["start"] = course_start
        s_grading[0].attrib["due"] = course_end

    # Close and write file.
    tree.write(
        os.path.join(dirpath, eachfile),
        encoding="UTF-8",
        xml_declaration=False,
    )


################################
# Vertical scraping
################################
def scrapeVerticals(details):

    # Count the number of all the component types in the course.
    # Especially need: ORA, LTI, discussion
    component_count = {}
    need_to_save = False
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

                if child.tag == "openassessment":
                    updateORA(child, tree, dirpath, eachfile, details)

                # Create new LTI components
                # so that the unique component ID passed to LTI providers changes
                if child.tag == "lti":
                    new_lti_filename = getNewEdxFilename()
                    new_lti_file = os.path.join(
                        dirpath, "..", "lti", new_lti_filename + ".xml"
                    )
                    old_lti_file = os.path.join(
                        dirpath, "..", "lti", child.attrib["url_name"] + ".xml"
                    )
                    shutil.move(old_lti_file, new_lti_file)
                    child.attrib["url_name"] = new_lti_filename
                    need_to_save = True

            if need_to_save:
                tree.write(
                    os.path.join(dirpath, eachfile),
                    encoding="UTF-8",
                    xml_declaration=False,
                )

    # Alphabetizing
    component_count_sorted = OrderedDict(sorted(component_count.items()))
    verticals = {"component_count": component_count_sorted}

    details = updateDetails(verticals, "verticals", details)
    return details


################################
# Video scraping
################################
def scrapeVideos(details):
    # TODO: Remove all references to YouTube in our videos.
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
# TODO: Add check for problems with no correct answer set.
################################
def scrapeProblems(details):
    # Count the number of problems of each assignment type
    # What % of content is gated?
    problems = {"total": 0, "ungated": 0, "solutions": 0}
    num_solutions = 0
    problem_types = [
        "choiceresponse",
        "customresponse",
        "optionresponse",
        "numericalresponse",
        "multiplechoiceresponse",
        "stringresponse",
        "formularesponse",
    ]
    problem_type_count = {
        "choiceresponse": 0,
        "customresponse": 0,
        "optionresponse": 0,
        "numericalresponse": 0,
        "multiplechoiceresponse": 0,
        "stringresponse": 0,
        "formularesponse": 0,
        "compound": 0,
    }
    trouble = {"no_solution": []}

    # Open everything in the problem/ folder
    for dirpath, dirnames, filenames in os.walk(
        os.path.join(details["run"]["pathname"], "course", "problem")
    ):
        for eachfile in filenames:

            # Get the XML for each file
            tree = ET.parse(os.path.join(dirpath, eachfile))
            root = tree.getroot()

            # Is this problem outside the paywall?
            if root.attrib.get("group_access", False):
                if root.attrib["group_access"] == "{&quot;51&quot;: [1, 2]}":
                    problems["ungated"] += 1

            # What type of problem is this?
            p_tags = 0
            for t in problem_types:
                check_type = root.iter(t)
                for c in check_type:
                    problem_type_count[t] = problem_type_count[t] + 1
                    p_tags += 1
            if p_tags > 1:
                problem_type_count["compound"] = problem_type_count["compound"] + 1

            # Does this problem have a non-empty solution?
            solutions = root.iter("solution")
            solution_texts = [ET.tostring(x, method="text") for x in solutions]
            non_empty_solutions = [len(x) for x in solution_texts]
            if sum(non_empty_solutions) > 0:
                problems["solutions"] += 1
            else:
                trouble["no_solution"].append("problem/" + eachfile)

            problems["total"] += 1

    num_problem_tags = 0
    for t in problem_type_count:
        num_problem_tags += problem_type_count[t]

    details = updateDetails(problem_type_count, "problems", details)
    details = updateDetails(problems, "problems", details)
    details = updateDetails(trouble, "trouble", details)
    return details


################################
# HTML and Tab Scraping
################################
def scrapePage(folder, filename, details):
    trouble = {
        "iframes": [],
        "flash_links": [],
        "discussion_links": [],
        "top_tab_js": [],
        "youtube_links": [],
    }
    run = details["run"]

    # Get the whole-file text so we can search it:
    with open(os.path.join(folder, filename), mode="r") as f:
        txt = f.read()

        if "<iframe" in txt:
            trouble["iframes"].append(folder + "/" + filename)
        if "youtube.com" in txt or "youtu.be" in txt:
            trouble["youtube_links"].append(folder + "/" + filename)
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

        # Find all instances of course_run in links in XML and HTML files,
        # and replace them with the new one. Only write file if it changed.
        txt_runfix = txt.replace(run["old"], run["new"])

        if txt_runfix == txt:
            txt_runfix = False

        details = updateDetails(trouble, "trouble", details)
        return details, txt_runfix


def getStaticFiles(extension, details):
    pathname = details["run"]["pathname"]
    trouble = {"js_files": []}

    # TODO: Should probably replace this with glob for better wildcard matching.
    for dirpath, dirnames, filenames in os.walk(
        os.path.join(pathname, "course", "static")
    ):
        for f in filenames:
            base, ext = os.path.splitext(f)
            # Ignore files starting with ._ They're resource fork files.
            if base[0:2] != "._":
                if ext == "*":
                    trouble["js_files"].append(f)
                elif ext == extension:
                    trouble["js_files"].append(f)

    details = updateDetails(trouble, "trouble", details)
    return details


def scrapeFolder(folder, details):
    pathname = details["run"]["pathname"]

    # Get the right type of files for this particular folder.
    if folder == "html" or folder == "tabs":
        extension = ".html"
    else:
        extension = ".xml"
    for dirpath, dirnames, filenames in os.walk(
        os.path.join(pathname, "course", folder)
    ):
        right_files = [x for x in filenames if x[-(len(extension)) :] == extension]
        for eachfile in right_files:

            det, txt = scrapePage(dirpath, eachfile, details)

            if txt != False:
                with open(
                    os.path.join(pathname, "course", folder, eachfile), mode="w"
                ) as file_contents:
                    file_contents.write(txt)

            return det


################################
# Take anything in the file_replacements folder
# and overwrite what's in Files & Uploads with them.
# Currently, file_replacements should be in the script's directory.
# Possible todo for future is making that a command-line argument.
################################
def replaceFiles(details):
    trouble = details["trouble"]
    # Open the replacement folder and step through all the files.
    replacement_folder = os.path.join(sys.path[0], "file_replacements")
    if os.path.exists(replacement_folder):
        for dirpath, dirnames, filenames in os.walk(replacement_folder):
            for f in filenames:
                shutil.copy2(
                    os.path.join(dirpath, f),
                    os.path.join(details["run"]["pathname"], "course", "static", f),
                )
                trouble["replaced_files"].append(f)

    details = updateDetails(trouble, "trouble", details)
    return details


################################
# High-level summary
################################
def createSummary(details):
    run = details["run"]
    dates = details["dates"]
    videos = details["videos"]
    trouble = details["trouble"]
    problems = details["problems"]
    component_count = details["verticals"]["component_count"]

    # Create high-level summary of course as takeaway file.
    summary_file = os.path.join(
        run["pathname"],
        run["course_nickname"] + " " + run["old"] + " to " + run["new"] + ".txt",
    )
    if os.path.exists(summary_file):
        os.remove(summary_file)
    with open(
        os.path.join(summary_file),
        "a",
    ) as summary:
        txt = ""
        txt += "Course Summary\n"
        txt += "--------------\n"
        txt += "\n"
        txt += "Course name: " + run["display_name"] + "\n"
        txt += "Identifier: " + run["id"] + " " + run["new"] + "\n"
        txt += "New Start: " + dates["new_start_edx"] + "\n"
        if dates["new_start_py"] < datetime.datetime.now():
            txt += "WARNING: course starts in the past\n"
        txt += "New End: " + dates["new_end_edx"] + "\n"
        if dates["new_end_py"] < datetime.datetime.now():
            txt += "WARNING: course ends in the past\n"
        txt += "Pacing: " + run["pacing"] + "\n"
        txt += "\n"
        txt += "Number of sections: " + str(details["chapters"]["num_chapters"]) + "\n"
        txt += (
            "Highlights set for "
            + str(details["chapters"]["num_highlights"])
            + " sections"
            + "\n"
        )
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
        txt += "Number of problems: " + str(problems["total"]) + "\n"
        txt += "Ungated problems: " + str(problems["ungated"]) + "\n"
        txt += (
            "Problems without written explanations: "
            + str(problems["total"] - problems["solutions"])
            + "\n"
        )

        # Types of problems
        problem_type_translator = {
            "choiceresponse": "checkbox",
            "customresponse": "custom input",
            "optionresponse": "dropdown",
            "numericalresponse": "numerical",
            "multiplechoiceresponse": "multiple-choice",
            "stringresponse": "text",
            "formularesponse": "math formula",
            "compound": "compound",
        }
        for t in problem_type_translator:
            txt += (
                "  "
                + spaceOut(str(problems[t]), 4, "right")
                + " "
                + problem_type_translator[t]
                + " problems\n"
            )

        # Trouble section
        txt += "\n"
        for troub in trouble:
            if len(trouble[troub]) > 0:
                if troub == "no_solution":
                    txt += "\nProblems without written explanations:\n"
                if troub == "discussion_links":
                    txt += "\nDirect links to discussion boards:\n"
                elif troub == "flash_links":
                    txt += "\nLinks to Flash files (.swf):\n"
                elif troub == "top_tab_js":
                    txt += "\nJavascript trying to access the top tab bar:\n"
                elif troub == "iframes":
                    txt += "\nComponents with iframes:\n"
                elif troub == "js_files":
                    txt += "\nJavascript in Files & Uploads:\n"
                elif troub == "youtube_links":
                    txt += "\nReferences to YouTube, usually links or iframes:\n"

                for l in trouble[troub]:
                    txt += str(l) + "\n"

        txt += "\n"
        txt += "Related Courses page must be replaced by hand.\n"
        if run["faq_page"] == "":
            txt += "Could not find FAQ page.\n"
        else:
            txt += "FAQ page " + run["faq_page"] + "\n"

        # Summarize LTI tools & keys
        txt += "\n"
        # print(run["lti_passports"])
        if len(run["lti_passports"]) > 0:
            txt += "LTI tools:\n"
            for l in run["lti_passports"]:
                txt += l + "\n"
        else:
            txt += "No LTI tools.\n"

        txt += "\n"
        txt += str(len(trouble["replaced_files"])) + " updates to Files & Uploads."
        txt += "\n"
        txt += "Discussion blackout dates removed."

        print(txt)
        summary.write(txt)

    # Anything else?

    # TODO: Post or e-mail this somewhere so we keep a record.


#########################
# Command Line Args and Dates
#########################
def getCommandLineArgs(args):

    # Read in the filename and options
    parser = argparse.ArgumentParser(usage=instructions, add_help=False)
    parser.add_argument("tarfile", default=None)
    parser.add_argument("-h", "--help", action="store_true")
    parser.add_argument("-f", "--file", action="store", default=None)

    args = parser.parse_args()
    if args.help or args.tarfile is None:
        sys.exit(instructions)

    if not os.path.exists(args.tarfile):
        sys.exit("Course export not found: " + args.tarfile)
    args.pathname = os.path.dirname(args.tarfile)

    # Handle JSON file input. Specifically, in this format:
    """
    {
        "start": "2030-01-31T14:15:00+00:00",
        "end:" "2030-01-31T20:15:00+00:00",
        "run": "1T2030"
    }
    """
    if args.file is not None:
        print("handling JSON input")
        if not os.path.exists(args.file):
            sys.exit("JSON settings file not found: " + args.file)
        with open(args.file, "r") as f:
            new_args = json.load(f)

            # Check for all arguments
            for k in ["start", "end", "run", "tarfile"]:
                if k not in new_args:
                    sys.exit("Missing key: " + k)

            if args.tarfile is None:
                args.tarfile = new_args["tarfile"]
            args.run = new_args["run"]
            args.start = new_args["start"]
            args.end = new_args["end"]
    else:
        # Get dates from user input
        print("Please input the start dates and times:")
        start_date = input("Start date (2077-01-31) = ") or "2077-01-31"
        start_time = input("Start time in UTC (15:00:00) = ") or "15:00:00"
        args.start = start_date + "T" + start_time + "+00:00"
        end_date = input("End date (2078-02-28) = ") or "2078-02-28"
        end_time = input("End time in UTC (23:59:59) = ") or "23:59:59"
        args.end = end_date + "T" + end_time + "+00:00"
        args.run = input("Run number (1T2077) = ") or "1T2077"

    # TODO: Hey, uh, what if it unzips to a folder other than "course/?
    # Like, what if it's course (1) or course (30) or something?
    # Can use tar.getnames()[0] to get the folder name inside the tar archive
    #  (might need to remove ._ from filename)
    #  and export it to something specific and helpfully named.
    # Should probably rename previous course/ folder if there is one.
    args.root_filename = "course/course.xml"

    return args


#######################
# Main starts here
#######################
def MakeNewRun(argv):

    args = getCommandLineArgs(argv)

    # Make a copy of the tarball for backup purposes
    shutil.copy2(args.tarfile, args.tarfile[:-7] + "_backup.tar.gz")

    # Extract the tarball.
    tar = tarfile.open(args.tarfile)
    tar.extractall(args.pathname)
    tar.close()

    details = setUpDetails(args)

    details = handleBaseFiles(details)
    details = handlePolicies(details)

    details = scrapeChapters(details)
    details = scrapeVerticals(details)

    details = scrapeFolder("html", details)
    details = scrapeFolder("tabs", details)
    details = updateTabs(details)
    details = scrapeFolder("problem", details)
    details = scrapeProblems(details)
    details = scrapeVideos(details)
    details = getStaticFiles(".js", details)

    details = replaceFiles(details)

    createSummary(details)

    # Re-tar
    # TODO: Is there a good way to remove the ._ files first?
    print("Creating tar.gz file... ")
    with tarfile.open(
        os.path.join(
            details["run"]["pathname"],
            details["run"]["course_nickname"]
            + "_"
            + details["run"]["new"]
            + ".new.tar.gz",
        ),
        "w:gz",
    ) as tar:
        tar.add(
            # TODO: If the folder isn't named course/, make sure to fix here.
            os.path.join(details["run"]["pathname"], "course"),
            arcname=os.path.basename(
                os.path.join(details["run"]["pathname"], "course")
            ),
        )
    print("Done.")


if __name__ == "__main__":
    MakeNewRun(sys.argv)
