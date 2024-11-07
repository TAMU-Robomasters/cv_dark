import cv2
import numpy as np
import torch 

from toolbox.globals import config

hardware_acceleration = config.model.hardware_acceleration

if hardware_acceleration in ['tensor_rt', 'gpu'] and torch.cuda.is_available():
    torch.set_default_device(torch.device("cuda"))

class TorchKF():
    def __init__(self, dynam_params: int, measure_params: int, control_params: int = 0, dtype=torch.float32):
        assert dynam_params > 0, "Number of dynamic parameters must be greater than 0"
        assert measure_params > 0, "Number of measure parameters must be greater than 0"
        assert control_params >= 0, "NUmber of control parameters must be greater than or equal to 0"

        self.state_pre = torch.zeros((dynam_params, 1), dtype=dtype)
        self.state_post = torch.zeros((dynam_params, 1), dtype=dtype)
        self.transition_matrix = torch.eye(dynam_params, dtype=dtype)
        
        self.process_noise_cov = torch.eye(dynam_params, dtype=dtype)
        self.measurement_matrix = torch.zeros((measure_params, dynam_params), dtype=dtype)
        self.measurement_noise_cov = torch.eye(measure_params, dtype=dtype)
        
        self.error_cov_pre = torch.zeros((dynam_params, dynam_params), dtype=dtype)
        self.error_cov_post = torch.zeros((dynam_params, dynam_params), dtype=dtype)
        self.gain = torch.zeros((dynam_params, measure_params), dtype=dtype)
        
        if control_params > 0:
            self.control_matrix = torch.zeros((dynam_params, control_params), dtype=dtype)
        else:
            self.control_matrix = None
        
        # Temporary matrices
        self.temp1 = torch.zeros((dynam_params, dynam_params), dtype=dtype)
        self.temp2 = torch.zeros((measure_params, dynam_params), dtype=dtype)
        self.temp3 = torch.zeros((measure_params, measure_params), dtype=dtype)
        self.temp4 = torch.zeros((measure_params, dynam_params), dtype=dtype)
        self.temp5 = torch.zeros((measure_params, 1), dtype=dtype)
    
    def predict(self, control=None):
        # Predict state: x'(k) = A*x(k)
        self.state_pre = torch.matmul(self.transition_matrix, self.state_post)
        
        if control is not None and self.control_matrix is not None:
            # x'(k) = x'(k) + B*u(k)
            self.state_pre += torch.matmul(self.control_matrix, control)
        
        # Update error covariance: P'(k) = A*P(k)*A^T + Q
        self.temp1 = torch.matmul(self.transition_matrix, self.error_cov_post)
        self.error_cov_pre = torch.matmul(self.temp1, self.transition_matrix.t()) + self.process_noise_cov
        
        # Copy state to prepare for next prediction
        self.state_post = self.state_pre.clone()
        self.error_cov_post = self.error_cov_pre.clone()
        
        return self.state_pre
    
    def update(self, measurement):
        # Compute Kalman gain

        # temp2 = H*P'(k)
        self.temp2 = torch.matmul(self.measurement_matrix, self.error_cov_pre)
        # temp3 = temp2*Ht + R
        self.temp3 = torch.matmul(self.temp2, self.measurement_matrix.t()) + self.measurement_noise_cov

        # temp4 = P'(k)*Ht
        self.temp4 = torch.matmul(self.error_cov_pre, self.measurement_matrix.t())
        self.gain = torch.matmul(self.temp4, torch.inverse(self.temp3))
        
        # Update state estimate
        self.temp5 = measurement - torch.matmul(self.measurement_matrix, self.state_pre) # innovation
        self.state_post = self.state_pre + torch.matmul(self.gain, self.temp5)
        
        # Update error covariance estimate
        self.error_cov_post = self.error_cov_pre - torch.matmul(self.gain, self.temp2)
        
        return self.state_post


class TorchKF3D():
    def __init__(self, init_kinematic_state, x_error, y_error, z_error, dt, acceleration_error: float):
        self.acceleration_error = acceleration_error

        # no control parameters. Assuming the target is moving with a constant acceleration
        self.kalman = TorchKF(9, 3)

        # Define the initial values of the state variables ([x, y, z, vx, vy, vz, ax, ay, az])
        # ? Would initiating based on finite difference help us converge faster
        self.kalman.state_post = init_kinematic_state

        # Define the error associated to the initial values of the state variables  
        # TODO see if it converges faster with different values
        self.kalman.error_cov_post = torch.eye(6, 6, dtype=torch.float32)

        # Define the measurement noise covariance matrix
        # NOTE y_error could be made into a function that's dependent on the distance. The further out the more uncertain we are. 
        self.kalman.measurement_noise_cov = torch.tensor(
            [
                [x_error ** 2, 0, 0],
                [0, y_error ** 2, 0],
                [0, 0, z_error ** 2]
            ], dtype=torch.float32)
        
        # Encodes how off our dynamic model (i.e. constant acceleration model) is from reality
        # NOTE might need to change how this works because it could prove out to be too computationally expensive
        self.kalman.process_noise_cov = torch.tensor(
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
            ], dtype=torch.float32
        ) * (self.acceleration_error ** 2)

        # maps state variables into measurements
        self.kalman.measurement_matrix = torch.tensor(
            [
                [1, 0, 0, 0, 0, 0, 0, 0, 0],
                [0, 0, 0, 1, 0, 0, 0, 0, 0],
                [0, 0, 0, 0, 0, 0, 1, 0, 0]
            ], dtype=torch.float32)

        # encodes how the state variables will evolve over a certain period of time assuming target has a constant acceleration 
        self.kalman.transition_matrix = torch.tensor(
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
            ], dtype=torch.float32)


    def predict(self, dt=None):
        if dt:
            self.kalman.process_noise_cov = torch.tensor(
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
            ], dtype=torch.float32
            ) * (self.acceleration_error ** 2)

            self.kalman.transition_matrix = torch.tensor(
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
                ], dtype=torch.float32)
        else:
            print('WARNING: Failed to receive change in time (dt)')

        return self.kalman.predict()


    def correct(self, measurement):
        return self.kalman.update(measurement)
    
    # This function won't affect any of the member variables
    # won't be used for kalman.correct()
    def forward_predict(self, dt):
        transition_mat = torch.tensor(
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
            ], dtype=torch.float32)
        return torch.matmul(transition_mat, self.kalman.state_post)

