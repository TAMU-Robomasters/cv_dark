
# receptacle_pose.py
# Started by Drew Wingfield
# on 2024-10-11

# Gets the pose of the receptacle given a frame

#TODO: Implement torch and CUDA support, clean up code, move constants to top of file

#region setup
# Imports

# Builtins
import sys
import os
import time
import math

# Externals
import cv2
import numpy as np
import itertools
from dotenv import load_dotenv

#endregion setup

#region Constants
if __name__ == "__main__":
    LOCAL_PATH = os.path.join("main","subsystems","nugget_receptacle")
else:
    LOCAL_PATH = os.path.join("subsystems","nugget_receptacle")

CAMERA_CALIB_PATH = os.path.join(LOCAL_PATH,"CalMatrix.npz") # Path to calibration data for camera.
#endregion Constants


#region Functions
def order_points(A, B, C, D, Ai, Bi, Ci, Di):
    """ 
    Orders points top-left, top-right, bottom-left, bottom-right using angles.
    With help from https://math.stackexchange.com/a/2587852
    """
    average_point = (0.25*sum([A[0], B[0], C[0], D[0]]), 0.25*sum([A[1], B[1], C[1], D[1]]))
    # Note that multiplying by 0.25 is faster than dividing by 4

    # Sort the points by angle from the "average point"
    angles = []
    for pt in [A, B, C, D]:
        angles.append(math.atan2(pt[1]-average_point[1], pt[0]-average_point[0]))

    #print([math.degrees(angle) for angle in angles]) #DEBUG

    # Sorting with help from https://stackoverflow.com/a/6618543/25598210
    try:
        sorted_ = [x for _,x in sorted(zip(angles, [A, B, C, D]))]

        # Numpy gets angry if we do this like the one above, so we must use indices
        Is = [Ai, Bi, Ci, Di]
        sorted_i= [x for _,x in sorted(zip(angles, [0,1,2,3]))]
        sorted_i= [Is[x] for x in sorted_i]

    except ValueError as e:
        print(f"Ai, Bi, Ci, Di = {[Ai, Bi, Ci, Di]}")
        print("Angles:",[math.degrees(angle) for angle in angles]) #DEBUG
        test = [(angles[0], Ai,), (angles[1], Bi), (angles[2], Ci), (angles[3], Di)]
        test = sorted(test)
        raise e

    return sorted_[0], sorted_[3], sorted_[1], sorted_[2], sorted_i[0], sorted_i[3], sorted_i[1], sorted_i[2],


def intersection_point(point_A:tuple, point_B:tuple, point_C:tuple, point_D:tuple)->tuple:
    """ 
    Returns a tuple of the intersection point coords between two lines from A-D and B-C. 
    If lines are parallel, returns (-1, -1).

    With help from https://en.wikipedia.org/wiki/Line%E2%80%93line_intersection#Given_two_line_equations
    """
    try:
        a = (point_D[1]-point_A[1])/(point_D[0]-point_A[0]) # Slope of line A-D
        b = (point_B[1]-point_C[1])/(point_B[0]-point_C[0]) # Slope of line B-C
    
    except ZeroDivisionError: # If Xs or Ys are the same, recalculate but with an added modifier
        a = (point_D[1]+0.1-point_A[1])/(point_D[0]+0.1-point_A[0]) # Slope of line A-D
        b = (point_B[1]+0.1-point_C[1])/(point_B[0]+0.1-point_C[0]) # Slope of line B-C

    #print(f"a slope={a:.4f}  b slope={b:.4f}") #DEBUG

    if a==b: return (-1, -1)

    c = point_A[1] - a*point_A[0] # y-intercept of line A-D
    d = point_C[1] - b*point_C[0] # y-intercept of line B-C

    #print(f"AD y-intercept={c:.4f}  BC y-intercept={d:.4f}") #DEBUG

    return  ( (d-c)/(a-b), a*((d-c)/(a-b))+c)


