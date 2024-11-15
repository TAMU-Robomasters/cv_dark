import cv2
from toolbox.globals import runtime, config

record_interval = config.videostream.testing.record_interval


class VideoStream:
    def __init__(self) -> None:
        self.cam = cv2.VideoCapture(0)

        self.video_output = None
        if record_interval > 0:
            self.video_output = self.cam

    def frames(self):
        from itertools import count

        video_output_write = self.video_output and self.video_output.write

        def generator():
            for frame_number in count(1):  # starting at 1
                try:
                    self.color_frame = runtime.color_image = self.cam.read()[1]

                    yield frame_number, self.color_frame, None
                except Exception as error:  # failure to connect to web came
                    import sys
                    print(error)
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