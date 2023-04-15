#! usr/bin/env python3
##########################################
# Static file sorter for edX
# This script sorts the files in static/
# into two folders based on whether or
# not they are used in the course.
##########################################

import os
import re
import sys
import bs4
import glob
import json
import tinycss2
from urllib.parse import urlparse
from lxml import etree as ET

# List of extensions that are likely to be used in course files.
# This is so we don't accidentally flag javascript code as files.
# We're only using this for the JSON, and JS files.
extensions = [
    "7z",
    "apk",
    "bin",
    "bz2",
    "c",
    "cpp",
    "css",
    "csv",
    "deb",
    "dmg",
    "doc",
    "docx",
    "eot",
    "exe",
    "gif",
    "gz",
    "h",
    "hpp",
    "htm",
    "html",
    "ico",
    "iso",
    "ipy",
    "ipython",
    "iso",
    "jar",
    "java",
    "jpeg",
    "jpg",
    "js",
    "json",
    "m",
    "mat",
    "md",
    "mp3",
    "mp4",
    "msi",
    "ogg",
    "otf",
    "pdf",
    "pkg",
    "png",
    "ppt",
    "pptx",
    "py",
    "r",
    "rar",
    "rmd",
    "rpm",
    "rst",
    "rtf",
    "sjson",
    "srt",
    "svg",
    "tar",
    "tsv",
    "ttf",
    "txt",
    "wav",
    "webm",
    "webp",
    "woff",
    "woff2",
    "xls",
    "xml",
    "xmlx",
    "xz",
    "zip",
]


def formatByteSize(size: int):
    """
    Formats a byte size into a human-readable string.
    """
    if size < 1024:
        return str(size) + " bytes"
    elif size < (1024 * 1024):
        return str(round(size / 1024, 2)) + " KB"
    else:
        return str(round(size / (1024 * 1024), 2)) + " MB"


def seekFilenames(jobj):
    """
    Returns a list of filenames from a JSON object.

    Parameters:
        jobj (dict): The JSON object to search.

    Returns:
        list: A list of filenames.
    """
    filenames = []
    for key in jobj:
        if type(jobj[key]) == str:
            if jobj[key].split(".")[-1] in extensions:
                filenames.append(jobj[key])
        elif type(jobj[key]) == dict:
            filenames += seekFilenames(jobj[key])
        elif type(jobj[key]) == list:
            for item in jobj[key]:
                if type(item) == dict:
                    filenames += seekFilenames(item)
                if type(item) == str:
                    if item.split(".")[-1] in extensions:
                        filenames.append(item)
    return filenames


def getFilesFromHTML(html_file: str, course_folder: str):
    """
    Returns a list of files used in the given HTML file.

    Parameters:
        html_file (str): The path to the HTML file.

    Returns:
        list: A list of files used in the HTML file.
    """

    files = []
    report = []

    # Get the HTML file. We're assuming utf-8 encoding.
    with open(os.path.join(course_folder, html_file), "r", encoding="utf-8") as f:
        html = f.read()

    # Parse the HTML file
    soup = bs4.BeautifulSoup(html, "html.parser")

    # Get the list of files used in the HTML file.
    # We are specifically looking for the following:
    # - Links to the /static/ folder
    #   The /static/ folder is sometimes expanded like this:
    #   /assets/courseware/ ... type@asset+block/filename.ext
    # - Images stored in the /static/ folder
    # - Iframes that point to the /static/ folder
    # - Audio tags that point to the /static/ folder
    # - Oddballs like <embed> and <object> tags
    # - Scripts and style sheets that point to the /static/ folder
    # - Basically anything that has a src, href, or data attribute or something like it

    link_types = ["a", "img", "iframe", "audio", "embed", "object", "script", "link"]
    sources = ["src", "href", "data"]
    identifiers = ["/static/", "type@asset+block", "/assets/courseware/"]

    print("\nFrom " + os.path.join(course_folder, html_file) + ":")

    for link_type in link_types:
        for link in soup.find_all(link_type):
            for source in sources:
                # Files stored in /static/ will refer to each other without
                # any of the identifiers above. If we have a source
                # that's *just* a file with no protocol or directory, count it.
                if link.has_attr(source):
                    link_path = urlparse(link[source]).path
                    linked_file = os.path.basename(link_path)
                    if link_path == linked_file:
                        files.append(link[source])
                    else:
                        add_file = False
                        for id in identifiers:
                            if id in link_path:
                                add_file = True
                        if add_file:
                            files.append(linked_file)
                            print("Including: " + linked_file)
                            break
                        else:
                            report.append(link_path)
                            print("Not including: " + link_path)

    # - TODO: Manifests and such from annotation tools
    # - TODO: The spreadsheets from Timeline.js will have images in /static/

    return {"files": files, "report": report}


