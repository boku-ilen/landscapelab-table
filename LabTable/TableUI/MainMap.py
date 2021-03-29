from typing import Dict, Tuple

from LabTable.Model.Vector import Vector
from .MapHandler import MapHandler
from ..Configurator import Configurator, ConfigError
from LabTable.Model.Extent import Extent
from ..Communicator import Communicator


# MainMap class
# responsible for management of central map
class MainMap(MapHandler):

    def __init__(self, config: Configurator, name, server: Communicator):

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
            self.get_start_extent(),
            zoom_limits,
            (resolution_x, resolution_y)
        )

        # set new extent
        config.set("map_settings", "extent_width", [self.current_extent.x_min, self.current_extent.x_max])
        config.set("map_settings", "extent_height", [self.current_extent.y_min, self.current_extent.y_max])

    # retrieves starting location and defines an extent around this location
    def get_start_extent(self):

        starting_location = self.get_start_location()

        # extrude start location to start extent
        zoom = self.config.get("general", "start_zoom")

        return Extent.around_center(starting_location, zoom, 1)

    # reads starting-location from scenario info or config
    # FIXME: rework protocol (starting location should come from landscapelab)
    def get_start_location(self) -> Vector:

        # FIXME: this should come from the landscape lab
        starting_location = Vector(0.0, 0.0)

        # TODO: maybe overwrite starting location if the config-defined starting location exists

        return starting_location

    # gets called whenever the map has been refreshed
    # updates extent on server
    def refresh_callback(self):
        self.server.update_extent_info(self.current_extent)
