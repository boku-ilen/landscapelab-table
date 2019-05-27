import numpy as np
#from Tracking.MyObject import MyObject

# Max distance change without updating the object: abs(x1 - x) & abs(y1 - y)
MAX_DISTANCE = 6


# FIXME: CODE NOT WORKING - MyObject not found!
# FIXME: replace print() with logging!
class MyTracker:
    """Initialize the next unique object ID with two ordered dictionaries"""

    def __init__(self, maxDisappeared=20):
        self.disappeared = {}
        self.nextObjectID = 0
        # Number of maximum consecutive frames a given object is allowed to be marked as "disappeared"
        self.maxDisappeared = maxDisappeared

    # TODO: register only if object is longer visible (about 10 frames)
    def register(self, inputObject):
        """When registering an object use the next available object ID to store the centroid"""
        MyObject(self.nextObjectID, (inputObject[0]), inputObject[1], inputObject[2])
        self.disappeared[self.nextObjectID] = 0
        self.nextObjectID += 1

    def deregister(self, objectID):
        """When deregistering an object ID delete the object ID from both of dictionaries"""
        MyObject.delete(objectID)
        del self.disappeared[objectID]

    def update(self, objects, length):
        """Update position of the object"""
        print("My Objects")
        print(MyObject.redRcts)
        print(MyObject.redSqrs)
        print(MyObject.blueRcts)
        print(MyObject.blueSqrs)

        # Check if the list of input bounding box rectangles is empty
        if length == 0:
            # If there is no objects in input, remove all objects
            # TODO: mark them as disappeared
            if not MyObject.empty:
                # Loop over any existing tracked objects and mark them as disappeared
                # TODO: solve RuntimeError: dictionary changed size during iteration
                for objectID in self.disappeared.keys():
                    self.disappeared[objectID] += 1
                    # Deregister, if a maximum number of consecutive frames is reached
                    if self.disappeared[objectID] > self.maxDisappeared:
                        self.deregister(objectID)
            # Return early as there are no centroids or tracking info to update
            return MyObject.redRcts, MyObject.redSqrs, MyObject.blueSqrs, MyObject.blueRcts

        # Initialize arrays of input objects and centroids only for the current frame
        # inputCentroids = np.zeros((length, 2), dtype="int")
        inputObjects = []

        # Loop over the objects with properties
        for (i, item) in enumerate(objects):
            # Save new objects and their centroids
            # inputCentroids[i] = (item[0], item[1])
            inputObjects.append((np.array(((item[0], item[1]), item[2], item[3]), dtype=object)))

        # If no objects are currently tracked take all objects and register each of them
        if MyObject.empty:
            for i in range(0, len(inputObjects)):
                self.register(inputObjects[i])

        # Otherwise try to match the input centroids to existing object centroids
        # TODO: match only objects with the same shape and color
        else:
            # print("Matching objects:", MyObject.allObjects, "with input objects:\n", inputObjects)
            # Example:
            # My Objects: [{'ID': 0, 'centroid': (217, 172), 'shape': 'square', 'color': 'red'}, {'ID': 1, 'centroid': (245, 229), 'shape': 'rectangle', 'color': 'blue'}, {'ID': 2, 'centroid': (113, 89), 'shape': 'rectangle', 'color': 'red'}]
            # Input Objects: [array([(243, 224), 'rectangle', 'blue'], dtype=object), array([(216, 166), 'square', 'red'], dtype=object), array([(116, 89), 'rectangle', 'red'], dtype=object)]
            # TODO: check which objects didn't change
            inputRedSqrs = []
            input = 0
            while input < len(inputObjects):
                print("input:", inputObjects[input])
                if (inputObjects[input][1] == "square") & (inputObjects[input][2] == "red"):
                    inputRedSqrs.append((inputObjects[input]))
                input += 1

            # TODO: update for all objects
            # Update for red squares
            redSqrs = MyObject.redSqrs
            # Input list is empty -> delete all objects
            if (inputRedSqrs == []) & (redSqrs != []):
                obj = 0
                while obj < len(redSqrs):
                    self.deregister(redSqrs[obj]["ID"])
                    obj += 1
            # Object list is empty -> register all objects
            elif (inputRedSqrs != []) & (redSqrs == []):
                input = 0
                while input < len(inputRedSqrs):
                    self.register(inputRedSqrs[input])
                    input += 1
            # Otherwise, check and update positions
            elif (inputRedSqrs != []) & (redSqrs != []):
                # Create list of id to update
                idsToUpdate = []
                inputToRegister = []
                obj = 0
                while obj < len(redSqrs):
                    idsToUpdate.append(redSqrs[obj]["ID"])
                    obj += 1
                input = 0
                obj = 0
                # Compare coordinates
                while input < len(inputRedSqrs):
                    while obj < len(redSqrs):
                        print("input:", inputRedSqrs[input][0][0])
                        print("object", redSqrs[obj]["centroid"][0])
                        if (abs(inputRedSqrs[input][0][0] - redSqrs[obj]["centroid"][0]) < 6) & (abs(inputRedSqrs[input][0][1] - redSqrs[obj]["centroid"][1]) < 6):
                            print("move:")
                            print(abs(inputRedSqrs[input][0][0] - redSqrs[obj]["centroid"][0]))
                            MyObject.move(redSqrs[obj]["ID"], inputRedSqrs[input][0])
                        obj += 1
                    input += 1

            # TODO: register new objects / remove old using idsToUpdate[] and inputToRegister[]