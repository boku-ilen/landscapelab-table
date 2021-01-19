from .Brick import Brick

from typing import Tuple, List

Point = Tuple[int, int]


# Vector class
# used for 2D vector calculations by UI and Map classes
class Vector:

    """
    constructors
    """

    # creates new vector from two floats
    def __init__(self, x: float = 0, y: float = 0):
        self.x: float = x
        self.y: float = y

    # creates vector from Point(=Int Tuple)
    @staticmethod
    def from_point(point: Point):
        x, y = point
        return Vector(x, y)

    # creates vector from brick position
    @staticmethod
    def from_brick(brick: Brick):
        return Vector(brick.centroid_x, brick.centroid_y)

    # creates vector from array
    @staticmethod
    def from_array(arr: List[float]):
        return Vector(arr[0], arr[1])

    """
    non-modifying methods
    """

    # add vector
    def __add__(self, other: 'Vector'):
        return Vector(self.x + other.x, self.y + other.y)

    # negate vector
    def __neg__(self):
        return Vector(-self.x, -self.y)

    # subtract vector
    def __sub__(self, other: 'Vector'):
        return self + (-other)

    # multiply with scalar
    def __mul__(self, other):
        return Vector(self.x * other, self.y*other)

    # divide by scalar
    def __truediv__(self, other):
        return self * (1/other)

    # in this case element wise multiplication with other vector
    def __pow__(self, other: 'Vector'):
        return Vector(self.x * other.x, self.y * other.y)

    # string representation
    def __str__(self):
        return "Vector({},{})".format(self.x, self.y)

    # return iterator
    def __iter__(self):
        return iter([self.x, self.y])

    # return y to x ratio
    def y_per_x(self) -> float:
        return self.y / self.x

    # return vector as point (=int tuple)
    def as_point(self) -> Point:
        return int(self.x), int(self.y)
