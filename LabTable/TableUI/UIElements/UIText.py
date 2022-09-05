

from cgitb import text
from turtle import position
from LabTable.TableUI.UIElements.UIStructureBlock import UIStructureBlock
from LabTable.Model.Vector import Vector
from LabTable.Configurator import Configurator
from typing import List
import cv2 as cv


class UIText(UIStructureBlock):
    text: str
    font_face: int
    font_size: float

    def __init__(self, config: Configurator, position: Vector, size: Vector, color: List = None,
                border_color: List = None, border_weight: float = None, text: str = "", 
                font_face = cv.FONT_HERSHEY_PLAIN, font_size: float = 1.0):
        super().__init__(config, position, size, color, border_color, border_weight)

        self.text = text
        self.font_face = font_face
        self.font_size = font_size
    
    def draw(self, img):
        
        if self.visible:
            # draw hierarchy
            self.draw_hierarchy(img)
        
        img = cv.putText(img, self.text, self.position, self.font_face, 
                   self.font_size, self.color[0], self.border_thickness, cv.LINE_AA)

        