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


class ServerListenerThread(threading.Thread):

    def __init__(
            self,
            config: ConfigManager,
            server: ServerCommunication,
            tracker: Tracker,
            get_program_stage: Callable[[], ProgramStage]):
        threading.Thread.__init__(self)

        self.config = config
        self.server = server
        self.ticker = threading.Event()
        self.tracker = tracker
        self.get_program_stage: Callable[[], ProgramStage] = get_program_stage

    def run(self):
        logger.info("starting to getting player position from server")

        while not self.ticker.wait(WAIT_SECONDS):

            logger.debug("starting routine server request")

            # set player marker
            player_instance = self.server.get_player_position()
            if player_instance is not None:
                self.tracker.player_position = player_instance

            # check if in correct program stage
            if self.get_program_stage() is ProgramStage.LEGO_DETECTION:

                # sync bricks with server
                self.tracker.sync_with_server_side_bricks()

                # get current energy lv
                pass

            logger.debug("finished routine server request")

