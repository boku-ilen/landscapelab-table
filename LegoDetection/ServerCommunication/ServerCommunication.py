import logging
import requests
import json
import config

# Configure logging
logger = logging.getLogger(__name__)


# TODO !! Class under construction !!
class ServerCommunication:

    prefix = None
    ip = None

    # Get location of the map
    get_location = None
    location_extension = None

    # Create, edit, remove
    # lego instance in godot
    create_asset = None
    set_asset = None
    remove_asset = None

    def __init__(self):
        self.prefix = config.prefix
        self.ip = config.ip
        self.create_asset = config.create_asset
        self.set_asset = config.set_asset
        self.remove_asset = config.remove_asset
        self.get_location = config.get_location
        self.location_extension = config.location_extension

    # TODO: check connection

    # Get location of the map and save in config a dictionary
    # with coordinates of board corners (map corners)
    # TODO: save coordinates in the class instead of config
    def compute_board_coordinates(self, map_id):

        # Send request getting location map and save the response (json)
        location_json = requests.get(self.prefix + self.ip + self.get_location
                                     + map_id + self.location_extension)

        # Check if status code is 200
        if self.check_status_code_200(location_json.status_code):

            # If status code is 200
            # Parse JSON
            location_json = location_json.json()
            logger.debug("location: {}".format(location_json))

            # Compute a dictionary with coordinates of board corners (map corners)
            config.location_coordinates = self.extract_board_coordinate(location_json)
            logger.debug("location_parsed: {}".format(config.location_coordinates))

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

    # TODO: check code etc., use in Tracker.py
    # Create lego instance and return response
    def create_lego_instance(self, lego_type_id, coordinates):

        # Send request creating lego instance and save the response
        response = requests.get(self.prefix + self.ip + self.create_asset + str(lego_type_id)
                                + "/" + str(coordinates[0]) + "/" + str(coordinates[1]))

        # Return lego instance response
        return response

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

