class Search(list):
    def searchShape(self, shape):
        """Return all objects that contain the search value in their shape."""

        matching_objects = []
        for obj in self:
            if shape in obj.shape:
                matching_objects.append(obj)
        return matching_objects


class MyObject:
    """Holder for object properties"""
    allObjects = []
    listObjects = Search()

    def __init__(self, centroid, shape, color):
        self.centroid = centroid
        self.shape = shape
        self.color = color
        MyObject.allObjects.append(self)

