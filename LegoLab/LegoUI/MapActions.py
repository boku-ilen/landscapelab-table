from enum import Enum


class MapActions(Enum):
    PAN_UP = 0,
    PAN_DOWN = 1,
    PAN_LEFT = 2,
    PAN_RIGHT = 3,
    ZOOM_IN = 4,
    ZOOM_OUT = 5,
    QUIT = 6