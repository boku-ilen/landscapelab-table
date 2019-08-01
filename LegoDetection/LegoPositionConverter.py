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

        # Initialize width and height of the map extent
        self.extent_width_list = self.config.get("map_settings", "extent_width")
        self.extent_height_list = self.config.get("map_settings", "extent_height")

        # Compute the extent dimensions
        self.extent_width = abs(self.extent_width_list[0] - self.extent_width_list[1])
        self.extent_height = abs(self.extent_height_list[0] - self.extent_height_list[1])
        logger.debug("extent size: {}, {}".format(self.extent_width, self.extent_height))

    # Calculate geographical position for lego bricks
    def compute_coordinates(self, lego_brick_position):
        # TODO take LegoBrick itself as argument instead of coordinates
        # TODO save brick pos in brick pos

        if not self.board_size_width or not self.board_size_height:
            # Get width and height of the board
            self.board_size_width = self.config.get("board", "width")
            self.board_size_height = self.config.get("board", "height")
            logger.debug("board size: {}, {}".format(self.board_size_width, self.board_size_height))

        # Calculate lego brick width (latitude)
        # Calculate proportions
        lego_brick_width = self.extent_width * lego_brick_position[0] / self.board_size_width
        # Add offset
        # TODO: control the offset
        lego_brick_width += self.extent_width_list[0]

        # Calculate lego brick height coordinate (longitude)
        # Calculate proportions
        lego_brick_height = self.extent_height * lego_brick_position[1] / self.board_size_height
        # Invert the axis
        lego_brick_height = self.extent_height - lego_brick_height
        # Add offset
        # TODO: control the offset
        lego_brick_height += self.extent_height_list[0]

        lego_brick_coordinates = float(lego_brick_width), float(lego_brick_height)

        return lego_brick_coordinates
