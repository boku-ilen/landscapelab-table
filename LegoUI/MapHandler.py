import numpy as np
import cv2 as cv
import socket
from ConfigManager import ConfigManager
from LegoUI.MapActions import MapActions
from functools import partial
import logging

# Configure Logger
logger = logging.getLogger(__name__)


class MapHandler:

    MAP_REFRESHED = True

    def __init__(self, config: ConfigManager):
        # initialize two black images
        self.qgis_image = [
            np.zeros((500, 500, 3), np.uint8),
            np.zeros((500, 500, 3), np.uint8)
        ]
        self.current_image = 0

        # set extents
        self.current_extent = config.get('map_settings', 'start_extent')
        self.next_extent = self.current_extent

        # set socket & connection info
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.qgis_addr = (config.get('qgis_interaction', 'QGIS_IP'), config.get('qgis_interaction', 'QGIS_READ_PORT'))
        self.lego_addr = (config.get('qgis_interaction', 'QGIS_IP'), config.get('qgis_interaction', 'LEGO_READ_PORT'))

        # get communication info
        self.image_path = config.get('qgis_interaction', 'QGIS_IMAGE_PATH')
        self.render_keyword = config.get('qgis_interaction', 'RENDER_KEYWORD')

        # request first render
        self.request_render(self.current_extent)

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

    # reloads the viewport image
    def refresh(self, extent):
        unused_slot = (self.current_image + 1) % 2

        self.qgis_image[unused_slot] = cv.imread(self.image_path, 1)
        self.current_image = unused_slot
        self.current_extent = extent
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

    def request_render(self, extent):
        self.send(
            '{}{} {} {} {}'.format(self.render_keyword, extent[0], extent[1], extent[2], extent[3])
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
        self.sock.sendto(b'exit', self.qgis_addr)
        self.sock.sendto(b'exit', self.lego_addr)
        self.sock.close()
