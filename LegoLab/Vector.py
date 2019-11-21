
from typing import Tuple

Point = Tuple[int, int]


class Vector:

    def __init__(self, x: float, y: float):
        self.x: float = x
        self.y: float = y

    @staticmethod
    def from_point(point: Point):
        x, y = point
        return Vector(x, y)

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

    def __str__(self):
        return "Vector({},{})".format(self.x, self.y)

    def __iter__(self):
        return iter([self.x, self.y])

    def as_point(self) -> Point:
        return int(self.x), int(self.y)
