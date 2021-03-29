import logging
from typing import Optional

# Configure logging
from enum import Enum

logger = logging.getLogger(__name__)


# constants for color
class BrickColor(Enum):
    UNKNOWN_COLOR = 0
    RED_BRICK = 1
    BLUE_BRICK = 2
    GREEN_BRICK = 3
    YELLOW_BRICK = 4


# constants for shape
class BrickShape(Enum):
    UNKNOWN_SHAPE = 0
    SQUARE_BRICK = 1
    RECTANGLE_BRICK = 2


# constants for the detection status
# INTERNAL: used for buttons and controls
# EXTERNAL: this has real geographical coordinates and an object_id
# CANDIDATE: we not yet know if this is a real brick
class BrickStatus(Enum):
    INTERNAL_BRICK = 0
    EXTERNAL_BRICK = 1
    CANDIDATE_BRICK = 2
    OUTDATED_BRICK = 3


# this class represents a brick and holds related properties
class Brick:

    def __init__(self, centroid_x: int, centroid_y: int, shape: BrickShape, color: BrickColor):

        # the object_id which the brick has in the LandscapeLab. this needs to be
        # available if it is not a candidate and not internal
        self.object_id = None

        # the identifier of the layer which is mapped from color and shape
        self.layer_id = None

        # the x and y coordinates locally (in stream coordinates)
        # of the center of the detected shape
        self.centroid_x: int = centroid_x
        self.centroid_y: int = centroid_y

        self.shape: BrickShape = shape
        self.color: BrickColor = color
        self.status: BrickStatus = BrickStatus.CANDIDATE_BRICK

        # these values will ONLY be set if the brick status is EXTERNAL_BRICK
        self.map_pos_x: Optional[float] = None
        self.map_pos_y: Optional[float] = None

    # returns an independent clone of this brick
    def clone(self):
        clone = Brick(self.centroid_x, self.centroid_y, self.shape, self.color)
        clone.status = self.status
        clone.object_id = self.object_id
        clone.layer_id = self.layer_id
        clone.map_pos_x = self.map_pos_x
        clone.map_pos_y = self.map_pos_y
        return clone

    def __eq__(self, other):
        # (type) safety first
        if type(self) is not type(other):
            return NotImplemented
        # FIXME: what about close by coordinates of the centroid?
        # FIXME: what about the status? do we consider them equal?
        return (self.centroid_x, self.centroid_y, self.color, self.shape) == \
               (other.centroid_x, other.centroid_y, other.color, other.shape)

    def __hash__(self):
        return hash((self.centroid_y, self.centroid_x, self.color, self.shape))

    def __str__(self):
        return "Brick ({}, {}) [{}|{}|{}] {} {}".format(self.centroid_x, self.centroid_y, self.color,
                                                        self.shape, self.status, self.object_id, self.layer_id)
