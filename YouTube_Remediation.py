# import XML libraries
import xml.etree.ElementTree as ET
import sys
import os
import argparse
from bs4 import BeautifulSoup

instructions = """
To use:
python3 StripYouTube.py path/to/course/folder -options

This script walks through video components to find those with YouTube URLs.
If it can safely remove them (i.e. there's another source listed), it does so.
If it can't, it flags the file for review.
It also checks HTML files for iframes and links to YouTube, and flags those.

Options:
  -h   Print this message and exit

Last update: August 2nd 2021
"""

parser = argparse.ArgumentParser(usage=instructions, add_help=False)
parser.add_argument("-h", "--help", action="store_true")
parser.add_argument("directory", default=".")

args = parser.parse_args()
if args.help:
    sys.exit(instructions)

if not os.path.exists(args.directory):
    sys.exit("Directory not found: " + args.directory)

# Global variables
num_fixed = 0
num_unfixable = 0
num_iframes = 0
num_links = 0
num_youtube_urls = 0
summary_file = ""
videos_youtube_only = []
videos_unsourced = []
links_to_youtube = []
iframes_to_youtube = []

# Get basic course info
coursefile_tree = ET.parse(os.path.join(args.directory, "course.xml"))
coursefile_root = coursefile_tree.getroot()
course_nickname = coursefile_root.attrib.get("course", "unknown")
course_run = coursefile_root.attrib.get("url_name", "unknown")
summary_file = course_nickname + "__" + course_run + ".txt"


def processVideo(folder):

    global num_fixed
    global num_unfixable
    global num_youtube_urls

    # Walk through the videos folder
    for dirpath, dirnames, filenames in os.walk(folder):
        for eachfile in filenames:

            # Get the XML for each file
            tree = ET.parse(os.path.join(dirpath, eachfile))
            root = tree.getroot()

            # If this isn't a video file, skip it.
            if root.tag != "video":
                continue

            # Is there at least one non-YouTube source?
            # These are stored in <source> or <encoded_video> tags.
            # Some files have both, some have neither.
            has_alternative_source = False
            for child in root.findall("source"):
                src = child.get("src", False)
                if src != False:
                    if "youtube.com" not in str(src) and "youtu.be" not in str(src):
                        has_alternative_source = True
            for child in root.iter("encoded_video"):
                url = child.get("url", False)
                if url != False:
                    if "youtube.com" not in str(url) and "youtu.be" not in str(url):
                        has_alternative_source = True

            # Is there a YouTube source?
            has_youtube_source = False
            for att in root.attrib:
                if "youtube" in att:
                    root.set(att, "")
                    has_youtube_source = True

            if has_alternative_source and has_youtube_source:
                # Empty out the youtube attributes.
                for att in root.attrib:
                    if "youtube" in att:
                        root.set(att, "")
                        had_youtube_url = True
                if has_youtube_source:
                    num_youtube_urls += 1

                # Remove encoded_video tags with profile="youtube"
                for tag in root.iter("encoded_video"):
                    if tag.get("profile", False) == "youtube":
                        child.remove(tag)

                # Increment file counter
                num_fixed += 1

                # Save the file
                tree.write(
                    os.path.join(dirpath, eachfile),
                    encoding="UTF-8",
                    xml_declaration=False,
                )

            elif has_alternative_source and not has_youtube_source:
                # It doesn't point to YouTube and it has an alternative source.
                # No need to fix anything.
                num_already_ok += 1

            elif has_youtube_source and not has_alternative_source:
                # If there's a youtube link and no fallback, flag it
                videos_youtube_only.append(eachfile)
                num_unfixable += 1

            else:
                # It doesn't have *any* video source. Should be very rare.
                videos_unsourced.append(eachfile)
                num_unsourced += 0

            # Debug code
            # print("has_alternative_source: " + str(has_alternative_source))
            # print("had_youtube_url: " + str(had_youtube_url))
            # print("num_fixed: " + str(num_fixed))
            # print("num_unfixable: " + str(num_unfixable))
            # input("Press enter to continue")


def processHTML(folder):

    global num_iframes
    global num_links

    # Walk through the HTML folder
    for dirpath, dirnames, filenames in os.walk(folder):
        for eachfile in filenames:

            if eachfile.endswith(".html"):
                with open(os.path.join(dirpath, eachfile)) as f:
                    # Get the HTML for each file
                    soup = BeautifulSoup(f, "html.parser")
                    # Find all iframes and links to YouTube and report them.
                    for iframe in soup("iframe"):
                        src = iframe["src"]
                        if "youtube.com" in str(src) or "youtu.be" in str(src):
                            iframes_to_youtube.append(eachfile)
                            num_iframes += 1
                    for link in soup("a"):
                        href = link["href"]
                        if "youtube.com" in str(href) or "youtu.be" in str(href):
                            links_to_youtube.append(eachfile)
                            num_links += 1


def makeReport():
    if num_fixed + num_unfixable == 0:
        print("No files found - wrong or empty directory?")
    else:
        txt = ""
        txt += "YouTube Remediation Report\n"
        txt += "--------------------------\n"
        txt += "Course identifier: " + course_nickname + " " + course_run + "\n"
        txt += str(num_youtube_urls) + " videos had YouTube URLs set.\n"
        txt += "New sources set for " + str(num_fixed) + " videos.\n"
        if num_unfixable == 0:
            txt += "All videos repaired.\n"
        else:
            txt += (
                "Could not find non-YouTube sources for "
                + str(num_unfixable)
                + " videos:\n"
            )
            for x in videos_youtube_only:
                txt += "  " + x + "\n"
        if len(videos_unsourced) > 0:
            txt += "No source at all for the following " + num_unsourced + " videos:"
            for x in videos_unsourced:
                txt += "  " + x + "\n"
        if num_links == 0:
            txt += "No links found to YouTube in HTML."
        else:
            txt += (
                "The following "
                + str(num_links)
                + " files have links that point to YouTube:\n"
            )
            for x in links_to_youtube:
                txt += "  " + x + "\n"
        if num_iframes == 0:
            txt += "No iframes found to YouTube in HTML.\n"
        else:
            txt += (
                "The following "
                + str(num_iframes)
                + " pages have iframes that point to YouTube:\n"
            )
            for x in iframes_to_youtube:
                txt += "  " + x + "\n"

        print("\n")
        print(txt)

        with open(
            os.path.join(args.directory, summary_file),
            "a",
        ) as summary:
            summary.write(txt)


processVideo(os.path.join(args.directory, "video"))
if os.path.exists(os.path.exists(os.path.join(args.directory, "drafts", "video"))):
    processVideo(os.path.join(args.directory, "drafts", "video"))

processHTML(os.path.join(args.directory, "html"))
if os.path.exists(os.path.exists(os.path.join(args.directory, "drafts", "html"))):
    processHTML(os.path.join(args.directory, "drafts", "html"))

makeReport()
