import sys

if sys.version_info <= (3, 0):
    sys.exit("I am a Python 3 script. Run me with python3.")

import os
import argparse
import glob
from markdownify import markdownify

# Probably going to use this later to grab some specific attributes, like alt text.
# from bs4 import BeautifulSoup

instructions = """
To use:
python3 edx2md.py path/to/html/folder (options)

Run this on a folder full of HTML items from edX.
You will get a Markdown file that you can open with any text editor.

You can specify the following options:
    --help  Print this message and exit.

Last update: August 18th 2020
"""

# Main function
def Convert_To_Markdown(args=["-h"]):

    # Handle arguments and flags
    parser = argparse.ArgumentParser(usage=instructions, add_help=False)
    parser.add_argument("--help", "-h", action="store_true")
    parser.add_argument("file_names", nargs="*")

    # "extra" will help us deal with out-of-order arguments.
    args, extra = parser.parse_known_args(args)

    # print("Arguments:")
    # print(args, extra)

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

    # Make a directory to store the markdown files in.
    html_folder = os.path.dirname(file_names[0])
    md_folder = "markdown"
    dir = os.path.join(html_folder, md_folder)
    if not os.path.exists(dir):
        os.mkdir(dir)

    # Get all the HTML files.
    for name in file_names:
        if name[-5:] == ".html":
            print(name)
            new_name = name[:-5] + ".md"
            # Open the file
            f = open(name)
            # Get its contents
            html = f.read()
            # Convert it to markdown
            md = markdownify(html)
            # Save the new file in the folder.
            new_file = open(os.path.join(html_folder, md_folder, new_name), "w")
            new_file.write(md)
            new_file.close()
            f.close()


if __name__ == "__main__":
    # this won't be run when imported
    Convert_To_Markdown(sys.argv)