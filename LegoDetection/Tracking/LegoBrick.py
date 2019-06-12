import logging

# Configure logging
logger = logging.getLogger(__name__)


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

    # Lego brick collections constructor
    def __init__(self):

        self.collections_empty = True
        # TODO: change to dictionary? add metadata?
        self.red_sqrs_collection = []
        self.red_rcts_collection = []
        self.blue_sqrs_collection = []
        self.blue_rcts_collection = []

    # Create lego brick with its properties and save in the related collection
    def create_lego_brick(self, id, centroid, shape, color):

        # TODO: check if there is some brick with similar position already

        # Create lego brick object
        lego_brick = LegoBrick(id, centroid, shape, color)

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


#if __name__ == "__main__":
#    collection = LegoBrickCollections()
#    collection.create_lego_brick()

