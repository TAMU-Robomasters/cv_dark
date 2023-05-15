from threading import Thread
from time import sleep

class CameraThreader:
    def __init__(self, vid_stream):
        self.vid_stream = vid_stream
        self.frame = None

        self.stopped = True
        self.t = Thread(target=self.update, args=())
        self.t.daemon = True
        
        self.start()

    def start(self):
        self.stopped = False
        self.t.start()

    def update(self):
        while not self.stopped:
            self.frame = self.vid_stream.frames()
            sleep(0.001) #1ms
    
    def frames(self):
        return self.frame

    def stop(self):
        self.stopped = True

    def __del__(self):
        self.t.join()