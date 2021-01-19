from typing import Optional

from LabTable.Model.Extent import Extent


# singleton class that keeps track of the different Extents that need to be globally available
class ExtentTracker(object):

    __instance: 'ExtentTracker' = None

    # NOTE do NOT call outside of ExtentTracker, use get_instance instead
    def __init__(self):
        self.board: Optional[Extent] = None
        self.beamer: Optional[Extent] = None
        self.map_extent: Optional[Extent] = None
        self.extent_changed: bool = True

    @classmethod
    def get_instance(cls) -> 'ExtentTracker':
        if not cls.__instance:
            cls.__instance = ExtentTracker()
        return cls.__instance




