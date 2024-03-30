import os
import sys
import cv2
import numpy as np
import torch
import torch.nn.functional as F
from torchvision.utils import save_image
# import torchvision.transforms.v2 as T

from ultralytics.engine.predictor import BasePredictor
from ultralytics.utils.ops import non_max_suppression
from ultralytics.data.augment import LetterBox

import tensorrt as trt

from toolbox.globals import config, print, print_synchronized, time_synchronized

class SquarePad:
    def __init__(self, input_size):
        w, h = input_size
        print(w, h)
        self.max_wh = max(w, h)
        self.hp = int((self.max_wh - w) / 2)
        self.vp = int((self.max_wh - h) / 2)
        self.padding = (self.hp, self.hp, self.vp, self.vp)
    def __call__(self, image):
        return F.pad(image, self.padding, 'constant', 0)

class Yolov8(object):
    """
    description: A YOLOv8 class that wraps initialization, preprocess and postprocess ops.
    """

    def __init__(self, model_filepath, model_dimension, rgb_input_dimension, acceleration, warmup=True):
        # config check
        assert acceleration in ['tensor_rt', 'gpu', 'cpu', None ]
        self.acceleration = acceleration

        def get_yolo_outputs(yolo_tens, *args, **kwargs):
            preds = non_max_suppression(yolo_tens, *args, **kwargs)[0]
            return preds[:, :4], preds[:, 4], preds[:, 5]

        if (self.acceleration == 'gpu' or self.acceleration == 'tensor_rt') and torch.cuda.is_available():
            print("[modeling]   GPU Acceleration: ENABLED\n")
            self.device = torch.device("cuda")
            if self.acceleration == 'tensor_rt':
                print("[modeling]   TensorRT: ENABLED\n")
                print("[modeling]   Warning: TensorRT will use prebuilt NMS value of 0.2. To change, rebuild TensorRT engine with new value.\n")

                # Register TRT plugins before deserializing engine
                logger = trt.Logger(trt.Logger.INFO)
                trt.init_libnvinfer_plugins(logger, namespace='')

                # nms excluded because tensorrt does it internally
                def get_yolo_outputs(yolo_tens, *args, **kwargs):
                    num_dets = yolo_tens[2][0].item()
                    bboxes, labels, confs = yolo_tens[0][0][:num_dets], yolo_tens[1][0][:num_dets], yolo_tens[3][0][:num_dets]
                    return bboxes, confs, labels
        else:
            print("[modeling]   Running on CPU\n")
            self.device = torch.device("cpu")
        
        self.get_yolo_outputs = get_yolo_outputs

        self.model_input_w = self.model_input_h = model_dimension

        # Computed once for rescaling
        self.h_rescaler = rgb_input_dimension[0] / self.model_input_h
        self.w_rescaler = rgb_input_dimension[1] / self.model_input_w

        # load model locally
        overrides = {'model': model_filepath,
                    'device': "0" if self.device.type == "cuda" else "cpu",
                    'half': True,
                    'imgsz': (self.model_input_h, self.model_input_w),
                    'verbose': False,
                    'save': False,
                    }
        self.predictor = BasePredictor(overrides=overrides)

        self.predictor.setup_model(self.predictor.model, verbose=False)

        self.predict = lambda image_tens: self.predictor.model(image_tens)

        # if warmup:
        #     self.predictor.model.warmup(imgsz=(1, 3, self.model_input_h, self.model_input_w))
        #     print("\n[modeling]   Warmup complete\n")
        
        # else:
        #     raise Exception(f'''acceleration == {acceleration}''')

    def preprocess_image(self, image_pre):
        # takes in (H, W, C) BGR image

        # t = time_synchronized()
        image_tensor = torch.as_tensor(image_pre, device=self.device) # create torch tensor directly on device (GPU or CPU)
        image_tensor = image_tensor.permute(2, 0, 1) # HWC to CHW
        image_tensor = image_tensor[[2, 1, 0]].unsqueeze(0) # RGB to BGR, add batch dimension
        image_tensor = F.interpolate(image_tensor, size=(self.model_input_w, self.model_input_h)) / 255 # resize, normalize from 0-255 to 0-1.0
        # save_image(image_tensor[0], 'imgtensor.png')
        if self.acceleration != 'tensor_rt': # half precision not supported in TensorRT
            image_tensor = image_tensor.half()
        # print(f"preprocess: {time_synchronized() - t:.3f} s")

        return image_tensor

    def infer(self, image_tensor):
        # time this
        # t = time_synchronized()
        preds = self.predict(image_tensor)
        # print(f"infer: {time_synchronized() - t:.3f} s")
        return preds

    def rescale_coords_to_original(self, boxes):
        """
        description:    Rescale the coordinates of the boxes from model size to image size
        param:
            boxes:     A boxes numpy, each row is a box [x1, y1, x2, y2]
        return:
            boxes:     A boxes numpy, each row is a box [x1, y1, x2, y2]
        """        
        boxes[:, [0, 2]] *= self.w_rescaler
        boxes[:, [1, 3]] *= self.h_rescaler
        return boxes

    def postprocess_preds(self, yolo_tens, conf_thres, detect_class=False):
        """
        description:    Postprocess the results from model inference
        param:
            yolo_tens:        A PyTorch Tensor, as output by YOLO
            detect_class:     Whether to detect class (in case model isn't trained to detect class)
        return:
            boxes: boxes, confidences, class_ids
        """
        # time this
        # t = time_synchronized()
        bboxes, confs, labels = self.get_yolo_outputs(yolo_tens=yolo_tens, conf_thres=conf_thres, iou_thres=0.2, max_nms=20)

        bboxes = self.rescale_coords_to_original(bboxes).round()
        # print(bboxes)
        # print(f"nms + rescale: {time_synchronized() - t:.3f} s")
        return bboxes, confs, labels