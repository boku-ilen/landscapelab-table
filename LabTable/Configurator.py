import os
import json
import logging
from typing import List

logger = logging.getLogger(__name__)


class ConfigError(Exception):

    def __init__(self, *args, **kwargs):
        super().__init__(args, kwargs)


class Configurator:
    """Loads config file and gives access to the data"""

    config_data = None
    _config_file = None

    def __init__(self, configfile="config.json"):

        # Load inital config data
        self._config_file = configfile
        self.refresh()

    # reload configuration file
    def refresh(self):

        try:
            with open(self._config_file) as config_file:
                self.config_data = json.load(config_file)

        except Exception as e:
            logger.exception("Error opening config file: {}".format(e))
            raise ConfigError("Could not load config data from {}".format(self._config_file))

    # Return searched json data
    def get(self, group, key=None):

        value = ""  # FIXME:

        try:
            if not key:
                value = self.config_data[group]
            else:
                value = self.config_data[group][key]
            logger.debug("Get config data: {} -> {} with {}".format(group, key, value))
        except Exception as e:
            logger.warning("Getting config data {} -> {} without success".format(group, key))
            logger.debug(e.__traceback__)

        # Return searched config data value
        return value

    # Overwrite config data
    def set(self, group, key, value):

        try:
            self.config_data[group][key] = value
            logger.debug("Overwriting config data {} -> {} with {}".format(group, key, value))

        except Exception as e:
            logger.error("Overwriting config data {} -> {} without success".format(group, key))
            logger.exception(e)

    @staticmethod
    def reconstruct_path(base_path, relative_path: List[str]):
        for d in relative_path:
            base_path = os.path.join(base_path, d)
        return base_path
