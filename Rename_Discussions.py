import sys

if sys.version_info <= (3, 0):
    sys.exit("I am a Python 3 script. Run me with python3.")

import os
import glob
import argparse
from bs4 import BeautifulSoup
import xml.etree.ElementTree as ET

instructions = """
To use:
python3 Rename_Discussions.py path/to/course.xml (options)

Run this on a course folder, or a course.xml file inside an edX course folder (from export).
You will get a Tab-Separated Value file that you should open with Google Drive,
which shows the location of each video and the srt filename for that video.

You can specify the following options:
    -problems  Includes problems AND problem XML instead of videos
    -html      Includes just HTML components
    -video     Forces inclusion of video with html or problems
    -all       Includes most components, including problem,
               html, video, discussion, poll, etc.
    -links     Lists all links in the course.
               Not compatible with above options.
    -alttext   Lists all images with their alt text.
               Not compatible with above options.
    -o         Sets the output filename to the next argument.

This script may fail on courses with empty containers.

Last update: July 15th 2021
"""


# Many of these are being skipped because they're currently expressed in inline XML
# rather than having their own unique folder in the course export.
# These will be moved out as we improve the parsing.
skip_tags = [
    "annotatable",  # This is the older, deprecated annotation component.
    "google-document",
    "oppia",
    "openassessment",  # This is the older, deprecated ORA.
    "poll_question",  # This is the older, deprecated poll component.
    "problem-builder",
    "recommender",
    "step-builder",
    "wiki",
]

# Canonical leaf node. Only for copying.
canon_leaf = {"type": "", "name": "", "url": "", "links": [], "images": [], "sub": []}


# Always gets the display name.
# For video and problem files, gets other info too
def getComponentInfo(folder, filename, child, parentage, args):

    # Try to open file.
    try:
        tree = ET.parse(folder + "/" + filename + ".xml")
        root = tree.getroot()
    except OSError:
        # If we can't get a file, try to traverse inline XML.
        root = child

    # Note: edX does discussions inline in the vertical xml by default.
    # Need to remove any discussion_category and discussion_target attributes
    # and replace them with section and subsection, respectively.

    temp = {
        "type": root.tag,
        "name": "",
        # space for other info
    }

    # get display_name or use placeholder
    if "display_name" in root.attrib:
        temp["name"] = root.attrib["display_name"]
    else:
        temp["name"] = root.tag

    if root.tag == "discussion":
        # Remove the attributes if they exist.
        if "discussion_category" in root.attrib:
            delete
        if "discussion_target" in root.attrib:
            delete
        # Add the attributes
        root.attrib["discussion_category"] = (
            parentage["section"] + ": " + parentage["subsection"]
        )
        root.attrib["discussion_target"] = parentage["page"]

    # Label all of them as components regardless of type.
    temp["component"] = temp["name"]

    return {"contents": temp, "parent_name": temp["name"], "childroot": root}


# Recursion function for outline-declared xml files
def drillDown(folder, filename, root, parentage, args):

    # Try to open file.
    try:
        tree = ET.parse(os.path.join(folder, (filename + ".xml")))
        root = tree.getroot()
    except IOError:
        # If we can't get a file, try to traverse inline XML.
        ddinfo = getXMLInfo(folder, root, parentage, args)
        if ddinfo:
            return ddinfo
        else:
            print(
                "Possible missing file or empty XML element: "
                + os.path.join(folder, (filename + ".xml"))
            )
            return {"contents": [], "parent_name": "", "found_file": False}

    XMLInfo = getXMLInfo(folder, root, parentage, args)

    # Rewrite all verticals that have discussion components.
    if XMLInfo["has_discussion"]:
        print(root[-1].attrib)
        print(filename)
        tree.write(
            os.path.join(folder, (filename + ".xml")),
            encoding="utf-8",
            xml_declaration=False,
        )

    return XMLInfo


