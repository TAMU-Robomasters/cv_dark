
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

#region Constants
if __name__ == "__main__":
    LOCAL_PATH = os.path.join("main","subsystems","nugget_receptacle")
else:
    LOCAL_PATH = os.path.join("subsystems","nugget_receptacle")

CAMERA_CALIB_PATH = os.path.join(LOCAL_PATH,"CalMatrix.npz") # Path to calibration data for camera.
#endregion Constants


#region Functions

#region Image Stuff
def filter_binarize(frame, save_output=False, save_raw=False):
    """ 
    Filters an image (frame) so that everythign except the LEDs are black.

    Takes in BGR frame, outputs the new frame (BGR) and mask (Greyscale) 
    """
    # Convert to hsv
    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

    # Threshold of colors we want in HSV space 
    bounds_lower = np.array([0, 0, 200]) # 50 120 85
    bounds_upper = np.array([255, 255, 255]) # 80 255 255

    # Preparing the mask to overlay 
    mask = cv2.inRange(frame, bounds_lower, bounds_upper) 

    # Mask the frame
    result = cv2.bitwise_and(frame, frame, mask = mask) 
    
    # Convert the masked frame back to BGR
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
    """ 
    Cleans an image by using Morph Open and Morph Close filters.

    Returns a cleaned version of the given frame in BGR. 
    """
    # Convert to hsv
    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

    # Use Morph Open to decrease noise
    kernel = np.ones((4,4),np.uint8)
    frame = cv2.morphologyEx(frame, cv2.MORPH_OPEN, kernel)
    if save_output:
        cv2.imwrite(os.path.join(LOCAL_PATH,"morph_open.png"), frame)
    
    # Use Morph Close to decrease noise
    kernel = np.ones((4,4),np.uint8)
    frame = cv2.morphologyEx(frame, cv2.MORPH_CLOSE, kernel)
    if save_output:
        cv2.imwrite(os.path.join(LOCAL_PATH,"morph_close.png"), frame)

    # Sharpening (isn't tuned very well so I'm disabling it for now)
    #kernel = np.array([[-1,-1,-1], [-1,9,-1], [-1,-1,-1]])
    #frame = cv2.filter2D(frame, -1, kernel)
    #if save_output:
    #    cv2.imwrite("/home/drewwingfield/TAMURobomasters/cv_dark.git/drew_detection/source/sharpen.png", frame)
    
    # Convert back to BGR
    frame = cv2.cvtColor(frame, cv2.COLOR_HSV2BGR)

    return frame


def draw_contours(frame, contours: list, color=(0,255,0)): #TODO: remove this - it's a oneliner
    cv2.drawContours(frame, contours, -1, color, 2) 

#endregion Image Stuff


#region Contours Stuff
def find_contours_list(frame, is_grayscale=False, save_output=False): #TODO: remove this - it's a oneliner
    if not is_grayscale:
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    #ret, thresh = cv2.threshold(frame, 127, 255, 0)
    #im2, contours, hierarchy = cv2.findContours(thresh, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    return cv2.findContours(frame, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)


