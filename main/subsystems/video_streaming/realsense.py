import json

from super_map import LazyDict

from toolbox.video_tools import Video
from toolbox.globals import path_to, config, print, runtime

from time import time

import pyrealsense2 as rs

videostream     = config.videostream
aiming          = config.aiming
record_interval = videostream.testing.record_interval

MUS_TO_MS = 1000

runtime.realsense = LazyDict(
    frame=None,
    acceleration=LazyDict(x=0,y=0,z=0),
    gyro=LazyDict(x=0,y=0,z=0),
    intrins=None
)

DS5_product_ids = ["0AD1", "0AD2", "0AD3", "0AD4", "0AD5", "0AF6", "0AFE", "0AFF", "0B00", "0B01", "0B03", "0B07", "0B3A", "0B5C"]

def find_device_that_supports_advanced_mode():
    # from: https://github.com/IntelRealSense/librealsense/blob/master/wrappers/python/examples/python-rs400-advanced-mode-example.py
    ctx = rs.context()
    ds5_dev = rs.device()
    devices = ctx.query_devices()
    for dev in devices:
        if dev.supports(rs.camera_info.product_id) and str(dev.get_info(rs.camera_info.product_id)) in DS5_product_ids:
            if dev.supports(rs.camera_info.name):
                print("Found device that supports advanced mode:", dev.get_info(rs.camera_info.name))
            return dev
        dev.hardware_reset()
    raise Exception("No D400 product line device that supports advanced mode was found")

