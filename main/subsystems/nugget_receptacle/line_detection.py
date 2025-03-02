
# This is a test of using line detection instead of other methods.
# See https://docs.opencv.org/3.4/d9/db0/tutorial_hough_lines.html


# Builtins
import sys
import os
import math

# Externals
import cv2
from dotenv import load_dotenv
import numpy as np

GRAYSCALE = True

if __name__ == "__main__":
    load_dotenv()
    IN_IMG = os.getenv("IN_IMG")
    if GRAYSCALE:
        frame = cv2.imread(IN_IMG, cv2.IMREAD_GRAYSCALE)
        frame_color = cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)
    
    else:
        frame = cv2.imread(IN_IMG)
        frame_color = frame.copy()

    screen_size = frame.shape
    print(f" Using shape {screen_size}")

    # Clean the image
    kernel = np.ones((3,3),np.uint8) # Used to be (3,10)
    #frame = cv2.erode(frame, kernel, iterations=1)
    frame = cv2.morphologyEx(frame, cv2.MORPH_OPEN, kernel)

    can = cv2.Canny(frame, 150, 250) # used to be 50, 200

    canny_write_path = os.path.join(IN_IMG[:-3]+"_canny.ignore."+IN_IMG[-3:])
    print(canny_write_path)
    cv2.imwrite(canny_write_path, can)

    max_line_gap = int(max(screen_size)*0.015)
    #                       img, rho, theta, threshold, minLineLength, maxLineGap
    lines = cv2.HoughLinesP(can, 5, np.pi / 180, 40, None, 3, max_line_gap)
    # used to be (can, 1, np.pi / 180, 150, None, 50, 10)
    # can: Output of the edge detector. It should be a grayscale image (although in fact it is a binary one)
    # outputs to lines: A vector that will store the parameters (xstart,ystart,xend,yend) of the detected lines
    # rho : The resolution of the parameter r in pixels. We use 1 pixel.
    # theta: The resolution of the parameter θ in radians. We use 1 degree (CV_PI/180)
    # threshold: The minimum number of intersections to "*detect*" a line
    # minLineLength: The minimum number of points that can form a line. Lines with less than this number of points are disregarded.
    # maxLineGap: The maximum gap between two points to be considered in the same line.

    print(f"Max line gap: {max_line_gap}")
    # Draw the lines
    # if lines is not None:
    #     for i in range(0, len(lines)):
    #         rho = lines[i][0][0]
    #         theta = lines[i][0][1]
    #         a = math.cos(theta)
    #         b = math.sin(theta)
    #         x0 = a * rho
    #         y0 = b * rho
    #         pt1 = (int(x0 + 1000*(-b)), int(y0 + 1000*(a)))
    #         pt2 = (int(x0 - 1000*(-b)), int(y0 - 1000*(a)))
    #         cv2.line(frame_color, pt1, pt2, (0,0,255), 1, cv2.LINE_AA)

    # Draw the lines
    if lines is not None:
        for i in range(0, len(lines)):
            l = lines[i][0]
            cv2.line(frame_color, (l[0], l[1]), (l[2], l[3]), (0,0,255), 2, cv2.LINE_AA)

    lines_write_path = os.path.join(IN_IMG[:-3]+"_lines.ignore."+IN_IMG[-3:])
    print(lines_write_path)
    cv2.imwrite(lines_write_path, frame_color)
