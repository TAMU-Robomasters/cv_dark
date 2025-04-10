"""Loads the camera to turret linear transformation 
    as a list of numpy matrices and provides a function
    to access the closet transformation given the time
"""
import numpy as np

DATA_FILENAME = "./Ozone_DataSampling_250302 2.csv"

class CamToTurretTransformation:
    def __init__(self) -> None:
        transformation_table = np.loadtxt(DATA_FILENAME, delimiter=',')
        self._transformation_matrices = transformation_table[:][2:].reshape(-1, 4, 4)
        self._index_per_time = 1000
        
# add check to see if the data was sampled at 10khz
        
    def trasnformation_at_time(time: float) -> np.ndarray:
        """find the nearest transformation at the time given
            time is in seconds"""
        
    