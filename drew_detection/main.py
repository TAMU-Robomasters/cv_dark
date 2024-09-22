

# drew_detection/main.py
# Started by Drew Wingfield
# on 2024/09/19

# usbipd attach --wsl --busid=4-1

# With lots of help (and code) from the docs:
# https://docs.opencv.org/

#region Imports
import numpy as np
import cv2 as cv
import sys


#endregion Imports


#region Constants
#endregion Constants


#region Classes
#endregion Classes


#region Functions
def filter_yellow(frame, save_output=False):
    # Threshold of blue in HSV space 
    yellow_lower = np.array([50, 120, 85])
    yellow_upper = np.array([80, 255, 255])

    # preparing the mask to overlay 
    mask = cv.inRange(img, yellow_lower, yellow_upper) 

    # The black region in the mask has the value of 0, 
    # so when multiplied with original image removes all non-blue regions 
    result = cv.bitwise_and(img, img, mask = mask) 

    if save_output:
        cv.imwrite("/home/drewwingfield/TAMURobomasters/cv_dark.git/drew_detection/source/yellow.png", 
            result)
        cv.imwrite("/home/drewwingfield/TAMURobomasters/cv_dark.git/drew_detection/source/mask.png", 
            mask)
    
    return result

def clean_image(frame,save_output=False):

    kernel = np.ones((5,5),np.uint8)
    frame = cv.morphologyEx(frame, cv.MORPH_OPEN, kernel)
    if save_output:
        cv.imwrite("/home/drewwingfield/TAMURobomasters/cv_dark.git/drew_detection/source/morph_open.png", frame)
    
    frame = cv.morphologyEx(frame, cv.MORPH_CLOSE, kernel)
    if save_output:
        cv.imwrite("/home/drewwingfield/TAMURobomasters/cv_dark.git/drew_detection/source/morph_close.png", frame)

    # Sharpening
    #kernel = np.array([[-1,-1,-1], [-1,9,-1], [-1,-1,-1]])
    #frame = cv.filter2D(frame, -1, kernel)
    #if save_output:
    #    cv.imwrite("/home/drewwingfield/TAMURobomasters/cv_dark.git/drew_detection/source/sharpen.png", frame)

    return frame

#endregion Functions

#region Procedural



img = cv.imread(cv.samples.findFile("/home/drewwingfield/TAMURobomasters/cv_dark.git/drew_detection/source/WIN_20240921_11_21_53_Pro.jpg"))
if img is None:
    sys.exit("Could not read the image.")

img = filter_yellow(img,save_output=True)

img = clean_image(img,save_output=True)

cv.imwrite("/home/drewwingfield/TAMURobomasters/cv_dark.git/drew_detection/source/output.png", img)

# When everything done, release the capture
print("program complete!")

#endregion Procedural

# -- end of file --