import logging
import requests
import json
from LegoBricks import LegoBrick

# Configure logging
logger = logging.getLogger(__name__)


class ServerCommunication:
    """Contains all method which need connection with the server.
    Requests map location and compute board coordinates.
    Creates and removes lego instances"""

    # Initialize server configurations
    prefix = None
    ip = None

    # Initialize create, edit, remove
    # requests for lego instances
    create_asset = None
    set_asset = None
    remove_asset = None

    # Initialize width and height
    # of the map extent
    extent_width_list = None
    extent_height_list = None

    def __init__(self, config, board_detector=None):

        self.prefix = config.get("server", "prefix")
        self.ip = config.get("server", "ip")
        self.create_asset = config.get("asset", "create")
        self.set_asset = config.get("asset", "set")
        self.remove_asset = config.get("asset", "remove")
        self.board_detector = board_detector
        self.extent_width_list = config.get("map_settings", "extent_width")
        self.extent_height_list = config.get("map_settings", "extent_height")

    # Check status code of the response
    # Return True if 200, else return False
    @staticmethod
    def check_status_code_200(status_code):

        # Check the status code
        # Return False if status code is not 200
        if status_code is not 200:
            logger.debug("request json status code: {}".format(status_code))
            return False

        # Return True if status code is 200
        return True

    # Create lego instance and return lego instance (id)
    def create_lego_instance(self, lego_brick: LegoBrick):

        coordinates = self.calculate_coordinates((lego_brick.centroid_x, lego_brick.centroid_y))
        logger.debug("Detection ({} {}) recalculated -> coordinates {}".format
                     (lego_brick.centroid_x, lego_brick.centroid_y, coordinates))

        # Send request creating lego instance and save the response
        # TODO: instead of color.value use a constant for type (shape & color)
        logger.debug(self.prefix + self.ip + self.create_asset + str(lego_brick.color.value)
                     + "/" + str(coordinates[0]) + "/" + str(coordinates[1]))
        lego_instance_response = requests.get(self.prefix + self.ip + self.create_asset + str(lego_brick.color.value)
                                + "/" + str(coordinates[0]) + "/" + str(coordinates[1]))

        # Check if status code is 200
        if self.check_status_code_200(lego_instance_response.status_code):

            # If status code is 200, save response text
            lego_instance_response_text = json.loads(lego_instance_response.text)

            # Match given instance id with lego brick id
            lego_instance_creation_success = lego_instance_response_text.get("creation_success")

            # Get asset_id in response
            lego_brick.asset_id = lego_instance_response_text.get("assetpos_id")
            logger.debug("creation_success: {}, assetpos_id: {}"
                         .format(lego_instance_creation_success, lego_brick.asset_id))

    # Remove lego instance
    def remove_lego_instance(self, lego_instance):

        # Send a request to remove lego instance
        logger.debug(self.prefix + self.ip + self.remove_asset + str(lego_instance.asset_id))
        lego_remove_instance_response = requests.get(self.prefix + self.ip +
                                                     self.remove_asset + str(lego_instance.asset_id))
        logger.debug("remove instance {}, response {}".format(lego_instance, lego_remove_instance_response))

    # Calculate geographical position for lego bricks
    def calculate_coordinates(self, lego_brick_position):

        extent_width = abs(self.extent_width_list[0] - self.extent_width_list[1])
        extent_height = abs(self.extent_height_list[0] - self.extent_height_list[1])

        logger.debug("extent size: {}, {}".format(extent_width, extent_height))
        board_size_width, board_size_height = self.board_detector.get_board_size()
        logger.debug("board size: {}, {}".format(board_size_width, board_size_height))

        # Calculate lego brick width (latitude)
        # Calculate proportions
        lego_brick_width = extent_width * lego_brick_position[0] / board_size_width
        # Add offset
        # TODO: control the offset
        lego_brick_width += self.extent_width_list[0]

        # Calculate lego brick height coordinate (longitude)
        # Calculate proportions
        lego_brick_height = extent_height * lego_brick_position[1] / board_size_height
        # Invert the axis
        lego_brick_height = extent_height - lego_brick_height
        # Add offset
        # TODO: control the offset
        lego_brick_height += self.extent_height_list[0]

        lego_brick_coordinates = float(lego_brick_width), float(lego_brick_height)

        return lego_brick_coordinates