def non_square_factor(Ax:int, Ay:int, Bx:int, By:int, Cx:int, Cy:int, Dx:int, Dy:int) -> float:
    """ 
    Returns the non_square_factor of a given four points. 
    The higher the number, the less of a square it is (curcumvents more division which is slow).
    If the four points form a perfect parallelogram, 0 is returned

    This function and its algorithm are (c) 2024 Drew Wingfield, All Rights Reserved.
    Used by the Texas A&M University Texas Aimbots RoboMasters robotics team with permission.

    Ax, Ay is top left
    Bx, By is top right
    Cx, Cy is bottom left
    Dx, Dy is bottom right
    """
    # TODO: Return 1000 if AD and BC don't cross
    # TODO: Return 1000 if AD and BC don't cross within the bounding box of the four points
    # TODO: Find an approximation of this algorithm that's much faster and doesn't need as much
    # division, squaring, or square rooting.
    AD_center = ( (Ax + Dx)*0.5, (Ay + Dy)*0.5 ) # Centerpoint between point A and point D
    BC_center = ( (Bx + Cx)*0.5, (By + Cy)*0.5 ) # Centerpoint between point A and point D
    G = intersection_point((Ax,Ay),(Bx,By),(Cx,Cy),(Dx,Dy)) # Crossing point of AD and BC
    #print(f"G={G[0]:.2f}, {G[1]:.2f}  --  AD_center={AD_center[0]:.2f},{AD_center[1]:.2f}  --  BC_center={BC_center[0]:.2f},{BC_center[1]:.2f}") #DEBUG

    if G==(-1,-1): # G returns -1,-1 if lines are parallel.
        return 0 # If this is the case, it's a perfect parallelogram so return 0.

    return math.sqrt((AD_center[0] - G[0])**2 + (AD_center[1] - G[1])**2) + math.sqrt((BC_center[0] - G[0])**2 + (BC_center[1] - G[1])**2)


#region Image Stuff
def filter_binarize(frame, save_output=False, save_raw=False):
    """ 
    Filters an image (frame) so that everythign except the LEDs are black.

    Takes in BGR frame, outputs the new frame (BGR) and mask (Greyscale) 
    """
    # Threshold of colors we want in BGR space 
    bounds_lower = np.array([180, 150, 150]) # 50 120 85
    bounds_upper = np.array([255, 255, 255]) # 80 255 255

    # Preparing the mask to overlay 
    mask = cv2.inRange(frame, bounds_lower, bounds_upper) 

    # Mask the frame
    result = cv2.bitwise_and(frame, frame, mask = mask) 

    # Save output if respective arguments are true
    if save_output:
        cv2.imwrite(os.path.join(LOCAL_PATH,"binarized.ignore.png"), 
            result)
        if save_raw:
            cv2.imwrite(os.path.join(LOCAL_PATH,"raw.ignore.png"), frame)
            cv2.imwrite(os.path.join(LOCAL_PATH,"raw-gray.ignore.png"), cv2.cvtColor(frame,cv2.COLOR_BGR2GRAY))
        cv2.imwrite(os.path.join(LOCAL_PATH,"mask.ignore.png"), mask)

    # Return the result and the mask
    return result, mask


def clean_image(frame,save_output=False):
    """ 
    Cleans an image by using Morph Open and Morph Close filters.

    Returns a cleaned version of the given frame in BGR. 
    """
    # Convert to hsv
    #frame = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    

    # Use Morph Close to decrease noise
    kernel = np.ones((3,10),np.uint8)
    #frame = cv2.erode(frame, kernel, iterations=1)
    frame = cv2.morphologyEx(frame, cv2.MORPH_CLOSE, kernel)
    if save_output:
        cv2.imwrite(os.path.join(LOCAL_PATH,"morph_close.ignore.png"), frame)
    
    # Use Morph Open to decrease noise
    kernel = np.ones((3,3),np.uint8)
    frame = cv2.morphologyEx(frame, cv2.MORPH_OPEN, kernel)
    if save_output:
        cv2.imwrite(os.path.join(LOCAL_PATH,"morph_open.ignore.png"), frame)


    # print("Shape of morphed image:")
    # print(frame.shape)

    # Sharpening (isn't tuned very well so I'm disabling it for now)
    #kernel = np.array([[-1,-1,-1], [-1,9,-1], [-1,-1,-1]])
    #frame = cv2.filter2D(frame, -1, kernel)
    #if save_output:
    #    cv2.imwrite(os.path.join(LOCAL_PATH,"sharpen.ignore.png"), frame)
    
    # Convert back to BGR
    #frame = cv2.cvtColor(frame, cv2.COLOR_HSV2BGR)

    return frame


def draw_contours(frame, contours: list, color=(0,255,0), thickness=2): #TODO: remove this - it's a oneliner
    cv2.drawContours(frame, contours, -1, color, thickness) 

