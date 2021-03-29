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
        cn = config.get("camera", "implementation") + "CameraTIS"
        module_is = __import__('LabTable.InputStream.' + cn, fromlist=[cn])
        class_ = getattr(module_is, cn)
        logger.debug("initializing {} as input stream".format(class_))
        return class_(config, board, usestream)

    # initialize the input stream (from live camera or bag file)
    def __init__(self, config, board, usestream):

        # Get the resolution from config file
        self.width = config.get("resolution", "width")
        self.height = config.get("resolution", "height")

        self.board = board

    @abstractmethod
    def get_frame(self):
        pass

    def is_initialized(self):
        return self.initialized

    def close(self):
        self.initialized = False
