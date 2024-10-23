import numpy as np
import cv2 as cv

import matplotlib.pyplot as plt

from kf_main import KalmanFilter as kf


stateVar = np.array([1, 1, 1, 1, 1, 1], dtype=np.float32)
kalmanFilter = kf(stateVar, 0.5, 0.5, 0.04, 20)


# Initial Measurement
measurement = np.array([0, 0], np.float32)

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
        
        # lower_blue = np.array([0, 152, 181])
        # upper_blue = np.array([44, 231, 243])

        lower_yellow = np.array([20, 100, 100])
        upper_yellow = np.array([30, 255, 255])


        mask = cv.inRange(hsv_frame, lower_yellow, upper_yellow)
        
        contours, _ = cv.findContours(mask, cv.RETR_TREE, cv.CHAIN_APPROX_SIMPLE)

        contour_areas = [cv.contourArea(contour) if len(contour) > 4 else 0 for contour in contours] 
        max_index = 0
        max_contour_area = 0
        for i, contour_area in enumerate(contour_areas):
            if contour_area >= max_contour_area:
                max_index = i
                max_contour_area = contour_area

        contour = contours[max_index]
        d_t = 0.5
        
        if len(contour) > 0:
            x, y, w, h = cv.boundingRect(contour)
            
            measurement[0] = x 
            measurement[1] = y 
            kalmanFilter.correct(measurement)
            predicted = kalmanFilter.predict(d_t)

            #print(kalman)
            # print(f"Predicted Position: x={predicted[0][0]}, y={predicted[3][0]}")

            #print(f"Box x position {x} Box y position {y}")
            cv.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
            cv.rectangle(frame, (int(predicted[0]), int(predicted[3])), (int(predicted[0]) + w, int(predicted[3]) +h), (255, 0, 0), 2)

        
        cv.imshow("Mask", mask)
        cv.imshow("Object Tracking", frame)
        
        if cv.waitKey(30) & 0xFF == ord('q'):
            break
    cap.release()
    cv.destroyAllWindows()

track_paper(0)