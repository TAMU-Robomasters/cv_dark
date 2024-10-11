
# receptacle_pose.py
# Started by Drew Wingfield
# on 2024-10-11

# Gets the pose of the receptacle given a frame

#region setup
# Imports
import cv2

#endregion setup



if __name__ == "__main__":
    print("receptacle_pose was called as main.")

        # Create a VideoCapture object
    cap = cv2.VideoCapture("main/subsystems/nugget_receptacle/receptacle_example.mp4")

    # Read the first frame
    ret, frame = cap.read()

    

