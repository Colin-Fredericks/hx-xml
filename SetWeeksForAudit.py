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
        'openassessment',
        'problem',
        'textannotation',
        'ubcpi',
        'videoannotation',
]


def getComponentInfo(folder, filename, child, week, args):

    isFile = False
    isGradeable = False
    isInRightWeek = False

    # Try to open file.
    try:
        tree = lxml.etree.parse(folder + '/' + filename + '.xml')
        root = tree.getroot()
        isFile = True
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
    # Remove any existing audit visibility for all gradeable items.
    if root.tag in gradeable_tags:
        isGradeable = True
        # print('found gradeable tag: ' + temp['name'])
        # root.set('visibility','')
        # If it's early enough in the course, set it to visible.
        if week <= int(args.weeks):
            isInRightWeek = True
            pass
            # print('making ' + temp['name'] + ' visible.')
            # root.set('visibility','audit')

        # If this is a file, save it. If not, report back to the parent.
        if isFile:
            # tree.write(os.path.join(folder, filename), encoding='UTF-8', xml_declaration=False)
            pass

    return {
        'contents': temp,
        'parent_name': temp['name'],
        'was_gradeable_fragment': isGradeable and not isFile and isInRightWeek
    }


# Recursion function for outline-declared xml files
def drillDown(folder, filename, root, week, args):

    # Try to open file.
    try:
        tree = lxml.etree.parse(os.path.join(folder, (filename + '.xml')))
        root = tree.getroot()
    except IOError:
        # If we can't get a file, try to traverse inner XML.
        # Don't redefine the root element.
        pass

    drill_down_info = getXMLInfo(folder, root, week, args)
    if drill_down_info:
        if drill_down_info['gradeable_children']:
            print(drill_down_info['parent_name'] + ' in week ' + str(week) + ' has gradeable children, writing file.')
            # tree.write(os.path.join(folder, filename), encoding='UTF-8', xml_declaration=False)
        return drill_down_info
    else:
        print('Possible missing file or empty XML element: ' + os.path.join(folder, (filename + '.xml')))
        return {'contents': [], 'parent_name': ''}


def getXMLInfo(folder, root, week, args):

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
        'openassessment',
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
    gradeable_children = False

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
            'url_name': '',
            'contents': []
        }

        if root.tag == 'course':
            week += 1

        # get display_name or use placeholder
        if 'display_name' in child.attrib:
            temp['name'] = child.attrib['display_name']
        else:
            temp['name'] = child.tag + str(index)
            temp['tempname'] = True

        # get url_name but there are no placeholders
        # Note that even some inline XML have url_names.
        if 'url_name' in child.attrib:
            temp['url_name'] = child.attrib['url_name']
        else:
            temp['url_name'] = None

        nextFile = os.path.join(os.path.dirname(folder), child.tag)
        if child.tag in branch_nodes:
            child_info = drillDown(nextFile, temp['url_name'], child, week, args)
            temp['contents'] = child_info['contents']
        elif child.tag in leaf_nodes:
            child_info = getComponentInfo(nextFile, temp['url_name'], child, week, args)
            if child_info['was_gradeable_fragment']:
                gradeable_children = True
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

    return {'contents': contents, 'parent_name': display_name, 'gradeable_children': gradeable_children}


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
            'url_name': course_root.attrib['url_name'],
            'contents': []
        }

        course_info = drillDown(
            os.path.join(rootFileDir, course_dict['type']),
            course_dict['url_name'],
            course_root,
            0,
            args
        )


if __name__ == "__main__":
    # this won't be run when imported
    SetWeeksForAudit(sys.argv)
