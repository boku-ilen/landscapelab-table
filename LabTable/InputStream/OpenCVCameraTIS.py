# enable logger
import logging
import cv2

from .TableInputStream import TableInputStream

logger = logging.getLogger(__name__)


class OpenCVCameraTIS(TableInputStream):

    camera = None

    def __init__(self, config, board, usestream):
        super().__init__(config, board, usestream)
        try:
            # FIXME: this outputs CPP warning and does not throw an exception
            self.camera = cv2.VideoCapture(-1)  # FIXME: configure device
        except:
            logger.info("Could not initialize OpenCV Camera")

    def get_frame(self):
        ret, frame = self.camera.read()

    def close(self):
        if self.camera.isOpened():
            self.camera.release()
