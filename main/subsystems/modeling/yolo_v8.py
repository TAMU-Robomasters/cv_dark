# library imports
import numpy as np
import cv2
import os
import time
import torch

# project imports
from toolbox.globals import path_to, absolute_path_to, config, print, runtime, time_synchronized
from toolbox.geometry_tools import BoundingBox, Position

#
# config
#
hardware_acceleration = config.model.hardware_acceleration
input_dimension = config.model.input_dimension
which_model = config.model.which_model

#
#
# helpers
#
#
def init_yolo_v8(model):
    print("\n[modeling] YOLO v8 loading")

    loaded_model = None

    if hardware_acceleration == 'tensor_rt':
        pass
    else:
        from subsystems.modeling.plugins.yolo_v8_plugins.yolo_v8_plugin import Yolov8

        if not os.path.exists(path_to.yolo_v8.pytorch_model):
            raise Exception(
                f"model not found at {path_to.yolo_v8.pytorch_model}")

        # create Yolov8 object
        model.yolov8 = Yolov8(model_filepath=path_to.yolo_v8.pytorch_model,
                            cfg_filepath=path_to.yolo_v8.settings,
                            input_dimension=config.model.input_dimension,
                            acceleration=config.model.hardware_acceleration)

        # export data
        model.net = model.yolov8.model
        model.get_bounding_boxes = lambda *args, **kwargs: yolo_v8_beta_bounding_boxes(
            model, *args, **kwargs)

def yolo_v8_beta_bounding_boxes(model, frame, minimum_confidence, threshold):
    # t0 = time_synchronized()

    # image_tensor, image_pre, image_h, image_w = model.yolov8.preprocess_image(
    #     frame)

    # t1 = time_synchronized()

    yolo_tens, inf_time = model.yolov8.infer(frame)

    # t2 = time_synchronized()

    # outputs = model.yolov8.non_max_suppression(
    #     inf_output, conf_thresh=0.25, nms_thresh=0.20)

    # print(results)

    # results = model.yolov8.postprocess_results(yolo_tens, detect_class=False)

    # t3 = time_synchronized()
    # print(results[0][:4])
    # print(results[0].boxes.xyxy)
    # raw_boxes = results.boxes.xyxy

    # print(results[0])

    raw_boxes = yolo_tens[0].boxes.xyxy
    confidences = yolo_tens[0].boxes.conf
    class_ids = yolo_tens[0].boxes.cls

    # print(raw_boxes, confidences, class_ids)

    boxes = [BoundingBox.from_points(
        top_left=(x1, y1), bottom_right=(x2, y2)) for x1, y1, x2, y2 in raw_boxes]

    # t4 = time_synchronized()

    # print(f"\n\npreprocess: {t1 - t0:.3f} s")
    # print(f"inference: {t2 - t1:.3f} s")
    # print(f"nms: {t3 - t2:.3f} s")
    # print(f"postprocess: {t4 - t3:.3f} s")

    return boxes, confidences, class_ids
    # return [], [], []