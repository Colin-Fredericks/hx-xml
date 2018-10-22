import sys
if sys.version_info <= (3, 0):
    sys.exit('I am a Python 3 script. Run me with python3.')

import os
import argparse
from bs4 import BeautifulSoup
import lxml
from glob import glob
import unicodecsv as csv # https://pypi.python.org/pypi/unicodecsv/0.14.1


instructions = """
To use:
python3 SetWeeksForAudit.py path/to/course.xml (number) (options)

Run this on a course folder, or a course.xml file inside an edX course folder (from export).
Use the required --weeks # argument to set the number of sections
where all assignments will be visible to audit learners.

This script may fail on courses with empty containers.

Last update: October 22nd, 2018
"""


# Many of these are being skipped because they're currently expressed in inline XML
# rather than having their own unique folder in the course export.
# These will be moved out as we improve the parsing.
skip_tags = [
    'annotatable', # This is the older, deprecated annotation component.
    'lti',  # This is the older, deprecated LTI component.
    'oppia',
    'openassessment', # This is the older, deprecated ORA.
    'poll_question', # This is the older, deprecated poll component.
    'problem-builder',
    'recommender',
    'step-builder',
    'wiki'
]

# List of all the gradeable components in edX
gradeable_tags = [
        'drag-and-drop-v2',
        'imageannotation',
        'lti_consumer',
        'problem',
        'textannotation',
        'ubcpi',
        'videoannotation',
]


# Always gets the display name.
# For video and problem files, gets other info too
def getComponentInfo(folder, filename, child, args):

    # Try to open file.
    try:
        tree = lxml.etree.parse(folder + '/' + filename + '.xml')
        root = tree.getroot()
    except OSError:
        # If we can't get a file, try to traverse inline XML.
        root = child

    temp = {
        'type': root.tag,
        'name': '',
        # space for other info
    }

    # get display_name or use placeholder
    if 'display_name' in root.attrib:
        temp['name'] = root.attrib['display_name']
    else:
        temp['name'] = root.tag

    # Label all of them as components regardless of type.
    temp['component'] = temp['name']
    # Note whether they're gradeable items
    if root.tag in gradeable_tags:
        temp['gradeable'] = True

    return {'contents': temp, 'parent_name': temp['name']}


# Recursion function for outline-declared xml files
def drillDown(folder, filename, root, args):

    # Try to open file.
    try:
        tree = lxml.etree.parse(os.path.join(folder, (filename + '.xml')))
        root = tree.getroot()
    except IOError:
        # If we can't get a file, try to traverse inline XML.
        ddinfo = getXMLInfo(folder, root, args)
        if ddinfo:
            return ddinfo
        else:
            print('Possible missing file or empty XML element: ' + os.path.join(folder, (filename + '.xml')))
            return {'contents': [], 'parent_name': '', 'found_file': False}

    return getXMLInfo(folder, root, args)


def getXMLInfo(folder, root, args):

    # We need lists of container nodes and leaf nodes so we can tell
    # whether we have to do more recursion.
    leaf_nodes = [
        'discussion',
        'done',
        'drag-and-drop-v2',
        'html',
        'imageannotation',
        'library_content',
        'lti_consumer',
        'poll',
        'problem',
        'survey',
        'textannotation',
        'ubcpi',
        'video',
        'videoannotation',
        'word_cloud'
    ]
    branch_nodes = [
        'course',
        'chapter',
        'sequential',
        'vertical',
        'split_test',
        'conditional'
    ]

    contents = []

    # Some items are created without a display name; use their tag name instead.
    if 'display_name' in root.attrib:
        display_name = root.attrib['display_name']
    else:
        display_name = root.tag

    for index, child in enumerate(root):
        temp = {
            'index': index,
            'type': child.tag,
            'name': '',
            'url': '',
            'contents': [],
            'links': [],
            'images': [],
            'sub': []
        }

        # get display_name or use placeholder
        if 'display_name' in child.attrib:
            temp['name'] = child.attrib['display_name']
        else:
            temp['name'] = child.tag + str(index)
            temp['tempname'] = True

        # get url_name but there are no placeholders
        # Note that even some inline XML have url_names.
        if 'url_name' in child.attrib:
            temp['url'] = child.attrib['url_name']
        else:
            temp['url'] = None

        # In the future: check to see whether this child is a pointer tag or inline XML.
        nextFile = os.path.join(os.path.dirname(folder), child.tag)
        if child.tag in branch_nodes:
            child_info = drillDown(nextFile, temp['url'], child, args)
            temp['contents'] = child_info['contents']
        elif child.tag in leaf_nodes:
            child_info = getComponentInfo(nextFile, temp['url'], child, args)
            # For leaf nodes, add item info to the dict
            # instead of adding a new contents entry
            temp.update(child_info['contents'])
            del temp['contents']
        elif child.tag in skip_tags:
            child_info = {'contents': False, 'parent_name': child.tag}
            del temp['contents']
        else:
            sys.exit('New tag type found: ' + child.tag)

        # If the display name was temporary, replace it.
        if 'tempname' in temp:
            temp['name'] = child_info['parent_name']
            del temp['tempname']

        # We need not only a name, but a custom key with that name.
        temp[temp['type']] = temp['name']

        contents.append(temp)

    return {'contents': contents, 'parent_name': display_name, 'found_file': True}


# Gets the full set of data headers for the course.
# flat_course is a list of dictionaries.
def getAllKeys(flat_course, key_set=set()):

    for row in flat_course:
        for key in row:
            key_set.add(key)

    return key_set


