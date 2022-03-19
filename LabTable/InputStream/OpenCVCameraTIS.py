# enable logger
import logging
import cv2

from .TableInputStream import TableInputStream

logger = logging.getLogger(__name__)


class OpenCVCameraTIS(TableInputStream):

    camera = None

    def __init__(self, config, board, usestream):

        try:
            self.camera = cv2.VideoCapture(config.get("camera", "opencv_device_nr"))
        except Exception as e:
            logger.info("Could not initialize OpenCV Camera")
            logger.debug(e.__traceback__)

        super().__init__(config, board, usestream)

    def get_frame(self):
        frame = self.camera.read()
        return None, frame[1]  # frame[0] should return True - TODO: check for this?

    def close(self):
        if self.camera.isOpened():
            self.camera.release()
