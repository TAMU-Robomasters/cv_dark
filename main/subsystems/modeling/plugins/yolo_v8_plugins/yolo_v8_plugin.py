import ctypes
import os
import shutil
import random
import sys
import threading
import time
import cv2
import numpy as np
import torch
import torch.nn.functional as F
from torchvision import transforms
from torchvision.ops import nms
from ultralytics import YOLO

from toolbox.globals import print, time_synchronized

class Yolov8(object):
    """
    description: A YOLOv8 class that wraps initialization, preprocess and postprocess ops.
    """

    def __init__(self, model_filepath, input_dimension, acceleration):
        # config check
        assert acceleration in ['tensor_rt', 'gpu', None]
        self.acceleration = acceleration

        self.input_w = self.input_h = input_dimension

        # load model locally
        self.model = YOLO(model_filepath, type='v8')

        if acceleration == 'gpu' and torch.cuda.is_available():
            print("[modeling]   gpu_acceleration: ENABLED\n")
            self.device = torch.device("cuda")
            # print(next(self.model.parameters()).is_cuda)
        else:
            print("[modeling]   Running on CPU\n")
            self.device = torch.device("cpu")
        
        self.model.to(self.device)

        self.model.fuse()
        self.model.info(verbose=True)  # Print model information

    def preprocess_image(self, image_pre):
        # takes in (h, w, c) BGR image
        # t1 = time_synchronized()
        image_tensor = torch.as_tensor(image_pre, device=self.device)
        # image_tensor = torch.from_numpy(image_pre).to(self.device)
        # t2 = time_synchronized()
        image_tensor = image_tensor.permute(2, 0, 1)
        # t3 = time_synchronized()
        image_tensor = image_tensor[[2, 1, 0]]
        # t4 = time_synchronized()
        image_tensor = image_tensor.unsqueeze(0)
        # t5 = time_synchronized()
        image_tensor = F.interpolate(image_tensor, size=(self.input_w, self.input_h)).div(255.0).half()
        # t6 = time_synchronized()

        # print(f"\ntensorify: {t2-t1:.3f} s")
        # print(f"permute: {t3-t2:.3f} s")
        # print(f"recolor: {t4-t3:.3f} s")
        # print(f"unsqueeze: {t5-t4:.3f} s")
        # print(f"resize: {t6-t5:.3f} s")
        return image_pre, image_pre, image_pre.shape[0], image_pre.shape[1]

    def infer(self, image_tensor):
        # start = time_synchronized()
        results = self.model.predict(image_tensor)
        # end = time_synchronized()
        return results, 0

    def xywh2xyxy(self, x):
        # Convert nx4 boxes from [x, y, w, h] to [x1, y1, x2, y2] where xy1=top-left, xy2=bottom-right
        y = x.clone() if isinstance(x, torch.Tensor) else np.copy(x)
        y[:, 0] = x[:, 0] - x[:, 2] / 2  # top left x
        y[:, 1] = x[:, 1] - x[:, 3] / 2  # top left y
        y[:, 2] = x[:, 0] + x[:, 2] / 2  # bottom right x
        y[:, 3] = x[:, 1] + x[:, 3] / 2  # bottom right y
        return y

    def rescale_coords_to_original(self, image_h, image_w, boxes):
        """
        description:    Rescale the coordinates of the boxes from model size to image size
        param:
            image_h:   height of original image
            image_w:   width of original image
            boxes:     A boxes numpy, each row is a box [x1, y1, x2, y2]
        return:
            boxes:     A boxes numpy, each row is a box [x1, y1, x2, y2]
        """
        h_rescaler = image_h / self.input_h
        w_rescaler = image_w / self.input_w

        boxes[:, 0] = boxes[:, 0] * w_rescaler
        boxes[:, 1] = boxes[:, 1] * h_rescaler
        boxes[:, 2] = boxes[:, 2] * w_rescaler
        boxes[:, 3] = boxes[:, 3] * h_rescaler
        return boxes
