import logging

# Configure logging
from enum import Enum

logger = logging.getLogger(__name__)


# constants for color
class LegoColor(Enum):
    RED_BRICK = 0
    BLUE_BRICK = 1
    GREEN_BRICK = 2
    UNKNOWN_COLOR = 3
    YELLOW_BRICK = 4


# constants for shape
class LegoShape(Enum):
    SQUARE_BRICK = 0
    RECTANGLE_BRICK = 1
    UNKNOWN_SHAPE = 2


# constants for the detection status
# INTERNAL: used for buttons and controls
# EXTERNAL: this has real geographical coordinates and an asset_id
# CANDIDATE: we not yet know if this is a real lego brick
class LegoStatus(Enum):
    INTERNAL_BRICK = 0
    EXTERNAL_BRICK = 1
    CANDIDATE_BRICK = 2


# this class represents a lego brick and holds related properties
class LegoBrick:

    def __init__(self, centroid_x: int, centroid_y: int, shape: LegoShape, color: LegoColor):

        # the asset_id which the brick has on the server. this needs to be
        # available if it is not a candidate and not internal
        self.asset_id = None

        # the x and y coordinates locally (in stream coordinates)
        # of the center of the detected shape
        self.centroid_x: int = centroid_x
        self.centroid_y: int = centroid_y

        self.shape: LegoShape = shape
        self.color: LegoColor = color
        self.status: LegoStatus = LegoStatus.CANDIDATE_BRICK

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
        return "LegoBrick ({}, {}) [{}|{}|{}] {}".format(self.centroid_x, self.centroid_y,
                                                         self.color, self.shape, self.status, self.asset_id)
