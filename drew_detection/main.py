

# drew_detection/main.py
# Started by Drew Wingfield
# on 2024/09/19

# usbipd attach --wsl --busid=4-1

# With lots of help (and code) from the docs:
# https://docs.opencv.org/

#region Imports
import numpy
import cv2 as cv
import sys


#endregion Imports


#region Constants
#endregion Constants


#region Classes
#endregion Classes


#region Functions
#endregion Functions

#region Procedural



img = cv.imread(cv.samples.findFile("/home/drewwingfield/TAMURobomasters/cv_dark.git/drew_detection/source/WIN_20240921_11_21_53_Pro.jpg"))
if img is None:
    sys.exit("Could not read the image.")
cv.imshow("Display window", img)
k = cv.waitKey(0)
if k == ord("s"):
    cv.imwrite("/home/drewwingfield/TAMURobomasters/cv_dark.git/drew_detection/source/WIN_20240921_11_21_53_Pro.png", img)

# When everything done, release the capture
print("program complete!")

#endregion Procedural

# -- end of file --