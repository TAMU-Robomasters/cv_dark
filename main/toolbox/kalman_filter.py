import cv2
import numpy as np


#! there could be an error with first measurement having high velocity and acceleration
#! this is dependent on what the firs time delay (dt) is
# TODO figure out if we need dt param
class KF3D:
    def __init__(self, init_kinematic_state, x_error, y_error, z_error, dt, acceleration_error: float):
        self.acceleration_error = acceleration_error

        # no control parameters. Assuming the target is moving with a constant acceleration
        self.kalman = cv2.KalmanFilter(9, 3)
        
        # Define the initial values of the state variables ([x, y, z, vx, vy, vz, ax, ay, az])
        # ? Would initiating based on finite difference help us converge faster
        self.kalman.statePost = init_kinematic_state

        # Define the error associated to the initial values of the state variables  
        # TODO see if it converges faster with different values
        self.kalman.errorCovPost = np.eye(6, 6, dtype=np.float32)

        # Define the measurement noise covariance matrix
        # NOTE y_error could be made into a function that's dependent on the distance. The further out the more uncertain we are. 
        self.kalman.measurementNoiseCov = np.array(
            [
                [x_error ** 2, 0, 0],
                [0, y_error ** 2, 0],
                [0, 0, z_error ** 2]
            ], dtype=np.float32)
        
        # Encodes how off our dynamic model (i.e. constant acceleration model) is from reality
        # NOTE might need to change how this works because it could prove out to be too computationally expensive
        self.kalman.processNoiseCov = np.array(
            [
                [(dt ** 4) / 4, (dt ** 3) / 2,  (dt ** 2) / 2, 0, 0, 0, 0, 0, 0],
                [(dt ** 3) / 2, (dt ** 2), dt, 0, 0, 0, 0, 0, 0],
                [(dt ** 2) / 2, dt, 1, 0, 0, 0, 0, 0, 0],
                [0, 0, 0, (dt ** 4) / 4, (dt ** 3) / 2,  (dt ** 2) / 2, 0, 0, 0],
                [0, 0, 0, (dt ** 3) / 2, (dt ** 2), dt, 0, 0, 0],
                [0, 0, 0, (dt ** 2) / 2, dt, 1, 0, 0, 0],
                [0, 0, 0, 0, 0, 0, (dt ** 4) / 4, (dt ** 3) / 2,  (dt ** 2) / 2],
                [0, 0, 0, 0, 0, 0, (dt ** 3) / 2, (dt ** 2), dt],
                [0, 0, 0, 0, 0, 0, (dt ** 2) / 2, dt, 1]    
            ], dtype=np.float32
        ) * (self.acceleration_error ** 2)

        # maps state variables into measurements
        self.kalman.measurementMatrix = np.array(
            [
                [1, 0, 0, 0, 0, 0, 0, 0, 0],
                [0, 0, 0, 1, 0, 0, 0, 0, 0],
                [0, 0, 0, 0, 0, 0, 1, 0, 0]
            ], dtype=np.float32)

        # encodes how the state variables will evolve over a certain period of time assuming target has a constant acceleration 
        self.kalman.transitionMatrix = np.array(
            [
                [1, dt ,0.5 * dt ** 2, 0, 0, 0, 0, 0, 0],
                [0, 1, dt, 0, 0, 0, 0, 0, 0],
                [0, 0, 1, 0, 0, 0, 0, 0, 0],
                [0, 0, 0, 1, dt, 0.5 * dt ** 2, 0, 0, 0],
                [0, 0, 0, 0, 1, dt, 0, 0, 0],
                [0, 0, 0, 0, 0, 1, 0, 0, 0],
                [0, 0, 0, 0, 0, 0, 1, dt, 0.5 * dt ** 2],
                [0, 0, 0, 0, 0, 0, 0, 1, dt],
                [0, 0, 0, 0, 0, 0, 0, 0, 1]
            ], dtype=np.float32)


    def predict(self, dt=None):
        if dt:
            self.kalman.processNoiseCov = np.array(
            [
                [(dt ** 4) / 4, (dt ** 3) / 2,  (dt ** 2) / 2, 0, 0, 0, 0, 0, 0],
                [(dt ** 3) / 2, (dt ** 2), dt, 0, 0, 0, 0, 0, 0],
                [(dt ** 2) / 2, dt, 1, 0, 0, 0, 0, 0, 0],
                [0, 0, 0, (dt ** 4) / 4, (dt ** 3) / 2,  (dt ** 2) / 2, 0, 0, 0],
                [0, 0, 0, (dt ** 3) / 2, (dt ** 2), dt, 0, 0, 0],
                [0, 0, 0, (dt ** 2) / 2, dt, 1, 0, 0, 0],
                [0, 0, 0, 0, 0, 0, (dt ** 4) / 4, (dt ** 3) / 2,  (dt ** 2) / 2],
                [0, 0, 0, 0, 0, 0, (dt ** 3) / 2, (dt ** 2), dt],
                [0, 0, 0, 0, 0, 0, (dt ** 2) / 2, dt, 1]    
            ], dtype=np.float32
            ) * (self.acceleration_error ** 2)

            self.kalman.transitionMatrix = np.array(
                [
                    [1, dt ,0.5 * dt ** 2, 0, 0, 0, 0, 0, 0],
                    [0, 1, dt, 0, 0, 0, 0, 0, 0],
                    [0, 0, 1, 0, 0, 0, 0, 0, 0],
                    [0, 0, 0, 1, dt, 0.5 * dt ** 2, 0, 0, 0],
                    [0, 0, 0, 0, 1, dt, 0, 0, 0],
                    [0, 0, 0, 0, 0, 1, 0, 0, 0],
                    [0, 0, 0, 0, 0, 0, 1, dt, 0.5 * dt ** 2],
                    [0, 0, 0, 0, 0, 0, 0, 1, dt],
                    [0, 0, 0, 0, 0, 0, 0, 0, 1]
                ], dtype=np.float32)
        else:
            print('WARNING: Failed to receive change in time (dt)')

        return self.kalman.predict()


    def correct(self, measurement):
        return self.kalman.correct(measurement)
    

    # This function won't affect any of the member variables
    # won't be used for kalman.correct()
    def forward_predict(self, dt):
        transition_mat = np.array(
            [
                [1, dt, 0.5 * dt ** 2, 0, 0, 0, 0, 0, 0],
                [0, 1, dt, 0, 0, 0, 0, 0, 0],
                [0, 0, 1, 0, 0, 0, 0, 0, 0],
                [0, 0, 0, 1, dt, 0.5 * dt ** 2, 0, 0, 0],
                [0, 0, 0, 0, 1, dt, 0, 0, 0],
                [0, 0, 0, 0, 0, 1, 0, 0, 0],
                [0, 0, 0, 0, 0, 0, 1, dt, 0.5 * dt ** 2],
                [0, 0, 0, 0, 0, 0, 0, 1, dt],
                [0, 0, 0, 0, 0, 0, 0, 0, 1]
            ], dtype=np.float32)
        return transition_mat @ self.kalman.statePost

