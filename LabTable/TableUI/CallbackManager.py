from typing import Dict, Tuple, List, Type
from enum import Enum
import logging

from LabTable.TableUI.UICallback import UICallback
from .UIElements.UIElement import UIElement
from .MainMap import MainMap
from .UIElements.MiniMap import MiniMap
from LabTable.BrickDetection.Tracker import Tracker
from LabTable.Model.ProgramStage import ProgramStage
from LabTable.Configurator import Configurator, ConfigError

logger = logging.getLogger(__name__)

NamedCallbacks = Dict[Enum, UICallback]
MappedCallbacks = Dict[int, Tuple[Enum, UICallback]]

ACTION_SLOT_ID = 1  # used to access to UICallback in Tuple[Enum, UICallback] of MappedCallbacks


class MapActions(Enum):
    PAN_UP = 0
    PAN_DOWN = 1
    PAN_LEFT = 2
    PAN_RIGHT = 3
    ZOOM_IN = 4
    ZOOM_OUT = 5


class MiniMapActions(Enum):
    MINI_MAP_PAN_UP = 0
    MINI_MAP_PAN_DOWN = 1
    MINI_MAP_PAN_LEFT = 2
    MINI_MAP_PAN_RIGHT = 3
    MINI_MAP_ZOOM_IN = 4
    MINI_MAP_ZOOM_OUT = 5
    MINI_MAP_FOCUS = 6


class OutputActions(Enum):
    CHANNEL_UP = 0
    CHANNEL_DOWN = 1


class TrackerActions(Enum):
    CONFIRM_BRICKS = 0


class UiActions(Enum):
    TOGGLE_NAV_BLOCK = 0
    SET_NAV_BLOCK_VISIBLE = 1
    SET_NAV_BLOCK_INVISIBLE = 2


# CallbackManager class
# project specific class that manages UICallbacks
# makes it possible to register key callbacks in any order during setup
# keeps track of button mappings and provides call_key_action(...) function, that finds the callback linked to a key and
# executes it
class CallbackManager:

    def __init__(self, config: Configurator):
        self.config = config

        # define program stage change actions
        self.stage_change_actions: NamedCallbacks = CallbackManager.define_action_set(ProgramStage)

        # define all actions that could also be called by key presses
        self.map_actions: NamedCallbacks = CallbackManager.define_action_set(MapActions)
        self.mini_map_actions: NamedCallbacks = CallbackManager.define_action_set(MiniMapActions)
        self.output_actions: NamedCallbacks = CallbackManager.define_action_set(OutputActions)
        self.tracker_actions: NamedCallbacks = CallbackManager.define_action_set(TrackerActions)
        self.ui_actions: NamedCallbacks = CallbackManager.define_action_set(UiActions)

        # create action map from action lists
        self.action_map: MappedCallbacks = CallbackManager.find_button_mapping(
            [self.map_actions, self.mini_map_actions, self.output_actions, self.tracker_actions, self.ui_actions],
            config)

    @staticmethod
    # creates UICallback objects for every action of a given enum class
    def define_action_set(names: Type[Enum]) -> NamedCallbacks:
        ret: NamedCallbacks = {}
        for n in names:
            ret[n] = UICallback()

        return ret

    @staticmethod
    # takes a List of NamedCallbacks, tries to find a button mapping for each individual action
    # and stores those button mappings in one large dictionary
    def find_button_mapping(action_sets: List[NamedCallbacks], config: Configurator) -> MappedCallbacks:
        ret: MappedCallbacks = {}

        # iterates over all NamedCallbacks (remember NamedCallbacks is a List itself)
        for action_dict in action_sets:
            # iterates over each action in the current list
            for action_name, callback in action_dict.items():
                try:
                    # try to find button mapping in config file
                    mapped_key = config.get("button_map", action_name.name)
                    ret[ord(mapped_key)] = (action_name, callback)
                except ConfigError:
                    logger.warning("Could not find button mapping for UI action {}.".format(action_name.name))

        return ret

    # defines all ui callback functions
    def set_ui_callbacks(self, nav_block: UIElement):
        self.ui_actions[UiActions.TOGGLE_NAV_BLOCK].callback = \
            lambda brick: nav_block.set_visible(not nav_block.visible)

        self.ui_actions[UiActions.SET_NAV_BLOCK_VISIBLE].callback = \
            lambda brick: nav_block.set_visible(True)

        self.ui_actions[UiActions.SET_NAV_BLOCK_INVISIBLE].callback = \
            lambda brick: nav_block.set_visible(False)

    # defines all map callback functions
    def set_map_callbacks(self, my_map: MainMap):
        self.map_actions[MapActions.PAN_UP].callback = my_map.pan_up
        self.map_actions[MapActions.PAN_DOWN].callback = my_map.pan_down
        self.map_actions[MapActions.PAN_LEFT].callback = my_map.pan_left
        self.map_actions[MapActions.PAN_RIGHT].callback = my_map.pan_right
        self.map_actions[MapActions.ZOOM_IN].callback = my_map.zoom_in
        self.map_actions[MapActions.ZOOM_OUT].callback = my_map.zoom_out

    # defines all map callback functions
    def set_mini_map_callbacks(self, mini_map: MiniMap):
        self.mini_map_actions[MiniMapActions.MINI_MAP_PAN_UP].callback = mini_map.pan_up
        self.mini_map_actions[MiniMapActions.MINI_MAP_PAN_DOWN].callback = mini_map.pan_down
        self.mini_map_actions[MiniMapActions.MINI_MAP_PAN_LEFT].callback = mini_map.pan_left
        self.mini_map_actions[MiniMapActions.MINI_MAP_PAN_RIGHT].callback = mini_map.pan_right
        self.mini_map_actions[MiniMapActions.MINI_MAP_ZOOM_IN].callback = mini_map.zoom_in
        self.mini_map_actions[MiniMapActions.MINI_MAP_ZOOM_OUT].callback = mini_map.zoom_out
        self.mini_map_actions[MiniMapActions.MINI_MAP_FOCUS].callback = mini_map.focus_main_map

    # defines all tracker callback functions
    def set_tracker_callbacks(self, tracker: Tracker):
        self.tracker_actions[TrackerActions.CONFIRM_BRICKS].callback = \
            lambda bricks: tracker.invalidate_external_bricks()

    # defines all output callback functions
    def set_output_actions(self, output):
        self.output_actions[OutputActions.CHANNEL_UP].callback = \
            lambda brick: output.channel_up()

        self.output_actions[OutputActions.CHANNEL_DOWN].callback = \
            lambda brick: output.channel_down()

    # tests if a given key is assigned an action and calls that action
    def call_key_action(self, key):
        if key in self.action_map:
            self.action_map[key][ACTION_SLOT_ID].call(None)
