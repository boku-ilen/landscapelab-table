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

    # the asset_id which the brick has on the server. this needs to be
    # available if it is not a candidate and not internal
    asset_id = None

    # the x and y coordinates locally (in stream coordinates)
    # of the center of the detected shape
    centroid_x: int = None
    centroid_y: int = None

    shape: LegoShape = None
    color: LegoColor = None
    status: LegoStatus = LegoStatus.CANDIDATE_BRICK

    def __init__(self, centroid_x: int, centroid_y: int, shape: LegoShape, color: LegoColor):
        self.centroid_x = centroid_x
        self.centroid_y = centroid_y
        self.shape = shape
        self.color = color