def getXMLInfo(folder, root, parentage, args):

    # We need lists of container nodes and leaf nodes so we can tell
    # whether we have to do more recursion.
    leaf_nodes = [
        "discussion",
        "done",
        "drag-and-drop-v2",
        "html",
        "imageannotation",
        "library_content",
        "lti",
        "lti_consumer",
        "pb-dashboard",  # This is currently unique to HarvardX DataWise
        "poll",
        "problem",
        "survey",
        "textannotation",
        "ubcpi",
        "video",
        "videoannotation",
        "word_cloud",
    ]
    branch_nodes = [
        "course",
        "chapter",
        "sequential",
        "vertical",
        "split_test",
        "conditional",
    ]

    contents = []
    has_discussion = False

    # Some items are created without a display name; use their tag name instead.
    if "display_name" in root.attrib:
        display_name = root.attrib["display_name"]
    else:
        display_name = root.tag

    if root.tag == "course":
        parentage["course"] = display_name
    elif root.tag == "chapter":
        parentage["section"] = display_name
    elif root.tag == "sequential":
        parentage["subsection"] = display_name
    elif root.tag == "vertical":
        parentage["page"] = display_name
    elif root.tag in branch_nodes:
        parentage["smaller"] = display_name

    for index, child in enumerate(root):
        temp = {
            "index": index,
            "type": child.tag,
            "name": "",
            "url": "",
            "contents": [],
            "links": [],
            "images": [],
            "sub": [],
        }

        # get display_name or use placeholder
        if "display_name" in child.attrib:
            temp["name"] = child.attrib["display_name"]
        else:
            temp["name"] = child.tag + str(index)
            temp["tempname"] = True

        # get url_name but there are no placeholders
        # Note that even some inline XML have url_names.
        if "url_name" in child.attrib:
            temp["url"] = child.attrib["url_name"]
        else:
            temp["url"] = None

        # In the future: check to see whether this child is a pointer tag or inline XML.
        nextFile = os.path.join(os.path.dirname(folder), child.tag)
        if child.tag in branch_nodes:
            child_info = drillDown(nextFile, temp["url"], child, parentage, args)
            temp["contents"] = child_info["contents"]
        elif child.tag in leaf_nodes:
            child_info = getComponentInfo(nextFile, temp["url"], child, parentage, args)
            # Looking for discussions that need to get fixed.
            # If we found one, fix its info.
            if child.tag == "discussion":
                has_discussion = True
            # For leaf nodes, add item info to the dict
            # instead of adding a new contents entry
            temp.update(child_info["contents"])
            del temp["contents"]
        elif child.tag in skip_tags:
            child_info = {"contents": False, "parent_name": child.tag}
            del temp["contents"]
        else:
            sys.exit("New tag type found: " + child.tag)

        # If the display name was temporary, replace it.
        if "tempname" in temp:
            temp["name"] = child_info["parent_name"]
            del temp["tempname"]

        # We need not only a name, but a custom key with that name.
        temp[temp["type"]] = temp["name"]

        contents.append(temp)

    return {
        "contents": contents,
        "parent_name": display_name,
        "found_file": True,
        "root": root,
        "has_discussion": has_discussion,
    }


# Main function
def Rename_Discussions(args=["-h"]):

    print("Creating course sheet")

    # Handle arguments and flags
    parser = argparse.ArgumentParser(usage=instructions, add_help=False)
    parser.add_argument("--help", "-h", action="store_true")
    parser.add_argument("-all", action="store_true")
    parser.add_argument("-problems", action="store_true")
    parser.add_argument("-html", action="store_true")
    parser.add_argument("-video", default=True, action="store_true")
    parser.add_argument("-links", action="store_true")
    parser.add_argument("-alttext", action="store_true")
    parser.add_argument("-o", action="store")
    parser.add_argument("file_names", nargs="*")

    # "extra" will help us deal with out-of-order arguments.
    args, extra = parser.parse_known_args(args)

    print("Arguments:")
    print(args, extra)

    if args.help:
        sys.exit(instructions)

    # Do video by default. Don't do it when we're doing other stuff,
    # unless someone intentionally turned it on.
    if not args.video:
        if args.problems or args.html or args.all or args.links or args.alttext:
            args.video = False

    # Link lister is not compatible with other options,
    # mostly because it makes for too big a spreadsheet.
    # Ditto for the alt text option.
    if args.links:
        args.problems = args.html = args.all = args.video = args.alttext = False
    elif args.alttext:
        args.problems = args.html = args.all = args.video = args.links = False

    # Replace arguments with wildcards with their expansion.
    # If a string does not contain a wildcard, glob will return it as is.
    # Mostly important if we run this on Windows systems.
    file_names = list()
    for arg in args.file_names:
        file_names += glob.glob(glob.escape(arg))
    for item in extra:
        file_names += glob.glob(glob.escape(item))

    # Don't run the script on itself.
    if sys.argv[0] in file_names:
        file_names.remove(sys.argv[0])

    # If the filenames don't exist, say so and quit.
    if file_names == []:
        sys.exit("No file or directory found by that name.")

    # Get the course.xml file and root directory
    for name in file_names:
        if os.path.isdir(name):
            if os.path.exists(os.path.join(name, "course.xml")):
                rootFileDir = name
        else:
            if "course.xml" in name:
                rootFileDir = os.path.dirname(name)

        rootFilePath = os.path.join(rootFileDir, "course.xml")
        course_tree = ET.parse(rootFilePath)

        # Open course's root xml file
        # Get the current course run filename
        course_root = course_tree.getroot()

        course_dict = {
            "type": course_root.tag,
            "name": "",
            "url": course_root.attrib["url_name"],
            "contents": [],
        }
        parentage = {
            "course": "",
            "section": "",
            "subsection": "",
            "page": "",
            "smaller": "",
        }

        course_info = drillDown(
            os.path.join(rootFileDir, course_dict["type"]),
            course_dict["url"],
            course_root,
            parentage,
            args,
        )
        course_dict["name"] = course_info["parent_name"]
        course_dict["contents"] = course_info["contents"]

        if args.links:
            course_dict["contents"].extend(getAuxLinks(rootFileDir))
        if args.alttext:
            course_dict["contents"].extend(getAuxAltText(rootFileDir))


if __name__ == "__main__":
    # this won't be run when imported
    Rename_Discussions(sys.argv)
