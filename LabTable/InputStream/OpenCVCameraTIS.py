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

    def __init__(self, config, board, usestream):

        try:
            dev_num = config.get("camera", "opencv_device_nr")
            self.camera = cv2.VideoCapture(dev_num)
            self.camera.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter.fourcc('M','J','P','G'))
            self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, config.get("video_resolution","width"))
            self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, config.get("video_resolution", "height"))
            self.camera.set(cv2.CAP_PROP_FPS, 30)
            cam_options = [
                ("auto_exposure", 1),
                ("focus_automatic_continuous", 0),
                ("focus_absolute", 0),
                ("white_balance_automatic",1),
                ("sharpness", 0)
            ]
            if sys.platform == "linux":
                for cam in cam_options:
                    linux_set_cam_option(cam[0], cam[1], dev_num)
            logger.info(self.camera.get(cv2.CAP_PROP_AUTO_EXPOSURE))

            self.camera.set(cv2.CAP_PROP_ZOOM, 128)
            self.camera.set(cv2.CAP_PROP_EXPOSURE, 100)

            self.distance = config.get("camera", "base_distance")
        except Exception as e:
            logger.info("Could not initialize OpenCV Camera")
            logger.debug(e.__traceback__)

        super().__init__(config, board, usestream)

    def get_frame(self):
        ok = False
        tries = 0
        while not ok and tries < 10:
            tries += 1
            ok,frame = self.camera.read()
        return None, frame  # frame[0] should return True - TODO: check for this?

    def close(self):
        if self.camera.isOpened():
            self.camera.release()

    def get_horizontal_fov(self):
        return 65.952
    def get_distance_to_board(self):
        self.board.distance = self.distance
