import logging
import requests
import json
from LegoBricks import LegoBrick
from LegoPositionConverter import LegoPositionConverter

# Configure logging
logger = logging.getLogger(__name__)


class ServerCommunication:
    """Creates and removes lego instances"""

    # Initialize server configurations
    prefix = None
    ip = None

    # Initialize create, edit, remove
    # requests for lego instances
    create_asset = None
    set_asset = None
    remove_asset = None

    def __init__(self, config):

        self.prefix = config.get("server", "prefix")
        self.ip = config.get("server", "ip")
        self.create_asset = config.get("asset", "create")
        self.set_asset = config.get("asset", "set")
        self.remove_asset = config.get("asset", "remove")

        # Initialize lego position converter
        self.lego_position_converter = LegoPositionConverter(config)

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

        coordinates = self.lego_position_converter.compute_coordinates((lego_brick.centroid_x, lego_brick.centroid_y))
        lego_brick.map_pos_x, lego_brick.map_pos_y = coordinates
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
