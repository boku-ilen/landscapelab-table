# Main source: https://www.pyimagesearch.com/2018/07/23/simple-object-tracking-with-opencv/
# TODO: to improve
# Add parameters: color, shape and use them to differ objects

# Dict subclass that remembers the order entries were added
from collections import OrderedDict
from scipy.spatial import distance as dist
import numpy as np


class Tracker:
    """Initialize the next unique object ID with two ordered dictionaries"""
    def __init__(self, maxDisappeared=50):
        self.nextObjectID = 0
        self.objects = OrderedDict()
        self.disappeared = OrderedDict()

        # Number of maximum consecutive frames a given object is allowed to be marked as "disappeared"
        self.maxDisappeared = maxDisappeared

    # TODO: register only if object is longer visible (about 10 frames)
    def register(self, centroid):
        """When registering an object use the next available object ID to store the centroid"""
        self.objects[self.nextObjectID] = centroid
        self.disappeared[self.nextObjectID] = 0
        self.nextObjectID += 1

    def deregister(self, objectID):
        """When deregistering an object ID delete the object ID from both of dictionaries"""
        del self.objects[objectID]
        del self.disappeared[objectID]

    def update(self, objects, length):
        """Update position of the object"""
        # Check if the list of input bounding box rectangles is empty
        if length == 0:
            # Loop over any existing tracked objects and mark them as disappeared
            for objectID in self.disappeared.keys():
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
            print("Matching object Centroids:", objectCentroids, "with input Centroids:")
            print(inputCentroids)

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