class VideoStream:
    def __init__(self):
        
        self.color_frame = None
        self.depth_frame = None

        stream_width  = aiming.stream_width
        stream_height = aiming.stream_height
        framerate     = aiming.stream_framerate

        self.depth_min = aiming.min_depth
        self.depth_max = aiming.max_depth
        
        self.video_output = None
        if record_interval > 0:
            self.video_output = self.begin_video_recording()

        self.pipeline = rs.pipeline() # declares and initializes the pipeline variable
        if config.realsense_settings:
            device = find_device_that_supports_advanced_mode() # self.pipeline.get_active_profile().get_device()
            rs.rs400_advanced_mode(device).load_json(json.dumps(config.realsense_settings))
        conf = rs.config()
        conf.enable_stream(rs.stream.depth, stream_width, stream_height, rs.format.z16, framerate)  # this starts the depth stream and sets the size and format
        conf.enable_stream(rs.stream.color, stream_width, stream_height, rs.format.bgr8, framerate) # this starts the color stream and set the size and format
        conf.enable_stream(rs.stream.accel)
        conf.enable_stream(rs.stream.gyro)
        # config.enable_stream(rs.stream.pose,rs.format.motion_xyz32f,200)
        
        while True:
            try:
                self.cfg = self.pipeline.start(conf)
                self.depth_scale = self.cfg.get_device().first_depth_sensor().get_depth_scale()
                self.color_intrin = self.cfg.get_stream(rs.stream.color).as_video_stream_profile().get_intrinsics()
                self.depth_intrin = self.cfg.get_stream(rs.stream.depth).as_video_stream_profile().get_intrinsics()
                self.depth_to_color_extrin = self.cfg.get_stream(rs.stream.depth).as_video_stream_profile().get_extrinsics_to(self.cfg.get_stream(rs.stream.color))
                self.color_to_depth_extrin = self.cfg.get_stream(rs.stream.color).as_video_stream_profile().get_extrinsics_to(self.cfg.get_stream(rs.stream.depth))

                sensors = self.pipeline.get_active_profile().get_device().query_sensors()
                for sensor in sensors:
                    sensor.set_option(rs.option.global_time_enabled, False)                # print("depth_scale:", self.depth_scale)
                # print("color_intrin:", self.color_intrin)
                # print("depth_intrin:", self.depth_intrin)
                # print("color fps: ", self.cfg.get_stream(rs.stream.color).fps)
                # print("depth fps: ", self.cfg.get_stream(rs.stream.depth).fps)
            except Exception as error:
                print("")
                print(error)
                print("trying again")
                continue
            # exit loop if successful
            break
    
    def frames(self):
        from numpy import array
        from itertools import count
        
        video_output_write = self.video_output and self.video_output.write
        
        def generator():
            for frame_number in count(1): # starting at 1
                try:
                    frame = runtime.realsense.frame = self.pipeline.wait_for_frames()
                    runtime.realsense.acceleration = frame[2].as_motion_frame().get_motion_data()
                    runtime.realsense.gyro         = frame[3].as_motion_frame().get_motion_data()
                    self.color_frame = frame.get_color_frame()
                    self.depth_frame = frame.get_depth_frame()

                    capture_time = frame.get_frame_metadata(rs.frame_metadata_value.sensor_timestamp)
                    frame_time = frame.get_frame_metadata(rs.frame_metadata_value.frame_timestamp)
                    self.capture_time = (time()*1000) - ((frame_time - capture_time)/MUS_TO_MS)
                    # print("frame_number:", frame_number, "capture_time:", self.capture_time)
                    yield frame_number, array(self.color_frame.get_data()), array(self.depth_frame.get_data())
                except Exception as error: # failure to connect to realsense
                    import sys
                    print("VideoStream: error while getting frames:", error, sys.exc_info()[0])
                    print('(retrying)')
        
        if not video_output_write:
            return generator()
        else:
            def wrapper():
                for frame_number, color_frame, depth_frame in generator():
                    if frame_number % record_interval == 0:
                        print(" saving_frame:", frame_number)
                        video_output_write(color_frame)
                    
                    yield frame_data
            return wrapper()
    
    def get_depth_at_point(self, point):
        depth_point = rs.rs2_project_color_pixel_to_depth_pixel(self.depth_frame.get_data(),
                                                            self.depth_scale,
                                                            self.depth_min,
                                                            self.depth_max,
                                                            self.depth_intrin,
                                                            self.color_intrin,
                                                            self.depth_to_color_extrin,
                                                            self.color_to_depth_extrin,
                                                            point) # color pixel)
        if (depth_point[0] < 0 or depth_point[1] < 0):
            return None
        depth = self.depth_frame.get_distance(int(depth_point[0]), int(depth_point[1]))
        return depth
    
    def get_xyz_at_point(self, point):
        depth = self.get_depth_at_point(point)
        if depth is None:
            return None
        point_3d = rs.rs2_deproject_pixel_to_point(self.depth_intrin, point, depth) # X is right/left, Y is forward/backward, Z is up/down
        point_3d[1], point_3d[2] = point_3d[2], -point_3d[1]
        return point_3d

    def __del__(self):
        print("Closing Realsense Pipeline")
        self.pipeline.stop()
    
    def begin_video_recording(self):
        """
        Run live video recording using nvenc.

        Input: None
        Output: Video object to add frames too.
        """
        import datetime
        color_video_location = path_to.record_video_output_color
        
        # Setup video output path based on date and counter
        c = 1
        file_path = color_video_location.replace(".do_not_sync",datetime.datetime.now().strftime("%Y-%m-%d")+"_"+str(c)+".do_not_sync")
        while os.path.isfile(file_path):
            c += 1
            file_path = color_video_location.replace(".do_not_sync",datetime.datetime.now().strftime("%Y-%m-%d")+"_"+str(c)+".do_not_sync")

        # Start up video output
        gst_out = "appsrc ! video/x-raw, format=BGR ! queue ! videoconvert ! video/x-raw,format=BGRx ! nvvidconv ! nvv4l2h264enc ! h264parse ! matroskamux ! filesink location="+file_path
        video_output = cv2.VideoWriter(gst_out, cv2.CAP_GSTREAMER, 0, float(framerate), (int(stream_width), int(stream_height)))
        if not video_output.isOpened():
            print("Failed to open output")

        return video_output    
    
    def save_video_if_needed(self):
        # Save video output
        if self.video_output:
            print("Saving Recorded Video")
            self.video_output.release()
            print("Finished Saving Video")