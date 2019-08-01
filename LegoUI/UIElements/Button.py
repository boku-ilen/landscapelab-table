from LegoUI.UIElements.UIElement import UIActionType, UIElement
from LegoUI.UIElements.UIStructureBlock import UIStructureBlock
from LegoBricks import LegoBrick, LegoStatus
from typing import Callable, Tuple, Dict
import cv2 as cv
import logging

# Configure Logger
logger = logging.getLogger(__name__)


# a rectangular button that calls specified functions once a brick enters/leaves the button
class Button(UIStructureBlock):

    def __init__(self, position: Tuple[float, float], size: Tuple[float, float], name: str = ''):

        super().__init__(position, size)

        # TODO: adjust colors
        # set visuals
        self.color = (50, 50, 50)
        self.icon = None

        self.color_pressed = (100, 100, 100)
        self.icon_pressed = None

        self.name: str = name
        self.show_name: bool = False
        self.border_thickness: float = 3
        self.border_color = (0, 0, 0)

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
                if brick.status == LegoStatus.CANDIDATE_BRICK and not self.pressed:
                    self.call(UIActionType.PRESS, brick)
                    UIElement.UI_REFRESHED = True
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
            UIElement.UI_REFRESHED = True
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

            # draw the button
            cv.rectangle(img, (x_min, y_min), (x_max, y_max), color, cv.FILLED)                             # background
            # TODO draw icon to position                                                                    # icon
            cv.rectangle(img, (x_min, y_min), (x_max, y_max), self.border_color, self.border_thickness)     # border
