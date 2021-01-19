import logging
import threading
from typing import Callable

from .Configurator import Configurator
from .ServerCommunication import ServerCommunication
from .BrickDetection.Tracker import Tracker
from LabTable.Model.ProgramStage import ProgramStage

# Configure logger
logger = logging.getLogger(__name__)

WAIT_SECONDS = 5


class SchedulerThread(threading.Thread):

    def __init__(
            self,
            config: Configurator,
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

        # Create a lock
        self.lock = threading.Lock()

    def run(self):

        while not self.ticker.wait(WAIT_SECONDS):

            logger.debug("starting routine server request")

            # check if in correct program stage
            if self.get_program_stage() is ProgramStage.PLANNING:

                self.lock.acquire()

                # sync bricks and the player with server
                self.tracker.sync_with_server_side_bricks()

                # get update progress bars to reflect new energy output
                self.progress_bar_update_function()

                self.lock.release()

            logger.debug("finished routine server request")

