import sys

if sys.version_info <= (3, 0):
    sys.exit("I am a Python 3 script. Run me with python3.")

import os
import glob
import argparse
import xml.etree.ElementTree as ET

instructions = """
To use:
python3 Rename_Discussions.py path/to/course.xml (options)

This script adds comments to every chapter, sequential, and vertical
identifying its location in the course so that it's easaier 
to do XML things.

"""


# Always gets the display name.
def getComponentInfo(folder, filename, child, parentage, args):

    # Try to open file.
    try:
        tree = ET.parse(os.path.join(folder, filename + ".xml"))
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
            del root.attrib["discussion_category"]
        if "discussion_target" in root.attrib:
            del root.attrib["discussion_target"]
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
        tree.write(
            os.path.join(folder, (filename + ".xml")),
            encoding="utf-8",
            xml_declaration=False,
        )

    return XMLInfo


def getXMLInfo(folder, root, parentage, args):

    # We need lists of container nodes so we can tell
    # whether we have to do more recursion.
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

        nextFile = os.path.join(os.path.dirname(folder), child.tag)
        # Some tags trip us up. Add them here so we can skip them.
        if child.tag in ["wiki"]:
            child_info = {"contents": False, "parent_name": child.tag}
            del temp["contents"]
        elif child.tag in ["vertical"]:
            # Write a comment with the vertical's location in the course.
            root.insert(
                0,
                ET.Comment(
                    "Section: "
                    + parentage["section"]
                    + ", Subsection: "
                    + parentage["subsection"]
                    + ", Page: "
                    + parentage["page"]
                ),
            )
        else:
            # If we're not at the "vertical" level, recurse.
            child_info = drillDown(nextFile, temp["url"], child, parentage, args)

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
def NameThatPage(args=["-h"]):

    # Handle arguments and flags
    parser = argparse.ArgumentParser(usage=instructions, add_help=False)
    parser.add_argument("--help", "-h", action="store_true")
    parser.add_argument("file_names", nargs="*")

    # "extra" will help us deal with out-of-order arguments.
    args, extra = parser.parse_known_args(args)

    if args.help:
        sys.exit(instructions)

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

        print("Added comments to all verticals in " + course_info["parent_name"])


if __name__ == "__main__":
    # this won't be run when imported
    NameThatPage(sys.argv)
