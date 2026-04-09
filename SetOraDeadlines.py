# import XML libraries
import os
import sys
import shutil
import tarfile
import argparse
import datetime as dt
from typing import Final
import xml.etree.ElementTree as ET

instructions = """
To use:
python3 SetOraDeadlines.py (-d deadline) (-s start) path/to/course/tarball

Opens an edX course export, sets ORA dates, and re-zips it for import.
By default, this sets ORA deadlines to match the start and end of the course.
It can also be set to a specific due date and time using the -d flag,
and a specific start date and time using the -s flag.
End dates for individual parts are set to the same as the overall deadline.
Date format is yyyy-mm-ddTHH:MM:SS, for example 2026-04-30T23:59:00.

Options:
  -h  Print help message and exit.
  -d  Pick the end date and time for the ORA.
  -s  Pick the start date and time for the ORA.
    
Last update: April 9th 2026
"""


def valiDate(date_str):
    """I really only care if it's a valid date. Not checking for potential day/month reversal."""
    try:
        d = dt.datetime.fromisoformat(date_str)
    except ValueError:
        sys.exit("Invalid date format. Use yyyy-mm-ddTHH:MM:SS.")


def DateInEnglish(date_str):
    """Convert a date string to a more human-friendly format."""
    d = dt.datetime.fromisoformat(date_str)
    return d.strftime("%B %d, %Y at %I:%M %p")


MAGIC_DATES: Final = {
    "START": "2001-01-01T00:00:00+00:00",
    "END": "2099-12-31T00:00:00+00:00",
}
numfiles = 0

parser = argparse.ArgumentParser(usage=instructions, add_help=False)
parser.add_argument("-h", "--help", action="store_true")
parser.add_argument("-d", "--deadline", default=None)
parser.add_argument("-s", "--start", default=None)
parser.add_argument("tarball", default=".")

args = parser.parse_args()
if args.help:
    sys.exit(instructions)

if not os.path.exists(args.tarball):
    sys.exit("Tarball not found: " + args.tarball)

folder_name = os.path.dirname(args.tarball)
root_file = os.path.join(folder_name, "course", "course.xml")

try:
    valiDate(args.deadline) if args.deadline else None
    valiDate(args.start) if args.start else None
except ValueError:
    sys.exit("Invalid date format. Use yyyy-mm-ddTHH:MM:SS.")

start_date = args.start if args.start else MAGIC_DATES["START"]
due_date = args.deadline if args.deadline else MAGIC_DATES["END"]

# Make a copy of the tarball for backup purposes
shutil.copy2(args.tarball, args.tarball[:-7] + "_backup.tar.gz")

# If there's an existing course/ folder, rename it.
# Otherwise we'll be extracting the tarfile into it.
if os.path.exists(os.path.join(folder_name, "course_previous")):
    print("Deleting existing course_previous/ folder.")
    shutil.rmtree(os.path.join(folder_name, "course_previous"))
if os.path.exists(os.path.join(folder_name, "course")):
    print("Renaming existing course/ folder to course_previous/")
    os.rename(
        os.path.join(folder_name, "course"),
        os.path.join(folder_name, "course_previous"),
    )

# Extract the tarball.
tar = tarfile.open(args.tarball, "r:gz")
tar.extractall(folder_name)
tar.close()

# # Get course ID from the root file.
root_file = os.path.join(folder_name, "course", "course.xml")
root_tree = ET.parse(root_file)
root_root = root_tree.getroot()
run_id = root_root.attrib.get("url_name", "unknown")
course_id = root_root.attrib.get("course", "unknown")
course_nickname = course_id + "_" + run_id

# Walk through the course folder.
for dirpath, dirnames, filenames in os.walk(os.path.join(folder_name, "course")):
    for eachfile in filenames:

        # Get the XML for each XML file in "problem", "vertical", and "openassessment" folders.
        if not eachfile.endswith(".xml"):
            continue
        tree = ET.parse(os.path.join(dirpath, eachfile))
        root = tree.getroot()

        # Find any "openassessment" tags. Might be root, might not.
        if root.tag == "openassessment":
            openassessment = root
        else:
            openassessment = root.find(".//openassessment")

        if openassessment is None:
            continue

        # Set the submission_start and submission_due attributes based on the command line arguments.
        openassessment.set("submission_start", start_date)
        openassessment.set("submission_due", due_date)

        # Find all <assessment> tags and set their submission_due attributes to match the overall deadline.
        for assessment in root.findall(".//assessment"):
            assessment.set("start", start_date)
            assessment.set("due", due_date)

        # Save the file
        tree.write(
            os.path.join(dirpath, eachfile), encoding="UTF-8", xml_declaration=False
        )
        numfiles += 1


if numfiles == 0:
    print("No ORAs found in this course.")
    print("Cleaning up.")
    os.remove(args.tarball[:-7] + "_backup.tar.gz")
    shutil.rmtree(os.path.join(folder_name, "course"))
else:
    print("ORA deadlines set for " + str(numfiles) + " files.")
    print(
        "Submission start set to: "
        + (DateInEnglish(start_date) if args.start else "start of course")
    )
    print(
        "Submission due set to: "
        + (DateInEnglish(due_date) if args.deadline else "end of course")
    )

    print("Creating tar.gz file... ")
    with tarfile.open(
        os.path.join(
            folder_name,
            course_nickname + "_new.tar.gz",
        ),
        "w:gz",
    ) as tar:
        tar.add(
            # TODO: If the folder isn't named course/, make sure to fix here.
            os.path.join(folder_name, "course"),
            arcname=os.path.basename(os.path.join(folder_name, "course")),
        )
    print(
        "Tarball created: " + os.path.join(folder_name, course_nickname + "_new.tar.gz")
    )

print("Done.")
