# enable logger
import logging
import sys

import cv2
import subprocess
from .TableInputStream import TableInputStream
from ..Model.Board import Board

logger = logging.getLogger(__name__)

def linux_set_cam_option(option_name, value, device):
    subprocess.run(["v4l2-ctl", "-d", str(device), "-c", f"{option_name}={value}"])

class OpenCVCameraTIS(TableInputStream):

    camera = None
    distance = 0
    fov = 65

    def __init__(self, config, board, usestream):

        try:
            dev_num = config.get("camera", "opencv_device_nr")
            if sys.platform == "win32":
                # on windows, manually select DSHOW backend
                self.camera = cv2.VideoCapture(dev_num, cv2.CAP_DSHOW)
            else:
                # on linux, automatic selection works fine
                self.camera = cv2.VideoCapture(dev_num)
            self.camera.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter.fourcc('M','J','P','G'))
            self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, config.get("video_resolution","width"))
            self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, config.get("video_resolution", "height"))
            self.camera.set(cv2.CAP_PROP_FPS, config.get("video_resolution", "framerate"))
            if sys.platform == "linux":
                linux_options = config.get("camera", "linux_options")
                for opt in linux_options.keys():
                    linux_set_cam_option(opt, linux_options[opt], dev_num)

                self.camera.set(cv2.CAP_PROP_ZOOM, config.get("camera", "opencv_zoom"))
                self.camera.set(cv2.CAP_PROP_EXPOSURE, config.get("camera", "opencv_exposure"))

            self.last_handled_frame_count = 0
        except Exception as e:
            logger.info("Could not initialize OpenCV Camera")
            logger.debug(e.__traceback__)

        super().__init__(config, board, usestream)

    def get_frame(self):
        if not self.camera.grab():
            return None, None
        ok, frame = self.camera.retrieve()
        if ok:
            return None, frame
        return None, None

    def close(self):
        if self.camera.isOpened():
            self.camera.release()