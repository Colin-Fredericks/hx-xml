import os
import re
import sys
import lxml.etree
import argparse
from glob import glob

instructions = """
To use:
python3 word_count.py filename (options)

Gets the word count from SRT files, YouTube transcripts,
and Markdown files. Not guaranteed to perfectly match any
other word counter, but should be within 10%.

Valid options:
  -h Help. Print this message.
  -o Output filename.

Last update: Dec 15th 2021
"""


##############################################
# Get the word count from the file
##############################################
def countWords(f, name):
    word_count = 0
    if name.endswith(".xml"):
        # Parse with lxml
        tree = lxml.etree.parse(f)
        root = tree.getroot()
        # Get the text of all tags.
        text = root.xpath("//text()")
        # Join the text together.
        text = " ".join(text)
        # Split the text into words.
        words = text.split(" ")
        # Remove empty strings.
        words = [w for w in words if w != ""]
        # Remove words that are just numbers.
        words = [w for w in words if not w.isnumeric()]
        # Remove words that are just punctuation.
        words = [w for w in words if not w.isalnum()]
        # Count the words
        word_count = len(words)


    else:
        for line in f:
            # Skip blank lines.
            if len(line) == 0 or line == "\n" or line == "\r":
                continue
            # Check for SRT time lines and skip them.
            if re.search("\d\d --> \d\d:", line):
                continue
            # Skip lines that are just a single number.
            if re.search("^\d+$", line):
                continue
            # Check for lines that are just times and skip them.
            if re.search("^\d\d:\d\d$", line):
                continue
            if re.search("^\d\d:\d\d:\d\d$", line):
                continue

            # Don't include HTML tags
            # TODO: Not sure how to handle that one at the moment...
            # ...especially since they might be split over multiple lines.
            # Might need to bring in the big guns.

            # TODO: Handle LaTeX? Might be easier to split than HTML, really.

            raw_words = line.split(" ")
            reduced_words = []
            for w in raw_words:
                # Don't include 1-character "words"
                if len(w) > 1:
                    reduced_words.append(w)

            # Store filename and count
            word_count += len(reduced_words)

    return word_count


##############################################
# Walk through the files.
##############################################
def walkFiles(file_names):
    results = []
    # Open all the files.
    for name in file_names:
        # Make sure every file exists.
        if not os.path.exists(name):
            print("File not found: " + name)
            continue

        # We don't currently handle folders.
        if os.path.isfile(name):
            with open(name, "r") as f:
                results.append({"name": name, "word_count": countWords(f, name)})
        else:
            sys.exit("Skipping directory: " + name)
            continue

    return results


##############################################
# Main starts here
##############################################
def MakeNewRun(argv):
    # Read in the filename and options
    parser = argparse.ArgumentParser(usage=instructions, add_help=False)
    parser.add_argument("source_files", default=None, nargs="*")
    parser.add_argument("-h", "--help", action="store_true")
    parser.add_argument("-o", default="word_count.csv")

    args = parser.parse_args()
    if args.help or args.source_files is None:
        sys.exit(instructions)

    # Replace arguments with wildcards with their expansion.
    # If a string does not contain a wildcard, glob will return it as is.
    file_names = list()
    for f in args.source_files:
        file_names += glob(f)

    # If the filenames don't exist, say so and quit.
    if file_names == []:
        sys.exit("No file or directory found by that name.")

    results = walkFiles(file_names)
    results_flat = ""

    # Print the totals to screen.
    for r in results:
        print(r["name"] + ": " + str(r["word_count"]))
        results_flat += r["name"] + "," + str(r["word_count"]) + "\n"

    # Put them in a file.
    new_file = open(args.o, "w")
    new_file.write(results_flat)
    new_file.close()


if __name__ == "__main__":
    MakeNewRun(sys.argv)
