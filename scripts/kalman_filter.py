import numpy as np
import cv2 as cv

import matplotlib.pyplot as plt

from kf_main import KalmanFilter as kf


stateVar = np.array([[1],[1],[1],[1],[1],[1]], dtype=np.float32)
kalmanFilter = kf(stateVar, 0.5,0.5, 0.04, 0.5)


# Initial Measurement
measurement = np.array([[0], [0]], np.float32)

real_x = []
real_y = []
predicted_x = []
predicted_y = []

def track_paper(video_path):
    cap = cv.VideoCapture(video_path)

    while True:
        ret , frame = cap.read()
        if not ret:
            break
        hsv_frame = cv.cvtColor(frame, cv.COLOR_BGR2HSV)
        
        lower_blue = np.array([0, 152, 181])
        upper_blue = np.array([44, 231, 243])


        mask = cv.inRange(hsv_frame, lower_blue, upper_blue)

        
        contours, _ = cv.findContours(mask, cv.RETR_TREE, cv.CHAIN_APPROX_SIMPLE)

        d_t = 0
        for contour in contours:
            area = cv.contourArea(contour)
            d_t += 0.04
            if area > 400:  
                x, y, w, h = cv.boundingRect(contour)
                
                
                
                measurement[0] = x
                measurement[1] = y
                kalmanFilter.correct(measurement)
                predicted = kalmanFilter.predict()
                #print(kalman)
                #print(f"Predicted Position: x={predicted[0][0]}, y={predicted[1][0]}")

                #print(f"Box x position {x} Box y position {y}")
                cv.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
                cv.rectangle(frame, (int(predicted[0][0]), int(predicted[1][0])), (int(predicted[0][0]) + w, int(predicted[1][0]) +h), (255, 0, 0), 2)

        
        cv.imshow("Mask", mask)
        cv.imshow("Object Tracking", frame)


        

        prediction = cv.KalmanFilter
        
        if cv.waitKey(30) & 0xFF == ord('q'):
            break
    cap.release()
    cv.destroyAllWindows()

track_paper(0)