

#region imports
from tempfile import mkstemp
from shutil import move, copymode
from os import fdopen, remove
import re
from pathlib import Path # for directory traversal
#endregion imports

# With help from https://stackoverflow.com/a/17141572/25598210
# and https://stackoverflow.com/a/39110/25598210

#region functions
def replace_caps(inpt):
    inpt = inpt.group(0)[:-1] + inpt.group(0)[-1].upper()
    return inpt


def blocks(files, size=65536):
    # See count_file_lines function
    # with help from https://stackoverflow.com/a/9631635/25598210
    while True:
        b = files.read(size)
        if not b: break
        yield b

def count_file_lines(file_path, size=1024*3) -> int:
    # Get the amount of lines in the file
    # with help from https://stackoverflow.com/a/9631635/25598210

    with open(file_path, "r",encoding="utf-8",errors='ignore') as f:
        return (sum(bl.count("\n") for bl in blocks(f,size)))


def fix_comments_in_file(the_path, debug=0, dry_run=False):
    """
    Fixes the comment capitalization in a file, overwriting the file with the new version.
    Setting dry_run to true does all calculation, but doesn't save the files.
    returns the total number of lines run through.
    Setting debug to -1 disables all printing.
    """
    # Get total lines
    total_lines = count_file_lines(the_path)

    #Create temp file
    fh, abs_path = mkstemp()
    with fdopen(fh,'w') as new_file:
        with open(the_path) as old_file:
            current_line = 0
            for line in old_file:
                current_line+=1
                if debug>0: print(f"Line {current_line}/{total_lines}")
                elif debug>-1: print(f"|            Line {current_line}/{total_lines}  ",end='\r')

                if debug>0: print(f" The raw line is      '{line}'".replace("\n",""))
                new_line = re.sub(r"# [a-z]", replace_caps, line)
                if debug>0: print(f" The subst. string is '{new_line}'".replace("\n",""))
                #new_file.write(line.replace(r"# [A-Z]", r"# [A-Z]"))
                new_file.write(new_line)
                #/home/drewwingfield/TAMURobomasters/cv_dark.git/main/comment_fix.py
            
            if debug==0: print() # Extra linebreak for carriage return


    if not(dry_run):
        # Copy the file permissions from the old file to the new file
        copymode(the_path, abs_path)
        # Remove original file
        remove(the_path)
        # Move new file
        move(abs_path, the_path)
    
    return total_lines


def traverse_directory(dir_path, extension=".py", dry_run=False):
    """
    Fix the comments in all files with the given extension in the directory.
    Directory traversal with help from https://stackoverflow.com/a/18394205/25598210
    """
    # Get the extension regular expression
    if extension[0]==".": extension=extension[1:] # remove the first period if any

    extension_regex = "".join(["["+a.lower()+a.upper()+"]" for a in extension])
    extension_regex = "*."+extension_regex
    #print(f"extension_regex='{extension_regex}'") #debug

    # Create the generator object for all files
    result = list(Path(dir_path).rglob(extension_regex))

    #print(f"result (type {type(result)}): ")
    #print(result)

    number_of_files = len(result)
    all_file_lines = 0

    n=0 # Counter of current file
    for file in result:
        n+=1
        print(f"| {n}/{number_of_files}  "+str(file))
        all_file_lines+=fix_comments_in_file(file, dry_run=dry_run, debug=-1)
    
    print(f" Traversed {number_of_files} files, reading {all_file_lines} lines.")

#endregion functions


#the_path = input("The path: \n>")
the_path = "/home/drewwingfield/TAMURobomasters/cv_dark.git/main/comment_fix.py"

#fix_comments_in_file(the_path)

dir_to_traverse = "main"
print("raw dir to traverse: "+str(dir_to_traverse))
#dir_to_traverse = Path(dir_to_traverse).resolve()
#print("absolute dir to traverse: "+str(dir_to_traverse))

traverse_directory(dir_to_traverse, "py", dry_run=True)


#TODO: Remove the below, uncited copypaste
#import os
#cwd = os.getcwd()
#print("current working directory: "+str(cwd))
