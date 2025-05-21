#! usr/bin/python3

import csv
import os
import sys
import shutil

# Get the csv file, target language, and input folder from the command line arguments
if len(sys.argv) != 4:
    print(
        "Usage: python get_transcripts_by_lang.py <csv_file> <target_language> <input_folder>"
    )
    sys.exit(1)

count = 0

csv_file = sys.argv[1]
target_language = sys.argv[2]
input_folder = sys.argv[3]

# Check if the CSV file exists
if not os.path.isfile(csv_file):
    print(f"Error: The file {csv_file} does not exist.")
    sys.exit(1)
# Check for valid language code
if not target_language.isalpha() or len(target_language) != 2:
    print("Error: The target language code must be a 2-letter ISO 639-1 code.")
    sys.exit(1)
# Check if the input folder exists
if not os.path.isdir(input_folder):
    print(f"Error: The folder {input_folder} does not exist.")
    sys.exit(1)

# Read the CSV file
with open(csv_file, "r", encoding="utf-8") as file:
    reader = csv.DictReader(file)

    # Remove all columns except "sub" "component", and "upload_name"
    new_rows = []
    for row in reader:
        if "sub" not in row or "component" not in row or "upload_name" not in row:
            print("Error: The CSV file does not contain the required columns.")
            sys.exit(1)
        if "-" + target_language + ".srt" not in row["sub"]:
            continue
        new_row = {
            "sub": row["sub"],
            "component": row["component"],
            "upload_name": row["upload_name"],
        }
        new_rows.append(new_row)

    # Write the revised rows to a new CSV file
    with open(
        os.path.join(input_folder, "videos.csv"), "w", encoding="utf-8"
    ) as output:
        writer = csv.DictWriter(output, fieldnames=["sub", "component", "upload_name"])
        writer.writeheader()
        writer.writerows(new_rows)

    transcripts = []
    # Copy all matching transcripts to a new folder
    if not os.path.exists("transcripts"):
        os.makedirs("transcripts")
    for row in new_rows:
        # Get the filename
        filename = row["sub"]
        # copy the file to the new folder
        src = os.path.join(input_folder, filename)
        dest = os.path.join("transcripts", filename)
        shutil.copy(src, dest)
        count += 1

print(
    f"Copied {count} transcripts to the 'transcripts' folder and created 'videos.csv' in {input_folder}"
)