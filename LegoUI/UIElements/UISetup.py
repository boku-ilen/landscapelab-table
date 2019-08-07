from LegoUI.UIElements.UIElement import UIElement, UIActionType
from LegoUI.UIElements.Button import Button
from LegoUI.UIElements.UIStructureBlock import UIStructureBlock
from ConfigManager import ConfigManager
from typing import Dict, Callable
from LegoUI.MapActions import MapActions

BUTTON_SIZE = (50, 50)


def setup_ui(action_map: Dict[MapActions, Callable], config: ConfigManager) -> UIElement:

    # create root element
    root = UIElement()

    # create other elements
    toggle_nav_block_button = Button((20, 20), BUTTON_SIZE, 'toggle navigation block')
    navigation_block = UIStructureBlock((-10, -10), (300, 300))
    pan_up_button = Button((75, 75), BUTTON_SIZE, 'pan up')
    pan_down_button = Button((75, 175), BUTTON_SIZE, 'pan down')
    pan_left_button = Button((25, 125), BUTTON_SIZE, 'pan left')
    pan_right_button = Button((125, 125), BUTTON_SIZE, 'pan right')
    zoom_in_button = Button((225, 75), BUTTON_SIZE, 'zoom in')
    zoom_out_button = Button((225, 175), BUTTON_SIZE, 'zoom out')

    # setup hierarchy
    root.add_child(toggle_nav_block_button)
    toggle_nav_block_button.add_child(navigation_block)
    navigation_block.add_child(pan_up_button)
    navigation_block.add_child(pan_down_button)
    navigation_block.add_child(pan_left_button)
    navigation_block.add_child(pan_right_button)
    navigation_block.add_child(zoom_in_button)
    navigation_block.add_child(zoom_out_button)

    # set nav block invisible
    navigation_block.set_visible(False)

    # set button functionality
    pan_up_button.set_callback(UIActionType.PRESS, action_map[MapActions.PAN_UP])
    pan_down_button.set_callback(UIActionType.PRESS, action_map[MapActions.PAN_DOWN])
    pan_left_button.set_callback(UIActionType.PRESS, action_map[MapActions.PAN_LEFT])
    pan_right_button.set_callback(UIActionType.PRESS, action_map[MapActions.PAN_RIGHT])
    zoom_in_button.set_callback(UIActionType.PRESS, action_map[MapActions.ZOOM_IN])
    zoom_out_button.set_callback(UIActionType.PRESS, action_map[MapActions.ZOOM_OUT])

    if config.get("ui-settings", "nav-block-toggle"):
        # this makes the button toggle
        toggle_nav_block_button.set_callback(
            UIActionType.PRESS,
            lambda brick: navigation_block.set_visible(not navigation_block.visible)
        )
    else:
        # this shows the nav_block only when a brick is on the button
        toggle_nav_block_button.set_callback(UIActionType.PRESS, lambda brick: navigation_block.set_visible(True))
        toggle_nav_block_button.set_callback(UIActionType.RELEASE, lambda brick: navigation_block.set_visible(False))

    return root

