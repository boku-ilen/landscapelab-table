from LabTable.Model.Vector import Vector
from .MapHandler import MapHandler
from LabTable.Configurator import Configurator
from LabTable.Model.Extent import Extent


# MainMap class
# responsible for management of central map
class MainMap(MapHandler):

    def __init__(self, config: Configurator, name, ll_communicator):

        self.config = config
        self.landscape_lab = ll_communicator

        # get desired screen resolution
        resolution_x = int(config.get("beamer_resolution", "width"))
        resolution_y = int(config.get("beamer_resolution", "height"))

        # get zoom limits
        zoom_limits = config.get("map_settings", "map_zoom_limits")

        super().__init__(config, name, self.get_start_extent(), zoom_limits, (resolution_x, resolution_y))

        # set new extent
        config.set("map_settings", "extent_width", [self.current_extent.x_min, self.current_extent.x_max])
        config.set("map_settings", "extent_height", [self.current_extent.y_min, self.current_extent.y_max])

    # retrieves starting location and defines an extent around this location
    def get_start_extent(self):
        starting_location = Vector(self.config.get("map_settings", "start_x"),
                                   self.config.get("map_settings", "start_y"))

        # extrude start location to start extent
        zoom = self.config.get("map_settings", "start_zoom")

        return Extent.around_center(starting_location, zoom, 1)

    # gets called whenever the map has been refreshed and updates extent on server
    def refresh_callback(self):
        self.landscape_lab.update_extent_info(self.current_extent)
