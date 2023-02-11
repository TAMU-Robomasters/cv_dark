import cv2
import os
import datetime
import pyzed.sl as sl
import numpy as np
# relative imports
from time import time

from toolbox.video_tools import Video
from toolbox.globals import path_to, config, print, runtime


videostream = config.videostream
aiming      = config.aiming
record_interval = videostream.testing.record_interval

class VideoStream:
    def __init__(self):
        
        self.video_output = None
        if record_interval > 0:
            self.video_output = self.begin_video_recording()

        self.zed = None
        self.zed = sl.Camera()

        init_params = sl.InitParameters(sdk_verbose=True)

        init_params.camera_resolution = getattr(sl.RESOLUTION, config.zed.resolution)
        init_params.depth_mode        = getattr(sl.DEPTH_MODE, config.zed.depth_mode)
        init_params.coordinate_units  = getattr(sl.UNIT      , config.zed.unit      )
        init_params.coordinate_system = sl.COORDINATE_SYSTEM.LEFT_HANDED_Y_UP
        init_params.depth_minimum_distance = 0.3
        init_params.depth_maximum_distance = 10.0

        self.capture_time = 0
                
        err = self.zed.open(init_params)
        while err != sl.ERROR_CODE.SUCCESS:
            print('VideoStream: Failed to open ZED camera! Retrying...')
            err = self.zed.open(init_params)

        detection_parameters = sl.ObjectDetectionParameters()
        detection_parameters.detection_model = sl.DETECTION_MODEL.CUSTOM_BOX_OBJECTS
        detection_parameters.enable_tracking = True
        detection_parameters.enable_mask_output = True

        if detection_parameters.enable_tracking:
            positional_tracking_parameters = sl.PositionalTrackingParameters()
            err = self.zed.enable_positional_tracking(positional_tracking_parameters)
            while err != sl.ERROR_CODE.SUCCESS:
                print('VideoStream: Failed to enable positional tracking! Retrying...')
                err = self.zed.enable_positional_tracking(positional_tracking_parameters)

        self.zed_pose = sl.Pose()

        err = self.zed.enable_object_detection(detection_parameters)
        while err != sl.ERROR_CODE.SUCCESS:
            print('VideoStream: Failed to enable object detection! Retrying...')
            err = self.zed.enable_object_detection(detection_parameters)
        # TODO - customize runtime params with config
        self.runtime_parameters = sl.RuntimeParameters()
        self.runtime_parameters.sensing_mode = sl.SENSING_MODE.STANDARD
        
        self.image_size = self.zed.get_camera_information().camera_resolution
        
        self.color_frame = sl.Mat(self.image_size.width, self.image_size.height, sl.MAT_TYPE.U8_C4)
        # sl.Mat(resolution.width, 
        #             resolution.height,
        #             sl.MAT_TYPE.MAT_TYPE_8U_C4,
        #             memory_type=sl.MEM.MEM_GPU)
        self.depth_frame = sl.Mat(self.image_size.width, self.image_size.height, sl.MAT_TYPE.U8_C4)

        self.point_cloud = sl.Mat()
    
    # def frames(self):
    #     """
    #     Returns a generator that outputs color and depth frames. Save the frames on the fly if video recording is enabled.

    #     Input: None
    #     Output: A generator which will produce color and depth images at each step.
    #     """
    #     frame_number = 0
    #     # retry after failure
    #     while True:
    #         while self.zed.grab(self.runtime_parameters) == sl.ERROR_CODE.SUCCESS:
    #             frame_number += 1

    #             # TODO - if using depth and left camera view, have to reconcile them with an additional transformation
    #             self.zed.retrieve_image(self.color_frame, sl.VIEW.LEFT, sl.MEM.CPU, self.image_size)
    #             self.zed.retrieve_measure(self.depth_frame, sl.MEASURE.DEPTH, sl.MEM.CPU, self.image_size)
                
    #             self.pose_state = self.zed.get_position(self.zed_pose, sl.REFERENCE_FRAME.WORLD)
    #             # Convert images to ocv format, remove alpha channel
    #             # self.color_frame = self.color_frame.get_data()
    #             # self.depth_frame = self.depth_frame.get_data()
    #             # Add frame to video recording based on recording frequency
    #             if self.video_output and (frame_number % videostream.testing.record_interval == 0):
    #                 print(" saving_frame:",frame_number)
    #                 self.video_output.write(self.color_frame.get_data())
    #             # cv2.imshow('img', depth_frame)
    #             # cv2.waitKey(100)
    #             yield frame_number, self.color_frame.get_data(), self.depth_frame.get_data()
    #         if config.mode == 'development':
    #             print("VideoStream: unable to retrieve frame.")
    #             print('(retrying)')

    def frames(self):
        from itertools import count
        video_output_write = self.video_output and self.video_output.write

        gpu_color_frame = cv2.cuda_GpuMat()

        def generator():
            for frame_number in count(1):
                if self.zed.grab(self.runtime_parameters) == sl.ERROR_CODE.SUCCESS:
                    self.zed.retrieve_image(self.color_frame, sl.VIEW.LEFT, sl.MEM.CPU, self.image_size)
                    # self.zed.retrieve_measure(self.depth_frame, sl.MEASURE.DEPTH, sl.MEM.CPU, self.image_size)
                
                    self.pose_state = self.zed.get_position(self.zed_pose, sl.REFERENCE_FRAME.WORLD)

                    # gpu_color_frame.upload(self.color_frame.get_data())
                    
                    # color_img_rgb = cv2.cuda.cvtColor(gpu_color_frame, cv2.COLOR_RGBA2RGB)
                    color_img_rgb = cv2.cvtColor(self.color_frame.get_data(), cv2.COLOR_RGBA2RGB)
            
                    yield frame_number, color_img_rgb, None # self.depth_frame.get_data()
                else:
                    print("VideoStream: unable to retrieve frame.")
                    print('(retrying)')
        
        if not video_output_write:
            return generator()
        else:
            def wrapper():
                for frame_number, color_image, depth_image in generator():
                    if frame_number % record_interval == 0:
                        print(" saving_frame:",frame_number)
                        video_output_write(color_image)
                    yield frame_data
            return wrapper()

    def get_xyz_at_point(self, point):
        self.zed.retrieve_measure(self.point_cloud, sl.MEASURE.XYZRGBA)
        point_3d = self.point_cloud.get_value(point[0], point[1])
        if (point_3d[0] != sl.ERROR_CODE.SUCCESS):
            return None
        else:
            # print(f"point_3d: {point_3d[1][0]}, {point_3d[1][1]}, {point_3d[1][2]}")
            return (point_3d[1][0], point_3d[1][1], point_3d[1][2])

    def get_position(self):
        py_translation = sl.Translation()
        tx = round(self.zed_pose.get_translation(py_translation).get()[0], 3)
        ty = round(self.zed_pose.get_translation(py_translation).get()[1], 3)
        tz = round(self.zed_pose.get_translation(py_translation).get()[2], 3)
        print("Translation: Tx: {0}, Ty: {1}, Tz {2}".format(tx, ty, tz))
        return (tx, ty, tz)
    
    def get_orientation(self):
        py_orientation = sl.Orientation()
        ox = round(self.zed_pose.get_orientation(py_orientation).get()[0], 3)
        oy = round(self.zed_pose.get_orientation(py_orientation).get()[1], 3)
        oz = round(self.zed_pose.get_orientation(py_orientation).get()[2], 3)
        ow = round(self.zed_pose.get_orientation(py_orientation).get()[3], 3)
        print("Orientation: Ox: {0}, Oy: {1}, Oz {2}, Ow {3}".format(ox, oy, oz, ow))
        return (ox, oy, oz, ow)

    def __del__(self):
        if self.zed:
            print("Closing ZED camera")
            self.zed.close()
    
    # TODO - another option for ZED is to use SVO instead of a collection of video frames.
    # If we want to record with SVO, we cannot also use the camera in "live" mode.
    # The benefit of SVO is that it fakes all zed sensors if we want to replay it in a testing env.
    def begin_video_recording(self):
        """
        Run live video recording using nvenc.

        Input: None
        Output: Video object to add frames too.
        """

        color_video_location = path_to.record_video_output_color
        
        # Setup video output path based on date and counter
        c = 1
        file_path = color_video_location.replace(".do_not_sync",datetime.datetime.now().strftime("%Y-%m-%d")+"_"+str(c)+".do_not_sync")
        while os.path.isfile(file_path):
            c += 1
            file_path = color_video_location.replace(".do_not_sync",datetime.datetime.now().strftime("%Y-%m-%d")+"_"+str(c)+".do_not_sync")

        # Start up video output
        gst_out = "appsrc ! video/x-raw, format=BGR ! queue ! videoconvert ! video/x-raw,format=BGRx ! nvvidconv ! nvv4l2h264enc ! h264parse ! matroskamux ! filesink location="+file_path
        video_output = cv2.VideoWriter(gst_out, cv2.CAP_GSTREAMER, 0, float(aiming.framerate), (int(aiming.stream_width), int(aiming.stream_height)))
        if not video_output.isOpened():
            print("Failed to open output")

        return video_output    
    
    def save_video_if_needed(self):
        # Save video output
        if self.video_output:
            print("Saving Recorded Video")
            self.video_output.release()
            print("Finished Saving Video")
