import logging

# Configure logging
logger = logging.getLogger(__name__)


class LegoPositionConverter:
    """Converts lego position on the board
    to geographical coordinates"""

    board_size_width = None
    board_size_height = None

    def __init__(self, config):

        self.config = config

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
    def compute_geo_coordinates(self, lego_brick):

        self.refresh_extent_info()

        if not self.board_size_width or not self.board_size_height:
            # Get width and height of the board
            self.board_size_width = self.config.get("board", "width")
            self.board_size_height = self.config.get("board", "height")
            logger.debug("board size: {}, {}".format(self.board_size_width, self.board_size_height))

        # Calculate lego brick width (latitude)
        # Calculate proportions
        lego_brick.map_pos_x = self.extent_width * lego_brick.centroid_x / self.board_size_width
        # Add offset
        # TODO: control the offset
        lego_brick.map_pos_x += self.extent_width_list[0]

        # Calculate lego brick height coordinate (longitude)
        # Calculate proportions
        lego_brick.map_pos_y = self.extent_height * lego_brick.centroid_y / self.board_size_height
        # Invert the axis
        lego_brick.map_pos_y = self.extent_height - lego_brick.map_pos_y
        # Add offset
        # TODO: control the offset
        lego_brick.map_pos_y += self.extent_height_list[0]

        logger.debug("Board ({} {}) recalculated -> geo coordinates {} {}".format
                     (lego_brick.centroid_x, lego_brick.centroid_y, lego_brick.map_pos_x, lego_brick.map_pos_y))

    # Calculate board position for lego bricks from their geographical position
    def compute_board_coordinates(self, lego_brick):

        self.refresh_extent_info()

        if not self.board_size_width or not self.board_size_height:
            # Get width and height of the board
            self.board_size_width = self.config.get("board", "width")
            self.board_size_height = self.config.get("board", "height")
            logger.debug("board size: {}, {}".format(self.board_size_width, self.board_size_height))

        # map x and y
        lego_brick.centroid_x = (lego_brick.map_pos_x - self.extent_width_list[0]) / self.extent_width
        lego_brick.centroid_y = (lego_brick.map_pos_y - self.extent_height_list[0]) / self.extent_height
        # flip y axis
        lego_brick.centroid_y = self.extent_height - lego_brick.centroid_y


        logger.debug("geo coordinates ({} {}) recalculated -> board {} {}".format
                     (lego_brick.map_pos_x, lego_brick.map_pos_y , lego_brick.centroid_x, lego_brick.centroid_y))
