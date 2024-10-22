import cv2
import numpy as np

# Callback function for trackbar (required but can be empty)
def nothing(x):
    pass

# Create a window
cv2.namedWindow('Trackbars')

# Create trackbars for color change
cv2.createTrackbar('Hue Min', 'Trackbars', 0, 179, nothing)
cv2.createTrackbar('Hue Max', 'Trackbars', 179, 179, nothing)
cv2.createTrackbar('Saturation Min', 'Trackbars', 0, 255, nothing)
cv2.createTrackbar('Saturation Max', 'Trackbars', 255, 255, nothing)
cv2.createTrackbar('Value Min', 'Trackbars', 0, 255, nothing)
cv2.createTrackbar('Value Max', 'Trackbars', 255, 255, nothing)

# Capture video from the webcam
cap = cv2.VideoCapture(0)

while True:
    # Read a frame from the webcam
    ret, frame = cap.read()
    
    # Convert the frame from BGR to HSV
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

    # Get trackbar positions
    h_min = cv2.getTrackbarPos('Hue Min', 'Trackbars')
    h_max = cv2.getTrackbarPos('Hue Max', 'Trackbars')
    s_min = cv2.getTrackbarPos('Saturation Min', 'Trackbars')
    s_max = cv2.getTrackbarPos('Saturation Max', 'Trackbars')
    v_min = cv2.getTrackbarPos('Value Min', 'Trackbars')
    v_max = cv2.getTrackbarPos('Value Max', 'Trackbars')

    # Define the lower and upper bounds for the HSV values
    lower_bound = np.array([h_min, s_min, v_min])
    upper_bound = np.array([h_max, s_max, v_max])

    # Create a mask for the specified color
    mask = cv2.inRange(hsv, lower_bound, upper_bound)

    # Bitwise-AND mask and original image
    result = cv2.bitwise_and(frame, frame, mask=mask)

    # Display the original frame and the filtered result
    cv2.imshow('Original Frame', frame)
    cv2.imshow('Filtered Result', result)

    # Exit the program when 'q' is pressed
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# Release the capture and close windows
cap.release()
cv2.destroyAllWindows()
