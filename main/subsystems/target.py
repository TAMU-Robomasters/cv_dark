from typing import Union
from toolbox.geometry_tools import BoundingBox, Position
from toolbox.kalman_filter import KF2D, KF3D


class IDSystem:
    def __init__(self):
        self.used_ids = []
        self.targets = []

    def update(self, *bboxes:BoundingBox):
        if bboxes == None:
            pass
        if self.targets != None: # init targets
            for bbox in bboxes:
                



# TODO find out if conf is just a float
# TODO configures this to work for non depth compatible
class Target:
    def __init__(self, id: int, bbox:BoundingBox, conf, target_3d:Position, kf:Union[KF2D, KF3D]):
        self.id = id
        self.bbox = bbox
        self.conf = conf
        self.center_point = bbox.center # center point is in units of pixels
        self.target_3d = target_3d
        self.kf = kf

    def __repr__(self) -> str:
        str_width = 30
        str_repr = f'TARGET INFO\n'.center(str_width)
        str_repr += f'ID: {self.id}\n'.center(str_width)
        str_repr += f'BBOX: {self.bbox}\n'.center(str_width)
        str_repr += f'Center Point (pixel units): {self.center_point}\n'.center(str_width)
        str_repr += f'Target Measured Position (meters): {self.target_3d}\n'.center(str_width)
        # TODO figure out dt stuff
        current_kinematic_state = self.kf.forward_predict(dt)
        str_repr += f'Current Estimate of target\'s kinematic state (meters):\n \/
                    Position: {current_kinematic_state[0]}, {current_kinematic_state[3]}, {current_kinematic_state[6]}\n \/
                    Velocity: {current_kinematic_state[1]}, {current_kinematic_state[4]}, {current_kinematic_state[7]}\n \/
                    Acceleration: {current_kinematic_state[2]}, {current_kinematic_state[5]}, {current_kinematic_state[8]}\n \/'.center(str_width)
        return str_repr
    

    
        