class KF2D:
    def __init__(self, init_kinematic_state, x_error, y_error, dt, acceleration_error: float):
        self.acceleration_error = acceleration_error

        # no control parameters. Assuming the target is moving with a constant acceleration
        self.kalman = cv2.KalmanFilter(6, 2)
        
        # Define the initial values of the state variables (x = [x, y, vx, vy, ax, ay])
         # ? Would initiating based on finite difference help us converge faster
        self.kalman.statePost = init_kinematic_state

        # Define the error associated to the initial values of the state variables  
        # TODO see if it converges faster with different values
        self.kalman.errorCovPost = np.eye(6, 6, dtype=np.float32)

        # Define the measurement noise covariance matrix
        # NOTE y_error could be made into a function based on the distance. The further out the more uncertain we are. 
        self.kalman.measurementNoiseCov = np.array(
            [
                [x_error**2, 0],
                [0, y_error**2]
            ], dtype=np.float32)
        
        # Encodes how off our dynamic model (constant acceleration model) is from reality
        # NOTE might need to change how this works because it could prove out to be too computationally expensive
        self.kalman.processNoiseCov = np.array(
            [
                [(dt ** 4) / 4, (dt ** 3) / 2,  (dt ** 2) / 2, 0, 0, 0],
                [(dt ** 3) / 2, (dt ** 2), dt, 0, 0, 0],
                [(dt ** 2) / 2, dt, 1, 0, 0, 0],
                [0, 0, 0, (dt ** 4) / 4, (dt ** 3) / 2,  (dt ** 2) / 2],
                [0, 0, 0, (dt ** 3) / 2, (dt ** 2), dt],
                [0, 0, 0, (dt ** 2) / 2, dt, 1],
                
            ], dtype=np.float32
        ) * (self.acceleration_error ** 2)

        # maps state variables into measurements
        self.kalman.measurementMatrix = np.array(
            [
                [1, 0, 0, 0, 0, 0],
                [0, 0, 0, 1, 0, 0]

            ], dtype=np.float32)

        # encodes how the state variables will evolve over a certain period of time assuming the target has a constant acceleration 
        self.kalman.transitionMatrix = np.array(
            [
                [1, dt ,0.5 * dt ** 2, 0, 0, 0],
                [0, 1, dt, 0, 0, 0],
                [0, 0, 1, 0, 0, 0],
                [0, 0, 0, 1, dt, 0.5 * dt ** 2, ],
                [0, 0, 0, 0, 1, dt],
                [0, 0, 0, 0, 0, 1],
            
            ], dtype=np.float32)
    

    def predict(self, dt=None):
        if dt:
            self.kalman.processNoiseCov = np.array(
            [
                [(dt ** 4) / 4, (dt ** 3) / 2,  (dt ** 2) / 2, 0, 0, 0],
                [(dt ** 3) / 2, (dt ** 2), dt, 0, 0, 0],
                [(dt ** 2) / 2, dt, 1, 0, 0, 0],
                [0, 0, 0, (dt ** 4) / 4, (dt ** 3) / 2,  (dt ** 2) / 2],
                [0, 0, 0, (dt ** 3) / 2, (dt ** 2), dt],
                [0, 0, 0, (dt ** 2) / 2, dt, 1],
                
            ], dtype=np.float32
            ) * (self.acceleration_error ** 2)
            self.kalman.transitionMatrix = np.array(
            [
                [1, dt ,0.5 * dt ** 2, 0, 0, 0],
                [0, 1, dt, 0, 0, 0],
                [0, 0, 1, 0, 0, 0],
                [0, 0, 0, 1, dt, 0.5 * dt ** 2, ],
                [0, 0, 0, 0, 1, dt],
                [0, 0, 0, 0, 0, 1],
            
            ], dtype=np.float32)
        else:
            print('WARNING: Failed to receive change in time (dt)')

        return self.kalman.predict()


    def correct(self, measurement):
        return self.kalman.correct(measurement)
    
    # This function won't affect any of the member variables
    # won't be used for kalman.correct()
    def forward_predict(self, dt):
        transition_mat = np.array(
            [
                [1, dt ,0.5 * dt ** 2, 0, 0, 0],
                [0, 1, dt, 0, 0, 0],
                [0, 0, 1, 0, 0, 0],
                [0, 0, 0, 1, dt, 0.5 * dt ** 2, ],
                [0, 0, 0, 0, 1, dt],
                [0, 0, 0, 0, 0, 1],
            
            ], dtype=np.float32)
        return transition_mat @ self.kalman.statePost