class TorchKF2D():
    def __init__(self, init_kinematic_state, x_error, y_error, dt, acceleration_error: float):
        self.acceleration_error = acceleration_error

        # no control parameters. Assuming the target is moving with a constant acceleration
        self.kalman = TorchKF(6, 2)
        
        # Define the initial values of the state variables (x = [x, y, vx, vy, ax, ay])
         # ? Would initiating based on finite difference help us converge faster
        self.kalman.state_post = init_kinematic_state

        # Define the error associated to the initial values of the state variables  
        # TODO see if it converges faster with different values
        self.kalman.error_cov_post = torch.eye(6, 6, dtype=torch.float32)

        # Define the measurement noise covariance matrix
        # NOTE y_error could be made into a function based on the distance. The further out the more uncertain we are. 
        self.kalman.measurement_noise_cov = torch.tensor(
            [
                [x_error**2, 0],
                [0, y_error**2]
            ], dtype=torch.float32)
        
        # Encodes how off our dynamic model (constant acceleration model) is from reality
        # NOTE might need to change how this works because it could prove out to be too computationally expensive
        self.kalman.process_noise_cov = torch.tensor(
            [
                [(dt ** 4) / 4, (dt ** 3) / 2,  (dt ** 2) / 2, 0, 0, 0],
                [(dt ** 3) / 2, (dt ** 2), dt, 0, 0, 0],
                [(dt ** 2) / 2, dt, 1, 0, 0, 0],
                [0, 0, 0, (dt ** 4) / 4, (dt ** 3) / 2,  (dt ** 2) / 2],
                [0, 0, 0, (dt ** 3) / 2, (dt ** 2), dt],
                [0, 0, 0, (dt ** 2) / 2, dt, 1],
                
            ], dtype=torch.float32
        ) * (self.acceleration_error ** 2)

        # maps state variables into measurements
        self.kalman.measurement_matrix = torch.tensor(
            [
                [1, 0, 0, 0, 0, 0],
                [0, 0, 0, 1, 0, 0]

            ], dtype=torch.float32)

        # encodes how the state variables will evolve over a certain period of time assuming target has a constant acceleration 
        self.kalman.transition_matrix = torch.tensor(
            [
                [1, dt ,0.5 * dt ** 2, 0, 0, 0],
                [0, 1, dt, 0, 0, 0],
                [0, 0, 1, 0, 0, 0],
                [0, 0, 0, 1, dt, 0.5 * dt ** 2, ],
                [0, 0, 0, 0, 1, dt],
                [0, 0, 0, 0, 0, 1],
            
            ], dtype=torch.float32)
    

    def predict(self, dt=None):
        if dt:
            self.kalman.process_noise_cov = torch.tensor(
            [
                [(dt ** 4) / 4, (dt ** 3) / 2,  (dt ** 2) / 2, 0, 0, 0],
                [(dt ** 3) / 2, (dt ** 2), dt, 0, 0, 0],
                [(dt ** 2) / 2, dt, 1, 0, 0, 0],
                [0, 0, 0, (dt ** 4) / 4, (dt ** 3) / 2,  (dt ** 2) / 2],
                [0, 0, 0, (dt ** 3) / 2, (dt ** 2), dt],
                [0, 0, 0, (dt ** 2) / 2, dt, 1],
                
            ], dtype=torch.float32
            ) * (self.acceleration_error ** 2)
            self.kalman.transition_matrix = torch.tensor(
            [
                [1, dt ,0.5 * dt ** 2, 0, 0, 0],
                [0, 1, dt, 0, 0, 0],
                [0, 0, 1, 0, 0, 0],
                [0, 0, 0, 1, dt, 0.5 * dt ** 2, ],
                [0, 0, 0, 0, 1, dt],
                [0, 0, 0, 0, 0, 1],
            
            ], dtype=torch.float32)
        else:
            print('WARNING: Failed to receive change in time (dt)')

        return self.kalman.predict()


    def correct(self, measurement):
        return self.kalman.update(measurement)
    
    # This function won't affect any of the member variables
    # won't be used for kalman.correct()
    def forward_predict(self, dt):
        transition_mat = torch.tensor(
            [
                [1, dt ,0.5 * dt ** 2, 0, 0, 0],
                [0, 1, dt, 0, 0, 0],
                [0, 0, 1, 0, 0, 0],
                [0, 0, 0, 1, dt, 0.5 * dt ** 2, ],
                [0, 0, 0, 0, 1, dt],
                [0, 0, 0, 0, 0, 1],
            
            ], dtype=torch.float32)
        
        return torch.matmul(transition_mat, self.kalman.state_post)


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

        # encodes how the state variables will evolve over a certain period of time assuming target has a constant acceleration 
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