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
# OUTDATED: this brick does not exist in reality anymore
class BrickStatus(Enum):
    INTERNAL_BRICK = 0
    EXTERNAL_BRICK = 1
    CANDIDATE_BRICK = 2
    OUTDATED_BRICK = 3

icon_config = {}

# this class represents a type of brick
class Token:

    def __init__(self, shape: BrickShape, color: BrickColor, svg: str = None):
        self.shape: BrickShape = shape
        self.color: BrickColor = color

        brick_format = (shape.name, str(color))
        if svg == None and brick_format in icon_config:
            self.svg = icon_config[brick_format]
        else:
            icon_config[brick_format] = svg
            self.svg: str = svg

    def __str__(self):
        return "{} | {}".format(self.shape, self.color)

    def __eq__(self, other):
        if type(self) is not type(other):
            return NotImplemented
        if self.color == other.color and self.shape == other.shape:
            return True
        else:
            return False

    def __hash__(self):
        return hash((self.shape, self.color))


# this class represents a brick and holds related properties
class Brick:

    def __init__(self, centroid_x: int, centroid_y: int, token: Token):
        # the object_id which the brick has in the LandscapeLab (for external bricks)
        self.object_id = None

        # the x and y coordinates locally (in stream coordinates)
        # of the center of the detected shape
        self.centroid_x: int = centroid_x
        self.centroid_y: int = centroid_y

        self.token = token
        self.status: BrickStatus = BrickStatus.CANDIDATE_BRICK

        # the x and y coordinates in projected coordinates
        # these values will ONLY be set if the brick status is EXTERNAL_BRICK
        self.map_pos_x: Optional[float] = None
        self.map_pos_y: Optional[float] = None

        # some DEBUG information
        self.average_detected_color = 0  # Hue
        self.detected_area = 0.0  # square pixel
        self.aspect_ratio = 0
        self.rotated_bbox_lengths = None

    # returns an independent clone of this brick
    def clone(self):
        clone = Brick(self.centroid_x, self.centroid_y, self.token)
        clone.status = self.status
        clone.object_id = self.object_id
        clone.map_pos_x = self.map_pos_x
        clone.map_pos_y = self.map_pos_y
        return clone

    def __eq__(self, other):
        # (type) safety first
        if type(self) is not type(other):
            return NotImplemented
        # FIXME: what about close by coordinates of the centroid?
        # FIXME: what about the status? do we consider them equal?
        return (self.centroid_x, self.centroid_y, self.token) == \
               (other.centroid_x, other.centroid_y, other.token)

    def __hash__(self):
        return hash((self.centroid_y, self.centroid_x, self.token))

    def __str__(self):
        return "Brick ({}, {}) [{}|{}] {}".format(self.centroid_x, self.centroid_y, self.token, self.status,
                                                  self.object_id)