def draw_pose(img, corner_contours):
    """
    WIP
    Draws the plane and points of the receptacle given the four corners and imgpts.
    Four corner contours should be in order of topleft, topright, bottomleft, bottomright
    This function modified from https://docs.opencv.org/4.x/d7/d53/tutorial_py_pose.html

    Inputs:
      - img - a frame in BGR colorspace
      - corner_contours - the corner contours
    """
    OBJECT_HEIGHT = 2
    OBJECT_WIDTH  = 2
    AXIS_LENGTH   = 1
    #DRAW_TYPE = "simple" # simple or advanced, for just axes or 8-point cube, respectively
    
    if DRAW_TYPE=="simple":
        DRAW_POINTS = np.float32([[AXIS_LENGTH,0,0], [0,AXIS_LENGTH,0], [0,0,-AXIS_LENGTH]]).reshape(-1,3)

    else:
        DRAW_POINTS = np.float32([
            [0,0,0],          [0,AXIS_LENGTH,0],   [AXIS_LENGTH,AXIS_LENGTH,0], 
            [AXIS_LENGTH,0,0],[0,0,-AXIS_LENGTH],  [0,AXIS_LENGTH,-AXIS_LENGTH],
            [AXIS_LENGTH,AXIS_LENGTH,-AXIS_LENGTH],[AXIS_LENGTH,0,-AXIS_LENGTH] 
            ]).reshape(-1,3)

    gray = cv2.cvtColor(img,cv2.COLOR_BGR2GRAY)
    corners = []
    for cont in range(len(corner_contours)):
        cont = corner_contours[cont]
        x, y, w, h = cv2.boundingRect(cont)
        # Draw center points
        Center_cord = (x+(w//2), y+(h//2))
        cv2.circle(img, Center_cord, 6, (255,0,234), 4)
        corners.append(Center_cord)
    
    corner_contours = np.array(corners).astype(np.float32)

    #print(f"corner_contours ({corner_contours.shape}) = {corner_contours}")

    objpoints = [] # 3d point in real world space
    imgpoints = [] # 2d points in image plane.
    
    criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.001)
    objpoints = np.zeros((OBJECT_HEIGHT*OBJECT_WIDTH,3), np.float32)
    objpoints[:,:2] = np.mgrid[0:OBJECT_HEIGHT,0:OBJECT_WIDTH].T.reshape(-1,2)
 
    # Find corners
    corners2 = cv2.cornerSubPix(gray.astype(np.uint8),corner_contours,(2,2),(-1,-1),criteria)

    #print(f"corners2 (Image Points) ({corners2.shape}): {corners2}")
    #print(f"objpoints ({objpoints.shape}): {objpoints}")
    #print(f"cam_mat ({cam_mat.shape}): {cam_mat}")
    #print(f"dist_coef ({dist_coef.shape}): {dist_coef}")

    #objectPoints expects Array of object points in the object coordinate space, Nx3 1-channel or 1xN/Nx1 3-channel, 
    # where N is the number of points. vector<Point3d> can be also passed here.  while imagePoints expects an Array of
    #  corresponding image points, Nx2 1-channel or 1xN/Nx1 2-channel, where N is the number of points.

    # Find the rotation and translation vectors.
    ret,rvecs, tvecs = cv2.solvePnP(objpoints, corners2, cam_mat, dist_coef) 
    # cv.solvePnP(objectPoints, imagePoints, cameraMatrix, distCoeffs[, rvec[, tvec[, useExtrinsicGuess[, flags]]]]	) 

    # project 3D points to image plane
    projected_points, jac = cv2.projectPoints(DRAW_POINTS, rvecs, tvecs, cam_mat, dist_coef)
    #print(f"imgpoints projected ({imgpoints.shape}): {imgpoints}")
    projected_points = np.int32(projected_points).reshape(-1,2)
    #print(f"imgpoints int32'd ({imgpoints.shape}): {imgpoints}")


    # So our X axis is drawn from (0,0,0) to (1,0,0)
    #        Y axis is drawn from (0,0,0) to (0,1,0) 
    #        Z axis is drawn from (0,0,0) to (0,0,-1). 
    # Negative denotes it is drawn towards the camera.
    if DRAW_TYPE=="simple":
        corner = list(corners2[0].ravel())
        corner = tuple(int(x) for x in corner)
        # X axis
        img = cv2.line(img, corner, tuple(projected_points[0].ravel()), (255,0,0), 5)
        # Y axis, Green
        img = cv2.line(img, corner, tuple(projected_points[1].ravel()), (0,255,0), 5)
        # Z axis
        img = cv2.line(img, corner, tuple(projected_points[2].ravel()), (0,0,255), 5)

    else: # Drawing 8-point cube
        # draw bottom in green
        img = cv2.drawContours(img, [projected_points[:4]],-1,(0,255,0),-3)
    
        # draw pillars in blue color
        for i,j in zip(range(4),range(4,8)):
            img = cv2.line(img, tuple(projected_points[i]), tuple(projected_points[j]),(255),3)
    
        # draw top layer in red color
        img = cv2.drawContours(img, [projected_points[4:]],-1,(0,0,255),3)

    # Draw points on top
    for pt in imgpoints:
        cv2.circle(img, tuple(pt), 5, (0,0,0), 4)
        cv2.circle(img, tuple(pt), 3, (0,150,0), 4)
        #print(f"pt {pt}")
 
    return img

def draw_cross(frame, pts):
    """ Draws the green cross with midpoints on the given frame. """
    # Draw green lines connecting centers
    for pair in [(pts[0], pts[3]), (pts[1], pts[2])]:
        x, y, w, h = cv2.boundingRect(pair[0])
        x2, y2, w2, h2 = cv2.boundingRect(pair[1])
        cv2.line(frame, (x+(w//2), y+(h//2)), (x2+(w2//2), y2+(h2//2)), (0, 200, 0), 2)

        # Draw center points
        Center_cord = ( (x+(w//2) + x2+(w2//2))//2, (y+(h//2) + y2+(h2//2))//2 )
        cv2.circle(frame, Center_cord, 6, (255,0,234), 4)


def undistort(frame, save_output=False):
    """ Returns an undistorted version of a given image. """
    h,  w = frame.shape[:2]
    newcameramtx, roi = cv2.getOptimalNewCameraMatrix(cam_mat, dist_coef, (w,h), 1, (w,h))
    
    # undistort
    dst = cv2.undistort(frame, cam_mat, dist_coef, None, newcameramtx)
    # crop the image
    x, y, w, h = roi
    dst = dst[y:y+h, x:x+w]
    if save_output: cv2.imwrite(os.path.join(LOCAL_PATH,"undistorted.ignore.png"), dst)
    return dst


def image_debug_text(img, text):
    cv2.putText(img,text, (0, int(img.shape[0]-10)), cv2.FONT_HERSHEY_SIMPLEX, 1,(0,0,255),2,2)

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

    #if __name__ == "__main__":
    #    #print(f"x={center_x}, y={center_y}, cx={cx}, cy={cy}, x_size={w}, y_size={h}")
    #    print(f"x={center_x}, y={center_y}, cx is {percent_off_x*100 :.2f}% off, cy is {percent_off_y*100 :.2f}% off.")

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


def filter_contours(contours:list, screensize:tuple = (1920,1024), filter_l:bool = False):
    """
    Filters a given list of contours by ones that are likely the receptacle.
    Filters by size and area
    """
    # The below code was modified from https://stackoverflow.com/a/63934162/25598210
    contours_rtn = []
    max_rect_area   = screensize[0] * screensize[1] * 0.75
    #max_rect_width  = screensize[0] * 0.9
    #max_rect_height = screensize[1] * 0.95

    for contour in contours:
        x, y, w, h = cv2.boundingRect(contour)
        rect_area = w * h

        # If contour is certain shape
        # (both dimensions > 8px, at least one dimension > 10px)
        if (
                # Min width and height
                (w>8 and h>8) 
            and (w>10 or h>10)

                # Max width and height
            #and (w < max_rect_width)
            #and (h < max_rect_height)

                # Maximum Area
            and (rect_area < max_rect_area)

                # L-shape filtering if enabled
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


def filter_n_contours(contours:list, n:int, filter_by:str, debug=False, screensize:tuple=(1920,1024)) -> list:
    """ 
    Filters out n number of contours for likely candidates of the four corners of the receptacle. 
    filter_by may be either 'drew algorithm' or 'size.'

    NOTE: Contours MUST be free of duplicates, or you risk many extra iterations and wasted time.
    
    Also filters out pairs that extend past 70% of screen width/height
    """
    assert filter_by in ["drew algorithm", "size"]
    if len(contours)==0: return [] # Prevent errors
    
    rtnlist = []

    if filter_by=="size":
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
    
    elif filter_by=="drew algorithm":

        # Prevent errors if n or less contours exist
        if len(contours)<=n: return contours

        # Filter by how much of a squished rectangle it is.
        # Or rather (to save cpu time), filter by how much it isn't a squished rectangle.
        
        #combination_index_list = [] # Each item is a set of the combination indices
        combination_list = []
        coordinate_list = []
        nsqf_list = [] # List of non-square-factors corresponding to items in contours list

        if debug: # TODO: Remove this before prod for speed
            # Max number of combos: n!/r!(n-r)!
            # where n is number of objects and r is number of objects per combination (4)
            print(f" [filter_n_counters] There will be a maximum number of {math.factorial(len(contours))/(24*math.factorial(len(contours)-4)):.0f} combinations of 4 points.")

        iteration=0
        max_rect_width  = screensize[0] * 0.7
        max_rect_height = screensize[1] * 0.7
        # Iterate over the indexes of every combination of four contours.
        for A, B, C, D in itertools.combinations(contours, r=4):
            iteration += 1
            # A, B, C, and D are the contours
            # A_cord, B_cord, C_cord, and D_cord are (x,y) coordinate tuples
            x, y, w, h = cv2.boundingRect(A)
            A_cord = ((x+(w//2), y+(h//2)))
            x, y, w, h = cv2.boundingRect(B)
            B_cord = ((x+(w//2), y+(h//2)))
            x, y, w, h = cv2.boundingRect(C)
            C_cord = ((x+(w//2), y+(h//2)))
            x, y, w, h = cv2.boundingRect(D)
            D_cord = ((x+(w//2), y+(h//2)))

            # Order the points
            try: #TODO: Remove the try/except before prod because it takes up memory and time
                A_cord, B_cord, C_cord, D_cord, A, B, C, D = order_points(A_cord, B_cord, C_cord, D_cord, A, B, C, D)
            except ValueError as e:
                print(f"ValueError has occured! Some debug info:")
                print(f"A_cord={A_cord}, B_cord={B_cord}, C_cord={C_cord}, D_cord={D_cord}")
                print(f"Types of A, B, C, and D: {type(A), type(B), type(C), type(D)}")
                raise e

            # Reject combos that exceed the max size
            if (
                   max_rect_width  < (max(A_cord[0], B_cord[0], C_cord[0], D_cord[0])-min(A_cord[0], B_cord[0], C_cord[0], D_cord[0]))
                or max_rect_height < (max(A_cord[1], B_cord[1], C_cord[1], D_cord[1])-min(A_cord[1], B_cord[1], C_cord[1], D_cord[1]))
            ):
                nsqf_list.append(1000)
                coordinate_list.append([A_cord, B_cord, C_cord, D_cord])
                combination_list.append([A, B, C, D])
                continue

            # Get the non square factor
            NSqF = non_square_factor(A_cord[0], A_cord[1], B_cord[0], B_cord[1], C_cord[0], C_cord[1], D_cord[0], D_cord[1])
            #print(f" [filter_n_contours] Iteration {iteration:4}, Ai={Ai:3}, Bi={Bi:3}, Ci={Ci:3}, Di={str(Di):3}, A={str(A):12}, B={str(B):12}, C={str(C):12}, D={str(D):12},  NSqF={NSqF:.3f}")
            nsqf_list.append(NSqF)
            #combination_index_list.append({Ai, Bi, Ci, Di})
            coordinate_list.append([A_cord, B_cord, C_cord, D_cord])
            combination_list.append([A, B, C, D])
        
        if debug: # TODO: Remove this before prod for speed
            print(f" [filter_n_contours] Iterated through {len(nsqf_list)} combinations. Now sorting.")
            print(f" [filter_n_contours] Average NSqF: {sum(nsqf_list)/len(nsqf_list):.3f}")
            print(f" [filter_n_contours] Highest & lowest NSqF: {max(nsqf_list):.3f} - {min(nsqf_list):.3f}")

        # Just return the lowest non-square combination
        indx = nsqf_list.index(min(nsqf_list))

        if debug:
            print(f" Returning combination #{indx} and nsqf {nsqf_list[indx]:.2f}")
            comb = combination_list[indx]
            print(f" Best combination types (should be arrays): {[type(i) for i in combination_list[indx]]}")
            print("Ordered points:")
            print(coordinate_list[indx])
            #print(f"combination index list: {combination_index_list}")

        return combination_list[indx] # Should return the top combination of four points
        

        # Sort the combinations by the least non-squareish (the most square)
        # Sorting with help from https://stackoverflow.com/a/6618543/25598210
        # sorted_combos = [x for _,x in sorted(zip(nsqf_list, combination_index_list))]
        
        # Unpack all combinations and remove duplicates into a sorted list of contour indices
        # sorted_indices = []
        # for combo in sorted_combos: # Unpack combos
        #     combo = list(combo)
        #     sorted_indices += [combo[0], combo[1], combo[2], combo[3]]

        # if __name__ == "__main__": # TODO: Remove this before prod for speed
        #     print(f" [filter_n_contours] Sorted and unpacked contour indices - Now removing duplicates")

        #sorted_indices = list(dict.fromkeys(sorted_indices)) # This is the fastest way to remove duplicates while preserving order in Python.

        #if __name__ == "__main__": # TODO: Remove this before prod for speed
        #    print(f" [filter_n_contours] Duplicates removed: {sorted_indices}  - Now getting contours for each index.")

        # Sorted contours
        # return contours[sorted_indices[0]], contours[sorted_indices[1]], contours[sorted_indices[2]], contours[sorted_indices[3]]
        # rtnlist = []
        # iteration = 0
        # for i in sorted_indices:
        #     iteration +=1
        #     rtnlist.append(contours[i])

        #     if iteration==n: break

    assert len(rtnlist) <= n
    return rtnlist




def find_and_draw_contours(
    frame, frame_to_write_ontop_of, 
    save_output         = False, 
    do_draw_contours    = True, 
    screensize          = (1920,1024),
    do_draw_cross       = False,
    do_draw_com_circles = False,
    save_intermediate   = False,
    do_pose             = False,
    ):
    """
    Finds and draws contours on an image, filtering for valid and virgin contours.
    Frames are BGR. 

    do_draw_cross draws the green X with magenta circles for midpoints of the 
    best estimated points.

    do_draw_com_circles draws center of mass circles.
    """
    # Grayscale the image and find all the contours
    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    contours_tree, hierarchy_tree = cv2.findContours(frame, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE) # see https://stackoverflow.com/a/71891581/25598210
    
    frame = cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)

    if save_intermediate:
        cv2.imwrite(os.path.join(LOCAL_PATH,"fadc_1_greyscale.ignore.png"), frame)

    
    if save_output:
        print(f" Found {len(contours_tree)} total contours.")
        raw_frame_to_write_ontop_of = frame_to_write_ontop_of.copy()
        big_four_frame_write = frame_to_write_ontop_of.copy()
        pose_frame_write = frame_to_write_ontop_of.copy()
    
    
    # Get contours without children
    virgin_contours_list = virgin_contours(contours_tree, hierarchy_tree)
    
    if save_output:
        print(f" Found {len(virgin_contours_list)} total virgin contours")
    
    if save_intermediate: # Save intermediate image for debug
        print("    (saved as contours-virgins-0.ignore.png)")
        contours_virgins_zero_frame = raw_frame_to_write_ontop_of.copy()
        draw_contours(contours_virgins_zero_frame, virgin_contours_list)
        contours_virgins_one_frame = contours_virgins_zero_frame.copy()
        image_debug_text(contours_virgins_zero_frame, f"{len(virgin_contours_list)} virgin contours (all virgin contours)")
        cv2.imwrite(os.path.join(LOCAL_PATH,"contours-virgins-0.ignore.png"), contours_virgins_zero_frame)
        draw_contours(contours_virgins_one_frame, virgin_contours_list, color=(0,100,0)) # Dark green contours for filtered contours to be more prominent


    virgin_contours_list = filter_contours(virgin_contours_list, screensize=screensize, filter_l=False)
    
    if save_output:
        print(f" Filtered virgins, now {len(virgin_contours_list)} virgin contours")
    
    if save_intermediate: # Save intermediate image for debug
        print("    (saved as contours-virgins-1.ignore.png)")
        draw_contours(contours_virgins_one_frame, virgin_contours_list)
        image_debug_text(contours_virgins_one_frame, f"{len(virgin_contours_list)} virgin contours (filtered out tiny contours)")
        cv2.imwrite(os.path.join(LOCAL_PATH,"contours-virgins-1.ignore.png"), contours_virgins_one_frame)

    # Simplify the contours - see https://docs.opencv.org/4.x/dd/d49/tutorial_py_contour_features.html
    SIMPLIFY = True # for debug
    if SIMPLIFY:
        virgin_contours_list = [simplify_contour(contour, n_corners=6) for contour in virgin_contours_list]
        #TODO: also look into the Ramer–Douglas–Peucker algorithm for simplification

        if save_intermediate: # Save intermediate image for debug
            print("    (saved as contours-virgins-2-simple.ignore.png)")
            contours_virgins_simple_frame = raw_frame_to_write_ontop_of.copy()
            draw_contours(contours_virgins_simple_frame, virgin_contours_list)
            for cnt in virgin_contours_list:
                draw_contour_points(contours_virgins_simple_frame, cnt)
            image_debug_text(contours_virgins_simple_frame, f"{len(virgin_contours_list)} virgin contours (simplified)")
            cv2.imwrite(os.path.join(LOCAL_PATH,"contours-virgins-2-simple.ignore.png"), contours_virgins_simple_frame)
    
    # Filter contours once more, but with L-shape filtering
    #virgin_contours_list = filter_contours(virgin_contours_list, screensize=screensize, filter_l=True)

    # Filter out the four corners
    big_four = filter_n_contours(
        virgin_contours_list.copy(), n=4, filter_by="drew algorithm",
        screensize=screensize
        )

    #if __name__ == "__main__": print(f"Big four={big_four}") #DEBUG


    if len(big_four)==4:
        if save_output and do_draw_cross:
            draw_cross(big_four_frame_write, big_four)
            
        if do_pose and save_output:
            if do_draw_cross: draw_cross(pose_frame_write, big_four)
            draw_pose(pose_frame_write, big_four)
        
        elif do_pose:
            draw_pose(frame_to_write_ontop_of, big_four)
        
        if do_draw_cross:
            draw_cross(frame_to_write_ontop_of, big_four)
        
    # Filter out the four corners??
    #virgin_contours_list = filter_n_contours(virgin_contours_list, n=4)

    # Draw lots of boxes on top of things
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

    if do_draw_com_circles:
        draw_center_of_mass_circles(frame_to_write_ontop_of, virgin_contours_list)

    #if save_intermediate:
    #    cv2.imwrite(os.path.join(LOCAL_PATH,"fadc_2_virgin_contours_before_l_filter.png"), frame_to_write_ontop_of)
    #    cv2.imwrite(os.path.join(LOCAL_PATH,"fadc_2_before_l_COM_Circles.png"), draw_center_of_mass_circles(frame.copy(), virgin_contours_list))
    
    if save_output:
        #print(f" Found {len(contours_tree)} total contours.")
        #print(f" Found {len(virgin_contours_list)} virgin contours.")
        #print("largest contour has ",len(contours_tree[highest_instance[0]]),"points")
        cv2.imwrite(os.path.join(LOCAL_PATH,"contours.ignore.png"), frame_to_write_ontop_of)
        cv2.imwrite(os.path.join(LOCAL_PATH,"COM_Circles.ignore.png"), draw_center_of_mass_circles(frame.copy(), virgin_contours_list))
        cv2.imwrite(os.path.join(LOCAL_PATH,"big_four.ignore.png"), draw_center_of_mass_circles(big_four_frame_write, big_four))
        cv2.imwrite(os.path.join(LOCAL_PATH,"pose.ignore.png"), pose_frame_write)


#endregion Contours Stuff
    

def analyze_video(
        video_path, save_output=False,
        save_raw=False, do_pose=False, 
        undistort=False, save_at_frame=False, 
        do_draw_cross=True,
        frame_number=740):
    """ 
    Analyzes a given video at video_path, draws contours stuff,
    and saves it as output.mp4 and output_ontop.mp4

    NOTE: The save_outtput argument is only to save intermediate outputs
    at every frame for every function, and does not control whether
    the video will be saved.

    Returns the number of frames. 

    If save_at_frame is True, saves the nth frame of the video, where n is frame_number.
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
        os.path.join(LOCAL_PATH,".ignore.output.mp4"),
        fourcc=fourcc,
        apiPreference=0,
        fps=fps, 
        frameSize=(width, height)
    )

    fourcc_ontop = cv2.VideoWriter_fourcc(*'mp4v')
    writer_ontop = cv2.VideoWriter(
        os.path.join(LOCAL_PATH,"output_ontop.ignore.mp4"),
        fourcc=fourcc_ontop,
        apiPreference=0,
        fps=fps, 
        frameSize=(width, height)
    )

    pos_frame = cap.get(1) #cv2.CV_CAP_PROP_POS_FRAMES
    total_frames = cap.get(cv2.CAP_PROP_FRAME_COUNT)
    #endregion setup

    num_frames=0

    while True:
        num_frames+=1
        flag, frame = cap.read()
        if flag:
            # The frame is ready and already captured
            #cv2.imshow('video', frame)
            pos_frame = cap.get(1)
            print(f"Frame {pos_frame} / {total_frames}  ",end='\r')

            if save_at_frame and num_frames>=frame_number:
                 cv2.imwrite(os.path.join(LOCAL_PATH,str(int(frame_number))+".ignore.png"), frame)
                 exit()
            elif save_at_frame:
                continue
            
            if undistort:
                frame = undistort(frame, save_output=save_output)

            new_frame = clean_image(filter_binarize(frame, save_output=save_output, save_raw=save_raw)[0])
            
            find_and_draw_contours(
                new_frame, frame, save_output=False, screensize=(width, height), 
                do_draw_contours=False, do_draw_cross=do_draw_cross, do_draw_com_circles=True, do_pose=do_pose
            )

            if undistort:
                # If undistorted, resize so the video writer doesn't freak out
                frame = cv2.resize(frame, (width, height))
                new_frame = cv2.resize(new_frame, (width, height))

            writer_ontop.write(frame)
            writer.write(new_frame)

        else:
            print("End of video")
            break

    cap.release()
    writer.release()
    writer_ontop.release()

    return num_frames



def analyze_frame(
        frame, 
        save_output   = False, 
        save_raw      = False, 
        do_draw_cross = False, 
        do_draw_com_circles = False, 
        do_pose       = False,
        do_undistort  = False):
    """ Gets most likely pose of nugget from frame. """

    height, width, channels = frame.shape
    screensize = (width, height)
    
    if do_undistort:
        undistort(frame, save_output=save_raw)
    
    new_frame = clean_image(filter_binarize(frame, save_output=save_output, save_raw=save_raw)[0], save_output=save_output)

    find_and_draw_contours(
        new_frame, new_frame, save_output=save_output, 
        screensize          = screensize,
        save_intermediate   = save_raw,
        do_draw_com_circles = do_draw_com_circles,
        do_draw_cross       = do_draw_cross,
        do_pose             = do_pose,
        )

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
    load_dotenv() # Load environment vars from .env file

    # Create a VideoCapture object
    #cap = cv2.VideoCapture(os.path.join(LOCAL_PATH,"receptacle_example.mp4"))

    #for i in range(30*25): # Get the frame at 30 seconds
    #    # Read the first frame
    #    ret, frame = cap.read()

    #cap.release()
    DO_VIDEO = False

    args = sys.argv[1:] # Take all arguments (first one is name of this script)
    
    TRUE_VALUES = ["true", "t", "yes", "1"]

    in_file_override    = os.getenv("IN_FILE", None)
    do_pose             = os.getenv("DO_POSE",          False).lower() in TRUE_VALUES
    do_undistort        = os.getenv("DO_UNDISTORT",     False).lower() in TRUE_VALUES
    DRAW_TYPE           = os.getenv("POSE_TYPE", "simple")
    save_raw            = os.getenv("SAVE_RAW",         False).lower() in TRUE_VALUES
    do_draw_com_circles = os.getenv("DRAW_COM_CIRCLES", False).lower() in TRUE_VALUES
    do_draw_cross       = os.getenv("DRAW_CROSS",       True ).lower() in TRUE_VALUES

    for arg in args:
        if "infile" in arg.lower():
            in_file_override = arg[arg.index("=")+1:]
            print("Input file override set.")

        if "do_pose" in arg.lower() and not(arg.lower().endswith("false")):
            do_pose = True
            print("do_pose overridden to True.")

        if ("do_undistort" in arg.lower() or "undistort" in arg.lower()) and not(arg.lower.endswith("false")):
            do_undistort = True
            print("do_undistort overridden to True.")
        
        if "pose_type" in arg.lower():
            DRAW_TYPE = arg[arg.index("=")+1:]
            #simple or advanced, for just axes or 8-point cube, respectively

    # Determine if it's a single frame or image sequence
    DO_VIDEO = None
    try:
        # If it's a video
        cap = cv2.VideoCapture(in_file_override)
        if cap.isOpened() and cap.get(cv2.CAP_PROP_FRAME_COUNT)>1:
            DO_VIDEO = True
        else:
            raise AssertionError
    except:
        # If it's not a video
        img = cv2.imread(in_file_override)
        if img is not None:
            DO_VIDEO = False
        else:
            raise AssertionError("Provided file is neither a valid video nor image!")

    if DO_VIDEO:
        print("doing video now")
        time_start = time.time()        
        num_frames = analyze_video(
            in_file_override, do_pose=do_pose, 
            do_draw_cross=do_draw_cross, undistort=do_undistort)

        time_end = time.time()
        time_taken = time_end - time_start
        print(f"That took {time_taken:.4f} seconds ({num_frames/time_taken:.2f} FPS)")

    else:
        print("Analyzing frame...")
        frame = cv2.imread(os.path.join(LOCAL_PATH,"raw_testbench.ignore.png"))

        if in_file_override!=None:
            frame = cv2.imread(in_file_override)
        
        #frame = undistort(frame, save_output=True)

        # minVal = 100
        # maxVal = 200
        # canny = cv2.Canny(frame.copy(),minVal,maxVal)

        # canny_corners = canny
        
        # corners = cv2.goodFeaturesToTrack(canny, 10, 0.5, 50)
        # #         cv.goodFeaturesToTrack(image, maxCorners, qualityLevel, minDistance[, corners[, mask[, blockSize[, useHarrisDetector[, k]]]]]

        # for corner in corners:
        #     x,y = corner.ravel()
        #     #print(f"x={x},y={y}")
        #     cv2.circle(canny_corners,(int(x),int(y)), 3, (255,40,40), 3)
        #     #cv2.circle(frame, (x, y), radius, color, thickness)

        # cv2.imwrite(os.path.join(LOCAL_PATH,"canny_corners.ignore.png"), canny_corners)

        analyze_frame(
            frame, save_output  = True, 
            save_raw            = save_raw, 
            do_draw_com_circles = do_draw_com_circles, 
            do_draw_cross       = do_draw_cross, 
            do_pose             = do_pose,
            do_undistort        = do_undistort
            )

#endregion Procedural