def draw_center_of_mass_circles(frame, contours):
    for contour in contours:
        x, y, w, h = cv2.boundingRect(contour)
        center_x = x+(w//2)
        center_y = y+(h//2)

        moments = cv2.moments(contour)
        cx = int(moments['m10'] / moments['m00'])
        cy = int(moments['m01'] / moments['m00'])

        cv2.circle(frame, (x, y),               5, (0,0,255),   1) # red
        cv2.circle(frame, (cx, cy),             8, (13,128,255), 2) # yellowish
        cv2.line(frame, (center_x, center_y), (cx, cy), (0, 255, 0), 2)
        cv2.circle(frame, (center_x, center_y), 6, (255,100,100),   2) # blue

        cv2.rectangle(frame, cv2.boundingRect(contour), (0, 0, 200), 1) 
    
    return frame


def is_l_shape(contour, min_x_percent = 0.05, min_y_percent = 0.05, or_=False) -> tuple:
    """ 
    Returns bool, x_diff_percent, y_diff_percent on whether contour is an l shape and confidence. 
    min_x_percent and min_y_percent are the minimum percentage of the bounding box that 
    the center of mass can be off to be considered an L shape.
    """
    #up-right bounding rectangle
    x, y, w, h = cv2.boundingRect(contour)
    center_x = x+(w//2)
    center_y = y+(h//2)
    

    
    moments = cv2.moments(contour)
    cx = int(moments['m10'] / moments['m00'])
    cy = int(moments['m01'] / moments['m00'])

    percent_off_x = (cx - center_x)/w # TODO: Maybe figure out a way to do floor division (faster?)
    percent_off_y = (cy - center_y)/h

    if __name__ == "__main__":
        #print(f"x={center_x}, y={center_y}, cx={cx}, cy={cy}, x_size={w}, y_size={h}")
        print(f"x={center_x}, y={center_y}, cx is {percent_off_x*100 :.2f}% off, cy is {percent_off_y*100 :.2f}% off.")

    is_l = (
        #    (abs(percent_off_x)>0) 
        #and (abs(percent_off_y)>0)
         (abs(percent_off_x)>min_x_percent) 
        and (abs(percent_off_y)>min_y_percent) 
        or (
            (or_)
            and (
                   (abs(percent_off_x)>min_x_percent) 
                or (abs(percent_off_y)>min_y_percent)
                )
            )
    )
    return is_l, percent_off_x, percent_off_y


def filter_contours(contours:list, screensize=(1920,1024), filter_l=False):
    """ Filters a given list of contours by ones that are likely the receptacle. """
    # The below code was modified from https://stackoverflow.com/a/63934162/25598210
    contours_rtn = []
    max_rect_area = screensize[0] * screensize[1] * 0.75

    for contour in contours:
        x, y, w, h = cv2.boundingRect(contour)
        rect_area = w * h

        # If contour is certain shape
        # (both dimensions > 8px, at least one dimension > 10px)
        if (
                (w>8 and h>8) 
            and (w>10 or h>10) 
            and (rect_area < max_rect_area) 
            and (is_l_shape(contour, or_=True)[0] or not(filter_l))
            ):
            contours_rtn.append(contour) # Add it to the return list


    return contours_rtn


def virgin_contours(contours_tree, hierarchy_tree):
    """
    Given a contours_tree and hierarchy_tree, returns a list of 'virgin' contours
    (contours that have no children).

    Solution taken from https://stackoverflow.com/a/52398603/25598210 
    """
    ChildContour = hierarchy_tree[0, :,2]

    WithoutChildContour = (ChildContour==-1).nonzero()[0]

    return [ contours_tree[i] for i in WithoutChildContour] # Contours without children


def draw_contour_points(frame, contour, radius=10, thickness=1, color=(255,40,40)):
    """ Draws the points of a given contour on a given frame. """
    for point in contour:
        x, y = point[0]
        cv2.circle(frame, (x, y), radius, color, thickness)


def simplify_contour(contour, n_corners=4, print_stats=False):
    '''
    This function was taken from https://stackoverflow.com/a/55339684/25598210
    Binary searches best `epsilon` value to force contour 
        approximation contain exactly `n_corners` points.
        
    :param contour: OpenCV2 contour.
    :param n_corners: Number of corners (points) the contour must contain.
    
    :returns: Simplified contour in successful case. Otherwise returns initial contour.
    '''
    n_iter, max_iter = 0, 100
    lb, ub = 0., 1.
    
    while True:
        n_iter += 1
        if n_iter > max_iter:
            if print_stats: print("[simplify_contour] n_iter>max_iter, returning contour.")
            return contour
        
        k = (lb + ub)/2.
        eps = k*cv2.arcLength(contour, True)
        approx = cv2.approxPolyDP(contour, eps, True)
        
        if len(approx) > n_corners:
            lb = (lb + ub)/2.
        elif len(approx) < n_corners:
            ub = (lb + ub)/2.
        else:
            if print_stats: print(f"[simplify_contour] eps={eps}.")
            return approx


def draw_corners(img, corners, imgpts):
    """ Returns the given image with corners drawn. Function taken from https://docs.opencv.org/4.x/d7/d53/tutorial_py_pose.html """
    corner = tuple(corners[0].ravel())
    img = cv2.line(img, 
    corner, tuple(imgpts[0].ravel()), (255,0,0), 5)
    img = cv2.line(img, corner, tuple(imgpts[1].ravel()), (0,255,0), 5)
    img = cv2.line(img, corner, tuple(imgpts[2].ravel()), (0,0,255), 5)
    return img


def filter_n_contours(contours:list, n:int) -> list:
    """ Filters out n number of contours for likely candidates of the four corners of the receptacle. """
    if len(contours)==0: return [] # Prevent errors
    
    rtnlist = []
    contour_sizes = []

    for contour in contours:
        x, y, w, h = cv2.boundingRect(contour)
        contour_sizes.append(w*h)

    for i in range(n):
        try:
            if len(contours)==0: break
            biggest_contour = contours[contour_sizes.index(max(contour_sizes))]
            rtnlist.append(biggest_contour)
            del contours[contour_sizes.index(max(contour_sizes))]
            contour_sizes.remove(max(contour_sizes))
        
        except IndexError: # If n < len(contours) we eventually hit an index error
            break # Just return whatever we currently have

        except ValueError as e:
            print(f"Value Error, here is some debug info: n={n}, there are {len(contour_sizes)} sizes for {len(contours)} contours. contour_sizes={contour_sizes}, i={i}, rtnlist={rtnlist}")
            raise e

    assert len(rtnlist) <= n
    return rtnlist




def find_and_draw_contours(
    frame, frame_to_write_ontop_of, 
    save_output=False, do_draw_contours=True, 
    screensize=(1920,1024),
    write_l_debug_circles=False,
    save_intermediate=False
    ):
    """
    Findds and draws contours on an image, filtering for valid and virgin contours.
    Frames are BGR. 
    """
    # Grayscale the image and find all the contours
    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    contours_tree, hierarchy_tree = cv2.findContours(frame, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    
    frame = cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)

    if save_intermediate:
        cv2.imwrite(os.path.join(LOCAL_PATH,"fadc_1_greyscale.png"), frame)

    #print "contours:",len(contours)
    #print "largest contour has ",len(contours[0]),"points"

    # Draw all contours
    # a lot of this I got from https://stackoverflow.com/a/74620309/25598210
    #if do_draw_contours: draw_contours(frame_to_write_ontop_of,contours_tree,color=(0,200,200)) # All contours - yellowish - RGB

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
    virgin_contours_list = filter_contours(virgin_contours_list, screensize=screensize, filter_l=False)

    # Simplify the contours - see https://docs.opencv.org/4.x/dd/d49/tutorial_py_contour_features.html
    copy_ = []
    for contour in virgin_contours_list:
        # Simplify the contour
        copy_.append(simplify_contour(contour, n_corners=6))
        #TODO: also look into the Ramer–Douglas–Peucker algorithm for simplification
    
    virgin_contours_list = copy_.copy()
    del copy_

    # Filter contours once more, but with L-shape filtering
    #virgin_contours_list = filter_contours(virgin_contours_list, screensize=screensize, filter_l=True)

    # Filter out the four corners
    big_four = filter_n_contours(virgin_contours_list, n=4)

    # Filter out the four corners??
    virgin_contours_list = filter_n_contours(virgin_contours_list, n=4)

    # Do some visualization stuff
    if do_draw_contours:
        for contour in virgin_contours_list:
            # Thick red bounding boxes
            cv2.rectangle(frame_to_write_ontop_of, cv2.boundingRect(contour), (0, 0, 200), 3) 
            #rect = cv2.minAreaRect(contour) # Rotated (for minimum area) rectangle, red
            #cv2.drawContours(frame_to_write_ontop_of,[np.intp(cv2.boxPoints(rect))],0,(100,100,100),1)
            # Draw circles around the contour points
            #draw_contour_points(frame_to_write_ontop_of, contour,color=(0,200,0))
        # Draw contours
        draw_contours(frame_to_write_ontop_of, virgin_contours_list,color=(255,249,130))

    draw_center_of_mass_circles(frame_to_write_ontop_of, virgin_contours_list)

    #if save_intermediate:
    #    cv2.imwrite(os.path.join(LOCAL_PATH,"fadc_2_virgin_contours_before_l_filter.png"), frame_to_write_ontop_of)
    #    cv2.imwrite(os.path.join(LOCAL_PATH,"fadc_2_before_l_COM_Circles.png"), draw_center_of_mass_circles(frame.copy(), virgin_contours_list))
    
    if save_output:
        print(f" Found {len(contours_tree)} total contours.")
        print(f" Found {len(virgin_contours_list)} good contours.")
        #print("largest contour has ",len(contours_tree[highest_instance[0]]),"points")
        cv2.imwrite(os.path.join(LOCAL_PATH,"contours.png"), frame_to_write_ontop_of)
        cv2.imwrite(os.path.join(LOCAL_PATH,"COM_Circles.png"), draw_center_of_mass_circles(frame.copy(), virgin_contours_list))
        cv2.imwrite(os.path.join(LOCAL_PATH,"big_four.png"), draw_center_of_mass_circles(frame_to_write_ontop_of.copy(), big_four))

    if write_l_debug_circles:
        draw_center_of_mass_circles(frame_to_write_ontop_of, virgin_contours_list)

#endregion Contours Stuff
    

def analyze_video(video_path, save_output=False,save_raw=False):
    """ 
    Analyzes a given video at video_path, draws contours stuff,
    and saves it as output.mp4 and output_ontop.mp4

    NOTE: The save_outtput argument is only to save intermediate outputs
    at every frame for every function, and does not control whether
    the video will be saved.

    Returns the number of frames. 
    """

    print("Now doing video...")

    #region setup
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
    #endregion setup

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
            
            find_and_draw_contours(new_frame, frame, save_output=False, screensize=(width, height))
            
            writer_ontop.write(frame)
            writer.write(new_frame)

        else:
            print("End of video")
            break

    cap.release()
    writer.release()
    writer_ontop.release()

    return num_frames



def analyze_frame(frame, save_output=False, save_raw=False, write_l_debug_circles=True):
    """ Gets most likely pose of nugget from frame. """

    height, width, channels = frame.shape
    screensize = (width, height)
    
    new_frame = clean_image(filter_binarize(frame, save_output=save_output, save_raw=save_raw)[0])
    
    find_and_draw_contours(new_frame, new_frame, save_output=save_output, screensize=screensize, write_l_debug_circles=write_l_debug_circles, save_intermediate=save_raw)

    return new_frame


#endregion Functions


#region Procedural

# Load camera distortion coefficients. Source taken from https://github.com/TAMU-Robomasters/aruco-location-estimation
try:
    calib_data = np.load(CAMERA_CALIB_PATH)
    cam_mat    = calib_data["camMatrix"]
    dist_coef  = calib_data["distCoef"]

except FileNotFoundError as e:
    print(" [receptacle_pose.py] ERROR: Cannot find file for camera calibration data. Listing dirs below: ")
    print(os.listdir())
    raise e



if __name__ == "__main__":
    print("receptacle_pose was called as main.")

    # Create a VideoCapture object
    #cap = cv2.VideoCapture(os.path.join(LOCAL_PATH,"receptacle_example.mp4"))

    #for i in range(30*25): # Get the frame at 30 seconds
    #    # Read the first frame
    #    ret, frame = cap.read()

    #cap.release()
    DO_VIDEO = False

    if DO_VIDEO:
        print("doing video now")
        time_start = time.time()
        num_frames = analyze_video(os.path.join(LOCAL_PATH,"receptacle_example.mp4"))
        time_end = time.time()
        time_taken = time_end - time_start
        print(f"That took {time_taken:.4f} seconds ({num_frames/time_taken:.2f} FPS)")

    else:
        print("Analyzing frame...")
        #frame = cv2.imread(os.path.join(LOCAL_PATH,"raw_testbench.png"))
        frame = cv2.imread(os.path.join(LOCAL_PATH,"raw_testbench_3.png"))
        #frame = cv2.imread(os.path.join(LOCAL_PATH,"raw_testbench_cropped.PNG"))
        analyze_frame(frame, save_output=True, save_raw=True, write_l_debug_circles=True)

#endregion Procedural
