from ...LegoExtent import LegoExtent, int_point
from ...LegoBricks import LegoBrick
from ..UIElements.UIElement import UIElement
from ...ConfigManager import ConfigManager
from typing import List
import numpy as np
import cv2 as cv


# UI element used for hierarchical structuring of other ui elements
class UIStructureBlock(UIElement):

    def __init__(
            self,
            config: ConfigManager,
            position: np.ndarray,
            size: np.ndarray,
            color: List = None,
            border_color: List = None,
            border_weight: float = None
    ):
        super().__init__()

        # overwrite none values with defaults
        if color is None:
            color = config.get("ui-settings", "nav-block-background-color")
        if border_color is None:
            border_color = config.get("ui-settings", "nav-block-border-color")
        if border_weight is None:
            border_weight = config.get("ui-settings", "nav-block-border-weight")

        # set block position/size
        # TODO maybe save position & size as LegoExtent?
        self.position = position.astype(int)
        self.size = size.astype(int)
        self.is_ellipse = False

        # set block color
        self.color = (color[0], color[1], color[2])
        self.show_background_color = True

        self.border_thickness: float = border_weight
        self.border_color = (border_color[0], border_color[1], border_color[2])
        self.show_border = True

    # draws the block onto an image
    def draw(self, img):

        if self.visible:

            self.draw_background(img, self.color)
            self.draw_border(img, self.border_color)

            self.draw_hierarchy(img)

    def draw_background(self, img, color, force=False):

        if self.show_background_color or force:
            # get bounds
            x_min, y_min, x_max, y_max = self.get_bounds()

            if self.is_ellipse:

                # calc attributes
                x_avg = int((x_min + x_max) / 2)
                y_avg = int((y_min + y_max) / 2)
                x_span = int((x_max - x_min) / 2)
                y_span = int((y_max - y_min) / 2)

                # draw ellipse
                cv.ellipse(img, (x_avg, y_avg), (x_span, y_span), 0, 0, 360, color, -1)

            else:
                # draw rect
                cv.rectangle(img, (x_min, y_min), (x_max, y_max), color, cv.FILLED)

    def draw_border(self, img, color, force=False):

        if self.show_border or force:

            # get bounds
            x_min, y_min, x_max, y_max = self.get_bounds()

            if self.is_ellipse:
                # calc attributes
                x_avg = int((x_min + x_max) / 2)
                y_avg = int((y_min + y_max) / 2)
                x_span = int((x_max - x_min) / 2)
                y_span = int((y_max - y_min) / 2)

                # draw ellipse
                cv.ellipse(img, (x_avg, y_avg), (x_span, y_span), 0, 0, 360, color, self.border_thickness)

            else:
                # draw rect
                cv.rectangle(img, (x_min, y_min), (x_max, y_max), color, self.border_thickness)

    # checks if a given brick lies on top of the block or any of it's children
    def brick_on_element(self, brick: LegoBrick) -> bool:
        if self.visible:
            x, y = (brick.centroid_x, brick.centroid_y)

            return super().brick_on_element(brick) or self.pos_on_block(x, y)
        return False

    # checks if a given (unconfirmed) brick would land on top of the block or any of it's children
    def brick_would_land_on_element(self, brick: LegoBrick) -> bool:
        if self.visible:
            x, y = (brick.centroid_x, brick.centroid_y)

            return super().brick_would_land_on_element(brick) or self.pos_on_block(x, y)
        return False

    # checks if any screen coordinate lies on top of
    def pos_on_block(self, x: float, y: float) -> bool:
        if self.visible:
            x_min, y_min, x_max, y_max = self.get_bounds()

            if x_min < x < x_max:
                if y_min < y < y_max:
                    return True
        return False

    # get the global bound coordinates
    def get_bounds(self):
        pos = self.position

        if self.parent is not None:
            pos = np.add(self.parent.get_pos(), pos)

        x_min, y_min = pos
        x_max, y_max = np.add(pos, self.size)

        return x_min, y_min, x_max, y_max

    # draws a rectangle using a given area
    def rectangle(self, img, area: LegoExtent, color, border_thickness):

        cv.rectangle(
            img,
            int_point(area.get_upper_left()),
            int_point(area.get_lower_right()),
            color,
            border_thickness
        )
