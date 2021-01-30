import sys

if sys.version_info <= (3, 0):
    sys.exit("I am a Python 3 script. Run me with python3.")

import os
import argparse
import glob
import markdown

# Probably going to use this later to grab some specific attributes, like alt text.
# from bs4 import BeautifulSoup

instructions = """
To use:
python3 md2edx.py path/to/markdown/folder (options)

Run this on a folder full of markdown files.
You will get paired HTML files that you can
insert into edX's html folder. You will need the
original XML files to maintain display names.

You can specify the following options:
    --help  Print this message and exit.

Last update: August 18th 2020
"""

# Main function
def Convert_From_Markdown(args=["-h"]):

    print(" Beginning conversion")

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

    # If one of the items is a folder, get its contents instead.
    interior_files = list()
    for f in file_names:
        if os.path.isdir(f):
            interior_files += glob.glob(f + "/*.md")
            file_names.remove(f)
    file_names += interior_files

    # If the filenames don't exist, say so and quit.
    if file_names == []:
        sys.exit("No .md files found.")

    # Make a directory to store the html files in.
    md_folder = os.path.dirname(file_names[0])
    html_folder = "html"
    dir = os.path.join(md_folder, html_folder)
    if not os.path.exists(dir):
        os.mkdir(dir)

    # Get all the markdown files.
    for name in file_names:
        if name[-3:] == ".md":
            print(name)
            # Open the file. Need encoding to avoid nonprinting byte order mark.
            f = open(name, encoding="utf-8-sig")
            # Get its contents
            md = f.read()
            # Convert it to html
            html = markdown.markdown(md)

            # Save the new file in the folder.
            new_name_html = name[:-3] + ".html"
            new_file_html = open(
                os.path.join(md_folder, html_folder, os.path.basename(new_name_html)),
                "w",
            )
            new_file_html.write(html)
            new_file_html.close()

            # Removed because we're using the original XML files.
            # new_name_xml = name[:-3] + ".xml"
            # new_file_xml = open(os.path.join(md_folder, html_folder, os.path.basename(new_name_html)), "w")
            # new_file_xml.write(
            #     '<html filename="'
            #     + new_name_html
            #     + '" display_name="HTML" editor="raw"/>'
            # )
            # new_file_xml.close()

            f.close()

    print(" Conversion complete")


if __name__ == "__main__":
    # this won't be run when imported
    Convert_From_Markdown(sys.argv)