def getFilesFromXML(xml_file: str, course_folder: str):
    """
    Returns a list of files used in the given XML file.
    Finds files in both attributes and text,
    as long as the text is the only thing in the tag.

    Parameters:
        html_file (str): The path to the XML file.

    Returns:
        list: A list of files used in the XML file.
    """

    files = []
    report = []

    # Get the XML file. We're assuming utf-8 encoding.
    with open(os.path.join(course_folder, xml_file), "r", encoding="utf-8") as f:
        xml = f.read()

    # Parse the XML file
    soup = bs4.BeautifulSoup(xml, "lxml")

    # We need to check basically the same stuff from HTML, and also:
    # - <jsinput> tags
    # - Python libraries from CAPA problems
    # - Video transcripts

    # TODO: How do we catch things like SuperEarths' randomized images?
    # Do we just need to run the whole thing through QA?

    link_types = [
        "a",
        "img",
        "iframe",
        "audio",
        "embed",
        "object",
        "script",
        "link",
        "jsinput",
        "transcript",
    ]
    sources = ["src", "href", "data", "html_file"]
    identifiers = ["/static/", "type@asset+block", "/assets/courseware/"]

    for link_type in link_types:
        for link in soup.find_all(link_type):
            for source in sources:
                for id in identifiers:
                    if link.has_attr(source):
                        if id in link[source]:
                            files.append(os.path.basename(link[source]))
                        else:
                            report.append(link[source])

    return {"files": files, "report": report}


def getFilesFromJSON(json_file: str, course_folder: str):
    """
    Returns a list of files used in the given JSON file.

    Parameters:
        html_file (str): The path to the JSON file.

    Returns:
        list: A list of files used in the JS file, or at least things that are probably filenames.
    """

    # Here we may have to just look for "anything that seems like a filename".
    # Use the extension list to filter out things that aren't files.
    files = []
    report = []

    # open the file and read the contents
    with (open(os.path.join(course_folder, json_file), "r")) as f:
        json_data = json.load(f)

    # Read through all values in the object and look for filenames
    possible_filenames = seekFilenames(json_data)

    return {"files": files, "report": report}


def getFilesFromCSS(css_file: str, course_folder: str):
    """
    Returns a list of files used in the given CSS file.

    Parameters:
        html_file (str): The path to the CSS file.

    Returns:
        list: A list of files used in the CSS file.
    """
    files = []
    report = []

    # Get the CSS file. We're assuming utf-8 encoding.
    with open(os.path.join(course_folder, css_file), "r", encoding="utf-8") as f:
        css = f.read()
    sheet = tinycss2.parse_stylesheet(css)

    # Look through the CSS file for url() statements.
    for rule in sheet:
        if rule.type == "qualified_rule":
            for token in rule.content:
                if token.type == "function":
                    if token.name == "url":
                        files.push(token.arguments[0].value)

    # If there are files stored somewhere other than /static/,
    # add them to the report.
    for filename in files:
        if "//" in filename:
            report.append(filename)

    # TODO: Are there any other places we need to look for files?

    return {"files": files, "report": report}


