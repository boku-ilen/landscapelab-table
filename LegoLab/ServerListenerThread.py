import logging
import time
import threading

from .ConfigManager import ConfigManager
from .ServerCommunication import ServerCommunication
from .LegoDetection.Tracker import Tracker

# Configure logger
logger = logging.getLogger(__name__)

WAIT_SECONDS = 5


class ServerListenerThread(threading.Thread):

    def __init__(self, config: ConfigManager, server: ServerCommunication, tracker: Tracker):
        threading.Thread.__init__(self)

        self.config = config
        self.server = server
        self.ticker = threading.Event()
        self.tracker = tracker

    def run(self):
        logger.info("starting to getting player position from server")

        while not self.ticker.wait(WAIT_SECONDS):
            player_instance = self.server.get_player_position()
            if player_instance is not None:
                self.tracker.player_position = player_instance
