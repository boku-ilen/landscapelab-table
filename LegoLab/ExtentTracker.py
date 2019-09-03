from typing import Optional

from .LegoExtent import LegoExtent


# singleton class that keeps track of the different Extents that need to be globally available
class ExtentTracker(object):

    __instance: 'ExtentTracker' = None

    # NOTE do NOT call outside of FrameTracker, use get_instance instead
    def __init__(self):
        self.board: Optional[LegoExtent] = None
        self.beamer: Optional[LegoExtent] = None
        self.map_extent: Optional[LegoExtent] = None
        self.extent_changed: bool = True

    @classmethod
    def get_instance(cls) -> 'ExtentTracker':
        if not cls.__instance:
            cls.__instance = ExtentTracker()
        return cls.__instance