def getFilesFromJavascript(js_file: str, course_folder: str):
    """
    Returns a list of files used in the given JS file.

    Parameters:
        html_file (str): The path to the JS file.

    Returns:
        list: A list of files used in the JS file, or at least things that are probably filenames.
    """
    temp = []
    files = []
    report = []

    # Here we need to go through each file line by line.
    # Any time we find one of our extensions, we'll see if
    # the text is inside a string. If it is, we'll add it.

    # Get the JS file. We're assuming utf-8 encoding.
    with open(os.path.join(course_folder, js_file), "r", encoding="utf-8") as f:
        js = f.read()

    # Read through the file line by line
    for line in js.splitlines():
        # Check if the line has any of our extensions
        for ext in extensions:
            if ext in line:
                # See if it's inside a string. If it is, take the whole line.
                # We'll do this with a regex on the line.
                if re.search(r'".*"', line):
                    temp.append(line)
                if re.search(r"'.*'", line):
                    temp.append(line)

    # decide whether the line has a local file or a full URL
    for line in temp:
        if "//" in line:  # This means it has a protocol listed, like https://
            report.append(line)
        else:
            files.append(line)

    return {"files": files, "report": report}


def fullCourseTextSearch(unused_files: list, course_folder: str):
    """
    Double-checks our list of unused files against a full text
    search of every file in the course.
    Specifically checks .html, .xml, .json, .css, and .js files.

    @param course_folder: The path to the course folder.
    @param unused_files: A list of files that are unused.
    @return: A list of files that are definitely unused.
    """

    all_files = []
    # Tired of pass-by-value issues, so we'll just make a copy of the list.
    really_unused = unused_files.copy()

    # Get a list of all files in the course
    for root, dirs, files in os.walk(course_folder):
        for file in files:
            if os.path.basename(file).split(".")[-1] in [
                ".html",
                ".xml",
                ".json",
                ".css",
                ".js",
            ]:
                all_files.append(os.path.join(root, file))

    # Open the files one at a time.
    # Parse the file one line at a time.
    # If one of our unused files is in the line, remove it from the list.
    for file in all_files:
        with open(file, "r") as f:
            for line in f:
                for unused_file in really_unused:
                    if unused_file in line:
                        really_unused.remove(unused_file)

    return really_unused


