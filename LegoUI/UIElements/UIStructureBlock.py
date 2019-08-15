from LegoBricks import LegoBrick
from LegoUI.UIElements.UIElement import UIElement
from typing import Tuple
import numpy as np
import cv2 as cv


# UI element used for hierarchical structuring of other ui elements
class UIStructureBlock(UIElement):

    def __init__(self, position: Tuple[float, float], size: Tuple[float, float]):
        super().__init__()

        # set block position/size
        self.position = np.array(position)
        self.size = np.array(size)

        # set block color
        self.color = (230, 230, 230)

    # draws the block onto an image
    def draw(self, img):

        if self.visible:
            # get bounds
            x_min, y_min, x_max, y_max = self.get_bounds()

            # draw the button
            cv.rectangle(img, (x_min, y_min), (x_max, y_max), self.color, cv.FILLED)

            # draw hierarchy
            super().draw(img)

    # checks if a given brick lies on top of the block
    def brick_on_element(self, brick: LegoBrick) -> bool:
        if self.visible:
            x, y = (brick.centroid_x, brick.centroid_y)

            return super().brick_on_element(brick) or self.pos_on_block(x, y)
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
