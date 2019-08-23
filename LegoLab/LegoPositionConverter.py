import logging

from .LegoBricks import LegoBrick

# Configure logging
logger = logging.getLogger(__name__)


class LegoPositionConverter:
    """Converts lego position on the board
    to geographical coordinates"""

    def __init__(self, config, board):

        self.config = config
        self.board = board

        self.extent_width_list = None
        self.extent_height_list = None
        self.extent_width = None
        self.extent_height = None
        self.refresh_extent_info()

    def refresh_extent_info(self):
        # Initialize width and height of the map extent
        self.extent_width_list = self.config.get("map_settings", "extent_width")
        self.extent_height_list = self.config.get("map_settings", "extent_height")

        # Compute the extent dimensions
        self.extent_width = abs(self.extent_width_list[0] - self.extent_width_list[1])
        self.extent_height = abs(self.extent_height_list[0] - self.extent_height_list[1])
        logger.debug("extent size: {}, {}".format(self.extent_width, self.extent_height))

    # Calculate geographical position for lego bricks from their board position
    def compute_geo_coordinates(self, lego_brick: LegoBrick):

        if self.board.width and self.board.height:

            self.refresh_extent_info()

            # Calculate lego brick width (latitude)
            # Calculate proportions
            lego_brick.map_pos_x = self.extent_width * lego_brick.centroid_x / self.board.width
            # Add offset
            # TODO: control the offset
            lego_brick.map_pos_x += self.extent_width_list[0]

            # Calculate lego brick height coordinate (longitude)
            # Calculate proportions
            lego_brick.map_pos_y = self.extent_height * lego_brick.centroid_y / self.board.height
            # Invert the axis
            lego_brick.map_pos_y = self.extent_height - lego_brick.map_pos_y
            # Add offset
            # TODO: control the offset
            lego_brick.map_pos_y += self.extent_height_list[0]

            logger.debug("Board ({} {}) recalculated -> geo coordinates {} {}".format
                         (lego_brick.centroid_x, lego_brick.centroid_y, lego_brick.map_pos_x, lego_brick.map_pos_y))

    # Calculate board position for lego bricks from their geographical position
    def compute_board_coordinates(self, lego_brick: LegoBrick):

        if self.board.width and self.board.height:

            self.refresh_extent_info()

            px = lego_brick.centroid_x
            py = lego_brick.centroid_y

            # reverse engineered code from compute_geo_coordinates
            lego_brick.centroid_x = (lego_brick.map_pos_x - self.extent_width_list[0]) \
                                    * self.board.width / self.extent_width

            lego_brick.centroid_y = (self.extent_height - (lego_brick.map_pos_y - self.extent_height_list[0])) \
                                    * self.board.height / self.extent_height
            # FIXME this somehow works when zooming but not for panning
            #  it seems that somewhere in the code the x and y axes get switched around... I could not find that part

            logger.debug("geo coordinates ({:.3f} {:.3f}) recalculated -> board {:.1f} {:.1f}".format(
                lego_brick.map_pos_x, lego_brick.map_pos_y, lego_brick.centroid_x, lego_brick.centroid_y)
            )

            logger.debug("movement vector: ({:.1f}, {:.1f})".format(lego_brick.centroid_x - px, lego_brick.centroid_y - py))
