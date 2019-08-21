from ..UIElements.UIElement import UIActionType
from ..UIElements.UIStructureBlock import UIStructureBlock
from ...LegoBricks import LegoBrick, LegoStatus
from ...LegoOutputStream import LegoOutputStream
from ...ConfigManager import ConfigManager
from typing import Callable, Dict
import numpy as np

import cv2 as cv
import logging

# Configure Logger
logger = logging.getLogger(__name__)


# a rectangular button that calls specified functions once a brick enters/leaves the button
class Button(UIStructureBlock):

    def __init__(self, config: ConfigManager, position: np.ndarray, size: np.ndarray, name: str = ''):

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

        self.color_pressed = (default_active_color[0], default_active_color[1], default_active_color[2])
        self.icon_pressed = None

        self.name: str = name
        self.show_name: bool = False

        self.border_thickness: float = default_border_weight
        self.border_color = (default_border_color[0], default_border_color[1], default_border_color[2])
        self.show_border = True

        self.is_ellipse = True

        # set button callback functions
        self.callbacks: Dict[UIActionType, Callable[[LegoBrick], None]] = {}
        self.set_callback(UIActionType.PRESS, self.callback_do_nothing)
        self.set_callback(UIActionType.RELEASE, self.callback_do_nothing)
        # self.set_callback(UIActionType.HOLD, self.callback_do_nothing)

        self.pressed = False
        self.pressed_once = False

    # assigns callback functions to different button actions
    def set_callback(self, action_type: UIActionType, callback: Callable[[LegoBrick], None]):
        self.callbacks[action_type] = callback

    # assign this to an action if you don't want it to do anything
    def callback_do_nothing(self, brick):
        pass

    # checks if a given brick lies on top of the button
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
            self.callbacks[action_type](brick)
            logger.info('{} button {}'.format(self.name, action_type.name))

    # draws the button onto an image
    def draw(self, img):

        if self.visible:

            # call super for hierarchical drawing
            super().draw(img)
            # NOTE call this before the rest so the button is rendered in front of its children

            # get correct color / icon
            color = self.color
            icon = self.icon
            if self.pressed:
                color = self.color_pressed
                icon = self.icon_pressed

            # get bounds
            x_min, y_min, x_max, y_max = self.get_bounds()
            x_avg = int((x_min + x_max) / 2)
            y_avg = int((y_min + y_max) / 2)
            x_span = int((x_max - x_min) / 2)
            y_span = int((y_max - y_min) / 2)

            # draw the button
            if self.show_background_color:                                                                  # background
                if self.is_ellipse:
                    cv.ellipse(img, (x_avg, y_avg), (x_span, y_span), 0, 0, 360, color, -1)
                else:
                    cv.rectangle(img, (x_min, y_min), (x_max, y_max), color, cv.FILLED)

            if icon is not None:                                                                            # icon
                LegoOutputStream.img_on_background(img, icon, (x_min, y_min))

            if self.show_border:                                                                            # border
                if self.is_ellipse:
                    cv.ellipse(img, (x_avg, y_avg), (x_span, y_span), 0, 0, 360, self.border_color, self.border_thickness)
                else:
                    cv.rectangle(img, (x_min, y_min), (x_max, y_max), self.border_color, self.border_thickness)
