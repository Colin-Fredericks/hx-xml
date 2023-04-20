import io
import os
import re
import sys
import lxml.etree
import argparse
from glob import glob

instructions = """
To use:
python3 word_count.py path/to/course/folder (options)

Gets the word count from SRT files, YouTube transcripts,
and Markdown files. Not guaranteed to perfectly match any
other word counter, but should be within 10%. Outputs a text file.

Valid options:
  -h Help. Print this message.
  -o Output filename. Default is word_count.csv

Last update: Apr 20th 2023
"""


def countWords(f, ext):
    """
    Counts the words in a file.
    @param f: The file object for the file to count words in.
    @param ext: The extension of the file.
    @return: A tuple containing the filename and the word count
    """

    word_count = 0
    if ext == ".xml" or ext == ".html":
        if ext == ".xml":
            # Parse with lxml
            tree = lxml.etree.parse(f)
            root = tree.getroot()
        else:
            # Parse the html file with lxml
            parser = lxml.etree.HTMLParser()
            tree   = lxml.etree.parse(io.StringIO(f), parser)
            root   = tree.getroot()

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

    elif ext == ".md" or ext == ".srt":
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


def walkFiles(file_names):
    """
    Walks through the directory structure
    @param file_names: A list of files and directories to walk through.
    @param results_flat: A string to store the results in.
    @return: A list of dictionaries containing the filename and word count.
    """

    results = []
    results_flat = "Word count results:\n"
    # Open all the files or folders.
    for name in file_names:
        # Check to make sure it exists
        if not os.path.exists(name):
            print("File not found: " + name)
            continue

        for root, dirs, thing in os.walk(name):
            for d in dirs:
                # Add the directory name to the flat results.
                results_flat += "\n" + d + "\n"
                # Walk through the directory.
                for root, dirs, files in os.walk(d):
                    for f in files:
                        # Only open files with specific extensions.
                        ext = os.path.splitext(f)[1]
                        if ext not in [".xml", ".html", ".md", ".srt"]:
                            continue
                        with open(f, "r") as f:
                            name, count = countWords(f, ext)
                            results.append({"name": f, "word_count": count})
                            results_flat += f + ": " + str(count) + "\n"

    return results, results_flat


##############################################
# Main starts here
##############################################
def WordCount(argv):
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

    results, results_flat = walkFiles(file_names)

    # Print the totals to screen.
    total_count = 0
    for r in results:
        total_count += r["word_count"]
        print(r["name"] + ": " + str(r["word_count"]))
        print("Total words:" + str(total_count))

    # Put them in a file.
    new_file = open(args.o, "w")
    new_file.write(results_flat)
    new_file.close()


if __name__ == "__main__":
    WordCount(sys.argv)
