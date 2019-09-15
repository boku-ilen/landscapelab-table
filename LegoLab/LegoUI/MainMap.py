from functools import partial
from typing import Dict, Tuple
import numpy as np

from .MapHandler import MapHandler
from .MapActions import MapActions
from ..ConfigManager import ConfigManager, ConfigError
from ..LegoExtent import LegoExtent
from ..ServerCommunication import ServerCommunication


class MainMap(MapHandler):

    def __init__(self, config: ConfigManager, name, scenario: Dict, server: ServerCommunication):

        self.config = config
        self.server = server

        # get desired screen resolution
        resolution_x = int(config.get("beamer-resolution", "width"))
        resolution_y = int(config.get("beamer-resolution", "height"))

        super().__init__(
            config,
            name,
            self.get_start_extent(scenario),
            (resolution_x, resolution_y)
        )

        # set new extent
        config.set("map_settings", "extent_width", [self.current_extent.x_min, self.current_extent.x_max])
        config.set("map_settings", "extent_height", [self.current_extent.y_min, self.current_extent.y_max])

        # set extent modifiers
        pan_up_modifier = np.array([0, 1, 0, 1])
        pan_down_modifier = np.array([0, -1, 0, -1])
        pan_left_modifier = np.array([-1, 0, -1, 0])
        pan_right_modifier = np.array([1, 0, 1, 0])
        zoom_in_modifier = np.array([1, 1, -1, -1])
        zoom_out_modifier = np.array([-1, -1, 1, 1])

        # get navigation settings
        pan_distance = config.get('map_settings', 'pan_distance')
        zoom_strength = config.get('map_settings', 'zoom_strength')

        self.action_map = {
            MapActions.PAN_UP: partial(self.init_render, pan_up_modifier, pan_distance),
            MapActions.PAN_DOWN: partial(self.init_render, pan_down_modifier, pan_distance),
            MapActions.PAN_LEFT: partial(self.init_render, pan_left_modifier, pan_distance),
            MapActions.PAN_RIGHT: partial(self.init_render, pan_right_modifier, pan_distance),
            MapActions.ZOOM_IN: partial(self.init_render, zoom_in_modifier, zoom_strength),
            MapActions.ZOOM_OUT: partial(self.init_render, zoom_out_modifier, zoom_strength),
        }

    def get_start_extent(self, scenario):

        starting_location = self.get_start_location(scenario)

        # extrude start location to start extent
        zoom = self.config.get("general", "start_zoom")

        return LegoExtent.around_center(starting_location, zoom, 1)

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

    # modifies the current extent and requests an updated render image
    # param brick gets ignored so that UIElements can call the function
    def init_render(self, extent_modifier, strength, brick):
        # modify extent
        width = self.current_extent.get_width()
        height = self.current_extent.get_height()

        move_extent = np.multiply(
            extent_modifier,
            np.array([width, height, width, height])
        ) * strength[0]

        next_extent = self.current_extent.clone()
        next_extent.add_extent_modifier(move_extent)

        # request render
        self.request_render(next_extent)

    def refresh_callback(self):
        self.server.update_extent_info(self.current_extent)

    def invoke(self, action: MapActions):
        if action in self.action_map:
            self.action_map[action](None)
