import numpy as np
import cv2 as cv
import socket
from functools import partial
from typing import Tuple
import logging

from .ImageHandler import ImageHandler
from ..Configurator import Configurator
from LabTable.Model.Extent import Extent
from ..ExtentTracker import ExtentTracker

# Configure Logger
logger = logging.getLogger(__name__)


# MapHandler class
# base class for other map related classes
# handles render requests, image updates and map navigation
class MapHandler:

    def __init__(self, config: Configurator, name: str, extent: Extent, zoom_limits: Tuple[int, int], resolution: Tuple[int, int]):
        self.name = name
        self.config = config
        self.extent_tracker = ExtentTracker.get_instance()
        self.min_zoom, self.max_zoom = zoom_limits

        # set resolution and extent
        self.resolution_x, self.resolution_y = resolution
        extent.fit_to_ratio(self.resolution_y / self.resolution_x)
        self.current_extent: Extent = extent

        # initialize two black images
        self.map_image = [
            ImageHandler.ensure_alpha_channel(np.ones((self.resolution_y, self.resolution_x, 3), np.uint8) * 255),
            ImageHandler.ensure_alpha_channel(np.ones((self.resolution_y, self.resolution_x, 3), np.uint8) * 255)
        ]
        self.current_image = 0

        self.crs = config.get("map_settings", "coordinate_reference_system")

        # set socket & connection info
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        qgis_ip = config.get('qgis_interaction', 'qgis_ip')
        self.qgis_addr = (qgis_ip, config.get('qgis_interaction', 'qgis_read_port'))
        self.lego_addr = (qgis_ip, config.get('qgis_interaction', 'lego_read_port'))

        # get communication info
        self.image_path: str = config.get('qgis_interaction', 'qgis_image_path')
        self.render_keyword = config.get('qgis_interaction', 'render_keyword')
        self.exit_keyword = config.get('qgis_interaction', 'exit_keyword')

        # set extent modifiers
        pan_up_modifier = np.array([0, 1, 0, 1])
        pan_down_modifier = np.array([0, -1, 0, -1])
        pan_left_modifier = np.array([-1, 0, -1, 0])
        pan_right_modifier = np.array([1, 0, 1, 0])
        self.zoom_in_modifier = np.array([1, 1, -1, -1])
        self.zoom_out_modifier = np.array([-1, -1, 1, 1])

        # get navigation settings
        pan_distance = config.get('map_settings', 'pan_distance')
        zoom_strength = config.get('map_settings', 'zoom_strength')

        # these functions can be used to interact with the map
        # by calling these functions one can pan and zoom on the map
        # the functions will automatically request a new rendered map extent from the QGIS plugin
        # they need accept an unused brick parameter to make it possible to call these functions via UICallback
        self.pan_up = partial(self.modify_extent, pan_up_modifier, pan_distance)
        self.pan_down = partial(self.modify_extent, pan_down_modifier, pan_distance)
        self.pan_left = partial(self.modify_extent, pan_left_modifier, pan_distance)
        self.pan_right = partial(self.modify_extent, pan_right_modifier, pan_distance)
        self.zoom_in = partial(self.modify_extent, self.zoom_in_modifier, zoom_strength)
        self.zoom_out = partial(self.modify_extent, self.zoom_out_modifier, zoom_strength)

    # reloads the viewport image
    def refresh(self, extent: Extent):
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
            self.refresh_callback()

        self.config.set("map_settings", 'map_refreshed', True)

    # gets called whenever the map was refreshed and the extent has changed
    # may carry out different tasks in different subclasses
    def refresh_callback(self):
        pass

    # modifies the current extent and requests an updated render image
    # also enforces zoom limits
    # param brick gets ignored so that UIElements can call the function (could however be used to change strength of
    # modification depending on brick type)
    def modify_extent(self, extent_modifier, strength, brick):
        # get relevant current extent data
        width, height = self.current_extent.get_size().as_point()
        dims = np.array([width, height, width, height])

        # calculate value change
        move_extent = (extent_modifier * dims) * strength[0]

        # apply value change
        next_extent = self.current_extent.clone()
        next_extent.add_extent_modifier(move_extent)

        # check if width is below min zoom
        diff = self.min_zoom - next_extent.get_width()
        if diff > 0:
            change = diff / 2
            change_ratio = dims / width

            next_extent.add_extent_modifier(
                self.zoom_out_modifier * (change_ratio * change)
            )

        # check if width is above max zoom
        diff = next_extent.get_width() - self.max_zoom
        if diff > 0:
            change = diff / 2
            change_ratio = dims / width

            next_extent.add_extent_modifier(
                self.zoom_in_modifier * (change_ratio * change)
            )

        # request render
        self.request_render(next_extent)

    # requests a new rendered map extent from qgis plugin
    def request_render(self, extent: Extent = None):

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

    # returns current map image
    def get_map_image(self):
        return self.map_image[self.current_image]

    # closes sockets
    def end(self):
        self.sock.sendto(self.exit_keyword.encode(), self.lego_addr)
        self.sock.close()
