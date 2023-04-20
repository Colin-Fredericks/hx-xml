import os
import re
import sys
import lxml.etree
import argparse
from glob import glob
from bs4 import BeautifulSoup as BS

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
    if ext == ".xml":
        # Parse with lxml
        tree = lxml.etree.parse(f)
        root = tree.getroot()
        # Get the text of all tags.
        if root is not None:
            text = root.xpath("//text()")
        else:
            return word_count
        # Join the text together.
        text = " ".join(text)
        # Split the text into words.
        words = text.split(" ")
        # Remove empty strings.
        words = [w for w in words if w != ""]
        # Remove words that are just numbers.
        words = [w for w in words if not w.isnumeric()]
        # Remove one-letter words
        words = [w for w in words if len(w) > 1]
        # Count the words
        word_count = len(words)
        # Subtract off the number of child tags from the root.
        word_count = word_count - len(root.getchildren()) - 1

    elif ext == ".html":
        # Parse the file with BeautifulSoup.
        soup = BS(f, "html.parser")
        # Get the text of all tags.
        text = soup.get_text()
        # Split the text into words.
        words = text.split(" ")
        # Remove empty strings.
        words = [w for w in words if w != ""]
        # Remove words that are just numbers.
        words = [w for w in words if not w.isnumeric()]
        # Remove one-letter words
        words = [w for w in words if len(w) > 1]
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

            raw_words = line.split(" ")
            reduced_words = []
            for w in raw_words:
                # Don't include 1-character "words"
                if len(w) > 1:
                    reduced_words.append(w)

            # Store filename and count
            word_count += len(reduced_words)

    # Sometimes the word count is negative. I don't know why.
    if word_count < 0:
        word_count = 0
    return word_count


def walkFiles(file_names):
    """
    Walks through the directory structure
    @param file_names: A list of files and directories to walk through.
    @param results_flat: A string to store the results in.
    @return: A list of dictionaries containing the filename and word count.
    """

    results = []
    results_flat = "filename,words\n"
    # Open all the files or folders.
    for name in file_names:
        # Check to make sure it exists
        if not os.path.exists(name):
            print("File not found: " + name)
            continue

        for root, dirs, thing in os.walk(name):
            for d in dirs:
                # We're only keeping certain directories.
                # TODO: Handle the drafts directory properly.
                if d not in ["html", "problem", "vertical", "static", "tabs"]:
                    continue
                # Add the directory name to the flat results.
                results_flat += "\n" + d + "\n"
                # Walk through the directory.
                for root, dirs, files in os.walk(os.path.join(name, d)):
                    # If this is the HTML directory, skip the XML files.
                    if d == "html":
                        files = [f for f in files if f[-4:] != ".xml"]
                    for f in files:
                        # Only open files with specific extensions.
                        ext = os.path.splitext(f)[1]
                        if ext not in [".xml", ".html", ".md", ".srt"]:
                            continue
                        with open(os.path.join(name, d, f), "r") as g:
                            # print(os.path.basename(g.name))
                            count = countWords(g, ext)
                            results.append(
                                {
                                    "name": os.path.basename(g.name),
                                    "word_count": count
                                }
                            )
                            results_flat += os.path.basename(g.name) + "," + str(count) + "\n"

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
        # print(r["name"] + ": " + str(r["word_count"]))
    
    print("Total words:" + str(total_count))

    # Put them in a file.
    new_file = open(args.o, "w")
    new_file.write(results_flat)
    new_file.close()


if __name__ == "__main__":
    WordCount(sys.argv)
