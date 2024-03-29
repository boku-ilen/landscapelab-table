from abc import abstractmethod
import logging

# enable logger
logger = logging.getLogger(__name__)


class TableInputStream:

    initialized = False

    # Initialize the resolution
    width = None
    height = None

    @staticmethod
    def get_table_input_stream(config, board, usestream=None) -> 'TableInputStream':

        ret = None
        cn = config.get("camera", "implementation") + "CameraTIS"

        try:
            module_is = __import__('LabTable.InputStream.' + cn, fromlist=[cn])
            class_ = getattr(module_is, cn)
            ret = class_(config, board, usestream)
            logger.debug("initializing {} as input stream".format(class_))
        except ModuleNotFoundError as e:
            logger.fatal("Could not initialize camera with Module {}".format(cn))

        return ret

    # initialize the input stream (from live camera or bag file)
    def __init__(self, config, board, usestream):

        # Get the resolution from config file
        self.width = config.get("video_resolution", "width")
        self.height = config.get("video_resolution", "height")

        self.board = board

        logger.info("initialized input stream with board {} ({} x {})".format(board, self.width, self.height))
        self.initialized = True

    @abstractmethod
    def get_frame(self):
        pass

    @abstractmethod
    def get_distance_to_board(self):
        pass

    def is_initialized(self):
        return self.initialized

    def close(self):
        self.initialized = False
