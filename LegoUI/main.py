import socket
from CVControllerThread import CVControllerThread
from ListenerThread import ListenerThread
from LegoDetection.ConfigManager import ConfigManager
import logging

try:
    logging.config.fileConfig('logging.conf')
    logger.info("Logging initialized")
except:
    logging.basicConfig(level=logging.INFO)
    logging.info("Could not initialize: logging.conf not found or misconfigured")


def main():

    config = ConfigManager('E:/Users/rotzr/Documents/Desktoperweiterungen/desktop/Arbeit/BOKU_2018/Projekt/landscapelab-lego/LegoDetection/config.json')

    # create and start the threads
    cv_c = CVControllerThread(config)
    listener = ListenerThread(config, cv_c)

    # starting
    cv_c.start()
    listener.start()

    # wait till all threads are finished, then close the socket
    cv_c.join()
    listener.join()


if __name__ == '__main__':
    main()
