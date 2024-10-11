
# receptacle_pose.py
# Started by Drew Wingfield
# on 2024-10-11

# Gets the pose of the receptacle given a frame

#region setup
# Imports
import cv2
import numpy as np

#endregion setup



def filter_yellow(frame, save_output=False, save_raw=False):
    """ TAKES IN BGR """
    # Convert to hsv
    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    frame = cv2.cvtColor(frame, cv2.COLOR_RGB2HSV)

    # Threshold of yellow in HSV space 
    yellow_lower = np.array([16, 60, 30]) # 50 120 85
    yellow_upper = np.array([45, 255, 255]) # 80 255 255

    # preparing the mask to overlay 
    mask = cv2.inRange(frame, yellow_lower, yellow_upper) 

    # Mask the frame
    result = cv2.bitwise_and(frame, frame, mask = mask) 
    
    # convert back to BGR
    result = cv2.cvtColor(result, cv2.COLOR_HSV2BGR)

    # Save output if respective arguments are true
    if save_output:
        cv2.imwrite("/home/drewwingfield/TAMURobomasters/cv_dark.git/drew_detection/source/yellow.png", 
            result)
        if save_raw:
            frame = cv2.cvtColor(frame, cv2.COLOR_HSV2BGR)
            cv2.imwrite("/home/drewwingfield/TAMURobomasters/cv_dark.git/drew_detection/source/raw.png", 
                frame)
        cv2.imwrite("/home/drewwingfield/TAMURobomasters/cv_dark.git/drew_detection/source/mask.png", 
            mask)

    # Return the result and the mask
    return result, mask


def clean_image(frame,save_output=False):
    """ Returns a cleaned version of a given image in BGR. """
    # Convert to hsv
    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    frame = cv2.cvtColor(frame, cv2.COLOR_RGB2HSV)

    # Use Morph Open to decrease noise
    kernel = np.ones((5,5),np.uint8)
    frame = cv2.morphologyEx(frame, cv2.MORPH_OPEN, kernel)
    if save_output:
        cv2.imwrite("/home/drewwingfield/TAMURobomasters/cv_dark.git/drew_detection/source/morph_open.png", frame)
    
    # Use Morph Close to decrease noise
    frame = cv2.morphologyEx(frame, cv2.MORPH_CLOSE, kernel)
    if save_output:
        cv2.imwrite("/home/drewwingfield/TAMURobomasters/cv_dark.git/drew_detection/source/morph_close.png", frame)

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


def filter_contours(contours:list, hierarchy, debug_text=False):
    # The below code was modified from https://stackoverflow.com/a/63934162/25598210
    contours = list(contours)
    for i in range(len(contours)):
        x, y, w, h = cv2.boundingRect(contours[i])
        #aspect_ratio = float(w) / h
        #area = cv2.contourArea(cnt)
        #x, y, w, h = cv2.boundingRect(cnt)
        #rect_area = w * h
        #extent = float(area) / rect_area
        #hull = cv2.convexHull(cnt)
        #hull_area = cv2.contourArea(hull)
        #solidity = float(area) / hull_area
        #equi_diameter = np.sqrt(4 * area / np.pi)

        # If conditions not met
        #TODO: Fix all of this
        if not (w>8 and h>8):
            print(hierarchy[0])
            print(f"Removing from index {i}")
            contours = contours
            print(hierarchy[0][np.where(hierarchy[0][0] != i)])
            hierarchy[0] = np.delete(hierarchy[0], (0,i), axis=0)
            exit()
            
        #(x, y), (MA, ma), Orientation = cv2.fitEllipse(cnt)


    return tuple(contours), hierarchy


def find_and_draw_contours(frame, frame_to_write_ontop_of, save_output=False):

    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    contours_tree, hierarchy_tree = cv2.findContours(frame, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    
    # filter_contours isn't working right now - fix it later
    #contours_tree, hierarchy_tree = filter_contours(contours_tree,hierarchy_tree)
    frame = cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)

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
    
    cv2.rectangle(frame_to_write_ontop_of, cv2.boundingRect(contours_tree[highest_instance[0]]), (0, 0, 255), 4)


    #draw_contours(frame_original, contours_tree,color=(255,0,255))
    
    if save_output:
        print(f" Found {len(contours_tree)} contours.")
        print("largest contour has ",len(contours_tree[highest_instance[0]]),"points")

        cv2.imwrite("/home/drewwingfield/TAMURobomasters/cv_dark.git/drew_detection/source/contours.png", frame_to_write_ontop_of)

    


if __name__ == "__main__":
    print("receptacle_pose was called as main.")

        # Create a VideoCapture object
    cap = cv2.VideoCapture("main/subsystems/nugget_receptacle/receptacle_example.mp4")

    # Read the first frame
    ret, frame = cap.read()

    cv2.imwrite("main/subsystems/nugget_receptacle/temp.png", frame)

