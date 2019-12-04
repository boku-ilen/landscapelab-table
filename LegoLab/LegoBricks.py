import logging
from typing import Optional

# Configure logging
from enum import Enum

logger = logging.getLogger('MainLogger')


# constants for color
class LegoColor(Enum):
    UNKNOWN_COLOR = 0
    RED_BRICK = 1
    BLUE_BRICK = 2
    GREEN_BRICK = 3
    YELLOW_BRICK = 4


# constants for shape
class LegoShape(Enum):
    UNKNOWN_SHAPE = 0
    SQUARE_BRICK = 1
    RECTANGLE_BRICK = 2


# constants for the detection status
# INTERNAL: used for buttons and controls
# EXTERNAL: this has real geographical coordinates and an assetpos_id
# CANDIDATE: we not yet know if this is a real lego brick
class LegoStatus(Enum):
    INTERNAL_BRICK = 0
    EXTERNAL_BRICK = 1
    CANDIDATE_BRICK = 2
    OUTDATED_BRICK = 3


# this class represents a lego brick and holds related properties
class LegoBrick:

    def __init__(self, centroid_x: int, centroid_y: int, shape: LegoShape, color: LegoColor):

        # the assetpos_id which the brick has on the server. this needs to be
        # available if it is not a candidate and not internal
        self.assetpos_id = None

        # the asset_id which is mapped
        # from color and shape
        self.asset_id = None

        # the x and y coordinates locally (in stream coordinates)
        # of the center of the detected shape
        self.centroid_x: int = centroid_x
        self.centroid_y: int = centroid_y

        self.shape: LegoShape = shape
        self.color: LegoColor = color
        self.status: LegoStatus = LegoStatus.CANDIDATE_BRICK
        # these values will ONLY be set if the brick status is EXTERNAL_BRICK
        self.map_pos_x: Optional[float] = None
        self.map_pos_y: Optional[float] = None

    # used in program stage PLANNING
    def map_asset_id(self, config):

        # map the lego brick asset_id from color & shape
        self.asset_id = config.get(str(self.shape.name), str(self.color.name))

    # used in program stage EVALUATION
    def map_evaluation_asset_id(self, config):

        # map the lego brick asset_id from color & shape
        self.asset_id = config.get("EVALUATION_BRICKS", str(self.color.name))

    def clone(self):
        clone = LegoBrick(self.centroid_x, self.centroid_y, self.shape, self.color)
        clone.status = self.status
        clone.assetpos_id = self.assetpos_id
        clone.asset_id = self.asset_id
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
        return "LegoBrick ({}, {}) [{}|{}|{}] {} {}".format(self.centroid_x, self.centroid_y, self.color,
                                                         self.shape, self.status, self.assetpos_id, self.asset_id)
