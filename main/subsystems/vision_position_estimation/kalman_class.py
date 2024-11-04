import numpy as np


class KalmanFilter2D:
    def __init__(self, initial_state, initial_covariance, process_noise, measurement_noise):
        self.state = initial_state
        self.covariance = initial_covariance
        self.process_noise = process_noise
        self.measurement_noise = measurement_noise

    def predict(self, dt):
        # Prediction step (state and covariance prediction)
        A = np.array([[1, 0, dt, 0, 0.5 * dt ** 2, 0],
                      [0, 1, 0, dt, 0, 0.5 * dt ** 2],
                      [0, 0, 1, 0, dt, 0],
                      [0, 0, 0, 1, 0, dt],
                      [0, 0, 0, 0, 1, 0],
                      [0, 0, 0, 0, 0, 1]])

        Q = self.process_noise * np.eye(6)

        # Predicted state
        self.state = np.dot(A, self.state)

        # Predicted covariance
        self.covariance = np.dot(np.dot(A, self.covariance), A.T) + Q

    def update(self, measurement):
        # Update step (measurement update)
        H = np.array([[1, 0, 0, 0, 0, 0],
                      [0, 1, 0, 0, 0, 0]])

        R = self.measurement_noise * np.eye(2)

        K = np.dot(np.dot(self.covariance, H.T), np.linalg.inv(np.dot(np.dot(H, self.covariance), H.T) + R))

        # Update state
        self.state = self.state + np.dot(K, (measurement - np.dot(H, self.state)))

        # Update covariance
        self.covariance = np.dot((np.eye(6) - np.dot(K, H)), self.covariance)
