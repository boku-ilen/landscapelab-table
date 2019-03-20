import numpy as np
from Tracking.MyObject2 import MyObject2

class MyTracker:
    """Initialize the next unique object ID with two ordered dictionaries"""
    def __init__(self):
        pass

    # TODO: register only if object is longer visible (about 10 frames)
    def register(self, inputObject):
        """When registering an object use the next available object ID to store the centroid"""
        MyObject2(self.nextObjectID, (inputObject[0]), inputObject[1], inputObject[2])

    def deregister(self, objectID):
        """When deregistering an object ID delete the object ID from both of dictionaries"""
        MyObject2.delete(MyObject2.count, MyObject2.allObjects, objectID)

    def update(self, objects, length):
        """Update position of the object"""
        print("My Objects2:", MyObject2.allObjects)

        # Check if the list of input bounding box rectangles is empty
        if length == 0:
            # Remove all object
            # TODO: mark them as disappeared
            if MyObject2.allObjects != []:
                MyObject2.allObjects == []
            # Return early as there are no centroids or tracking info to update
            return self.objects

        # Initialize arrays of input objects and centroids only for the current frame
        # inputCentroids = np.zeros((length, 2), dtype="int")
        inputObjects = []

        # Loop over the objects with properties
        for (i, item) in enumerate(objects):
            # Save new objects and their centroids
            # inputCentroids[i] = (item[0], item[1])
            inputObjects.append((np.array(((item[0], item[1]), item[2], item[3]), dtype=object)))

        # If no objects are currently tracked take all objects and register each of them
        if len(self.objects) == 0:
            for i in range(0, len(inputObjects)):
                self.register(inputObjects[i])

        # Otherwise try to match the input centroids to existing object centroids
        # TODO: match only objects with the same shape and color
        else:
            print("Matching objects:", MyObject2.allObjects, "with input objects:\n", inputObjects)
            # Example:
            # My Objects: [{'ID': 0, 'centroid': (217, 172), 'shape': 'square', 'color': 'red'}, {'ID': 1, 'centroid': (245, 229), 'shape': 'rectangle', 'color': 'blue'}, {'ID': 2, 'centroid': (113, 89), 'shape': 'rectangle', 'color': 'red'}]
            # Input Objects: [array([(243, 224), 'rectangle', 'blue'], dtype=object), array([(216, 166), 'square', 'red'], dtype=object), array([(116, 89), 'rectangle', 'red'], dtype=object)]
            # TODO: check which objects didn't change
            # print(MyObject2.searchShape(MyObject2.count, MyObject2.allObjects, "square"))
            # TODO: for other objects look for new inputObjects
            # TODO: register new objects / remove old