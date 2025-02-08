import cv2
import numpy as np

# to run file do python3 scripts/color_paper.py in terminal

# make algorithm using opencv that will return the bounding box of this
# color piece of paper

#Below is code for colorfiltering with an imported image
'''
# Convert image to HSV to separate color values for detection
img = cv2.imread("../data/rune_example.png")
cv2.imshow('Original Image', img)
cv2.waitKey(0)
hsv_img = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)

# Set ranges for color to filter, (red in this case)
lower_range = (0, 50, 50)
upper_range = (10, 255, 255)
mask = cv2.inRange(hsv_img, lower_range, upper_range)

# Filter for color
color_image = cv2.bitwise_and(img, img, mask=mask)

# Show result
cv2.imshow('Color Image', color_image)
cv2.waitKey(0)
cv2.destroyAllWindows()


contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

max_w = 0
max_h = 0
for contour in contours:
    x, y, w, h = cv2.boundingRect(contour)
    if (w > max_w):
        max_w = w
    if (h > max_h):
        max_h = h
cv2.rectangle(img, (x, y), (x + max_w, y + max_h), (0, 255, 0), 2) # Draw the rectangle on the original image

cv2.imshow('Bounding Boxes', img)
cv2.waitKey(0)
cv2.destroyAllWindows()
'''

cap = cv2.VideoCapture(0)

while True:
    ret, frame = cap.read()
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

    lower_blue = np.array([40, 100, 100])
    upper_blue = np.array([80, 255, 255])

    mask = cv2.inRange(hsv, lower_blue, upper_blue)


    result = cv2.bitwise_and(frame, frame, mask=mask)

    #cv2.imshow('Original', frame)
    #cv2.imshow('Mask', mask)
    #cv2.imshow('Filtered', result)

    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    max_w = 0
    max_h = 0
    x, y, w, h = 0, 0, 0, 0
    for contour in contours:
        x, y, w, h = cv2.boundingRect(contour)
        if (w > max_w):
            max_w = w
        if (h > max_h):
            max_h = h
    #cv2.rectangle(frame, (x, y), (x + max_w, y + max_h), (0, 255, 0), 2) # Draw the rectangle on the original image
    #cv2.rectangle(result, (x, y), (x + max_w, y + max_h), (0, 255, 0), 2) # Draw the rectangle on the original image
    cv2.rectangle(result, (x, y), (x + max_w, y + max_h), (0, 255, 0), 2) # Draw the rectangle on the original image

    # Parameters for circle
    #center = (x + (max_w / 2), y + (max_h / 2))
    circle_x = int(x + max_w / 2)
    circle_y = int(y + max_h / 2)
    center = (circle_x, circle_y)
    radius = 5
    color = (0, 255, 0)
    thickness = 2
    result = cv2.circle(result, center, radius, color, thickness)
    #cv2.imshow('Original', frame)
    #cv2.imshow('Mask', mask)
    cv2.imshow('Filtered', result)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()