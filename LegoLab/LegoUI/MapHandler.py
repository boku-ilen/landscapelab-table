import numpy as np
import cv2 as cv
import socket
from typing import Tuple
import logging

from .ImageHandler import ImageHandler
from ..ConfigManager import ConfigManager
from ..LegoExtent import LegoExtent
from ..ExtentTracker import ExtentTracker

# Configure Logger
logger = logging.getLogger(__name__)


class MapHandler:

    def __init__(self, config: ConfigManager, name: str, extent: LegoExtent, resolution: Tuple[int, int]):
        self.name = name
        self.config = config
        self.extent_tracker = ExtentTracker.get_instance()

        # set resolution and extent
        self.resolution_x, self.resolution_y = resolution
        extent.fit_to_ratio(self.resolution_y / self.resolution_x)
        self.current_extent: LegoExtent = extent

        # initialize two black images
        self.map_image = [
            ImageHandler.ensure_alpha_channel(np.ones((self.resolution_y, self.resolution_x, 3), np.uint8) * 255),
            ImageHandler.ensure_alpha_channel(np.ones((self.resolution_y, self.resolution_x, 3), np.uint8) * 255)
        ]
        self.current_image = 0

        self.crs = config.get("map_settings", "crs")

        # set socket & connection info
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.qgis_addr = (config.get('qgis_interaction', 'QGIS_IP'), config.get('qgis_interaction', 'QGIS_READ_PORT'))
        self.lego_addr = (config.get('qgis_interaction', 'QGIS_IP'), config.get('qgis_interaction', 'LEGO_READ_PORT'))

        # get communication info
        self.image_path: str = config.get('qgis_interaction', 'QGIS_IMAGE_PATH')
        self.render_keyword = config.get('qgis_interaction', 'RENDER_KEYWORD')
        self.exit_keyword = config.get('qgis_interaction', 'EXIT_KEYWORD')

    # reloads the viewport image
    def refresh(self, extent: LegoExtent):
        logger.info("refreshing map")

        unused_slot = (self.current_image + 1) % 2

        image = cv.imread(self.image_path.format(self.name), -1)
        image = ImageHandler.ensure_alpha_channel(image)

        # put image on white background to eliminate issues with 4 channel image display
        alpha = image[:, :, 3] / 255.0
        image[:, :, 0] = (1. - alpha) * 255 + alpha * image[:, :, 0]
        image[:, :, 1] = (1. - alpha) * 255 + alpha * image[:, :, 1]
        image[:, :, 2] = (1. - alpha) * 255 + alpha * image[:, :, 2]
        image[:, :, 3] = 255

        # assign image and set slot correctly
        self.map_image[unused_slot] = image
        self.current_image = unused_slot

        # update extent and set extent changes flag unless extent stayed the same
        if not extent == self.current_extent:
            self.current_extent = extent

            self.extent_tracker.map_extent = extent
            self.extent_tracker.extent_changed = True
            logger.info("extent changed")

        self.config.set("map_settings", 'map_refreshed', True)

    def request_render(self, extent: LegoExtent = None):

        if extent is None:
            extent = self.current_extent

        self.send(
            '{keyword}{target_name} {required_resolution} {crs} {extent0} {extent1} {extent2} {extent3}'.format(
                keyword=self.render_keyword, target_name=self.name, required_resolution=self.resolution_x, crs=self.crs,
                extent0=extent.x_min, extent1=extent.y_min, extent2=extent.x_max, extent3=extent.y_max
            )
            .encode()
        )

    # sends a message to qgis
    def send(self, msg: bytes):
        logger.debug('sending to qgis: {}'.format(msg))
        self.sock.sendto(msg, self.qgis_addr)

    def get_map_image(self):
        return self.map_image[self.current_image]

    def end(self):
        # self.sock.sendto(self.exit_keyword.encode(), self.qgis_addr)
        self.sock.sendto(self.exit_keyword.encode(), self.lego_addr)
        self.sock.close()
