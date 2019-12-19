from .LegoBricks import LegoBrick

from typing import Tuple, List

Point = Tuple[int, int]


class Vector:

    def __init__(self, x: float = 0, y: float = 0):
        self.x: float = x
        self.y: float = y

    @staticmethod
    def from_point(point: Point):
        x, y = point
        return Vector(x, y)

    @staticmethod
    def from_brick(brick: LegoBrick):
        return Vector(brick.centroid_x, brick.centroid_y)

    @staticmethod
    def from_array(arr: List[float]):
        return Vector(arr[0], arr[1])

    def __add__(self, other: 'Vector'):
        return Vector(self.x + other.x, self.y + other.y)

    def __neg__(self):
        return Vector(-self.x, -self.y)

    def __sub__(self, other: 'Vector'):
        return self + (-other)

    def __mul__(self, other):
        return Vector(self.x * other, self.y*other)

    def __truediv__(self, other):
        return self * (1/other)

    # in this case element wise multiplication
    def __pow__(self, other: 'Vector'):
        return Vector(self.x * other.x, self.y * other.y)

    def __str__(self):
        return "Vector({},{})".format(self.x, self.y)

    def __iter__(self):
        return iter([self.x, self.y])

    def y_per_x(self) -> float:
        return self.y / self.x

    def as_point(self) -> Point:
        return int(self.x), int(self.y)