# Ensure that all dicts have the same entries, adding blanks if needed.
# flat_course is a list of dictionaries.
def fillInRows(flat_course):

    # Get a list of all dict keys from the entire nested structure and store it in a set.
    key_set = getAllKeys(flat_course)

    # Iterate through the list and add blank entries for any keys in the set that aren't present.
    for row in flat_course:
        for key in key_set:
            if key not in row:
                row[key]=''

    return flat_course

# Takes a nested structure of lists and dicts that represents the course
# and returns a single list of dicts where each dict is a component
def CourseFlattener(course_dict, new_row={}):
    flat_course = []
    temp_row = new_row.copy()

    # Add all the data from the current level to the current row except 'contents'.
    for key in course_dict:
        if key is not 'contents':
            temp_row[key] = course_dict[key]

    # If the current structure has "contents", we're not at the bottom of the hierarchy.
    if 'contents' in course_dict:
        # Go down into each item in "contents" and add its contents to the course.
        for entry in course_dict['contents']:
            temp = CourseFlattener(entry, temp_row)
            if temp:
                flat_course = flat_course + temp
        return flat_course

    # If there are no contents, we're at the bottom.
    else:
        # Don't include the wiki and certain other items.
        if temp_row['type'] not in skip_tags:
            return [temp_row]

def SetAuditVis(all_gradeable, gradeable_to_change, rootFileDir):
    unfound_tags = []
    num_files = 0
    num_changed_files = 0
    gradeable_url_names = [x['url'] for x in all_gradeable]
    change_url_names = [x['url'] for x in gradeable_to_change]

    folders_to_walk = set([x['type'] for x in all_gradeable])
    graded_item_folders = [os.path.join(rootFileDir, x) for x in folders_to_walk]

    for folder in graded_item_folders:
        # Walk through the folder for each type of tag in the list.
        for dirpath, dirnames, filenames in os.walk(folder):
            for eachfile in filenames:
                thisProbType = []

                # Get the XML for each file. When we can't, keep a list.
                try:
                    tree = lxml.etree.parse(os.path.join(dirpath, eachfile))
                    root = tree.getroot()
                except OSError:
                    unfound_tags.append(eachfile)
                    break


                # Remove any existing audit visibility for all gradeable items.
                # if eachfile in gradeable_url_names:
                #   root.set('visibility','')
                # Set audit visibility for the ones we want to change.
                if os.path.splitext(eachfile)[0] in change_url_names:
                    num_changed_files += 1
                    # root.set('visibility','audit')

                # Save the file
                # tree.write(os.path.join(dirpath, eachfile), encoding='UTF-8', xml_declaration=False)
                num_files += 1

    if num_files == 0:
        print('No files found - wrong or empty directory?')
    else:
        print('Visibility set for ' + str(num_files) + ' files.')
        print(str(num_changed_files) + ' made visible.')
        if len(unfound_tags) > 0:
            print('Could not set visibility for the following items:')
            print(unfound_tags)


# Main function
def SetWeeksForAudit(args = ['-h']):

    # Handle arguments and flags
    parser = argparse.ArgumentParser(usage=instructions, add_help=False)
    parser.add_argument('--help', '-h', action='store_true')
    parser.add_argument('-weeks', default='3', action='store')
    parser.add_argument('file_names', nargs='*')

    # "extra" will help us deal with out-of-order arguments.
    args, extra = parser.parse_known_args(args)

    if args.help: sys.exit(instructions)

    # Replace arguments with wildcards with their expansion.
    # If a string does not contain a wildcard, glob will return it as is.
    # Mostly important if we run this on Windows systems.
    file_names = list()
    for arg in args.file_names:
        file_names += glob(arg)
    for item in extra:
        file_names += glob(item)

    # Don't run the script on itself.
    if sys.argv[0] in file_names:
        file_names.remove(sys.argv[0])

    # If the filenames don't exist, say so and quit.
    if file_names == []:
        sys.exit('No file or directory found by that name.')

    # Get the course.xml file and root directory
    for name in file_names:
        if os.path.isdir(name):
            if os.path.exists( os.path.join(name, 'course.xml')):
                rootFileDir = name
        else:
            if 'course.xml' in name:
                rootFileDir = os.path.dirname(name)

        rootFilePath = os.path.join(rootFileDir, 'course.xml')
        course_tree = lxml.etree.parse(rootFilePath)

        # Open course's root xml file
        # Get the current course run filename
        course_root = course_tree.getroot()

        course_dict = {
            'type': course_root.tag,
            'name': '',
            'url': course_root.attrib['url_name'],
            'contents': []
        }

        course_info = drillDown(
            os.path.join(rootFileDir, course_dict['type']),
            course_dict['url'],
            course_root,
            args
        )
        course_dict['name'] = course_info['parent_name']
        course_dict['contents'] = course_info['contents']

        flat_course = fillInRows(CourseFlattener(course_dict))

        # Get all the problem url_names period.
        all_gradeable = [x for x in flat_course if x['gradeable'] == True]
        # Get all the problem url_names that need to be changed.
        gradeable_to_change = [y for y in all_gradeable if y['index'] < int(args.weeks)]
        # Set audit visibility for all problems.
        SetAuditVis(all_gradeable, gradeable_to_change, rootFileDir)



if __name__ == "__main__":
    # this won't be run when imported
    SetWeeksForAudit(sys.argv)
