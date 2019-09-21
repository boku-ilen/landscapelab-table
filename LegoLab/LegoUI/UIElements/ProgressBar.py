from typing import Optional, Callable
import logging
import numpy as np
import cv2

from .UIStructureBlock import UIStructureBlock
from ...ConfigManager import ConfigManager

# Configure logger
logger = logging.getLogger(__name__)

GREEN = (0, 255, 0)
OFFSET = 20


class ProgressBar(UIStructureBlock):

    def __init__(self, config: ConfigManager, position: np.ndarray, size: np.ndarray, horizontal: bool, flipped: bool, bar_color=None):
        super().__init__(config, position, size)
        self.config = config

        default_bar_color = config.get("ui-settings", "progress-bar-color")

        self.bar_color = [(color[2], color[1], color[0]) for color in default_bar_color]

        if bar_color:
            self.bar_color = bar_color

        self.horizontal: bool = horizontal
        self.flipped: bool = flipped
        self.wrap_around = False

        self.target = 1
        self.progress: float = 0
        self.progress_calculation: Optional[Callable[[], float]] = None

        self.bar_position = position

    def update_progress(self, new_progress):
        self.progress = min(new_progress, 1)
        self.config.set("ui-settings", "ui-refreshed", True)
        # TODO find better solution for flag

    # draws this element + all child elements to the scene
    def draw(self, img):

        if self.visible:
            # draw hierarchy
            self.draw_hierarchy(img)

            # get bounds
            x_min, y_min, x_max, y_max = self.get_bounds()
            width = x_max - x_min
            height = y_max - y_min

            bar_color, bar_background = self.get_bar_colors()

            self.draw_background(img, bar_background, True)

            # if bar should wrap around modify progress
            progress = self.progress
            if self.wrap_around:
                progress = progress % 1

            # scale bar down to fit progress
            if self.horizontal:
                if self.flipped:
                    x_min = x_max - width * progress
                else:
                    x_max = x_min + width * progress

            else:
                if self.flipped:
                    y_min = y_max - height * progress
                else:
                    y_max = y_min + height * progress

            cv2.rectangle(img, (int(x_min), int(y_min)), (int(x_max), int(y_max)), bar_color, cv2.FILLED)

            self.draw_border(img, self.border_color)

            # show a green circle if the progress is achieved
            if progress >= 1:
                self.draw_success(img, int(self.bar_position[0]), int(self.bar_position[1]), int(width/2))

    # returns the color pf the bar as well as the chosen background
    # (if the bar exceeds 100% it wraps around with a new color)
    def get_bar_colors(self):
        if self.wrap_around:
            bar_color_id = max(int(self.progress), 0)
            bar_color = self.bar_color[bar_color_id % len(self.bar_color)]
            bar_background = self.bar_color[(bar_color_id - 1) % len(self.bar_color)]

            return bar_color, bar_background
        else:
            return self.bar_color[0], self.color

    def calculate_progress(self):
        if self.progress_calculation:
            self.update_progress(self.progress_calculation() / self.target)
        else:
            raise TypeError("No progress calculation was defined.")

    # show a green circle if the progress is achieved
    @staticmethod
    def draw_success(img, x_pos, y_pos, half_of_width):

        cv2.circle(img, (x_pos + half_of_width, y_pos - OFFSET), half_of_width, GREEN, cv2.FILLED)
