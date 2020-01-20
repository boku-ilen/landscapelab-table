from typing import Tuple, List, Callable
from functools import partial

from .UIElement import UIElement, UIActionType
from .Button import Button
from .UIStructureBlock import UIStructureBlock
from .MiniMap import MiniMap
from .ProgressBar import ProgressBar
from ..CallbackManager import CallbackManager, MapActions, UiActions, TrackerActions
from ..MainMap import MainMap
from ...ConfigManager import ConfigManager
from ...ServerCommunication import ServerCommunication
from ...ProgramStage import ProgramStage
from ...Extent import Vector


# project specific function used to create the necessary UIElements and link them to their respective callback functions
def setup_ui(root: UIElement, main_map: MainMap, config: ConfigManager, server: ServerCommunication,
             callback_manager: CallbackManager) \
        -> Tuple[MiniMap, UIElement, Callable]:

    # create nav block
    nav_block = UIElement()
    mini_map, navigation_block = setup_nav_block_ui(nav_block, config, main_map, callback_manager)

    # create detection mode ui
    lego_detection_ui = UIElement()
    progress_bar_update_function = setup_detection_ui(lego_detection_ui, server, config, callback_manager)

    # setup hierarchy
    root.add_child(nav_block)
    root.add_child(lego_detection_ui)

    # setup ui callback functions
    callback_manager.set_ui_callbacks(navigation_block)

    return \
        mini_map,\
        lego_detection_ui, \
        progress_bar_update_function


# constant class used by the ui setup methods to easily access vector constants
class Constants:
    def __init__(self, config):
        self.scale_factor = config.get("ui-settings", "scale-factor")
        self.button_size = Vector(50, 50) * self.scale_factor

        self.x = self.button_size ** Vector(1, 0)  # x offset       ** is element wise multiplication
        self.y = self.button_size ** Vector(0, 1)  # y offset

        self.screen_width = config.get("beamer-resolution", "width")
        self.screen_height = config.get("beamer-resolution", "height")
        self.bot_right_corner = Vector(self.screen_width, self.screen_height)
        self.nav_toggle_pos = Vector(20, 20) * self.scale_factor
        self.nav_block_pos = Vector(-10, -10) * self.scale_factor
        self.nav_block_size = Vector(300, 600) * self.scale_factor
        self.cross_offset = self.x * 0.5 + self.y * 1.5  # default button offset for the pan controls
        self.zoom_offset = self.cross_offset + self.x * 4  # default button offset for the zoom controls


