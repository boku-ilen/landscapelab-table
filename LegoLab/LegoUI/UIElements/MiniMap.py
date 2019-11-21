from .UIStructureBlock import UIStructureBlock
from ..MapHandler import MapHandler
from ..ImageHandler import ImageHandler
from ...LegoBricks import LegoBrick, LegoStatus
from ...LegoExtent import LegoExtent
from ...ExtentTracker import ExtentTracker
from ...ConfigManager import ConfigManager

from typing import List
import numpy as np
import logging

logger = logging.getLogger(__name__)


class MiniMap(UIStructureBlock, MapHandler):

    def __init__(
            self,
            config: ConfigManager,
            name,
            position: np.ndarray,
            size: np.ndarray,
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
        MapHandler.__init__(self, config, name, self.get_start_extent(config), (int(size[0]), int(size[1])))

        if extent_color is None:
            self.extent_color = config.get("ui-settings", "mini-map-extent-color")
        else:
            self.extent_color = extent_color

        # save extent info of the UI viewport
        self.viewport_extent = LegoExtent.from_tuple(self.get_bounds())

        self.pressed = False
        self.pressed_once = False

    # retrieves or calculates the perfect start extent for a given scenario and returns it
    def get_start_extent(self, config):
        # start extent calculation using main map extent as reference
        # center = self.controlled_map.current_extent.get_center()
        # zoom = self.controlled_map.current_extent.get_width() * 2

        # return LegoExtent.around_center(center, zoom, 1)

        extent_arr = config.get("general", "mini_map_extent")

        # get finished extent from config but modify it
        # full_extent = LegoExtent.from_tuple(tuple(extent_arr), True)
        # return LegoExtent.around_center(full_extent.get_center(), full_extent.get_width() * 0.5, full_extent.y_inverted)

        return LegoExtent.around_center((extent_arr[0], extent_arr[1]), extent_arr[2], True)

    # displays this element and all it's children to the given image
    def draw(self, img):

        if self.visible:
            super().draw(img)

            if self.map_image:
                map_dict = {'image': self.map_image[self.current_image]}
                x_min, y_min, x_max, y_max = self.get_bounds()
                ImageHandler.img_on_background(img, map_dict, (x_min, y_min))

            if self.current_extent.overlapping(self.controlled_map.current_extent):
                extent_indicator = self.current_extent.cut_extent_on_borders(self.controlled_map.current_extent)
                extent_indicator = LegoExtent.remap_extent(
                    extent_indicator,
                    self.current_extent,
                    self.viewport_extent

                )

                self.rectangle(img, extent_indicator, self.extent_color, 1)
            # TODO draw current extent or at least point at center

    # checks if a given brick lies on top of the block or any of it's children
    # also initiates a teleport to the specified position
    def brick_on_element(self, brick: LegoBrick) -> bool:

        if self.visible:
            x, y = (brick.centroid_x, brick.centroid_y)

            if self.pos_on_block(x, y):
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
        map_brick = LegoExtent.remap_brick(brick, self.viewport_extent, self.current_extent)
        map_pos = (map_brick.centroid_x, map_brick.centroid_y)
        c_map_extent = self.controlled_map.current_extent

        new_extent = LegoExtent.around_center(map_pos, c_map_extent.get_width(), c_map_extent.get_aspect_ratio())
        self.controlled_map.request_render(new_extent)






