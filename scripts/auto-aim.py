# Trial Function for filterefd_position:

def filtered_position(best_target_3d):
    self.kalman = cv2.KalmanFilter(best_target_3d[0], best_target_3d[1], best_target_3d[2])
    
    