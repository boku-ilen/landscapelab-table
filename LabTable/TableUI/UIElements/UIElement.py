from LabTable.Model.Brick import Brick
from LabTable.Model.Vector import Vector
from typing import Optional, List
from enum import Enum


# base class for UI element (other than the map itself) the user can interact with
class UIElement:

    def __init__(self):
        self.position = Vector()    # use set_position to modify
        self.visible: bool = True
        self.parent: Optional[UIElement] = None
        self.children: List[UIElement] = []

    # checks whether a Brick lies on top of this element or any of it's children
    def brick_on_element(self, brick: Brick) -> bool:
        if self.visible:
            for child in self.children:
                if child.brick_on_element(brick):
                    return True
        return False

    # checks whether a yet unconfirmed Brick would lie on top of this element or any of it's children
    def brick_would_land_on_element(self, brick: Brick) -> bool:
        if self.visible:
            for child in self.children:
                if child.brick_would_land_on_element(brick):
                    return True
        return False

    # call once all bricks in a frame have been processed so that e.g. buttons can call their release action
    def ui_tick(self):
        for child in self.children:
            child.ui_tick()

    # displays this element and all it's children to the given image
    def draw(self, img):
        self.draw_hierarchy(img)

    def draw_hierarchy(self, img):
        if self.visible:
            for child in self.children:
                child.draw(img)

    # get global position of this element
    def get_global_pos(self) -> Vector:
        if self.parent is None:
            return self.position

        return self.parent.get_global_pos() + self.position

    # add a child element
    def add_child(self, child):
        self.children.append(child)
        child.parent = self

    def set_visible(self, visible: bool):
        self.visible = visible

    # overwrites current position
    def set_position(self, pos: Vector):
        self.position = pos

    # recursively return all elements of given type
    def get_by_type(self, my_type) -> List:
        ret = []
        for child in self.children:
            ret.append(child.get_by_type(my_type))
            if type(child) == my_type:
                ret.append(child)

        return ret


# used for buttons etc
class UIActionType(Enum):
    PRESS = 0
    RELEASE = 1
    HOLD = 2
