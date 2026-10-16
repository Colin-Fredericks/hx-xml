import argparse
import csv
import os
import xml.etree.ElementTree as ET

found_ids = []


def main():
    """
    Swaps one set of LTI IDs for another.
    Targets files in the "vertical" and "lti_consumer" directories within the course directory.
    """

    instructions = """
    Usage: python3 ed_id_swap.py <course_dir> <id_file.csv> -old <old_column_name> (optional) -new <new_column_name> (optional) 

    <course_dir>: Path to the root "course" directory for an edX course.
    <id_file.csv>: Path to a CSV file. By default, uses column names "2023_id" and "2026_id"
    <old_column_name>: (Optional) The name of the column in the CSV file that contains the old IDs.
    <new_column_name>: (Optional) The name of the column in the CSV file that contains the new IDs.

    This writes over the course files in-place rather than making a duplicate folder.
    It does not touch discussion category names.
    It does not re-zip.
    """

    # Get filename and course directory from command line arguments
    parser = argparse.ArgumentParser(description="Swap LTI IDs in course files.")
    parser.add_argument("course_dir", help="Path to the course directory")
    parser.add_argument("id_csv", help="Path to the CSV file containing ID mappings")
    parser.add_argument(
        "-old",
        "--old_column",
        default="2023_id",
        help="Name of the CSV column with old IDs (default: '2023_id')",
    )
    parser.add_argument(
        "-new",
        "--new_column",
        default="2026_id",
        help="Name of the CSV column with new IDs (default: '2026_id')",
    )
    args = parser.parse_args()

    # If we have the wrong number of arguments, course folder doesn't exist, or the CSV file doesn't exist, print an error and exit
    if not args.course_dir or not args.id_csv:
        print(instructions)
        return
    if not os.path.isdir(args.course_dir):
        print(f"Error: Course directory '{args.course_dir}' does not exist.")
        return
    if not os.path.isfile(args.id_csv):
        print(f"Error: CSV file '{args.id_csv}' does not exist.")
        return

    # Load the id-matching CSV
    id_mapping = {}
    new_id_header = args.new_column
    old_id_header = args.old_column
    with open(args.id_csv, mode="r", encoding="utf-8-sig") as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            old_id = row[old_id_header].strip()
            new_id = row[new_id_header].strip()
            id_mapping[old_id] = new_id

    # Walk the course directory and find all files in "vertical" and "lti_consumer" directories
    for root, dirs, files in os.walk(args.course_dir):
        if "vertical" in root or "lti_consumer" in root:
            for file in files:
                if file.endswith(".xml"):
                    # Process the XML file
                    process_xml_file(os.path.join(root, file), id_mapping)

    print("Finished processing.")
    if len(found_ids) > 0:
        print("The following old IDs were found and swapped:")
        for old_id in found_ids:
            print(old_id)
    else:
        print("No old IDs were found in the course files.")


def process_xml_file(file_path, id_mapping):
    """
    Processes an XML file, swapping old LTI IDs for new ones based on the provided mapping.
    """
    tree = ET.parse(file_path)
    root = tree.getroot()
    modified = False

    # Get the `lti_1p3_launch_url` attribute from the <lti_consumer> tag
    for consumer in root.findall(".//lti_consumer"):
        launch_url = consumer.get("lti_1p3_launch_url", "")
        for old_id, new_id in id_mapping.items():
            # If one of the old IDs is in the launch URL, swap it for the new ID
            if old_id in launch_url:
                new_launch_url = launch_url.replace(old_id, new_id)
                consumer.set("lti_1p3_launch_url", new_launch_url)
                print(f"Updated {file_path}: {old_id} -> {new_id}")
                modified = True

    if modified:
        # Save the modified XML file
        found_ids.append(old_id)
        tree.write(file_path)

    return modified


if __name__ == "__main__":
    main()
