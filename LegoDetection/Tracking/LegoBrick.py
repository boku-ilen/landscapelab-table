import logging
from enum import Enum
import config
import requests
import json


# FIXME: make the server, port and prefix configurable
# Assets request URLs (lego bricks position)
# Create an asset (.../id/pos_x/pos_y), return an instance_id
REQUEST_CREATE_ASSET = "http://141.244.151.53/landscapelab/assetpos/create/"
# Update an asset position (.../instance_id/pos_x/pos_y)
REQUEST_SET_ASSET = "http://141.244.151.53/landscapelab/assetpos/set/"
# Remove an asset (.../instance_id)
REQUEST_REMOVE_ASSET = "http://141.244.151.53/landscapelab/assetpos/remove/"

# configure logging
logger = logging.getLogger(__name__)


# Define lego type ids
class LegoTypeId(Enum):
    SQUARE_RED = 1
    RECTANGLE_RED = 1
    SQUARE_BLUE = 2
    RECTANGLE_BLUE = 2


class LegoBrick:
    """Holder for lego brick properties"""

    id = None
    centroid = None
    shape = None
    color = None

    def __init__(self, id, centroid, shape, color):
        self.id = id
        self.centroid = centroid
        self.shape = shape
        self.color = color


class LegoBrickCollections:
    """Collection and manager of all lego bricks,
    enable to create, move and delete lego bricks"""

    collections_empty = None
    red_rcts_collection = None
    red_sqrs_collection = None
    blue_rcts_collection = None
    blue_sqrs_collection = None

    # Match between lego instance given in create response
    # and lego brick id
    match_collection = None

    # Lego brick collections constructor
    def __init__(self):

        self.collections_empty = True
        # TODO: change to dictionary? add metadata?
        self.red_sqrs_collection = []
        self.red_rcts_collection = []
        self.blue_sqrs_collection = []
        self.blue_rcts_collection = []
        self.match_collection = {}

    # Create lego brick with its properties and save in the related collection
    def create_lego_brick(self, id, centroid, shape, color):

        # TODO: check if there is some brick with similar position already

        # Create lego brick object
        lego_brick = LegoBrick(id, centroid, shape, color)

        # HTTP request with a new object
        # Match a type id based on contour name and color
        lego_type_id = self.match_lego_type_id(shape, color)

        # Calculate coordinates for detected lego bricks
        coordinates = self.calculate_coordinates(centroid)
        logger.debug("Detection recalculated: coordinates:{}".format(coordinates))

        # Send a request to create a lego instance
        logger.debug(REQUEST_CREATE_ASSET + str(lego_type_id) + "/" + str(coordinates[0]) + "/" + str(coordinates[1]))
        lego_instance_response = requests.get(REQUEST_CREATE_ASSET + str(lego_type_id) + "/" + str(coordinates[0]) + "/" + str(coordinates[1]))

        # Initialize values which will be given in response
        lego_instance_creation_success = False
        lego_instance_id = None

        # Set values given in response
        if lego_instance_response.status_code is not 200:
            logger.debug("request create instance status code: {}".format(lego_instance_response.status_code))
        else:
            lego_instance_response_text = json.loads(lego_instance_response.text)
            for key, value in lego_instance_response_text.items():
                if key == "creation_success":
                    lego_instance_creation_success = value
                elif key == "assetpos_id":
                    lego_instance_id = value

        logger.debug("creation_success: {}, assetpos_id: {}".format(lego_instance_creation_success, lego_instance_id))

        # Match given instance id with lego brick id
        if lego_instance_id is not None:

            # Add match to the match collection
            self.match_collection[id] = lego_instance_id

        # Look for the related collection and save as dictionary
        # FIXME: can we use constants for the string identifiers? e.g. COLOR_RED, SHAPE_SQUARE, ..
        if color == "red":
            if shape == "square":
                self.red_sqrs_collection.append(lego_brick.__dict__)
            elif shape == "rectangle":
                self.red_rcts_collection.append(lego_brick.__dict__)
                for lego in self.red_rcts_collection:
                    logger.debug("LegoBrick", lego)
        elif color == "blue":
            if shape == "square":
                self.blue_sqrs_collection.append(lego_brick.__dict__)
            elif shape == "rectangle":
                self.blue_rcts_collection.append(lego_brick.__dict__)

        # Notify that at least one collection is not empty
        self.collections_empty = False

    # Delete lego brick from related collection
    def delete_lego_brick(self, id):

        lego_brick_deleted = False
        collection_idx = 0

        # Compute a list of all lego brick collections
        collections_list = [self.red_rcts_collection, self.red_sqrs_collection,
                            self.blue_rcts_collection, self.blue_sqrs_collection]

        # Look for lego brick id in all collections until found and deleted
        while collection_idx < len(collections_list) and not lego_brick_deleted:

            lego_idx = 0

            # Look for lego brick id in the current collection in the list until found and deleted
            while lego_idx < len(collections_list[collection_idx]) and not lego_brick_deleted:

                # If id is found, delete lego brick from related collection and stop searching
                if collections_list[collection_idx][lego_idx]["id"] == id:

                    # Check if there is instance of the lego brick in 3D
                    for key, value in self.match_collection.items():
                        if key == id:

                            # Match the lego instance id value
                            lego_instance_id = value

                            # Send a request to remove lego instance in 3D
                            logger.debug(REQUEST_REMOVE_ASSET + str(lego_instance_id))
                            lego_remove_instance_response = requests.get(REQUEST_REMOVE_ASSET + str(lego_instance_id))
                            logger.debug("remove instance {}, response {}".format(lego_instance_id, lego_remove_instance_response))

                    # Remove lego brick id from the related to the shape and color collection
                    del collections_list[collection_idx][lego_idx]
                    lego_brick_deleted = True

                    # TODO: remove LegoBrick reference?

                lego_idx += 1
            collection_idx += 1

        # Check if all collections are empty
        self.check_if_collections_empty()

    # Move lego brick to another position
    def move_lego_brick(self, id, new_centroid):

        lego_brick_moved = False
        collection_idx = 0
        logger.debug(id, new_centroid)

        # Compute a list of all lego brick collections
        collection_list = [self.red_rcts_collection, self.red_sqrs_collection,
                           self.blue_rcts_collection, self.blue_sqrs_collection]

        # Look for lego brick id in all collections until found and moved
        while collection_idx < len(collection_list) and not lego_brick_moved:
            lego_idx = 0
            while lego_idx < len(collection_list[collection_idx]) and not lego_brick_moved:

                # If id is found, change centroid and stop searching
                if collection_list[collection_idx][lego_idx]["id"] == id:
                    collection_list[collection_idx][lego_idx]["centroid"] == new_centroid
                    lego_brick_moved = True
                lego_idx += 1
            collection_idx += 1

    # Delete all lego bricks from collections
    def delete_all_lego_bricks(self):
        self.red_rcts_collection = []
        self.red_sqrs_collection = []
        self.blue_rcts_collection = []
        self.blue_sqrs_collection = []

    # Check if all collections are empty
    def check_if_collections_empty(self):
        if not self.red_rcts_collection and not self.red_sqrs_collection\
                and not self.blue_rcts_collection and not self.blue_sqrs_collection:
                    self.collections_empty = True
        else:
            self.collections_empty = False

    # Match a type id of a lego brick
    @staticmethod
    def match_lego_type_id(contour_name, shape):

        lego_type_id = 0

        # Match the type using the defined Enum
        if contour_name is "square" and shape is "red":
            lego_type_id = LegoTypeId.SQUARE_RED.value
        elif contour_name is "square" and shape is "blue":
            lego_type_id = LegoTypeId.SQUARE_BLUE.value
        elif contour_name is "rectangle" and shape is "red":
            lego_type_id = LegoTypeId.RECTANGLE_RED.value
        elif contour_name is "rectangle" and shape is "blue":
            lego_type_id = LegoTypeId.RECTANGLE_BLUE.value

        # Return the lego type id
        return lego_type_id

    # calculate geographical position for lego bricks
    @staticmethod
    def calculate_coordinates(lego_brick_position):

        # Calculate width and height in geographical coordinates
        if config.geo_board_width is None or config.geo_board_height is None:

            config.geo_board_width = config.location_data_parsed['C_TR'][0] - config.location_data_parsed['C_TL'][0]
            config.geo_board_height = config.location_data_parsed['C_TL'][1] - config.location_data_parsed['C_BL'][1]

        logger.debug("geo size: {}, {}".format(config.geo_board_width, config.geo_board_height))
        logger.debug("board size: {}, {}".format(config.board_size_width, config.board_size_height))

        # Calculate lego brick x coordinate
        # Calculate proportions
        lego_brick_coordinate_x = config.geo_board_width * lego_brick_position[0] / config.board_size_width
        # Add offset
        lego_brick_coordinate_x += config.location_data_parsed['C_TL'][0]

        # Calculate lego brick y coordinate
        # Calculate proportions
        lego_brick_coordinate_y = config.geo_board_height * lego_brick_position[1] / config.board_size_height
        # Invert the axis
        lego_brick_coordinate_y = config.geo_board_height - lego_brick_coordinate_y
        # Add offset
        lego_brick_coordinate_y += config.location_data_parsed['C_BL'][1]

        lego_brick_coordinates = float(lego_brick_coordinate_x), float(lego_brick_coordinate_y)

        return lego_brick_coordinates


if __name__ == "__main__":
    collection = LegoBrickCollections()
    collection.create_lego_brick()
