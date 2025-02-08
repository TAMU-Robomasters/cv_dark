import cv2 as cv
import numpy as np
import matplotlib.pyplot as plt


measurementsX = []
measurementsY = []
predictionsX = []
predictionsY = []


# Creating a Kalman Filter
kalman = cv.KalmanFilter(6,2)

kalman.measurementMatrix = np.array(
   [[1,0,0,0,0,0],
    [0,0,0,1,0,0]], np.float32)
    
# I made a change to the transition matrix by adding the state variables of x acceleration and y acceleration:
# (change in time - dt) = 1

kalman.transitionMatrix = np.array(
    [[1,1,0.5,0,0,0],
     [0,1,1,0,0,0],
     [0,0,1,0,0,0],
     [0,0,0,1,1,0.5],
     [0,0,0,0,1,1],
     [0,0,0,0,0,1]], np.float32)


kalman.processNoiseCov = np.array(
    [[1,0,0,0,0,0],
    [0,1,0,0,0,0],
    [0,0,1,0,0,0],
    [0,0,0,1,0,0],
    [0,0,0,0,1,0],
    [0,0,0,0,0,1]], np.float32) * 0.03

kalman.measurementNoiseCov = np.array(
    [[0.01,0],
     [0,0.01]], np.float32)

# Initialize state
kalman.statePre = np.zeros((6, 1), np.float32)


def track_object(frame):
    # Initialize center of frame:
    # x, y = (frame.shape[1] // 2, frame.shape[0] // 2)

    # measurement = np.array([[x], [y]], np.float32)
    
    hsv_frame = cv.cvtColor(frame, cv.COLOR_BGR2HSV)


    lower_blue = np.array([110, 50, 50])
    upper_blue = np.array([130, 255, 255])

    lower_orange = np.array([0, 0, 0])
    upper_orange = np.array([180, 255, 50] )

    mask = cv.inRange(hsv_frame, lower_orange, upper_orange)

    contours, _ = cv.findContours(mask, cv.RETR_TREE, cv.CHAIN_APPROX_SIMPLE)

    measurement = np.array([[0], [0]], np.float32)  # Ensure this is a (2, 1) array


    for c in contours:
        area = cv.contourArea(c)

        if area > 200:
            x, y, w, h = cv.boundingRect(c)

            measurement[0] = x
            measurement[1] = y

            measurementsX.append(measurement[0])
            measurementsY.append(measurement[1])

            kalman.correct(measurement)

            prediction = kalman.predict()

            predictionsX.append(prediction[0][0])
            predictionsY.append(prediction[1][0])


            cv.rectangle(frame, (x, y), (x+w, y+h), (255, 0, 0), 2)
            cv.rectangle(frame, (int(prediction[0][0]), int(prediction[1][0])), (int(prediction[0][0]) + w, int(prediction[1][0]) + h), (0,255,0), 2)

    cv.imshow("Mask", mask)
    cv.imshow("Object", frame)





def graph():
    plt.plot(measurementsX, np.array(predictionsX) - np.array(measurementsX))
    plt.xlabel('X-axis Label (Time)')
    plt.ylabel('Y-axis Error (in X)')
    plt.title('X Graph Error')
    plt.show()

    plt.plot(measurementsY, np.array(predictionsY) - np.array(measurementsY))
    plt.xlabel('X-axis Label (Time)')
    plt.ylabel('Y-axis Error (in Y)')
    plt.title('X Graph Error')
    plt.show()

    




if __name__ == "__main__":
    cap = cv.VideoCapture(0)
    
    while True:
        ret, frame = cap.read()

        if not ret:
            print("Failed to read frame")
            break
        # Track the object:

        track_object(frame)

        # pred_x, pred_y = int(prediction[0]), int(prediction[1])

        # cv.rectangle(frame, (pred_x - 5, pred_y - 5), (pred_x + 5, pred_y + 5), (0,255,0), 2)

        # Not sure what this does:
        if cv.waitKey(1) & 0xFF == ord("q"):
            break

    graph()

    cap.release()
    cv.destroyAllWindows()











