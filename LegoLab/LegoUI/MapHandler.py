import numpy as np
import cv2 as cv
import socket
from functools import partial
from typing import Dict
import logging

from ..ConfigManager import ConfigManager, ConfigError
from ..LegoUI.MapActions import MapActions
from ..LegoUI.ImageHandler import ImageHandler

# Configure Logger
logger = logging.getLogger(__name__)


class MapHandler:

    MAP_REFRESHED = True

    def __init__(self, config: ConfigManager, scenario: Dict):

        self.config = config

        # get desired screen resolution
        self.resolution_x = int(self.config.get("beamer-resolution", "width"))
        self.resolution_y = int(self.config.get("beamer-resolution", "height"))

        # initialize two black images
        self.qgis_image = [
            np.ones((self.resolution_y, self.resolution_x, 3), np.uint8) * 255,
            np.ones((self.resolution_y, self.resolution_x, 3), np.uint8) * 255
        ]
        self.current_image = 0

        # calculate beamer ratio
        beamer_ratio = self.resolution_x / self.resolution_y

        # fit extent to beamer ratio and set it
        extent_width, extent_height = self.get_start_extent(scenario)
        extent_w = abs(extent_width[0] - extent_width[1])
        extent_h = abs(extent_height[0] - extent_height[1])
        extent_h_diff = extent_w / beamer_ratio - extent_h
        # adjust height so that extent has the same ratio as beamer resolution
        if extent_height[0] < extent_height[1]:
            extent_height[0] -= extent_h_diff / 2
            extent_height[1] += extent_h_diff / 2
        else:
            extent_height[0] += extent_h_diff / 2
            extent_height[1] -= extent_h_diff / 2
        self.current_extent = [extent_width[0], extent_height[0], extent_width[1], extent_height[1]]
        logger.info("extent: {}".format(str(self.current_extent)))
        logger.debug("extent width: {}, height: {}".format(
            self.current_extent[2] - self.current_extent[0],
            self.current_extent[3] - self.current_extent[1]
        ))

        # set new extent
        self.config.set("map_settings", "extent_width", [self.current_extent[0], self.current_extent[2]])
        self.config.set("map_settings", "extent_height", [self.current_extent[1], self.current_extent[3]])

        self.crs = config.get("map_settings", "crs")

        # set socket & connection info
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.qgis_addr = (config.get('qgis_interaction', 'QGIS_IP'), config.get('qgis_interaction', 'QGIS_READ_PORT'))
        self.lego_addr = (config.get('qgis_interaction', 'QGIS_IP'), config.get('qgis_interaction', 'LEGO_READ_PORT'))

        # get communication info
        self.image_path = config.get('qgis_interaction', 'QGIS_IMAGE_PATH')
        self.render_keyword = config.get('qgis_interaction', 'RENDER_KEYWORD')
        self.exit_keyword = config.get('qgis_interaction', 'EXIT_KEYWORD')

        # set extent modifiers
        pan_up_modifier = np.array([0, 1, 0, 1])
        pan_down_modifier = np.array([0, -1, 0, -1])
        pan_left_modifier = np.array([-1, 0, -1, 0])
        pan_right_modifier = np.array([1, 0, 1, 0])
        zoom_in_modifier = np.array([1, 1, -1, -1])
        zoom_out_modifier = np.array([-1, -1, 1, 1])

        # get navigation settings
        pan_distance = config.get('map_settings', 'pan_distance')
        zoom_strength = config.get('map_settings', 'zoom_strength')

        self.action_map = {
            MapActions.PAN_UP: partial(self.init_render, pan_up_modifier, pan_distance),
            MapActions.PAN_DOWN: partial(self.init_render, pan_down_modifier, pan_distance),
            MapActions.PAN_LEFT: partial(self.init_render, pan_left_modifier, pan_distance),
            MapActions.PAN_RIGHT: partial(self.init_render, pan_right_modifier, pan_distance),
            MapActions.ZOOM_IN: partial(self.init_render, zoom_in_modifier, zoom_strength),
            MapActions.ZOOM_OUT: partial(self.init_render, zoom_out_modifier, zoom_strength),
        }

    def get_start_extent(self, scenario):

        if len(scenario["locations"]) == 0:
            raise ConfigError("No locations in scenario {}".format(scenario["name"]))

        # find start location
        config_starting_location_name = self.config.get("general", "starting_location")
        config_starting_location = None

        starting_location = None

        for location_key in scenario["locations"]:
            location = scenario["locations"][location_key]

            if location["name"] == config_starting_location_name:
                config_starting_location = location["location"]

            if location["starting_location"]:
                starting_location = location["location"]

        # overwrite starting location if the config-defined starting location exists
        if config_starting_location:
            starting_location = config_starting_location

        # choose first location if no starting location was found
        if not starting_location:
            first_key = next(iter(scenario["locations"]))
            starting_location = scenario["locations"][first_key]["location"]

        # extrude start location to start extent
        zoom = self.config.get("general", "start_zoom") / 2
        start_extent_width = [starting_location[0] - zoom, starting_location[0] + zoom]
        start_extent_height = [starting_location[1]-zoom, starting_location[1] + zoom]

        return start_extent_width, start_extent_height

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

        MapHandler.MAP_REFRESHED = True

    # modifies the current extent and requests an updated render image
    # param brick gets ignored so that UIElements can call the function
    def init_render(self, extent_modifier, strength, brick):

        # modify extent
        width = abs(self.current_extent[2] - self.current_extent[0])
        height = abs(self.current_extent[3] - self.current_extent[1])

        move_extent = np.multiply(
            extent_modifier,
            np.array([width, height, width, height])
        ) * strength[0]

        next_extent = np.add(self.current_extent, move_extent)

        # request render
        self.request_render(next_extent)

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

    def invoke(self, action: MapActions):
        if action in self.action_map:
            self.action_map[action](None)

    def get_frame(self):
        return self.qgis_image[self.current_image]

    def end(self):
        # self.sock.sendto(self.exit_keyword.encode(), self.qgis_addr)
        self.sock.sendto(self.exit_keyword.encode(), self.lego_addr)
        self.sock.close()
