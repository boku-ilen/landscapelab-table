from LabTable.Model.Extent import Extent
from LabTable.Model.Vector import Vector
from LabTable.Model.Brick import Brick
from ..UIElements.UIElement import UIElement
from LabTable.Configurator import Configurator
from typing import List
import cv2 as cv


# UI element used for hierarchical structuring of other ui elements
class UIStructureBlock(UIElement):

    def __init__(self, config: Configurator, position: Vector, size: Vector, color: List = None,
                 border_color: List = None, border_weight: float = None):

        super().__init__()

        # overwrite none values with defaults
        if color is None:
            color = config.get("ui_settings", "nav_block_background_color")
        if border_color is None:
            border_color = config.get("ui_settings", "nav_block_border_color")
        if border_weight is None:
            border_weight = config.get("ui_settings", "nav_block_border_weight")

        # set block position/size
        self.position = position                                            # only modify with set_position
        self.size = size                                                    # only modify with set_size
        self.area = Extent.from_vectors(position, position + size, False)   # only modify with set_area
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

    # draws the background of the structure block onto an image
    def draw_background(self, img, color, force=False):

        if self.show_background_color or force:

            if self.is_ellipse:
                # draw ellipse
                UIStructureBlock.ellipse(img, self.get_global_area(), color, cv.FILLED)

            else:
                # draw rect
                UIStructureBlock.rectangle(img, self.get_global_area(), color, cv.FILLED)

    # draws the border of the structure block onto an image
    def draw_border(self, img, color, force=False):

        if self.show_border or force:

            if self.is_ellipse:
                # draw ellipse
                UIStructureBlock.ellipse(img, self.get_global_area(), color, self.border_thickness)

            else:
                # draw rect
                UIStructureBlock.rectangle(img, self.get_global_area(), color, self.border_thickness)

    # checks if a given brick lies on top of the block or any of it's children
    def brick_on_element(self, brick: Brick) -> bool:
        if self.visible:
            return super().brick_on_element(brick) or self.pos_on_block(Vector.from_brick(brick))
        return False

    # checks if a given (unconfirmed) brick would land on top of the block or any of it's children
    def brick_would_land_on_element(self, brick: Brick) -> bool:
        if self.visible:
            return super().brick_would_land_on_element(brick) or self.pos_on_block(Vector.from_brick(brick))
        return False

    # checks if any screen coordinate lies on top of
    def pos_on_block(self, pos: Vector) -> bool:
        if self.visible:
            return self.get_global_area().vector_inside(pos)
        return False

    # get the global area as extent
    def get_global_area(self) -> Extent:
        pos = self.get_global_pos()
        return Extent.from_vectors(pos, pos + self.size)

    # overwrites current position
    # also updates area
    def set_position(self, pos: Vector):
        self.area.move_by(pos - self.position)
        super().set_position(pos)

    # overwrites current size and updates area
    def set_size(self, size: Vector):
        self.area = Extent(self.area.get_upper_left(), self.position + size)
        self.size = size

    # overwrites current area and updates size and position
    def set_area(self, area: Extent):
        self.position = area.get_upper_left
        self.size = area.get_size()
        self.area = area

    # draws a rectangle using a given area
    @staticmethod
    def rectangle(img, area: Extent, color, border_thickness):
        cv.rectangle(
            img,
            area.get_upper_left().as_point(),
            area.get_lower_right().as_point(),
            color,
            border_thickness
        )

    # draws a rectangle using a given area
    @staticmethod
    def ellipse(img, area: Extent, color, border_thickness):
        cv.ellipse(
            img,
            area.get_center().as_point(),
            (area.get_size() / 2).as_point(),
            0, 0, 360,
            color,
            border_thickness
        )
