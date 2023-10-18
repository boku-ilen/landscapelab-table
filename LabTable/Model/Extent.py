from typing import Tuple
import numpy as np
import logging

from .Brick import Brick
from LabTable.Model.Vector import Vector

logger = logging.getLogger(__name__)


# Extent class
# used for map extent calculations as well as UI calculations
class Extent:

    # creates a new Extent based on all four edges
    def __init__(self, x_min, y_min, x_max, y_max, y_up_is_positive=False):
        self.x_min: float = x_min
        self.y_min: float = y_min
        self.x_max: float = x_max
        self.y_max: float = y_max

        self.y_inverted: bool = y_up_is_positive

    # creates and returns a new Extent from a given tuple
    @staticmethod
    def from_tuple(borders: Tuple[float, float, float, float], y_up_is_positive=False):
        x_min, y_min, x_max, y_max = borders
        return Extent(x_min, y_min, x_max, y_max, y_up_is_positive)

    # creates and returns a new Extent based on it's left upper corner and it's size
    @staticmethod
    def from_rectangle(x_min, y_min, width, height, y_up_is_positive=False) -> 'Extent':
        return Extent(x_min, y_min, x_min + width, y_min + height, y_up_is_positive)

    # creates and returns a new Extent using Vectors for the upper left, and lower right corner
    @staticmethod
    def from_vectors(upper_left: Vector, lower_right: Vector, y_up_is_positive=False):
        return Extent(upper_left.x, upper_left.y, lower_right.x, lower_right.y, y_up_is_positive)

    # creates a new Extent based on it's center point, width and aspect ratio
    @staticmethod
    def around_center(center: Vector, width: float, y_per_x: float, y_up_is_positive=False) -> 'Extent':
        center_x, center_y = center
        height = width * y_per_x

        return Extent.from_rectangle(center_x - width / 2, center_y - height / 2, width, height, y_up_is_positive)

    """
    non-modifying methods
    these methods will not modify the extent but return a new extent with the desired result
    """

    # returns tuple of with and height
    def get_size(self) -> Vector:
        return Vector(self.get_width(), self.get_height())

    # returns with of the extent
    def get_width(self) -> float:
        return self.x_max - self.x_min

    # returns height of the extent
    def get_height(self):
        return self.y_max - self.y_min

    # returns center position as vector
    def get_center(self) -> Vector:
        return Vector((self.x_min + self.x_max) / 2, (self.y_min + self.y_max) / 2)

    # returns upper left corner position as vector
    def get_upper_left(self) -> Vector:
        return Vector(self.x_min, self.y_min)

    # returns lower right corner position as vector
    def get_lower_right(self) -> Vector:
        return Vector(self.x_max, self.y_max)

    # adjusts height to fit to the given aspect ratio
    def fit_to_ratio(self, y_per_x: float):
        curr_height = self.get_height()
        target_height = self.get_width() * y_per_x
        diff = target_height - curr_height

        self.y_min -= diff / 2
        self.y_max += diff / 2

    # returns the height per width aspect ratio
    def get_aspect_ratio(self):
        return self.get_height() / self.get_width()

    # returns clone of self
    def clone(self) -> 'Extent':
        return Extent(self.x_min, self.y_min, self.x_max, self.y_max, self.y_inverted)

    # returns true if a given point is inside the extent, false otherwise
    def vector_inside(self, vec: Vector) -> bool:

        x, y = vec
        if self.x_min <= x <= self.x_max:
            return self.y_min <= y <= self.y_max
        return False

    # returns true if another extent is completely inside the extent, false otherwise
    def extent_inside(self, extent: 'Extent') -> bool:
        return self.vector_inside(extent.get_upper_left()) and \
               self.vector_inside(extent.get_lower_right())

    # source: https://stackoverflow.com/questions/306316/determine-if-two-rectangles-overlap-each-other
    # returns true if the extent overlaps with the other one
    def overlapping(self, extent: 'Extent'):
        return self.x_min < extent.x_max and \
               self.x_max > extent.x_min and \
               self.y_min < extent.y_max and \
               self.y_max > extent.y_min

    # creates a new extent from the given extent that completely lies within this extent
    def cut_extent_on_borders(self, extent: 'Extent'):
        return Extent(
            max(self.x_min, extent.x_min),
            max(self.y_min, extent.y_min),
            min(self.x_max, extent.x_max),
            min(self.y_max, extent.y_max),
            extent.y_inverted
        )
    
    def get_position_within_extent(self, x_position, y_position):
        return [
            (x_position - self.x_min) / (self.x_max - self.x_min),
            (y_position - self.y_min) / (self.y_max - self.y_min),
        ]

    # returns human readable string interpretation
    def __str__(self):
        return "[Extent x_min: {}, y_min: {}, x_max: {}, y_max: {}, width: {}, height: {}, y_inverted: {}]"\
            .format(
            self.x_min, self.y_min, self.x_max, self.y_max,
            self.get_width(), self.get_height(), self.y_inverted
        )

    def __iter__(self):
        return iter([self.x_min, self.y_min, self.x_max, self.y_max])

    """ 
    modifying methods
    these methods actually modify the current extent
    """

    # modifies the extent by element-wise addition
    def add_extent_modifier(self, modifier: np.ndarray):
        self.x_min += modifier[0]
        self.y_min += modifier[1]
        self.x_max += modifier[2]
        self.y_max += modifier[3]

    # moves the extent by a given vector
    def move_by(self, vec: Vector):
        x, y = vec

        self.x_min += x
        self.x_max += x
        self.y_min += y
        self.y_max += y

    """
    static methods
    """

    #                  +----------------------------+
    #                  |                            |
    # +----+        \  |                            |
    # |    | --------\ |                            |
    # | X  | --------/ |                            |
    # +----+        /  |                            |
    #                  |          X                 |
    #                  |                            |
    #                  +----------------------------+
    # maps a point from one extent to another
    @staticmethod
    def remap_point(vec: Vector, old_extent: 'Extent', new_extent: 'Extent') -> Vector:

        x, y = vec

        if old_extent is None or new_extent is None:
            logger.warning("Could not remap the point")

        else:
            old_width, old_height = old_extent.get_size()
            new_width, new_height = new_extent.get_size()

            x -= old_extent.x_min
            y -= old_extent.y_min

            x /= old_width
            y /= old_height

            x *= new_width
            y *= new_height

            if new_extent.y_inverted != old_extent.y_inverted:
                y = new_height - y

            x += new_extent.x_min
            y += new_extent.y_min

            ret = Vector(x, y)
            return ret

    #                  +----------------------------+
    #                  |                            |
    # +----+        \  |                            |
    # |    | --------\ |                            |
    # | B  | --------/ |                            |
    # +----+        /  |                            |
    #                  |          B                 |
    #                  |                            |
    #                  +----------------------------+
    # maps a brick from one extent to another
    @staticmethod
    def remap_brick(brick: Brick, old_extent: 'Extent', new_extent: 'Extent'):
        remapped_brick = brick.clone()

        if old_extent is None or new_extent is None:
            logger.warning("Could not remap the brick: {} (old: {} or new: {} is None)".format(brick, old_extent,
                                                                                               new_extent))

        else:
            x, y = Extent.remap_point(Vector(remapped_brick.centroid_x, remapped_brick.centroid_y),
                                      old_extent, new_extent)

            remapped_brick.centroid_x = x
            remapped_brick.centroid_y = y

        return remapped_brick

    #                  +----------------------------+
    #                  |                            |
    # +----+        \  |  X-------+                 |
    # |X+  | --------\ |  |       |                 |
    # |+X  | --------/ |  |       |                 |
    # +----+        /  |  |       |                 |
    #                  |  +-------X                 |
    #                  |                            |
    #                  +----------------------------+
    # maps an extent from one extent to another
    @staticmethod
    def remap_extent(target_extent: 'Extent', old_extent: 'Extent', new_extent: 'Extent'):
        left, up = Extent.remap_point(target_extent.get_upper_left(), old_extent, new_extent)
        right, down = Extent.remap_point(target_extent.get_lower_right(), old_extent, new_extent)

        return Extent(left, up, right, down, target_extent.y_inverted)

    # calculates map position of a brick from any given local extent
    @staticmethod
    def calc_world_pos(brick: Brick, local_extent: 'Extent', global_extent: 'Extent'):
        remapped_brick = Extent.remap_brick(brick, local_extent, global_extent)
        brick.map_pos_x = remapped_brick.centroid_x
        brick.map_pos_y = remapped_brick.centroid_y

        return brick

    # calculates local position based on it's map position
    @staticmethod
    def calc_local_pos(brick: Brick, local_extent: 'Extent', global_extent: 'Extent'):
        calc_brick = brick.clone()
        calc_brick.centroid_x = brick.map_pos_x
        calc_brick.centroid_y = brick.map_pos_y
        calc_brick = Extent.remap_brick(calc_brick, global_extent, local_extent)

        brick.centroid_x = int(calc_brick.centroid_x)
        brick.centroid_y = int(calc_brick.centroid_y)

        return brick

