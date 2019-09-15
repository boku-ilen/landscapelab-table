from typing import Optional, Callable
import logging
import numpy as np
import cv2

from .UIStructureBlock import UIStructureBlock
from ...ConfigManager import ConfigManager

# Configure logger
logger = logging.getLogger(__name__)


class ProgressBar(UIStructureBlock):

    def __init__(self, config: ConfigManager, position: np.ndarray, size: np.ndarray, horizontal: bool, flipped: bool):
        super().__init__(config, position, size)
        self.config = config

        default_bar_color = config.get("ui-settings", "progress-bar-color")

        self.bar_color = [(color[2], color[1], color[0]) for color in default_bar_color]
        self.horizontal: bool = horizontal
        self.flipped: bool = flipped

        self.target = 1
        self.progress: float = 0
        self.progress_calculation: Optional[Callable[[], float]] = None

    def update_progress(self, new_progress):
        self.progress = new_progress
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

            # scale bar down to fit progress
            if self.horizontal:
                if self.flipped:
                    x_min = x_max - width * (self.progress % 1)
                else:
                    x_max = x_min + width * (self.progress % 1)

            else:
                if self.flipped:
                    y_min = y_max - height * (self.progress % 1)
                else:
                    y_max = y_min + height * (self.progress % 1)

            cv2.rectangle(img, (int(x_min), int(y_min)), (int(x_max), int(y_max)), bar_color, cv2.FILLED)

            self.draw_border(img, self.border_color)

    # returns the color pf the bar as well as the chosen background
    # (if the bar exceeds 100% it wraps around with a new color)
    def get_bar_colors(self):
        bar_color_id = max(int(self.progress), 0)
        bar_color = self.bar_color[bar_color_id % len(self.bar_color)]
        bar_background = self.bar_color[(bar_color_id - 1) % len(self.bar_color)]

        return bar_color, bar_background

    def calculate_progress(self):
        if self.progress_calculation:
            self.update_progress(self.progress_calculation() / self.target)
        else:
            raise TypeError("No progress calculation was defined.")
