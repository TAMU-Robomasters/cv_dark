

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


def find_contours_list(frame, is_grayscale=False, save_output=False):
    if not is_grayscale:
        frame = cv.cvtColor(frame, cv.COLOR_BGR2GRAY)

    #ret, thresh = cv.threshold(frame, 127, 255, 0)
    #im2, contours, hierarchy = cv.findContours(thresh, cv.RETR_TREE, cv.CHAIN_APPROX_SIMPLE)
    return cv.findContours(frame, cv.RETR_LIST, cv.CHAIN_APPROX_SIMPLE)


def draw_contours(frame, contours: list, color=(0,255,0)):
    cv.drawContours(frame, contours, -1, color, 2) 


def filter_contours(contours:list, hierarchy, debug_text=False):
    # The below code was modified from https://stackoverflow.com/a/63934162/25598210
    contours = list(contours)
    for i in range(len(contours)):
        x, y, w, h = cv.boundingRect(contours[i])
        #aspect_ratio = float(w) / h

        #area = cv.contourArea(cnt)
        #x, y, w, h = cv.boundingRect(cnt)
        #rect_area = w * h
        #extent = float(area) / rect_area

        #hull = cv.convexHull(cnt)
        #hull_area = cv.contourArea(hull)
        #solidity = float(area) / hull_area

        #equi_diameter = np.sqrt(4 * area / np.pi)

        # if conditions not met
        #TODO: Fix all of this
        if not (w>8 and h>8):
            print(hierarchy[0])
            print(f"Removing from index {i}")
            contours = contours
            print(hierarchy[0][np.where(hierarchy[0][0] != i)])
            hierarchy[0] = np.delete(hierarchy[0], (0,i), axis=0)
            exit()
            
        #(x, y), (MA, ma), Orientation = cv.fitEllipse(cnt)


    return tuple(contours), hierarchy


def find_and_draw_contours(frame, frame_to_write_ontop_of, save_output=False):

    frame = cv.cvtColor(frame, cv.COLOR_BGR2GRAY)
    contours_tree, hierarchy_tree = cv.findContours(frame, cv.RETR_TREE, cv.CHAIN_APPROX_SIMPLE)
    
    # filter_contours isn't working right now - fix it later
    #contours_tree, hierarchy_tree = filter_contours(contours_tree,hierarchy_tree)
    frame = cv.cvtColor(frame, cv.COLOR_GRAY2BGR)

    #print "contours:",len(contours)
    #print "largest contour has ",len(contours[0]),"points"

    # a lot of this I got from https://stackoverflow.com/a/74620309/25598210
    draw_contours(frame_to_write_ontop_of,contours_tree,color=(0,150,0))

    parent_instances = {}
    highest_instance = (0,0)

    for i in range(len(hierarchy_tree[0])-1):
        #[next, previous, first child, parent]
        #print(f"Contour {i} - {hierarchy_tree[0,i]}")

        if hierarchy_tree[0,i][3] != -1:
            #print(f"Has parent of {hierarchy_tree[0,i][3]}")
            if not (hierarchy_tree[0,i][3] in parent_instances.keys()):
                parent_instances[hierarchy_tree[0,i][3]]=1
            else:
                parent_instances[hierarchy_tree[0,i][3]]+=1
            
            if parent_instances[hierarchy_tree[0,i][3]]>highest_instance[1]:
                highest_instance = (hierarchy_tree[0,i][3], parent_instances[hierarchy_tree[0,i][3]])
    
    #print(f"Highest instance of {highest_instance}")


    for i in range(len(hierarchy_tree[0])-1):
        if hierarchy_tree[0,i][3]==highest_instance[0]:
            #print(f"Contour {i} - {hierarchy_tree[0,i]}")
            #print(f"{hierarchy_tree[0,i][0]} Has parent of {hierarchy_tree[0,i][3]}")
            draw_contours(frame_to_write_ontop_of, [contours_tree[hierarchy_tree[0,i][0]]],color=(255,0,255))
    
    draw_contours(frame_to_write_ontop_of, [contours_tree[highest_instance[0]]],color=(255,249,130))
    
    cv.rectangle(frame_to_write_ontop_of, cv.boundingRect(contours_tree[highest_instance[0]]), (0, 0, 255), 4)


    #draw_contours(frame_original, contours_tree,color=(255,0,255))
    
    if save_output:
        print(f" Found {len(contours_tree)} contours.")
        print("largest contour has ",len(contours_tree[highest_instance[0]]),"points")

        cv.imwrite("/home/drewwingfield/TAMURobomasters/cv_dark.git/drew_detection/source/contours.png", frame_to_write_ontop_of)




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

    fourcc_ontop = cv.VideoWriter_fourcc(*'mp4v')
    writer_ontop = cv.VideoWriter(
        "/home/drewwingfield/TAMURobomasters/cv_dark.git/drew_detection/source/output_ontop.mp4",
        fourcc=fourcc_ontop,
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
            
            find_and_draw_contours(new_frame, frame, save_output=False)
            
            writer_ontop.write(frame)

            writer.write(new_frame)

        else:
            print("End of video")
            break

    cap.release()
    writer.release()
    writer_ontop.release()


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

    find_and_draw_contours(img, img, save_output=True)

    cv.imwrite("/home/drewwingfield/TAMURobomasters/cv_dark.git/drew_detection/source/output.png", img)

#endregion Functions

#region Procedural



do_video(False,False)
#do_image()


# When everything done, release the capture
print("program complete!")

#endregion Procedural

# -- end of file --