import numpy
import numpy as np
import cv2 as cv
from functools import partial
from typing import Tuple
import logging

from LabTable.TableUI.ImageHandler import ImageHandler
from LabTable.Configurator import Configurator
from LabTable.Model.Extent import Extent
from LabTable.ExtentTracker import ExtentTracker

# Configure Logger
logger = logging.getLogger(__name__)


# MapHandler class
# base class for other map related classes
# handles render requests, image updates and map navigation
class MapHandler:

    def __init__(self, config: Configurator, name: str, extent: Extent,
                 zoom_limits: Tuple[int, int], resolution: Tuple[int, int]):

        self.name = name
        self.config = config
        self.extent_tracker = ExtentTracker.get_instance()
        self.min_zoom, self.max_zoom = zoom_limits

        # set resolution
        self.resolution_x, self.resolution_y = resolution

        # initialize two black images
        self.map_image = [
            ImageHandler.ensure_alpha_channel(np.ones((self.resolution_y, self.resolution_x, 3), np.uint8) * 255),
            ImageHandler.ensure_alpha_channel(np.ones((self.resolution_y, self.resolution_x, 3), np.uint8) * 255)
        ]
        self.current_image = 0

        # crs is initialized with a local configuration but overwritten once a connection with the LL is established
        self.crs = config.get("map_settings", "coordinate_reference_system")
        extent.fit_to_ratio(self.resolution_y / self.resolution_x)
        self.current_extent: Extent = extent

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

    # with these settings the map can be reset and display a different game mode
    def initialize_map(self, crs, extent):
        if crs > 0:  # TODO: truly validate epsg-code?
            self.crs = crs
        extent.fit_to_ratio(self.resolution_y / self.resolution_x)
        self.current_extent = extent
        self.request_render(self.current_extent)

    # reloads the viewport image - this gets called as a callback after a successful render request
    def refresh(self, extent: Extent, buffer):

        logger.debug("refreshing map to extent {}".format(extent))

        unused_slot = (self.current_image + 1) % 2

        png_array = numpy.frombuffer(buffer, dtype=np.uint8)
        image = cv.imdecode(png_array, cv.IMREAD_UNCHANGED)
        image = ImageHandler.ensure_alpha_channel(image)

        # put image on white background to eliminate issues with 4 channel image display
        alpha = image[:, :, 3] / 255.0
        image[:, :, 0] = (1. - alpha) * 255 + alpha * image[:, :, 0]
        image[:, :, 1] = (1. - alpha) * 255 + alpha * image[:, :, 1]
        image[:, :, 2] = (1. - alpha) * 255 + alpha * image[:, :, 2]
        image[:, :, 3] = 255

        # assign image and set slot correctly
        logger.debug("loading new image in slot {}".format(unused_slot))
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

            next_extent.add_extent_modifier(self.zoom_out_modifier * (change_ratio * change))

        # check if width is above max zoom
        diff = next_extent.get_width() - self.max_zoom
        if diff > 0:
            change = diff / 2
            change_ratio = dims / width
            next_extent.add_extent_modifier(self.zoom_in_modifier * (change_ratio * change))

        self.request_render(next_extent)

    # request render of a extent to the qgis plugin
    def request_render(self, extent):

        logger.debug("requesting rendering of extent {}".format(extent))
        if QGISCommunicator.get_instance():
            QGISCommunicator.get_instance().request_render(self, extent)
        else:
            logger.warning("could not request the render of extent {}".format(extent))

    # returns current map image from image buffer
    def get_map_image(self):
        logger.debug("displaying image stored in slot {}".format(self.current_image))
        return self.map_image[self.current_image]
