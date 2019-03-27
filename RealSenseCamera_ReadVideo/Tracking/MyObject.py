class Search(list):

    def searchShape(self, shape):
        """Return all objects that contain the search value in their shape."""

        matching_objects = []
        for obj in self:
            if shape in obj.shape:
                matching_objects.append(obj)
        return matching_objects


class LegoBrickCollection:

    collection = None

    def __init__(self):

        collection = {}

    def create_lego_brick(self):
        self.collection.append()
        return LegoBrick(id, cen)

    def delete_lego_brick(self, id):
        pass

    def serch_lego(self):



# TODO: del self.__dict__
# TODO: work properly with self
class LegoBrick:
    """Holder for object properties"""
    # allObjects = []
    empty = True
    shape = None
    color = None

    def __init__(self, id, centroid, shape, color):
        self.id = id
        self.centroid = centroid
        self.shape = shape
        self.color = color
        MyObject.empty = False
        # MyObject.allObjects.append(self.__dict__)

        if self.color == "red":
            if self.shape == "square":
                MyObject.redSqrs.append(self.__dict__)
            elif self.shape == "rectangle":
                MyObject.redRcts.append(self.__dict__)
        elif self.color == "blue":
            if self.shape == "square":
                MyObject.blueSqrs.append(self.__dict__)
            elif self.shape == "rectangle":
                MyObject.blueRcts.append(self.__dict__)

    def move(id, new_centroid):
        moved = 0
        objects = 0
        print(id, new_centroid)
        list = [MyObject.redRcts, MyObject.redSqrs, MyObject.blueRcts, MyObject.blueSqrs]
        # TODO: look for only until id found
        while objects < len(list):
            i = 0
            while i < len(list[objects]):
                if list[objects][i]["ID"] == id:
                    list[objects][i]["centroid"] == new_centroid
                    moved += 1
                i += 1
            objects += 1

    def delete(id):
        removed = 0
        objects = 0
        list = [MyObject.redRcts, MyObject.redSqrs, MyObject.blueRcts, MyObject.blueSqrs]
        # TODO: look for only until id found
        while objects < len(list):
            print("objects", objects)
            i = 0
            while i < len(list[objects]):
                print("len:", len(list[objects]))
                print("iteration:", i)
                print("id:", id)
                print(list[objects][i]["ID"])
                if list[objects][i]["ID"] == id:
                    del list[objects][i]
                    removed += 1
                i += 1
            objects += 1
        MyObject.ifEmpty()

        #redSqrs = MyObject.redSqrs
        #while i < len(redSqrs):
        #    if redSqrs[i]["ID"] == id:
        #        del redSqrs[i]
        #        i += 1
        #        removed += 1


    def deleteAll():
        MyObject.redRcts = []
        MyObject.redSqrs = []
        MyObject.blueRcts = []
        MyObject.blueSqrs = []

    #def searchShape(allObjects, shape):
    #    matching_objects = []
    #    for obj in allObjects:
    #        if obj["shape"] == shape:
    #            matching_objects.append(obj)
    #    return matching_objects

    #def searchColor(allObjects, color):
    #    matching_objects = []
    #    for obj in allObjects:
    #        if obj["color"] == color:
    #            matching_objects.append(obj)
    #    return matching_objects

    def ifEmpty():
        if len(MyObject.redSqrs) == 0 & len(MyObject.redRcts) == 0 & len(MyObject.blueSqrs) == 0 & len(MyObject.blueRcts) == 0:
            MyObject.empty = True
        MyObject.empty = False


if __name__ == "__main__":
    collection = {}
    lego_brick = LegoBrick()
    collection.append(lego_brick)
