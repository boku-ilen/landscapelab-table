import logging
import requests
import json

from LegoBricks import LegoBrick
from LegoPositionConverter import LegoPositionConverter

# Configure logging
logger = logging.getLogger(__name__)

# Constants for server communication
HTTP = "http://"
PREFIX = "/landscapelab-dev"
CREATE_ASSET_POS = "/assetpos/create/"
SET_ASSET_POS = "/assetpos/set/"
REMOVE_ASSET_POS = "/assetpos/remove/"

DEFAULT_ROTATION = 0


class ServerCommunication:
    """Creates and removes lego instances"""

    def __init__(self, config):

        self.config = config

        # Initialize ip
        self.ip = self.config.get("server", "ip")

        # Initialize lego position converter
        self.lego_position_converter = LegoPositionConverter(self.config)

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

    # Create lego instance
    def create_lego_instance(self, lego_brick: LegoBrick):

        # Compute geographical coordinates for lego bricks
        self.lego_position_converter.compute_geo_coordinates(lego_brick)

        # Map the lego brick asset_id from color & shape
        lego_brick.map_asset_id(self.config)

        # Send request creating lego instance and save the response
        create_instance_msg = "{http}{ip}{prefix}{command}{brick_id}/{brick_x}/{brick_y}/{default_rotation}".format(
            http=HTTP, ip=self.ip, prefix=PREFIX, command=CREATE_ASSET_POS, brick_id=str(lego_brick.asset_id),
            brick_x=str(lego_brick.map_pos_y), brick_y=str(lego_brick.map_pos_x), default_rotation=DEFAULT_ROTATION
        )

        logger.debug(create_instance_msg)
        lego_instance_response = requests.get(create_instance_msg)

        # Check if status code is 200
        if self.check_status_code_200(lego_instance_response.status_code):

            # If status code is 200, save response text
            lego_instance_response_text = json.loads(lego_instance_response.text)

            # Match given instance id with lego brick id
            lego_instance_creation_success = lego_instance_response_text.get("creation_success")

            # Get assetpos_id in response
            lego_brick.assetpos_id = lego_instance_response_text.get("assetpos_id")
            logger.debug("creation_success: {}, assetpos_id: {}"
                         .format(lego_instance_creation_success, lego_brick.assetpos_id))

    # Remove lego instance
    def remove_lego_instance(self, lego_instance):

        # Send a request to remove lego instance
        logger.debug(HTTP + self.ip + PREFIX + REMOVE_ASSET_POS + str(lego_instance.assetpos_id))
        lego_remove_instance_response = requests.get(HTTP + self.ip
                                                     + PREFIX + REMOVE_ASSET_POS + str(lego_instance.assetpos_id))
        logger.debug("remove instance {}, response {}".format(lego_instance, lego_remove_instance_response))
