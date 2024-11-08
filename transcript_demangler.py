#!usr/bin/python3

import os
import sys
import glob
import chardet

# Get a filename or folder from the command line args.
# If there is no command line argument, use the current working directory.
path: str = sys.argv[1] if len(sys.argv) > 1 else os.getcwd()

# Open any .srt .vtt or .txt files in the folder
for dirpath, dirnames, filenames in os.walk(path):
    if 'venv' in dirpath:
        continue
    for filename in filenames:
        filepath = os.path.join(dirpath, filename)
        if not filename.endswith(('.srt', '.vtt', '.txt')) or filename.startswith('.'):
            continue
        # Attempt to detect character encoding.
        with open(filepath, 'rb') as f_in:
            print()
            print(filename)
            detected = chardet.detect(f_in.read())
            print(detected)
            # If the encoding is not utf-8, try to convert it.
            if detected['encoding'] != 'utf-8':
                with open(filepath, 'r', encoding=detected['encoding']) as f_in:
                    data = f_in.read()
                with open(filepath, 'w', encoding='utf-8') as f_out:
                    f_out.write(data)
                print(f'Converted {filename} from {detected["encoding"]} to utf-8.')
            else:
                print(f'{filename} is already utf-8.')