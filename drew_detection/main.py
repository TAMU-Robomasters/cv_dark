

# drew_detection/main.py
# Started by Drew Wingfield
# on 2024/09/19

# usbipd attach --wsl --busid=4-1

# With lots of help (and code) from the docs:
# https://docs.opencv.org/

#region Imports
import numpy
import cv2 as cv


#endregion Imports


#region Constants
#endregion Constants


#region Classes
#endregion Classes


#region Functions
#endregion Functions

#region Procedural

cap = cv.VideoCapture(0)
if not cap.isOpened():
    print("Cannot open camera")
    exit()
while True:
    # Capture frame-by-frame
    ret, frame = cap.read()
 
    # if frame is read correctly ret is True
    if not ret:
        print("Can't receive frame (stream end?). Exiting ...")
        break
    # Our operations on the frame come here
    gray = cv.cvtColor(frame, cv.COLOR_BGR2GRAY)
    # Display the resulting frame
    cv.imshow('frame', gray)
    if cv.waitKey(1) == ord('q'):
        break
 
# When everything done, release the capture
cap.release()
cv.destroyAllWindows()

print("program complete!")

#endregion Procedural

# -- end of file --