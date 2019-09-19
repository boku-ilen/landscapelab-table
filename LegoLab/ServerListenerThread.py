import logging
import threading
from typing import Callable

from .ConfigManager import ConfigManager
from .ServerCommunication import ServerCommunication
from .LegoDetection.Tracker import Tracker
from .ProgramStage import ProgramStage

# Configure logger
logger = logging.getLogger(__name__)

WAIT_SECONDS = 5


# NOTE maybe rename, the class does not really listen for anything, it executes tasks in regular intervals
class ServerListenerThread(threading.Thread):

    def __init__(
            self,
            config: ConfigManager,
            server: ServerCommunication,
            tracker: Tracker,
            get_program_stage: Callable[[], ProgramStage],
            progress_bar_update_function: Callable
    ):
        threading.Thread.__init__(self)

        self.config = config
        self.server = server
        self.ticker = threading.Event()
        self.tracker = tracker
        self.get_program_stage: Callable[[], ProgramStage] = get_program_stage
        self.progress_bar_update_function = progress_bar_update_function

    def run(self):

        while not self.ticker.wait(WAIT_SECONDS):

            logger.info("starting routine server request")

            # check if in correct program stage
            if self.get_program_stage() is ProgramStage.LEGO_DETECTION:

                # sync bricks and the player with server
                self.tracker.sync_with_server_side_bricks()

                # get update progress bars to reflect new energy output
                self.progress_bar_update_function()

            logger.debug("finished routine server request")

