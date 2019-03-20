class MyObject2:
    """Holder for object properties"""
    allObjects = []
    count = 0

    def __init__(self, ID, centroid, shape, color):
        self.ID = ID
        self.centroid = centroid
        self.shape = shape
        self.color = color
        MyObject2.allObjects.append(self.__dict__)
        MyObject2.count += 1

    def move(count, allObjects, id, new_centroid):
        for idx in range(count):
            if allObjects[idx]["ID"] == id:
                allObjects[idx]["centroid"] == new_centroid

    def delete(count, allObjects, id):
        for idx in range(count):
            if allObjects[idx]["ID"] == id:
                del allObjects[idx]
                MyObject2.count -= 1

    def searchID(count, allObjects, id):
        for idx in range(count):
            if allObjects[idx]["ID"] == id:
                return True


    def searchShape(count, allObjects, shape):
        matching_objects = []
        for idx in range(count):
            if allObjects[idx]["shape"] == shape:
                matching_objects.append(allObjects[idx])
        return matching_objects

    def searchColor(count, allObjects, color):
        matching_objects = []
        for idx in range(count):
            if allObjects[idx]["color"] == color:
                matching_objects.append(allObjects[idx])
        return matching_objects