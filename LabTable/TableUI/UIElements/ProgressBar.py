from typing import List, Tuple
import logging
import cv2

from LabTable.Model.Score import Score
from .UIStructureBlock import UIStructureBlock
from LabTable.Configurator import Configurator
from LabTable.Model.Vector import Vector, Point

# Configure logger
logger = logging.getLogger(__name__)

GREEN = (0, 255, 0)
OFFSET = 20


# ProgressBar class
# rectangular progress bar used to visualize progress of "score" game objects
class ProgressBar(UIStructureBlock):

    def __init__(self, config: Configurator, position: Vector, size: Vector, horizontal: bool, flipped: bool,
                 score: Score, bar_color: List[Tuple[int, int, int]] = None, background_color: List = None,
                 border_color: List = None, border_weight: float = None):

        super().__init__(config, position, size, color=background_color, border_color=border_color,
                         border_weight=border_weight)

        self.config = config

        default_bar_color = config.get("ui_settings", "progress_bar_color")
        if bar_color is None:
            self.bar_color = [(color[2], color[1], color[0]) for color in default_bar_color]
        else:
            self.bar_color = bar_color

        self.horizontal: bool = horizontal
        self.flipped: bool = flipped
        self.wrap_around = False

        self.score: Score = score

    # draws this element + all child elements to the given image
    def draw(self, img):

        if self.visible:
            # draw hierarchy
            self.draw_hierarchy(img)

            # get bounds
            x_min, y_min, x_max, y_max = self.get_global_area()
            width, height = self.size

            bar_color, bar_background = self.get_bar_colors()

            self.draw_background(img, bar_background, True)

            # if bar should wrap around modify progress
            progress = self.score.percentage
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
                self.draw_success(img, self.get_global_pos().as_point(), int(width/2))

    # returns the color pf the bar as well as the chosen background
    # (if the bar exceeds 100% and wrap_around is True it wraps around with a new color)
    def get_bar_colors(self) -> Tuple[Tuple, Tuple]:
        if self.wrap_around:
            bar_color_id = max(int(self.score.percentage), 0)
            bar_color = self.bar_color[bar_color_id % len(self.bar_color)]
            bar_background = self.bar_color[(bar_color_id - 1) % len(self.bar_color)]

            return bar_color, bar_background
        else:
            return self.bar_color[0], self.color

    # show a green circle if the progress is achieved
    @staticmethod
    def draw_success(img, pos: Point, half_of_width):
        x_pos, y_pos = pos
        cv2.circle(img, (x_pos + half_of_width, y_pos - OFFSET), half_of_width, GREEN, cv2.FILLED)