# creates and sets up the navigation block ui
def setup_nav_block_ui(nav_block_root, config, main_map, callback_manager) -> (MainMap, UIStructureBlock):
    # get vector constants that will be used to position the ui elements
    c = Constants(config)

    # create elements
    toggle_nav_block_button = Button(config, c.nav_toggle_pos, c.button_size, 'toggle navigation block')
    navigation_block = UIStructureBlock(config, c.nav_block_pos, c.nav_block_size)
    pan_up_button = Button(config, c.cross_offset + c.x, c.button_size, 'pan up', 'button_up')
    pan_down_button = Button(config, c.cross_offset + c.x + c.y * 2, c.button_size, 'pan down', 'button_down')
    pan_left_button = Button(config, c.cross_offset + c.y, c.button_size, 'pan left', 'button_left')
    pan_right_button = Button(config, c.cross_offset + c.y + c.x * 2, c.button_size, 'pan right', 'button_right')
    zoom_in_button = Button(config, c.zoom_offset, c.button_size, 'zoom in', 'button_zoom_in')
    zoom_out_button = Button(config, c.zoom_offset + c.y * 2, c.button_size, 'zoom out', 'button_zoom_out')
    confirm_button = Button(config, c.cross_offset + c.x + c.y, c.button_size, 'confirm bricks', 'button_confirm')
    mini_map = MiniMap(
        config,
        'mini_map',
        Vector(10, 300) * c.scale_factor,
        Vector(280, 280) * c.scale_factor,
        main_map
    )
    callback_manager.set_mini_map_callbacks(mini_map)

    # setup hierarchy
    nav_block_root.add_child(toggle_nav_block_button)
    toggle_nav_block_button.add_child(navigation_block)
    navigation_block.add_child(pan_up_button)
    navigation_block.add_child(pan_down_button)
    navigation_block.add_child(pan_left_button)
    navigation_block.add_child(pan_right_button)
    navigation_block.add_child(zoom_in_button)
    navigation_block.add_child(zoom_out_button)
    navigation_block.add_child(confirm_button)
    navigation_block.add_child(mini_map)

    navigation_block.set_visible(False)

    # set button functionality
    map_callbacks = callback_manager.map_actions
    tracker_callbacks = callback_manager.tracker_actions

    pan_up_button.set_callback(UIActionType.PRESS, map_callbacks[MapActions.PAN_UP])
    pan_down_button.set_callback(UIActionType.PRESS, map_callbacks[MapActions.PAN_DOWN])
    pan_left_button.set_callback(UIActionType.PRESS, map_callbacks[MapActions.PAN_LEFT])
    pan_right_button.set_callback(UIActionType.PRESS, map_callbacks[MapActions.PAN_RIGHT])
    zoom_in_button.set_callback(UIActionType.PRESS, map_callbacks[MapActions.ZOOM_IN])
    zoom_out_button.set_callback(UIActionType.PRESS, map_callbacks[MapActions.ZOOM_OUT])
    confirm_button.set_callback(UIActionType.PRESS, tracker_callbacks[TrackerActions.CONFIRM_BRICKS])

    ui_callbacks = callback_manager.ui_actions
    if config.get("ui-settings", "nav-block-toggle"):
        # this makes the button toggle
        toggle_nav_block_button.set_callback(UIActionType.PRESS, ui_callbacks[UiActions.TOGGLE_NAV_BLOCK])
    else:
        # this shows the nav_block only when a brick is on the button
        toggle_nav_block_button.set_callback(UIActionType.PRESS, ui_callbacks[UiActions.SET_NAV_BLOCK_VISIBLE])
        toggle_nav_block_button.set_callback(UIActionType.RELEASE, ui_callbacks[UiActions.SET_NAV_BLOCK_INVISIBLE])

    return mini_map, navigation_block


# creates and sets up the ui for detection stage
def setup_detection_ui(detection_ui_root, server, config, callback_manager):
    # get vector constants that will be used to position the ui elements
    c = Constants(config)

    # create elements
    progress_bar_wind = ProgressBar(
        config,
        c.bot_right_corner - c.x - c.y * 5,
        c.x / 2 + c.y * 4.5,
        False,
        True,
        [(255, 0, 0)]  # bgr
    )
    progress_bar_pv = ProgressBar(
        config,
        c.bot_right_corner - c.x * 2 - c.y * 5,
        c.x / 2 + c.y * 4.5,
        False,
        True,
        [(0, 0, 255)]  # bgr
    )

    # set progress calculation callbacks
    asset_type_id = config.get("server", "wind_id")
    progress_bar_wind.target = server.get_energy_target(asset_type_id)
    progress_bar_wind.progress_calculation = partial(server.get_energy_contrib, asset_type_id)

    asset_type_id = config.get("server", "pv_id")
    progress_bar_pv.target = server.get_energy_target(asset_type_id)
    progress_bar_pv.progress_calculation = partial(server.get_energy_contrib, asset_type_id)

    # setup hierarchy
    detection_ui_root.add_child(progress_bar_wind)
    detection_ui_root.add_child(progress_bar_pv)

    # make detection root invisible
    detection_ui_root.set_visible(False)
    callback_manager.stage_change_actions[ProgramStage.PLANNING].set_callback(
        lambda brick: detection_ui_root.set_visible(True)
    )

    return partial(update_progress_bars, [progress_bar_wind, progress_bar_pv])


# calls the update function on all progress bars that were passed in
def update_progress_bars(progress_bars: List[ProgressBar]):
    for bar in progress_bars:
        bar.calculate_progress()
