from typing import List, Tuple
import numpy as np
import logging

from .LegoBricks import LegoBrick

logger = logging.getLogger(__name__)


class LegoExtent:

    # constructors

    # creates a new LegoExtent based on all four edges
    def __init__(self, x_min, y_min, x_max, y_max, y_up_is_positive=False):
        self.x_min: float = x_min
        self.y_min: float = y_min
        self.x_max: float = x_max
        self.y_max: float = y_max

        self.y_inverted: bool = y_up_is_positive

    # creates and returns a new LegoExtent from a given tuple
    @staticmethod
    def from_tuple(borders: Tuple[float, float, float, float], y_up_is_positive=False):
        x_min, y_min, x_max, y_max = borders
        return LegoExtent(x_min, y_min, x_max, y_max, y_up_is_positive)

    # creates and returns a new LegoExtent based on it's left upper corner and it's size
    @staticmethod
    def from_rectangle(x_min, y_min, width, height) -> 'LegoExtent':
        return LegoExtent(x_min, y_min, x_min + width, y_min + height, False)

    # creates a new LegoExtent based on it's center point, width and aspect ratio
    @staticmethod
    def around_center(center: Tuple[float, float], width: float, y_per_x: float) -> 'LegoExtent':
        center_x, center_y = center
        height = width * y_per_x

        return LegoExtent.from_rectangle(
            center_x - width / 2,
            center_y - height / 2,
            width,
            height
        )

    # methods

    # returns tuple of with and height
    def get_size(self) -> Tuple[float, float]:
        return self.get_width(), self.get_height()

    # returns with of the extent
    def get_width(self) -> float:
        return self.x_max - self.x_min

    # returns height of the extent
    def get_height(self):
        return self.y_max - self.y_min

    # returns center position as tuple
    def get_center(self) -> Tuple[float, float]:
        return (self.x_min + self.x_max) / 2, (self.y_min + self.y_max) / 2

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
    def clone(self) -> 'LegoExtent':
        return LegoExtent(self.x_min, self.y_min, self.x_max, self.y_max, self.y_inverted)

    # modifies the extent by element-wise addition
    def add_extent_modifier(self, modifier: np.ndarray):
        self.x_min += modifier[0]
        self.y_min += modifier[1]
        self.x_max += modifier[2]
        self.y_max += modifier[3]

    # returns human readable string interpretation
    def __str__(self):
        return "[LegoExtent x_min: {}, y_min: {}, x_max: {}, y_max: {}, width: {}, height: {}, y_inverted: {}]"\
            .format(
            self.x_min, self.y_min, self.x_max, self.y_max,
            self.get_width(), self.get_height(), self.y_inverted
        )

    # static methods

    #                  +----------------------------+
    #                  |                            |
    # +----+        \  |                            |
    # |    | --------\ |                            |
    # | X  | --------/ |                            |
    # +----+        /  |                            |
    #                  |          X                 |
    #                  |                            |
    #                  +----------------------------+
    # maps a brick from one extent to another
    @staticmethod
    def remap(brick: LegoBrick, old_extent: 'LegoExtent', new_extent: 'LegoExtent'):
        remapped_brick = brick.clone()

        if old_extent is None or new_extent is None:
            logger.info("Could not remap the lego brick")
        else:
            old_width, old_height = old_extent.get_size()
            new_width, new_height = new_extent.get_size()

            remapped_brick.centroid_x -= old_extent.x_min
            remapped_brick.centroid_y -= old_extent.y_min

            remapped_brick.centroid_x /= old_width
            remapped_brick.centroid_y /= old_height

            remapped_brick.centroid_x *= new_width
            remapped_brick.centroid_y *= new_height

            if new_extent.y_inverted != old_extent.y_inverted:
                remapped_brick.centroid_y = new_height - remapped_brick.centroid_y

            remapped_brick.centroid_x += new_extent.x_min
            remapped_brick.centroid_y += new_extent.y_min

        return remapped_brick

    # calculates map position of a brick from any given local extent
    @staticmethod
    def calc_world_pos(brick: LegoBrick, local_extent: 'LegoExtent', global_extent: 'LegoExtent'):
        remapped_brick = LegoExtent.remap(brick, local_extent, global_extent)
        brick.map_pos_x = remapped_brick.centroid_x
        brick.map_pos_y = remapped_brick.centroid_y

        return brick

    # calculates local position based on it's map position
    @staticmethod
    def calc_local_pos(brick: LegoBrick, local_extent: 'LegoExtent', global_extent: 'LegoExtent'):
        calc_brick = brick.clone()
        calc_brick.centroid_x = brick.map_pos_x
        calc_brick.centroid_y = brick.map_pos_y
        calc_brick = LegoExtent.remap(calc_brick, global_extent, local_extent)

        brick.centroid_x = int(calc_brick.centroid_x)
        brick.centroid_y = int(calc_brick.centroid_y)

        return brick

