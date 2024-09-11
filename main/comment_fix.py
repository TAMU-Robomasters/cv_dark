# this is a comment
from tempfile import mkstemp
from shutil import move, copymode
from os import fdopen, remove
import re
# With help from https://stackoverflow.com/a/17141572/25598210
# and https://stackoverflow.com/a/39110/25598210

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



def fix_comments_in_file(the_path, debug=0):
    """
    Fixes the comment capitalization in a file, overwriting the file with the new version.
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
                else: print(f" Line {current_line}/{total_lines}  ",end='\r')

                if debug>0: print(f" The raw line is      '{line}'".replace("\n",""))
                new_line = re.sub(r"# [a-z]", replace_caps, line)
                if debug>0: print(f" The subst. string is '{new_line}'".replace("\n",""))
                #new_file.write(line.replace(r"# [A-Z]", r"# [A-Z]"))
                new_file.write(new_line)
                #/home/drewwingfield/TAMURobomasters/cv_dark.git/main/comment_fix.py
            
            if debug==0: print() # Extra linebreak for carriage return


    # Copy the file permissions from the old file to the new file
    copymode(the_path, abs_path)
    # Remove original file
    remove(the_path)
    # Move new file
    move(abs_path, the_path)



#the_path = input("The path: \n>")
the_path = "/home/drewwingfield/TAMURobomasters/cv_dark.git/main/comment_fix.py"

fix_comments_in_file(the_path)
