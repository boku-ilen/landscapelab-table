from ..UIElements.UIElement import UIActionType
from ..UIElements.UIStructureBlock import UIStructureBlock
from LegoUI.UICallback import UICallback
from ...LegoBricks import LegoBrick, LegoStatus
from ..ImageHandler import ImageHandler
from ...ConfigManager import ConfigManager
from typing import Dict
import numpy as np

import logging

# Configure Logger
logger = logging.getLogger('MainLogger')


# a rectangular button that calls specified functions once a brick enters/leaves the button
class Button(UIStructureBlock):

    def __init__(self, config: ConfigManager, position: np.ndarray, size: np.ndarray, name: str = '', icon_name: str = None):

        super().__init__(config, position, size)

        # get defaults
        default_color = config.get("ui-settings", "button-background-color")
        default_active_color = config.get("ui-settings", "button-active-background-color")
        default_border_color = config.get("ui-settings", "button-border-color")
        default_border_weight = config.get("ui-settings", "button-border-weight")
        # TODO allow overwriting defaults with params

        # set visuals
        self.color = (default_color[0], default_color[1], default_color[2])
        self.icon = None
        if icon_name is not None:
            img_handler = ImageHandler(config)
            self.icon = img_handler.load_image(icon_name, (int(size[0]), int(size[1])))

        self.color_pressed = (default_active_color[0], default_active_color[1], default_active_color[2])
        self.icon_pressed = None

        self.name: str = name
        self.show_name: bool = False

        self.border_thickness: float = default_border_weight
        self.border_color = (default_border_color[0], default_border_color[1], default_border_color[2])
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
    def brick_on_element(self, brick: LegoBrick) -> bool:
        if self.visible:
            x, y = (brick.centroid_x, brick.centroid_y)

            if self.pos_on_block(x, y):

                if brick.status == LegoStatus.CANDIDATE_BRICK or brick.status == LegoStatus.INTERNAL_BRICK:
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

            self.draw_hierarchy(img)
            # NOTE call this before the rest so the button is rendered in front of its children

            # get correct color / icon
            color = self.color
            icon = self.icon
            if self.pressed:
                color = self.color_pressed
                icon = self.icon_pressed

            # draw the button
            self.draw_background(img, color)                                # background

            if icon is not None:                                            # icon
                # get bounds
                x_min, y_min, x_max, y_max = self.get_bounds()

                # draw the icon
                ImageHandler.img_on_background(img, icon, (x_min, y_min))

            self.draw_border(img, self.border_color)                        # border
