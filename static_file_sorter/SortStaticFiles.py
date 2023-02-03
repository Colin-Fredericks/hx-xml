#! usr/bin/env python3
##########################################
# Static file sorter for edX
# This script sorts the files in static/
# into two folders based on whether or
# not they are used in the course.
##########################################

import os
import sys
import bs4
import glob

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
    elif size < 1048576:
        return str(round(size / 1024, 2)) + " KB"
    else:
        return str(round(size / 1048576, 2)) + " MB"


def getFilesFromHTML(html_file: str):
    """
    Returns a list of files used in the given HTML file.

    Parameters:
        html_file (str): The path to the HTML file.

    Returns:
        list: A list of files used in the HTML file.
    """

    files = []

    # Get the HTML file. We're assuming utf-8 encoding.
    with open(html_file, "r", encoding="utf-8") as f:
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
    # - Manifests and such from annotation tools
    # - The spreadsheets from Timeline.js will have images in /static/

    # If we're linking to static files outside of the /static/ folder,
    # that's a problem. We should track that.

    pass


def getFilesFromXML(xml_file: str):
    """
    Returns a list of files used in the given XML file.

    Parameters:
        html_file (str): The path to the XML file.

    Returns:
        list: A list of files used in the XML file.
    """

    # We need to check basically the same stuff from HTML, and also:
    # - <customresponse> tags
    # - Python libraries from CAPA problems
    # How do we catch things like SuperEarths' randomized images?
    pass


def getFilesFromJSON(json_file: str):
    """
    Returns a list of files used in the given JSON file.

    Parameters:
        html_file (str): The path to the JSON file.

    Returns:
        list: A list of files used in the JSON file.
    """

    # Here we may have to just look for "anything that seems like a filename".
    # Use the extension list to filter out things that aren't files.
    pass


def getFilesFromJavascript(js_file: str):
    pass


def getFilesFromCSS(css_file: str):
    pass


def main():
    # Get the course folder from the command line
    if len(sys.argv) != 2:
        print("Usage: python3 SortStaticFiles.py <course_folder>")
        sys.exit(1)
    course_folder = sys.argv[1]

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
        "drafts/problems",
        "drafts/static",
        "drafts/vertical",
    ]
    other_folders = ["static"]

    for folder in html_folders:
        html_files = glob.glob(course_folder + "/" + folder + "/*.html")
        for f in html_files:
            course_files.extend(getFilesFromHTML(f))
    for folder in xml_folders:
        xml_files = glob.glob(course_folder + "/" + folder + "/*.xml")
        for f in xml_files:
            course_files.extend(getFilesFromXML(f))
    for folder in other_folders:
        other_files = glob.glob(course_folder + "/" + folder + "/*.json")
        for f in other_files:
            course_files.extend(getFilesFromJSON(f))
            course_files.extend(getFilesFromJavascript(f))
            course_files.extend(getFilesFromCSS(f))

    # Get the list of files in static/
    static_files = glob.glob(course_folder + "/static/*")

    # Create "used" and "unused" folders in static/
    if not os.path.exists(course_folder + "/static/used"):
        os.makedirs(course_folder + "/static/used")
    if not os.path.exists(course_folder + "/static/unused"):
        os.makedirs(course_folder + "/static/unused")

    # Put the files in the right folders
    for file in static_files:
        #  Print out the file size if it's over 1 MB
        print("Large files:")
        if os.path.getsize(file) > (1024 * 1024):
            print(os.path.basename(file) + ": " + formatByteSize(os.path.getsize(file)))
        if file in course_files:
            os.rename(file, course_folder + "/static/used/" + os.path.basename(file))
        else:
            os.rename(file, course_folder + "/static/unused/" + os.path.basename(file))

    print("\nDone!\n")

    pass


if __name__ == "__main__":
    main()
