from typing import Dict, Optional
from LabTable.Model.Brick import BrickColor, BrickShape, Brick
from abc import ABC

VIRTUAL_STRING = 'virtual'
REAL_STRING = 'real'


# BrickIcon class
# abstract base class for ExternalBrickIcon and InternalBrickIcon
# used as container class for brick icons
class BrickIcon(ABC):

    def __init__(self, icon: Dict):
        self.icon: Dict = icon


# ExternalBrickIcon class
# used as container for external brick icons
# variables id_rule and virtual_rule specify which types of bricks the icon may be used for
# provides matches function to check whether a brick should use this icon
class ExternalBrickIcon(BrickIcon):

    def __init__(self, rule: str, icon: Dict):
        super().__init__(icon)
        self.id_rule: Optional[int] = ExternalBrickIcon.extract_id_rule(rule)
        self.virtual_rule: Optional[bool] = ExternalBrickIcon.extract_virtual_rule(rule)

    # checks if the given brick matches the rules and should use this icon
    def matches(self, brick: Brick, virtual: bool):

        if brick.layer_id == self.id_rule:
            return virtual == self.virtual_rule or self.virtual_rule is None

        return False

    # extracts the id rule from the rule string
    @staticmethod
    def extract_id_rule(rule: str):
        id_string = rule.split(".")[0]

        if id_string == "":
            return None
        return int(id_string)

    # extracts the virtual rule from the rule string
    @staticmethod
    def extract_virtual_rule(rule: str):
        virtual_string = rule.split(".")[1]

        if virtual_string == "":
            return None

        if virtual_string == VIRTUAL_STRING:
            return True

        if virtual_string == REAL_STRING:
            return False


# InternalBrickIcon class
# used as container for internal brick icons
# variables color_rule and shape_rule specify which types of bricks the icon may be used for
# provides matches function to check whether a brick should use this icon
class InternalBrickIcon(BrickIcon):

    def __init__(self, rule: str, icon: Dict):
        super().__init__(icon)
        self.color_rule: Optional[BrickColor] = InternalBrickIcon.extract_color_rule(rule)
        self.shape_rule: Optional[BrickShape] = InternalBrickIcon.extract_shape_rule(rule)

    # checks if the given brick matches the rules and should use this icon
    def matches(self, brick: Brick):

        if brick.color == self.color_rule or self.color_rule is None:
            return brick.shape == self.shape_rule or self.shape_rule is None

        return False

    # extracts the color rule from the rule string
    @staticmethod
    def extract_color_rule(rule: str):
        color_string = rule.split(".")[0]

        if color_string == "":
            return None
        return BrickColor[color_string]

    # extracts the shape rule from the rule string
    @staticmethod
    def extract_shape_rule(rule: str):
        shape_string = rule.split(".")[1]

        if shape_string == "":
            return None
        return BrickShape[shape_string]
