from typing import Optional, Callable

from LabTable.Model.Brick import Brick


Callback = Callable[[Optional[Brick]], None]


# callback class
# makes it possible to assign / reassign a callback function
# after it has been linked to an UIElement
class UICallback:

    # creates a new UICallback object that does nothing
    def __init__(self):
        self.callback: Optional[Callback] = None

    # calls the current callback function
    def call(self, brick: Optional[Brick]):
        if self.callback is not None:
            self.callback(brick)

    # overwrites the current callback function with a new one
    def set_callback(self, callback: Callback):
        self.callback = callback
