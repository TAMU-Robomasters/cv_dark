
# receptacle_pose.py
# Started by Drew Wingfield
# on 2024-10-11

# Gets the pose of the receptacle given a frame

#TODO: Implement torch and CUDA support, clean up code, move constants to top of file

#region setup
# Imports
import cv2
import numpy as np
import sys
import os
import time

#endregion setup

LOCAL_PATH = "main/subsystems/nugget_receptacle"


def filter_binarize(frame, save_output=False, save_raw=False):
    """ Takes in BGR, outputs the frame (BGR) and mask (Greyscale) """
    # Convert to hsv
    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    frame = cv2.cvtColor(frame, cv2.COLOR_RGB2HSV)

    # Threshold of yellow in HSV space 
    bounds_lower = np.array([0, 0, 200]) # 50 120 85
    bounds_upper = np.array([255, 255, 255]) # 80 255 255

    # preparing the mask to overlay 
    mask = cv2.inRange(frame, bounds_lower, bounds_upper) 

    # Mask the frame
    result = cv2.bitwise_and(frame, frame, mask = mask) 
    
    # convert back to BGR
    result = cv2.cvtColor(result, cv2.COLOR_HSV2BGR)

    # Save output if respective arguments are true
    if save_output:
        cv2.imwrite(os.path.join(LOCAL_PATH,"yellow.png"), 
            result)
        if save_raw:
            frame = cv2.cvtColor(frame, cv2.COLOR_HSV2BGR)
            cv2.imwrite(os.path.join(LOCAL_PATH,"raw.png"), frame)
        cv2.imwrite(os.path.join(LOCAL_PATH,"mask.png"), mask)

    # Return the result and the mask
    return result, mask


def clean_image(frame,save_output=False):
    """ Returns a cleaned version of a given image in BGR. """
    # Convert to hsv
    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    frame = cv2.cvtColor(frame, cv2.COLOR_RGB2HSV)

    # Use Morph Open to decrease noise
    kernel = np.ones((4,4),np.uint8)
    frame = cv2.morphologyEx(frame, cv2.MORPH_OPEN, kernel)
    if save_output:
        cv2.imwrite(os.path.join(LOCAL_PATH,"morph_open.png"), frame)
    
    # Use Morph Close to decrease noise
    kernel = np.ones((6,7),np.uint8)
    frame = cv2.morphologyEx(frame, cv2.MORPH_CLOSE, kernel)
    if save_output:
        cv2.imwrite(os.path.join(LOCAL_PATH,"morph_close.png"), frame)

    # Sharpening (isn't tuned very well so I'm disabling it for now)
    #kernel = np.array([[-1,-1,-1], [-1,9,-1], [-1,-1,-1]])
    #frame = cv2.filter2D(frame, -1, kernel)
    #if save_output:
    #    cv2.imwrite("/home/drewwingfield/TAMURobomasters/cv_dark.git/drew_detection/source/sharpen.png", frame)
    
    # convert back to BGR
    frame = cv2.cvtColor(frame, cv2.COLOR_HSV2BGR)

    return frame


def find_contours_list(frame, is_grayscale=False, save_output=False): #TODO: remove this - it's a oneliner
    if not is_grayscale:
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    #ret, thresh = cv2.threshold(frame, 127, 255, 0)
    #im2, contours, hierarchy = cv2.findContours(thresh, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    return cv2.findContours(frame, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)


def draw_contours(frame, contours: list, color=(0,255,0)): #TODO: remove this - it's a oneliner
    cv2.drawContours(frame, contours, -1, color, 2) 


