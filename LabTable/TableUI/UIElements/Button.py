from ..UIElements.UIElement import UIActionType
from ..UIElements.UIStructureBlock import UIStructureBlock
from ..UICallback import UICallback
from LabTable.Model.Brick import Brick, BrickStatus
from ..ImageHandler import ImageHandler
from LabTable.Configurator import Configurator
from LabTable.Model.Vector import Vector
from typing import Dict, List

import logging

# Configure Logger
logger = logging.getLogger(__name__)


# a rectangular or circular button that calls specified functions once a brick enters/leaves the button
class Button(UIStructureBlock):

    def __init__(self, config: Configurator, position: Vector, size: Vector, name: str = '', icon_name: str = None,
                 color: List = None, active_color: List = None, border_color: List = None,
                 border_weight: float = None):

        # overwrite none values with defaults
        if color is None:
            color = config.get("ui_settings", "button_background_color")
        if active_color is None:
            active_color = config.get("ui_settings", "button_active_background_color")
        if border_color is None:
            border_color = config.get("ui_settings", "button_border_color")
        if border_weight is None:
            border_weight = config.get("ui_settings", "button_border_weight")

        # call super init
        super().__init__(config, position, size, color=color, border_color=border_color, border_weight=border_weight)

        # set visuals
        self.icon = None
        if icon_name is not None:
            img_handler = ImageHandler(config)
            self.icon = img_handler.load_image(icon_name, self.size.as_point())

        self.color_pressed = (active_color[0], active_color[1], active_color[2])
        self.icon_pressed = None

        self.name: str = name
        self.show_name: bool = False

        self.show_border = True

        self.is_ellipse = True

        # set button callback functions
        self.callbacks: Dict[UIActionType, UICallback] = {}
        self.set_callback(UIActionType.PRESS, UICallback())
        self.set_callback(UIActionType.RELEASE, UICallback())
        # self.set_callback(UIActionType.HOLD, self.callback_do_nothing)

        self.pressed = False
        self.pressed_once = False

    # assigns callback functions to different button actions
    def set_callback(self, action_type: UIActionType, callback: UICallback):
        self.callbacks[action_type] = callback

    # checks if a given brick lies on top of the button or any of it's children
    # also executes callback functions press and hold
    def brick_on_element(self, brick: Brick) -> bool:
        if self.visible:

            if self.pos_on_block(Vector.from_brick(brick)):

                if brick.status == BrickStatus.CANDIDATE_BRICK or brick.status == BrickStatus.INTERNAL_BRICK:
                    if not self.pressed:
                        self.call(UIActionType.PRESS, brick)
                    else:
                        self.call(UIActionType.HOLD, brick)

                    self.pressed_once = True
                    self.pressed = True
                return True

            return super().brick_on_element(brick)
        return False

    # call once all bricks in a frame have been processed so that e.g. buttons can call their release action
    def ui_tick(self):

        # if button was pressed until now but has not been pressed this frame it now is released
        if self.pressed and not self.pressed_once:
            self.pressed = False
            self.call(UIActionType.RELEASE, None)

        self.pressed_once = False
        super().ui_tick()

    # calls a callback function by action type
    def call(self, action_type: UIActionType, brick):

        if action_type in self.callbacks:
            self.callbacks[action_type].call(brick)
            logger.info('{} button {}'.format(self.name, action_type.name))

    # draws the button onto an image
    def draw(self, img):

        if self.visible:

            # draw children of button
            # call this before the rest so the button is rendered in front of its children
            # we want this behavior because then buttons can be used to toggle visibility of menus they are a part of
            self.draw_hierarchy(img)

            # get correct color / icon
            color = self.color
            icon = self.icon
            if self.pressed:
                color = self.color_pressed
                icon = self.icon_pressed

            # draw the actual button
            self.draw_background(img, color)
            if icon is not None:  # draw icon if defined
                ImageHandler.img_on_background(img, icon, self.get_global_pos().as_point())
            self.draw_border(img, self.border_color)
