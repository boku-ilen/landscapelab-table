from .UIStructureBlock import UIStructureBlock
from ..MapHandler import MapHandler
from ..ImageHandler import ImageHandler
from ...LegoBricks import LegoBrick, LegoStatus
from ...Extent import Extent, Vector
from ...ExtentTracker import ExtentTracker
from ...ConfigManager import ConfigManager

from typing import List
import logging

logger = logging.getLogger(__name__)


class MiniMap(UIStructureBlock, MapHandler):

    def __init__(
            self,
            config: ConfigManager,
            name: str,
            position: Vector,
            size: Vector,
            controlled_map: MapHandler,
            color: List = None,
            extent_color: List = None,
            border_color: List = None,
            border_weight: float = None
    ):

        self.controlled_map = controlled_map
        self.extent_tracker = ExtentTracker.get_instance()

        # call super initializers
        UIStructureBlock.__init__(self, config, position, size,
                                  color=color, border_color=border_color, border_weight=border_weight)
        MapHandler.__init__(self, config, name, self.get_start_extent(config), size.as_point())

        if extent_color is None:
            self.extent_color = config.get("ui-settings", "mini-map-extent-color")
        else:
            self.extent_color = extent_color

        # save extent info of the UI viewport
        self.viewport_extent = self.get_global_area()

        self.pressed = False
        self.pressed_once = False

    # retrieves or calculates the perfect start extent for a given scenario and returns it
    def get_start_extent(self, config):
        # start extent calculation using main map extent as reference
        # center = self.controlled_map.current_extent.get_center()
        # zoom = self.controlled_map.current_extent.get_width() * 2

        # return Extent.around_center(center, zoom, 1)

        extent_arr = config.get("general", "mini_map_extent")

        # get finished extent from config but modify it
        # full_extent = Extent.from_tuple(tuple(extent_arr), True)
        # return Extent.around_center(full_extent.get_center(), full_extent.get_width() * 0.5, full_extent.y_inverted)

        return Extent.around_center(Vector.from_array(extent_arr), extent_arr[2], 1, True)

    # displays this element and all it's children to the given image
    def draw(self, img):

        if self.visible:
            super().draw(img)

            if self.map_image:
                map_dict = {'image': self.map_image[self.current_image]}
                upper_left = self.get_global_area().get_upper_left().as_point()
                ImageHandler.img_on_background(img, map_dict, upper_left)

            if self.current_extent.overlapping(self.controlled_map.current_extent):
                extent_indicator = self.current_extent.cut_extent_on_borders(self.controlled_map.current_extent)
                extent_indicator = Extent.remap_extent(
                    extent_indicator,
                    self.current_extent,
                    self.get_global_area()
                )

                UIStructureBlock.rectangle(img, extent_indicator, self.extent_color, 1)

    # checks if a given brick lies on top of the block or any of it's children
    # also initiates a teleport to the specified position
    def brick_on_element(self, brick: LegoBrick) -> bool:

        if self.visible:
            if self.pos_on_block(Vector.from_brick(brick)):
                if brick.status == LegoStatus.CANDIDATE_BRICK or brick.status == LegoStatus.INTERNAL_BRICK:
                    if not self.pressed:
                        self.initiate_teleport(brick)

                    self.pressed_once = True
                    self.pressed = True
                return True

        return False

    # call once all bricks in a frame have been processed so that e.g. buttons can call their release action
    def ui_tick(self):

        # if mini-map was pressed until now but has not been pressed this frame it now is released
        if self.pressed and not self.pressed_once:
            self.pressed = False

        self.pressed_once = False
        super().ui_tick()

    def initiate_teleport(self, brick: LegoBrick):
        map_brick = Extent.remap_brick(brick, self.get_global_area(), self.current_extent)
        c_map_extent = self.controlled_map.current_extent

        new_extent = Extent.around_center(
            Vector.from_brick(map_brick),
            c_map_extent.get_width(),
            c_map_extent.get_aspect_ratio()
        )
        self.controlled_map.request_render(new_extent)