def filter_contours(contours:list, debug_text=False):
    # The below code was modified from https://stackoverflow.com/a/63934162/25598210
    contours_rtn = []
    for contour in contours:
        x, y, w, h = cv2.boundingRect(contour)
        #aspect_ratio = float(w) / h
        #area = cv2.contourArea(cnt)
        #x, y, w, h = cv2.boundingRect(cnt)
        #rect_area = w * h
        #extent = float(area) / rect_area
        #hull = cv2.convexHull(cnt)
        #hull_area = cv2.contourArea(hull)
        #solidity = float(area) / hull_area
        #equi_diameter = np.sqrt(4 * area / np.pi)

        # If conditions met
        #TODO: Fix all of this
        if (w>8 and h>8) and (w>10 or h>10):
            contours_rtn.append(contour)

        #(x, y), (MA, ma), Orientation = cv2.fitEllipse(cnt)


    return contours_rtn


def virgin_contours(contours_tree, hierarchy_tree):
    """ Solution taken from https://stackoverflow.com/a/52398603/25598210 """
    ChildContour = hierarchy_tree[0, :,2]

    WithoutChildContour = (ChildContour==-1).nonzero()[0]

    return [ contours_tree[i] for i in WithoutChildContour] # Contours without children


def draw_contour_points(frame, contour, radius=10, thickness=1, color=(255,40,40)):
    for point in contour:
        x, y = point[0]
        cv2.circle(frame, (x, y), radius, color, thickness)


def find_and_draw_contours(frame, frame_to_write_ontop_of, save_output=False, do_draw_contours=True):
    """ Input of BGR """

    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    contours_tree, hierarchy_tree = cv2.findContours(frame, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    
    # filter_contours isn't working right now - fix it later
    #contours_tree, hierarchy_tree = filter_contours(contours_tree,hierarchy_tree)
    frame = cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)

    #print "contours:",len(contours)
    #print "largest contour has ",len(contours[0]),"points"

    # Draw all contours
    # a lot of this I got from https://stackoverflow.com/a/74620309/25598210
    if do_draw_contours: draw_contours(frame_to_write_ontop_of,contours_tree,color=(0,200,200)) #RGB

    #region oldcode
    #TODO: re-enable this stuff later
    # # Draw contours with a certain heigharchy
    # parent_instances = {}
    # highest_instance = (0,0)

    # for i in range(len(hierarchy_tree[0])-1):
    #     #[next, previous, first child, parent]
    #     #print(f"Contour {i} - {hierarchy_tree[0,i]}")

    #     if hierarchy_tree[0,i][3] != -1:
    #         #print(f"Has parent of {hierarchy_tree[0,i][3]}")
    #         if not (hierarchy_tree[0,i][3] in parent_instances.keys()):
    #             parent_instances[hierarchy_tree[0,i][3]]=1
    #         else:
    #             parent_instances[hierarchy_tree[0,i][3]]+=1
            
    #         if parent_instances[hierarchy_tree[0,i][3]]>highest_instance[1]:
    #             highest_instance = (hierarchy_tree[0,i][3], parent_instances[hierarchy_tree[0,i][3]])
    
    # #print(f"Highest instance of {highest_instance}")


    # for i in range(len(hierarchy_tree[0])-1):
    #     if hierarchy_tree[0,i][3]==highest_instance[0]:
    #         #print(f"Contour {i} - {hierarchy_tree[0,i]}")
    #         #print(f"{hierarchy_tree[0,i][0]} Has parent of {hierarchy_tree[0,i][3]}")
    #         draw_contours(frame_to_write_ontop_of, [contours_tree[hierarchy_tree[0,i][0]]],color=(255,0,255))
    
    #endregion oldcode

    virgin_contours_list = virgin_contours(contours_tree, hierarchy_tree)
    virgin_contours_list = filter_contours(virgin_contours_list)

    # Dark green circles for complex contour points
    #for contour in virgin_contours_list:        
    #    draw_contour_points(frame_to_write_ontop_of, contour,color=(0,80,0))


    # Simplify the contours - see https://docs.opencv.org/4.x/dd/d49/tutorial_py_contour_features.html
    EPSILON_CONSTANT = 0.01 #10%

    copy_ = []
    for contour in virgin_contours_list:
        epsilon = EPSILON_CONSTANT*cv2.arcLength(contour,True)
        copy_.append(cv2.approxPolyDP(contour,epsilon,True))
    
    virgin_contours_list = copy_

    # Do some visualization stuff
    if do_draw_contours:
        for contour in virgin_contours_list:
            cv2.rectangle(frame_to_write_ontop_of, cv2.boundingRect(contour), (0, 0, 200), 4)
            
            rect = cv2.minAreaRect(contour) # rotated (for minimum area) rectangle
            cv2.drawContours(frame_to_write_ontop_of,[np.int0(cv2.boxPoints(rect))],0,(0,0,255),1)
            
            draw_contour_points(frame_to_write_ontop_of, contour,color=(0,200,0))

        # Draw contours
        draw_contours(frame_to_write_ontop_of, virgin_contours_list,color=(255,249,130))
    
    # cv2.rectangle(frame_to_write_ontop_of, cv2.boundingRect(contours_tree[highest_instance[0]]), (0, 0, 255), 4)


    #draw_contours(frame_original, contours_tree,color=(255,0,255))
    
    if save_output:
        print(f" Found {len(contours_tree)} total contours.")
        print(f" Found {len(virgin_contours_list)} good contours.")
        #print("largest contour has ",len(contours_tree[highest_instance[0]]),"points")

        cv2.imwrite(os.path.join(LOCAL_PATH,"contours.png"), frame_to_write_ontop_of)

    

