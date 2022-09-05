
from LabTable.TableUI.ImageHandler import ImageHandler
from LabTable.TableUI.UIElements.UIStructureBlock import UIStructureBlock
from ..UIElements.UIStructureBlock import UIStructureBlock
from ..ImageHandler import ImageHandler
from LabTable.Configurator import Configurator
from LabTable.Model.Vector import Vector
from typing import List



class Icon(UIStructureBlock):
    icon_name: str

    def __init__(self, config: Configurator, position: Vector, size: Vector, color: List = None,
                border_color: List = None, border_weight: float = None, icon_name: str = None):

        self.icon_name = icon_name
        super().__init__(config, position, size, color, border_color, border_weight)

        # set visuals
        self.icon = None
        if icon_name is not None:
            img_handler = ImageHandler(config)
            self.icon = img_handler.load_image(icon_name, self.size.as_point())

    def draw(self, img):
        
        if self.visible:

            # draw children of button
            # call this before the rest so the button is rendered in front of its children
            # we want this behavior because then buttons can be used to toggle visibility of menus they are a part of
            self.draw_hierarchy(img)

            # draw the actual button
            if self.icon is not None:  # draw icon if defined
                ImageHandler.img_on_background(img, self.icon, self.get_global_pos().as_point())