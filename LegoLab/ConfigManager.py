import json
import logging

logger = logging.getLogger(__name__)


# TODO: make it a singleton
class ConfigManager:
    """Loads config file and gives access to the data"""

    config_data = None

    def __init__(self, configfile="../config.json"):

        # Load config data
        try:
            with open(configfile) as config_file:
                self.config_data = json.load(config_file)
        except:
            logger.warning("Error opening config file: {}".format(configfile))
            self.config_data = {}

    # Return searched json data
    def get(self, group, key):

        value = None
        try:
            value = self.config_data[group][key]
            logger.debug("Get config data: {} -> {} with {}".format(group, key, value))
        except:
            logger.warning("Getting config data {} -> {} without success".format(group, key))

        # Return searched config data value
        return value

    # Overwrite config data
    def set(self, group, key, value):

        try:
            self.config_data[group][key] = value
            logger.debug("Overwriting config data {} -> {} with {}".format(group, key, value))
        except:
            logger.warning("Overwriting config data {} -> {} without success".format(group, key))
