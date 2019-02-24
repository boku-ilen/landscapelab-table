class MyObject:
    """Holder for object properties"""
    allObjects = []

    def __init__(self, centroid, shape, color):
        self.centroid = centroid
        self.shape = shape
        self.color = color
        MyObject.allObjects.append(self)
