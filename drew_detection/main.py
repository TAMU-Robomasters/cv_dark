

# drew_detection/main.py
# Started by Drew Wingfield
# on 2024/09/19

# usbipd attach --wsl --busid=4-1

# With lots of help (and code) from the docs:
# https://docs.opencv.org/

#region Imports
import time
import numpy as np
import cv2 as cv
import sys
from PIL import Image


#endregion Imports


#region Constants
#endregion Constants


#region Classes
#endregion Classes


#region Functions
def filter_yellow(frame, save_output=False, save_raw=False):
    """ TAKES IN BGR"""
    #covert to hsv
    frame = cv.cvtColor(frame, cv.COLOR_BGR2RGB)
    #print("\n"*3+"IMG in RGB"+str(frame))

    frame = cv.cvtColor(frame, cv.COLOR_RGB2HSV)
    #print("\n"*3+"IMG in HSV"+str(frame))
    

    # Threshold of yellow in HSV space 
    yellow_lower = np.array([16, 60, 30]) # 50 120 85
    yellow_upper = np.array([45, 255, 255]) # 80 255 255

    # preparing the mask to overlay 
    mask = cv.inRange(frame, yellow_lower, yellow_upper) 

    result = cv.bitwise_and(frame, frame, mask = mask) 
    
    # convert back to BGR
    result = cv.cvtColor(result, cv.COLOR_HSV2BGR)
    #print("\n"*4+"FILTER_YELLOW FRAME:")
    #print(frame)
    
    #for i, row in enumerate(frame):
    #    for j, col in enumerate(frame):
    #        print("aaaaa"+str(frame[row,col,:]))
    #        exit()
    #        frame[row,col,:] = frame[i,j,:]

    if save_output:
        cv.imwrite("/home/drewwingfield/TAMURobomasters/cv_dark.git/drew_detection/source/yellow.png", 
            result)
        if save_raw:
            frame = cv.cvtColor(frame, cv.COLOR_HSV2BGR)
            cv.imwrite("/home/drewwingfield/TAMURobomasters/cv_dark.git/drew_detection/source/raw.png", 
                frame)
        cv.imwrite("/home/drewwingfield/TAMURobomasters/cv_dark.git/drew_detection/source/mask.png", 
            mask)

    return result, mask


def clean_image(frame,save_output=False):

    #covert to hsv
    frame = cv.cvtColor(frame, cv.COLOR_BGR2RGB)
    frame = cv.cvtColor(frame, cv.COLOR_RGB2HSV)

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
    # convert back to BGR
    frame = cv.cvtColor(frame, cv.COLOR_HSV2BGR)

    return frame


def find_contours(frame, is_grayscale=False, save_output=False):
    if not is_grayscale:
        frame = cv.cvtColor(frame, cv.COLOR_BGR2GRAY)

    #ret, thresh = cv.threshold(frame, 127, 255, 0)
    #im2, contours, hierarchy = cv.findContours(thresh, cv.RETR_TREE, cv.CHAIN_APPROX_SIMPLE)
    contours = cv.findContours(frame, cv.RETR_LIST, cv.CHAIN_APPROX_SIMPLE)[0]
    return contours


def draw_contours(frame, contours: list, color=(0,255,0)):
    cv.drawContours(frame, contours, -1, color, 2) 


def filter_contours(contours:list):
    # The below code was modified from https://stackoverflow.com/a/63934162/25598210
    contours_new = []
    contours_excluded = []

    for cnt in contours:
        x, y, w, h = cv.boundingRect(cnt)
        aspect_ratio = float(w) / h

        area = cv.contourArea(cnt)
        x, y, w, h = cv.boundingRect(cnt)
        rect_area = w * h
        extent = float(area) / rect_area

        hull = cv.convexHull(cnt)
        hull_area = cv.contourArea(hull)
        solidity = float(area) / hull_area

        equi_diameter = np.sqrt(4 * area / np.pi)

        if w>10 and h>10 and 0.33<aspect_ratio and aspect_ratio<3:
            contours_new.append(cnt)
            #print(f" Width = {w}  Height = {h} area = {area}  aspect ration = {round(aspect_ratio,3)}  extent  = {extent}  solidity = {round(solidity,4)}   equi_diameter = {round(equi_diameter,3)} ")  #orientation = {Orientation}")
        
        else:
            contours_excluded.append(cnt)

        #(x, y), (MA, ma), Orientation = cv.fitEllipse(cnt)


    return contours_new, contours_excluded


def find_and_draw_contours(frame, save_output=False):
    contours = find_contours(frame, is_grayscale=False)
    #print(f"Found {len(contours)} contours.")
    contours, contours_excluded = filter_contours(contours)

    draw_contours(frame, contours)
    draw_contours(frame, contours_excluded,color=(255,0,255))

    if save_output:
        cv.imwrite("/home/drewwingfield/TAMURobomasters/cv_dark.git/drew_detection/source/contours.png", frame)




def do_video(save_output=False,save_raw=False):
    print("Now doing video...")

    cap = cv.VideoCapture("/home/drewwingfield/TAMURobomasters/cv_dark.git/drew_detection/source/WIN_20240921_11_22_15_Pro.mp4")
    fps = cap.get(cv.CAP_PROP_FPS)
    width = int(cap.get(3))
    height = int(cap.get(4))
    print(f"Size {int(width)}x{int(height)} with FPS {fps}")

    fourcc = cv.VideoWriter_fourcc(*'mp4v')
    writer = cv.VideoWriter(
        "/home/drewwingfield/TAMURobomasters/cv_dark.git/drew_detection/source/output.mp4",
        fourcc=fourcc,
        apiPreference=0,
        fps=fps, 
        frameSize=(width, height)
    )

    pos_frame = cap.get(1) #cv.CV_CAP_PROP_POS_FRAMES

    while True:
        flag, frame = cap.read()
        if flag:
            # The frame is ready and already captured
            #cv.imshow('video', frame)
            pos_frame = cap.get(1)
            print(f"Frame {pos_frame} ")
            
            new_frame = clean_image(filter_yellow(frame, save_output=save_output, save_raw=save_raw)[0])
            
            find_and_draw_contours(new_frame, save_output=False)
            
            writer.write(new_frame)

        else:
            print("End of video")
            break

    cap.release()
    writer.release()


def do_image():
    img = cv.imread(cv.samples.findFile("/home/drewwingfield/TAMURobomasters/cv_dark.git/drew_detection/source/raw.png"))
    if img is None:
        sys.exit("Could not read the image.")

    img = cv.cvtColor(img, cv.COLOR_BGR2RGB)

    #debug: test stripes
    #img[0:20][0:30]   = (255, 0, 0)
    #img[20:40][0:30] = (0, 255, 0)
    #img[40:60][0:30] = (0, 0, 255)

    img = cv.cvtColor(img, cv.COLOR_RGB2BGR)

    img, mask = filter_yellow(img,save_output=True, save_raw=False)

    img = clean_image(img,save_output=True)

    find_and_draw_contours(img, save_output=True)

    cv.imwrite("/home/drewwingfield/TAMURobomasters/cv_dark.git/drew_detection/source/output.png", img)

#endregion Functions

#region Procedural



do_video(False,False)
#do_image()


# When everything done, release the capture
print("program complete!")

#endregion Procedural

# -- end of file --