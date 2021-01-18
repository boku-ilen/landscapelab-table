from typing import Dict, Tuple

from .MapHandler import MapHandler
from ..ConfigManager import ConfigManager, ConfigError
from ..Extent import Extent
from ..ServerCommunication import ServerCommunication


# MainMap class
# responsible for management of central map
class MainMap(MapHandler):

    def __init__(self, config: ConfigManager, name, scenario: Dict, server: ServerCommunication):

        self.config = config
        self.server = server

        # get desired screen resolution
        resolution_x = int(config.get("beamer_resolution", "width"))
        resolution_y = int(config.get("beamer_resolution", "height"))

        # get zoom limits
        zoom_limits = config.get("map_settings", "map_zoom_limits")

        super().__init__(
            config,
            name,
            self.get_start_extent(scenario),
            zoom_limits,
            (resolution_x, resolution_y)
        )

        # set new extent
        config.set("map_settings", "extent_width", [self.current_extent.x_min, self.current_extent.x_max])
        config.set("map_settings", "extent_height", [self.current_extent.y_min, self.current_extent.y_max])

    # retrieves starting location and defines an extent around this location
    def get_start_extent(self, scenario):

        starting_location = self.get_start_location(scenario)

        # extrude start location to start extent
        zoom = self.config.get("general", "start_zoom")

        return Extent.around_center(starting_location, zoom, 1)

    # reads starting-location from scenario info or config
    def get_start_location(self, scenario) -> Tuple[float, float]:
        if len(scenario["locations"]) == 0:
            raise ConfigError("No locations in scenario {}".format(scenario["name"]))

        # find start location
        config_starting_location_name = self.config.get("general", "starting_location")
        config_starting_location = None

        starting_location = None

        for location_key in scenario["locations"]:
            location = scenario["locations"][location_key]

            if location["name"] == config_starting_location_name:
                config_starting_location = location["location"]

            if location["starting_location"]:
                starting_location = location["location"]

        # overwrite starting location if the config-defined starting location exists
        if config_starting_location:
            starting_location = config_starting_location

        # choose first location if no starting location was found
        if not starting_location:
            first_key = next(iter(scenario["locations"]))
            starting_location = scenario["locations"][first_key]["location"]

        return starting_location

    # gets called whenever the map has been refreshed
    # updates extent on server
    def refresh_callback(self):
        self.server.update_extent_info(self.current_extent)
