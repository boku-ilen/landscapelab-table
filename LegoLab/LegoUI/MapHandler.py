import numpy as np
import cv2 as cv
import socket
from typing import Tuple
import logging

from ConfigManager import ConfigManager
from LegoUI.ImageHandler import ImageHandler

# Configure Logger
logger = logging.getLogger(__name__)


class MapHandler:

    def __init__(self, config: ConfigManager, extent, resolution: Tuple[int, int]):

        self.config = config

        # set resolution and extent
        self.resolution_x, self.resolution_y = resolution
        self.current_extent = self.fit_extent_to_screen_ratio(extent)

        # initialize two black images
        self.qgis_image = [
            np.ones((self.resolution_y, self.resolution_x, 3), np.uint8) * 255,
            np.ones((self.resolution_y, self.resolution_x, 3), np.uint8) * 255
        ]
        self.current_image = 0

        self.crs = config.get("map_settings", "crs")

        # set socket & connection info
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.qgis_addr = (config.get('qgis_interaction', 'QGIS_IP'), config.get('qgis_interaction', 'QGIS_READ_PORT'))
        self.lego_addr = (config.get('qgis_interaction', 'QGIS_IP'), config.get('qgis_interaction', 'LEGO_READ_PORT'))

        # get communication info
        self.image_path = config.get('qgis_interaction', 'QGIS_IMAGE_PATH')
        self.render_keyword = config.get('qgis_interaction', 'RENDER_KEYWORD')
        self.exit_keyword = config.get('qgis_interaction', 'EXIT_KEYWORD')

    def fit_extent_to_screen_ratio(self, extent):
        # calculate target ratio
        target_ratio = self.resolution_x / self.resolution_y

        # fit extent to target ratio and set it
        extent_width, extent_height = extent
        extent_w = abs(extent_width[0] - extent_width[1])
        extent_h = abs(extent_height[0] - extent_height[1])
        extent_h_diff = extent_w / target_ratio - extent_h

        # adjust height so that extent has the same ratio as beamer resolution
        if extent_height[0] < extent_height[1]:
            extent_height[0] -= extent_h_diff / 2
            extent_height[1] += extent_h_diff / 2
        else:
            extent_height[0] += extent_h_diff / 2
            extent_height[1] -= extent_h_diff / 2

        new_extent = [extent_width[0], extent_height[0], extent_width[1], extent_height[1]]

        # log result
        logger.info("extent: {}".format(str(new_extent)))
        logger.debug("extent width: {}, height: {}".format(
            new_extent[2] - new_extent[0],
            new_extent[3] - new_extent[1]
        ))

        return new_extent

    # reloads the viewport image
    def refresh(self, extent):
        logger.info("refreshing map")

        unused_slot = (self.current_image + 1) % 2

        image = cv.imread(self.image_path, -1)
        image = ImageHandler.ensure_alpha_channel(image)

        # put image on white background to eliminate issues with 4 channel image display
        alpha = image[:, :, 3] / 255.0
        image[:, :, 0] = (1. - alpha) * 255 + alpha * image[:, :, 0]
        image[:, :, 1] = (1. - alpha) * 255 + alpha * image[:, :, 1]
        image[:, :, 2] = (1. - alpha) * 255 + alpha * image[:, :, 2]
        image[:, :, 3] = 255

        # assign image and set slot correctly
        self.qgis_image[unused_slot] = image
        self.current_image = unused_slot

        # update extent and set extent changes flag unless extent stayed the same
        if not np.array_equal(self.current_extent, extent):
            self.current_extent = extent
            self.config.set("map_settings", "extent_changed", True)
            self.config.set("map_settings", "extent_width", [extent[0], extent[2]])
            self.config.set("map_settings", "extent_height", [extent[1], extent[3]])
            logger.info("extent changed")

        self.config.set("map_settings", 'map_refreshed', True)

    def request_render(self, extent=None):

        if extent is None:
            extent = self.current_extent

        self.send(
            '{keyword}{required_resolution} {crs} {extent0} {extent1} {extent2} {extent3}'.format(
                keyword=self.render_keyword, required_resolution=self.resolution_x, crs=self.crs,
                extent0=extent[0], extent1=extent[1], extent2=extent[2], extent3=extent[3]
            )
            .encode()
        )

    # sends a message to qgis
    def send(self, msg: bytes):
        logger.debug('sending to qgis: {}'.format(msg))
        self.sock.sendto(msg, self.qgis_addr)

    def get_frame(self):
        return self.qgis_image[self.current_image]

    def end(self):
        # self.sock.sendto(self.exit_keyword.encode(), self.qgis_addr)
        self.sock.sendto(self.exit_keyword.encode(), self.lego_addr)
        self.sock.close()
