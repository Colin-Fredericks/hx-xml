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
import json
import tinycss2

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
    return filenames


def getFilesFromHTML(html_file: str):
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

    link_types = ["a", "img", "iframe", "audio", "embed", "object", "script", "link"]
    sources = ["src", "href", "data"]
    identifiers = ["/static/", "type@asset+block", "/assets/courseware/"]

    for link_type in link_types:
        for link in soup.find_all(link_type):
            for source in sources:
                if link.has_attr(source):
                    for id in identifiers:
                        if id in link[source]:
                            filename = link[source].split("/")[-1]
                            files.append(filename)
                        else:
                            report.append(link[source])

    # - TODO: Manifests and such from annotation tools
    # - TODO: The spreadsheets from Timeline.js will have images in /static/

    # If we're linking to static files outside of the /static/ folder,
    # that's a problem. We should track that.

    return {"files": files, "report": report}


def getFilesFromXML(xml_file: str):
    """
    Returns a list of files used in the given XML file.

    Parameters:
        html_file (str): The path to the XML file.

    Returns:
        list: A list of files used in the XML file.
    """

    files = []
    report = []

    # Get the HTML file. We're assuming utf-8 encoding.
    with open(xml_file, "r", encoding="utf-8") as f:
        xml = f.read()

    # Parse the HTML file
    soup = bs4.BeautifulSoup(xml, "lxml")

    # We need to check basically the same stuff from HTML, and also:
    # - <jsinput> tags
    # - Python libraries from CAPA problems
    # TODO: How do we catch things like SuperEarths' randomized images?

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
    ]
    sources = ["src", "href", "data", "html_file"]
    identifiers = ["/static/", "type@asset+block", "/assets/courseware/"]

    for link_type in link_types:
        for link in soup.find_all(link_type):
            for source in sources:
                if link.has_attr(source):
                    for id in identifiers:
                        if id in link[source]:
                            filename = link[source].split("/")[-1]
                            files.append(filename)
                        else:
                            report.append(link[source])

    return {"files": files, "report": report}


def getFilesFromJSON(json_file: str):
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
    with (open(json_file, "r")) as f:
        json_data = json.load(f)

    # Read through all values in the object and look for filenames
    possible_filenames = seekFilenames(json_data)

    return {"files": files, "report": report}


def getFilesFromCSS(css_file: str):
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
    with open(css_file, "r", encoding="utf-8") as f:
        css = f.read()
    sheet = tinycss2.parse_stylesheet(css)

    # Look through the CSS file for url() statements.
    for rule in sheet:
        if rule.type == 'qualified_rule':
            for token in rule.content:
                if token.type == 'function':
                    if token.name == 'url':
                        files.push(token.arguments[0].value)

    # If there are files stored somewhere other than /static/,
    # add them to the report. 
    for filename in files:
        if "http" in filename:
            report.append(filename)

    # TODO: Are there any other places we need to look for files?

    return {"files": files, "report": report}


def getFilesFromJavascript(js_file: str):
    """
    Returns a list of files used in the given JS file.

    Parameters:
        html_file (str): The path to the JS file.

    Returns:
        list: A list of files used in the JS file, or at least things that are probably filenames.
    """
    files = []
    report = []

    return {"files": files, "report": report}


def main():
    # Get the course folder from the command line
    if len(sys.argv) != 2:
        print("Usage: python3 SortStaticFiles.py <course_folder>")
        sys.exit(1)
    course_folder = sys.argv[1]

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
        "drafts/problems",
        "drafts/static",
        "drafts/vertical",
    ]
    other_folders = ["static"]

    for folder in html_folders:
        html_files = glob.glob(course_folder + "/" + folder + "/*.html")
        for f in html_files:
            html_data = getFilesFromHTML(f)
            course_files.extend(html_data.files)
            report.extend(html_data.report)
    for folder in xml_folders:
        xml_files = glob.glob(course_folder + "/" + folder + "/*.xml")
        for f in xml_files:
            xml_data = getFilesFromXML(f)
            course_files.extend(xml_data.files)
            report.extend(xml_data.report)
    for folder in other_folders:
        for filetype in ["json", "js", "css"]:
            other_files = glob.glob(course_folder + "/" + folder + "/*." + filetype)
            for f in other_files:
                json_data = getFilesFromJSON(f)
                css_data = getFilesFromCSS(f)
                js_data = getFilesFromJavascript(f)
                course_files.extend(json_data.files)
                course_files.extend(css_data.files)
                course_files.extend(js_data.files)
                report.extend(json_data.report)
                report.extend(css_data.report)
                report.extend(js_data.report)

    # Remove duplicates
    course_files = list(set(course_files))
    report = list(set(report))

    # Get the list of files in static/
    static_files = glob.glob(course_folder + "/static/*")

    # Create "used" and "unused" folders in static/
    if not os.path.exists(course_folder + "/static/used"):
        os.makedirs(course_folder + "/static/used")
    if not os.path.exists(course_folder + "/static/unused"):
        os.makedirs(course_folder + "/static/unused")

    # Put the files in the right folders
    used_count = 0
    unused_count = 0
    for file in static_files:
        #  Print out the file size if it's over 1 MB
        report += "\nLarge files:\n"
        if os.path.getsize(file) > (1024 * 1024):
            report += (
                os.path.basename(file)
                + ": "
                + formatByteSize(os.path.getsize(file))
                + "\n"
            )
        if file in course_files:
            os.rename(file, course_folder + "/static/used/" + os.path.basename(file))
            used_count += 1
        else:
            os.rename(file, course_folder + "/static/unused/" + os.path.basename(file))
            unused_count += 1

    # Build the report and write it to a file
    report += str(used_count) + " files moved to the 'used' folder.\n"
    report += str(unused_count) + " files moved to the 'unused' folder.\n\n"

    report += "Files linked to but not in Files & Uploads:\n"
    for line in report:
        final_report += line + "\n"

    with open(course_folder + "/static/report.txt", "w") as f:
        f.write(final_report)

    print(report)


if __name__ == "__main__":
    main()
