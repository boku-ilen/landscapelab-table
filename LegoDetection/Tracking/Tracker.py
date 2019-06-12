# Main source: https://www.pyimagesearch.com/2018/07/23/simple-object-tracking-with-opencv/
# TODO: to improve
# Add parameters: color, shape and use them to differ objects

# Dict subclass that remembers the order entries were added
from collections import OrderedDict
from scipy.spatial import distance as dist
import numpy as np
import logging.config
from Tracking.LegoBrick import LegoBrickCollections
from enum import Enum
from Tracking.LegoBrick import LegoBrick
import config


# configure logging
logger_tracker = logging.getLogger(__name__)
try:
    # TODO: Set configurations
    logging.config.fileConfig('logging.conf')
except:
    logging.basicConfig(level=logging.DEBUG)
    logging.info("Could not initialize: logging.conf not found or misconfigured")


# Define lego type ids
class LegoTypeId(Enum):
    SQUARE_RED = 1
    RECTANGLE_RED = 1
    SQUARE_BLUE = 2
    RECTANGLE_BLUE = 2


class Tracker:
    lego_brick_collection = None
    match_lego_instance_with_id_collection = None
    """Initialize the next unique object ID with two ordered dictionaries"""
    def __init__(self, server, maxDisappeared=20):
        self.nextObjectID = 0
        self.objects = OrderedDict()
        self.disappeared = OrderedDict()
        self.server = server
        self.match_lego_instance_with_id_collection = {}

        # Number of maximum consecutive frames a given object is allowed to be marked as "disappeared"
        self.maxDisappeared = maxDisappeared
        self.lego_brick_collection = LegoBrickCollections()

    # TODO: register only if object is longer visible (about 10 frames)
    def register(self, inputObject):
        """When registering an object use the next available object ID to store the centroid"""
        self.objects[self.nextObjectID] = inputObject
        self.disappeared[self.nextObjectID] = 0
        LegoBrickCollections.create_lego_brick(self.lego_brick_collection, self.nextObjectID, (inputObject[0]), inputObject[1], inputObject[2])
        self.nextObjectID += 1

        # Send a request to create a lego instance
        lego_instance = self.server.create_lego_instance(self.match_lego_type_id(inputObject[1], inputObject[2]), (inputObject[0]))

        # Match lego instance given from server and lego brick id
        self.match_lego_instance_with_id_collection[self.nextObjectID] = lego_instance

    def deregister(self, objectID):
        """When deregistering an object ID delete the object ID from both of dictionaries"""
        LegoBrickCollections.delete_lego_brick(self.lego_brick_collection, objectID)
        del self.objects[objectID]
        del self.disappeared[objectID]

        # Check if there is lego instance matched for current id
        for key, value in self.match_lego_instance_with_id_collection.items():
            if key == objectID:

                # Match the lego instance and remove it
                lego_instance = value
                self.server.remove_lego_instance(lego_instance)

    def update(self, objects, length):
        """Update position of the object"""
        # Show LegoBrickCollections
        logger_tracker.debug("LegoBrickCollections:\n red_sqrs: %s\n red_rcts: %s\n blue_sqrs: %s\n blue_rcts: %s",
                             self.lego_brick_collection.red_sqrs_collection,
                             self.lego_brick_collection.red_rcts_collection,
                             self.lego_brick_collection.blue_sqrs_collection,
                             self.lego_brick_collection.blue_rcts_collection)

        # Check if the list of input bounding box rectangles is empty
        if length == 0:
            # Loop over any existing tracked objects and mark them as disappeared
            for objectID in list(self.disappeared.keys()):
                self.disappeared[objectID] += 1

                # Deregister, if a maximum number of consecutive frames is reached
                if self.disappeared[objectID] > self.maxDisappeared:
                    self.deregister(objectID)

            # Return early as there are no centroids or tracking info to update
            return self.objects

        # Initialize arrays of input objects and centroids only for the current frame
        inputCentroids = np.zeros((length, 2), dtype="int")
        inputObjects = []

        # Loop over the objects with properties
        for (i, item) in enumerate(objects):
            # Save new objects and their centroids
            inputCentroids[i] = (item[0], item[1])
            inputObjects.append((np.array(((item[0], item[1]), item[2], item[3]), dtype=object)))

        # If no objects are currently tracked take all objects and register each of them
        if len(self.objects) == 0:
            for i in range(0, len(inputObjects)):
                self.register(inputObjects[i])

        # Otherwise try to match the input centroids to existing object centroids
        # TODO: match only objects with the same shape and color
        # try to list searched objects
        # print([c.shape for c in MyObject.listObjects.searchShape('rectangle')])
        else:
            # Grab the set of object IDs and corresponding centroids
            objectIDs = list(self.objects.keys())
            objectCentroids = []
            # print("first centroid", self.objects[0][0])
            # print("objects:", self.objects)
            for key, val in self.objects.items():
                objectCentroids.append(self.objects[key][0])
            logger_tracker.debug("Matching object Centroids: {} with input Centroids: \n{}".format(objectCentroids, inputCentroids))

            # Compute the distance between each pair of object centroids and input centroids
            # Goal is to match an input centroid to an existing object centroid
            # The output array shape of the distance map D will be (# of object centroids, # of input centroids)
            D = dist.cdist(np.array(objectCentroids), inputCentroids)

            # Sort the row indexes based on their minimum values
            rows = D.min(axis=1).argsort()

            # Find the smallest value in each column and sort the columns indexes based on the ordered rows
            # Goal is to have the index values with the smallest corresponding distance at the front of the lists
            cols = D.argmin(axis=1)[rows]

            # Example:
            # >>> D = dist.cdist(objectCentroids, centroids)
            # >>> D
            # array([[0.82421549, 0.32755369, 0.33198071],
            #        [0.72642889, 0.72506609, 0.17058938]])
            # >>> D.min(axis=1)
            # array([0.32755369, 0.17058938])
            # >>> rows = D.min(axis=1).argsort()
            # >>> rows
            # array([1, 0])

            # Use the distances to see if object IDs can be associated
            # Keep track of which of the rows and column indexes we have already examined (contains only unique values)
            usedRows = set()
            usedCols = set()

            # Update objects
            # Loop over the combination of the (row, column) index tuples
            for (row, col) in zip(rows, cols):
                # If the row or column value examined before, ignore it value
                if row in usedRows or col in usedCols:
                    continue
                # Otherwise the found input centroid has the smallest Euclidean distance to an existing centroid
                # and has not been matched with any other object, so it will be set as a new centroid
                # Grab the object ID for the current row, set its new centroid, and reset the disappeared counter
                objectID = objectIDs[row]
                self.objects[objectID] = inputObjects[col]
                self.disappeared[objectID] = 0

                # Indicate that we have examined each of the row and column indexes
                usedRows.add(row)
                usedCols.add(col)

            # Compute both the row and column index which have been not yet examined
            unusedRows = set(range(0, D.shape[0])).difference(usedRows)
            unusedCols = set(range(0, D.shape[1])).difference(usedCols)

            # If the number of object centroids is equal or greater than the number of input centroids
            # check if some of these objects have potentially disappeared
            if D.shape[0] >= D.shape[1]:
                # Loop over the unused row indexes
                for row in unusedRows:
                    # Grab the object ID for the corresponding row index and increment the disappeared counter
                    objectID = objectIDs[row]
                    self.disappeared[objectID] += 1

                    # Check if the number of consecutive frames the object has been marked "disappeared"
                    if self.disappeared[objectID] > self.maxDisappeared:
                        self.deregister(objectID)

            # Otherwise, register each new input object as a trackable object
            else:
                for col in unusedCols:
                    self.register(inputObjects[col])
        # Return the set of trackable objects
        return self.objects

# Match a type id of a lego brick
    @staticmethod
    def match_lego_type_id(contour_name, color):

        lego_type_id = 0

        # Match the type using the defined Enum
        if contour_name is "square" and color is "red":
            lego_type_id = LegoTypeId.SQUARE_RED.value
        elif contour_name is "square" and color is "blue":
            lego_type_id = LegoTypeId.SQUARE_BLUE.value
        elif contour_name is "rectangle" and color is "red":
            lego_type_id = LegoTypeId.RECTANGLE_RED.value
        elif contour_name is "rectangle" and color is "blue":
            lego_type_id = LegoTypeId.RECTANGLE_BLUE.value

        # Return the lego type id
        return lego_type_id