def main():
    # Get the course folder from the command line
    if len(sys.argv) != 2:
        sys.exit("Usage: python3 SortStaticFiles.py <course_folder>")
    course_folder = sys.argv[1]

    # Get the location of the course folder to use as our base
    course_folder = os.path.abspath(course_folder)

    # Keep a text string for the report
    final_report = "Static File Report\n-----------------\n\n"
    report = []

    # Get the list of files used in the course
    # Have to include verticals because they can have inline components.
    course_files = []
    html_folders = [
        "html",
        "tabs",
        "static",
        "drafts/html",
        "drafts/tabs",
        "drafts/static",
    ]
    xml_folders = [
        "problems",
        "static",
        "vertical",
        "video",
        "drafts/problems",
        "drafts/static",
        "drafts/vertical",
        "drafts/video",
    ]
    other_folders = ["static"]

    # Get the course run number.
    course_root = os.path.join(course_folder, "course.xml")
    course_run = ""
    with open(course_root, "r") as f:
        course_xml = f.read()
        tree = ET.fromstring(course_xml)
        course_run = tree.attrib["url_name"]

    # Check the policy.json file to see what tabs there are.
    policy_file = os.path.join(course_folder, "policies", course_run, "policy.json")
    tabs_to_keep = []
    with open(policy_file, "r") as f:
        policy = json.load(f)
        tabs = policy["course/" + course_run]["tabs"]
        for tab in tabs:
            if tab["type"] == "static_tab":
                # Add that tab to a list of files to not delete.
                tabs_to_keep.append(tab["url_slug"] + ".html")
    # Remove any tabs that aren't in the policy.json file.
    tab_list = glob.glob(os.path.join(course_folder, "tabs", "*.html"))
    for tab in tab_list:
        if os.path.basename(tab) not in tabs_to_keep:
            os.remove(tab)

    # Get the list of files used in the course
    for folder in html_folders:
        html_files = glob.glob(os.path.join(course_folder, folder, "*.html"))
        for f in html_files:
            html_data = getFilesFromHTML(f, course_folder)
            course_files.extend(html_data["files"].copy())
            report.extend(html_data["report"].copy())

    for folder in xml_folders:
        xml_files = glob.glob(os.path.join(course_folder, folder, "*.xml"))
        for f in xml_files:
            xml_data = getFilesFromXML(f, course_folder)
            course_files.extend(xml_data["files"].copy())
            report.extend(xml_data["report"].copy())

    for folder in other_folders:
        for filetype in ["json", "js", "css"]:
            other_files = glob.glob(
                os.path.join(course_folder, folder, "*." + filetype)
            )
            for f in other_files:
                data = {}
                if filetype == "json":
                    data = getFilesFromJSON(f, course_folder)
                elif filetype == "js":
                    data = getFilesFromJavascript(f, course_folder)
                elif filetype == "css":
                    data = getFilesFromCSS(f, course_folder)
                course_files.extend(data["files"].copy())
                report.extend(data["report"].copy())

    # Remove duplicates
    course_files = list(set(course_files))
    report = list(set(report))

    # "used" overrides "unused"
    report = [f for f in report if f not in course_files]
    # TODO: I'm not catching /static/backpack.html when I should be. Why?
    # Oh, it's because it's looking for a file named "static/backpack.html" rather than "backpack.html".

    # Throw out anything that doesn't end in an extension we're looking for.
    course_files = [f for f in course_files if f.split(".")[-1] in extensions]
    report = [f for f in report if f.split(".")[-1] in extensions]

    print("\ncourse files")
    print(course_files)
    print("\nreport")
    print(report)

    # Get the list of files in static/
    static_files = glob.glob(os.path.join(course_folder, "static", "*"))
    # If any of them are directories, skip those.
    static_files = [f for f in static_files if os.path.isfile(f)]

    # TODO: We may be ending up with files that are referenced from /static/ files
    # that have been removed from the course. We need to check for those.
    # Not a high-priority item.

    # Create "used" and "unused" folders in static/
    if not os.path.exists(course_folder + "/static/used"):
        os.makedirs(course_folder + "/static/used")
    if not os.path.exists(course_folder + "/static/unused"):
        os.makedirs(course_folder + "/static/unused")

    # Put the files in the right folders
    used_count = 0
    unused_count = 0

    for file in static_files:
        if os.path.basename(file) in course_files:
            os.rename(
                os.path.join(course_folder, file),
                os.path.join(course_folder, "static", "used", os.path.basename(file)),
            )
            used_count += 1
        else:
            os.rename(
                os.path.join(course_folder, file),
                os.path.join(course_folder, "static", "unused", os.path.basename(file)),
            )
            unused_count += 1

    # Check the "unused" folder for any files that are linked to in the course
    print("Double-checking the unused folder...")
    unused_files = glob.glob(os.path.join(course_folder, "static", "unused", "*"))
    really_unused = fullCourseTextSearch(unused_files, course_folder)

    # Move any items that are actually used back to the "used" folder
    turns_out_theyre_used = list(set(unused_files) - set(really_unused))
    for file in turns_out_theyre_used:
        os.rename(
            os.path.join(course_folder, file),
            os.path.join(course_folder, "static", "used", os.path.basename(file)),
        )
        used_count += 1
        unused_count -= 1

    # Build the report and write it to a file
    final_report += str(used_count) + " files moved to the 'used' folder.\n"
    final_report += str(unused_count) + " files moved to the 'unused' folder.\n\n"

    final_report += "Files linked to but not in Files & Uploads:\n"
    for line in report:
        final_report += line + "\n"

    with open(os.path.join(course_folder, "static", "report.txt"), "w") as f:
        f.write(final_report)

    print("\n")
    print(report)


if __name__ == "__main__":
    main()