def analyze_video(video_path, save_output=False,save_raw=False):
    """ Returns the number of frames """

    print("Now doing video...")

    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS)
    width = int(cap.get(3))
    height = int(cap.get(4))
    print(f"Size {int(width)}x{int(height)} with FPS {fps}")

    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    writer = cv2.VideoWriter(
        os.path.join(LOCAL_PATH,"output.mp4"),
        fourcc=fourcc,
        apiPreference=0,
        fps=fps, 
        frameSize=(width, height)
    )

    fourcc_ontop = cv2.VideoWriter_fourcc(*'mp4v')
    writer_ontop = cv2.VideoWriter(
        os.path.join(LOCAL_PATH,"output_ontop.mp4"),
        fourcc=fourcc_ontop,
        apiPreference=0,
        fps=fps, 
        frameSize=(width, height)
    )

    pos_frame = cap.get(1) #cv2.CV_CAP_PROP_POS_FRAMES

    num_frames=0

    while True:
        num_frames+=1
        flag, frame = cap.read()
        if flag:
            # The frame is ready and already captured
            #cv2.imshow('video', frame)
            pos_frame = cap.get(1)
            print(f"Frame {pos_frame} ",end='\r')
            
            new_frame = clean_image(filter_binarize(frame, save_output=save_output, save_raw=save_raw)[0])
            
            find_and_draw_contours(new_frame, frame, save_output=False)
            
            writer_ontop.write(frame)
            writer.write(new_frame)

        else:
            print("End of video")
            break

    cap.release()
    writer.release()
    writer_ontop.release()

    return num_frames


if __name__ == "__main__":
    print("receptacle_pose was called as main.")

    # Create a VideoCapture object
    #cap = cv2.VideoCapture(os.path.join(LOCAL_PATH,"receptacle_example.mp4"))

    #for i in range(30*25): # Get the frame at 30 seconds
    #    # Read the first frame
    #    ret, frame = cap.read()
    
    frame = cv2.imread(os.path.join(LOCAL_PATH,"receptacle_pdf.png"))
    cv2.imwrite(os.path.join(LOCAL_PATH,"temp.png"), frame)

    frame, mask = filter_binarize(frame,save_output=True)

    #print(frame)
    frame = clean_image(frame, save_output=True)

    frame = find_and_draw_contours(frame, frame, save_output=True)

    #cap.release()
    DO_VIDEO = True

    if DO_VIDEO:
        print("doing video now")
        time_start = time.time()
        num_frames = analyze_video(os.path.join(LOCAL_PATH,"receptacle_example.mp4"))
        time_end = time.time()
        time_taken = time_end - time_start
        print(f"That took {time_taken:.4f} seconds ({num_frames/time_taken:.2f} FPS)")


