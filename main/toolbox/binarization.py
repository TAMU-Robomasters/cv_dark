# script to binarize an image into pure black and pure white

import cv2
import numpy as np

vid = cv2.VideoCapture(0, cv2.CAP_DSHOW)


def binarize(image):
#     TODO:


while vid.isOpened():
    ret, frame = vid.read()
    if not ret:
        print("ERROR: Could not read frame")
        break

    bin_image = binarize(frame)
    cv2.imshow("original", frame)
    cv2.imshow("binarized", bin_image)
    if cv2.waitKey(1) == 27:
        break

vid.release()
cv2.destroyAllWindows()
