# script to extract red from an image

import cv2
import numpy as np

# IMAGE_PATH = r""
vid = cv2.VideoCapture(0, cv2.CAP_DSHOW)


def redextract(fr):
    # image = cv2.imread(frame)
    image = fr
    img_hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)

    # lower mask (0-10)
    lower_red = np.array([0, int(.5 * 255), int(.35 * 255)])
    upper_red = np.array([10, 255, 255])
    mask0 = cv2.inRange(img_hsv, lower_red, upper_red)

    # upper mask (170-180)
    lower_red = np.array([170, int(.5 * 255), int(.35 * 255)])
    upper_red = np.array([180, 255, 255])
    mask1 = cv2.inRange(img_hsv, lower_red, upper_red)

    mask = mask0 + mask1

    out_img = image.copy()
    out_img[np.where(mask == 0)] = 0

    out_hsv = img_hsv.copy()
    out_hsv[np.where(mask == 0)] = 0
    return out_img, out_hsv


while vid.isOpened():
    ret, frame = vid.read()
    if not ret:
        print("ERROR: Could not read frame")
        break
    img, hsv = redextract(frame)
    cv2.imshow('redextract', img)
    cv2.imshow('original', frame)
    if cv2.waitKey(1) == 27:
        break

vid.release()
cv2.destroyAllWindows()
