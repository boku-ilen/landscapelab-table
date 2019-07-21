import logging
import requests
from requests.exceptions import HTTPError
import json

# Configure logging
from Tracking.LegoBrick import LegoBrick

logger = logging.getLogger(__name__)


class ServerCommunication:
    """Contains all method which need connection with the server.
    Requests map location and compute board coordinates.
    Creates and removes lego instances"""

    prefix = None
    ip = None

    # Get location of the map (from config)
    get_location = None
    location_extension = None

    # Create, edit, remove
    # lego instance in godot (from config)
    create_asset = None
    set_asset = None
    remove_asset = None

    location_coordinates = None
    geo_board_width = None
    geo_board_height = None

    def __init__(self, config):

        self.prefix = config.get("server", "prefix")
        self.ip = config.get("server", "ip")
        self.create_asset = config.get("asset", "create")
        self.set_asset = config.get("asset", "set")
        self.remove_asset = config.get("asset", "remove")
        self.get_location = config.get("location", "get")
        self.location_extension = config.get("location", "extension")

    # Get location of the map and save in config a dictionary
    # with coordinates of board corners (map corners)
    def compute_board_coordinates(self, map_id):

        try:
            # Send request getting location map and save the response (json)
            location_json = requests.get(
                self.prefix + self.ip + self.get_location + map_id + self.location_extension)
            location_json.raise_for_status()

        except HTTPError as http_err:
            logger.error("HTTP error occurred: {}".format(http_err))

        except Exception as err:
            logger.error("Other error occurred: {}".format(err))

        else:
            # Check if status code is 200
            if self.check_status_code_200(location_json.status_code):

                # If status code is 200
                # Parse JSON
                location_json = location_json.json()
                logger.debug("location: {}".format(location_json))

                # Compute a dictionary with coordinates of board corners (map corners)
                self.location_coordinates = self.extract_board_coordinate(location_json)
                logger.debug("location_parsed: {}".format(self.location_coordinates))

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
        logger.debug("Detection recalculated: coordinates:{}".format(coordinates))

        # Send request creating lego instance and save the response
        lego_instance_response = requests.get(self.prefix + self.ip + self.create_asset + str(lego_brick.asset_id)
                                + "/" + str(coordinates[0]) + "/" + str(coordinates[1]))
        logger.debug(self.prefix + self.ip + self.create_asset + str(lego_brick.asset_id)
                     + "/" + str(coordinates[0]) + "/" + str(coordinates[1]))

        # Initialize values given in response
        lego_instance = None

        # Check if status code is 200
        if self.check_status_code_200(lego_instance_response.status_code):

            # If status code is 200, save response text
            lego_instance_response_text = json.loads(lego_instance_response.text)

            # Match given instance id with lego brick id
            lego_instance_creation_success = lego_instance_response_text.get("creation_success")
            lego_instance = lego_instance_response_text.get("assetpos_id")
            logger.debug("creation_success: {}, assetpos_id: {}"
                         .format(lego_instance_creation_success, lego_instance))

        # Return lego instance (id) given from server,
        # None if no instance created
        return lego_instance

    # Remove lego instance
    def remove_lego_instance(self, lego_instance):

        # Send a request to remove lego instance in 3D
        logger.debug(self.prefix + self.ip + self.remove_asset + str(lego_instance))
        lego_remove_instance_response = requests.get(self.prefix + self.ip + self.remove_asset + str(lego_instance))
        logger.debug("remove instance {}, response {}".format(lego_instance, lego_remove_instance_response))

    # Return a dictionary with coordinates of board corners
    # Return example: {'C_TL': [1515720.0, 5957750.0], 'C_TR': [1532280.0, 5957750.0],
    # 'C_BR': [1532280.0, 5934250.0], 'C_BL': [1515720.0, 5934250.0]}
    # Input location_data example:
    # {'identifier': 'Nockberge 1', 'bounding_box': '{ "type": "Polygon",
    # "coordinates": [ [ [ 1515720.0, 5957750.0 ], [ 1532280.0, 5957750.0 ],
    # [ 1532280.0, 5934250.0 ], [ 1515720.0, 5934250.0 ], [ 1515720.0, 5957750.0 ] ] ] }'}
    @staticmethod
    def extract_board_coordinate(location_data):

        # Extract coordinates
        bbox = json.loads(location_data['bounding_box'])
        bbox_coordinates = bbox['coordinates'][0]

        # Save coordinates x, y as (int, int) in a dictionary
        bbox_polygon_dict = {
            'C_TL': bbox_coordinates[0],
            'C_TR': bbox_coordinates[1],
            'C_BR': bbox_coordinates[2],
            'C_BL': bbox_coordinates[3]
        }

        # TODO: check if coordinates matched properly the corners

        # Return a dictionary with coordinates of board corners
        return bbox_polygon_dict

    # Calculate geographical position for lego bricks
    def calculate_coordinates(self, lego_brick_position):

        # TODO: remove when maps on the server are loaded
        self.location_coordinates = {
            'C_TL': [5957750, 1515720],
            'C_TR': [5957750, 1532280],
            'C_BR': [5934250, 1532280],
            'C_BL': [5934250, 1515720]
        }

        # Calculate width and height in geographical coordinates
        if self.geo_board_width is None or self.geo_board_height is None:
            self.geo_board_width = self.location_coordinates['C_TR'][0] - self.location_coordinates['C_TL'][0]
            self.geo_board_height = self.location_coordinates['C_TL'][1] - self.location_coordinates['C_BL'][1]

        logger.debug("geo size: {}, {}".format(self.geo_board_width, self.geo_board_height))
        logger.debug("board size: {}, {}".format(self.board_size_width, self.board_size_height))

        # Calculate lego brick x coordinate
        # Calculate proportions
        lego_brick_coordinate_x = self.geo_board_width * lego_brick_position[0] / self.board_size_width
        # Add offset
        lego_brick_coordinate_x += self.location_coordinates['C_TL'][0]

        # Calculate lego brick y coordinate
        # Calculate proportions
        lego_brick_coordinate_y = self.geo_board_height * lego_brick_position[1] / self.board_size_height
        # Invert the axis
        lego_brick_coordinate_y = self.geo_board_height - lego_brick_coordinate_y
        # Add offset
        lego_brick_coordinate_y += self.location_coordinates['C_BL'][1]

        lego_brick_coordinates = float(lego_brick_coordinate_x), float(lego_brick_coordinate_y)

        return lego_brick_coordinates
