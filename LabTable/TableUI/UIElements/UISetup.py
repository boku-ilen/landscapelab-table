from typing import Tuple
from LabTable.TableUI.UIElements.Icon import Icon

from LabTable.TableUI.UIElements.UIText import UIText
from .UIElement import UIElement, UIActionType
from .Button import Button
from .UIStructureBlock import UIStructureBlock
from .MiniMap import MiniMap
from .ProgressBar import ProgressBar
from ..CallbackManager import CallbackManager, MapActions, UiActions, TrackerActions
from ..MainMap import MainMap
from LabTable.Configurator import Configurator
from LabTable.Model.Extent import Vector


# project specific function used to create the necessary UIElements and link them to their respective callback functions
def setup_ui(root: UIElement, main_map: MainMap, config: Configurator, callback_manager: CallbackManager) -> \
        Tuple[MiniMap, UIElement]:

    # create nav block
    nav_block = UIElement()
    mini_map, navigation_block = setup_nav_block_ui(nav_block, config, main_map, callback_manager)

    # create detection mode ui
    progressbar_ui = UIElement()

    # Test text and icon ui
    test_text = UIText(config, Vector(0, 0), Vector(1, 1), [], [], 1.0, "test")
    test_icon = Icon(config, Vector(0, 0), Vector(1, 1), [], [], 0, "yes_icon")
    progressbar_ui.add_child(test_text)
    progressbar_ui.add_child(test_icon)

    # setup hierarchy
    root.add_child(nav_block)
    root.add_child(progressbar_ui)

    # setup ui callback functions
    callback_manager.set_ui_callbacks(navigation_block)

    return mini_map, progressbar_ui


# constant class used by the ui setup methods to easily access vector constants
class Constants:

    def __init__(self, config):

        self.scale_factor = config.get("ui_settings", "scale_factor")
        self.button_size = Vector(50, 50) * self.scale_factor

        self.Y = Vector(0, 1)
        self.X = Vector(1, 0)

        self.x = self.button_size ** self.X  # x offset       ** is element wise multiplication
        self.y = self.button_size ** self.Y  # y offset

        self.screen_width = config.get("beamer_resolution", "width")
        self.screen_height = config.get("beamer_resolution", "height")
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
    confirm_button = Button(config,
        c.zoom_offset ** c.X - c.nav_block_pos ** c.Y,  # align with zoom block on x axis, and toggle button on y axis
        c.button_size, 'confirm bricks', 'button_confirm')
    mini_map = MiniMap(config, 'mini_map', Vector(10, 300) * c.scale_factor, Vector(280, 280) * c.scale_factor,
                       main_map, None)
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
    if config.get("ui_settings", "nav_block_toggle"):
        # this makes the button toggle
        toggle_nav_block_button.set_callback(UIActionType.PRESS, ui_callbacks[UiActions.TOGGLE_NAV_BLOCK])
    else:
        # this shows the nav_block only when a brick is on the button
        toggle_nav_block_button.set_callback(UIActionType.PRESS, ui_callbacks[UiActions.SET_NAV_BLOCK_VISIBLE])
        toggle_nav_block_button.set_callback(UIActionType.RELEASE, ui_callbacks[UiActions.SET_NAV_BLOCK_INVISIBLE])

    return mini_map, navigation_block


# creates and sets up the ui for detection stage
def add_progressbars_to_ui(progressbars_ui_root, config, scores):

    # get vector constants that will be used to position the ui elements
    c = Constants(config)

    # create elements
    color_indexes = [[(255, 0, 0)], [(0, 0, 255)]]  # FIXME: load dynamically
    for counter, score in enumerate(scores):
        progress_bar = ProgressBar(config, c.bot_right_corner - c.x * (counter + 1) - c.y * 5,
                                   c.x / 2 + c.y * 4.5, False, True, score, color_indexes[counter])
        score.progress_bar = progress_bar
        progressbars_ui_root.add_child(progress_bar)
