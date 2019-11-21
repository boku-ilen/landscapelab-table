from .LegoUI.UICallback import UICallback

from enum import Enum
from typing import Dict


class ProgramStage(Enum):
    WHITE_BALANCE = 1
    FIND_CORNERS = 2
    EVALUATION = 3
    LEGO_DETECTION = 4

    def next_stage(self):
        value = self.value + 1
        if value > 4:
            value = 4
        return ProgramStage(value)


# TODO (future releases) convert to singleton
class CurrentProgramStage:

    def __init__(self, callbacks: Dict[Enum, UICallback]):
        self.current_stage: ProgramStage = ProgramStage.WHITE_BALANCE
        self.callbacks = callbacks

    def next(self):
        self.current_stage = self.current_stage.next_stage()

        # call callback function if there is one
        if self.current_stage in self.callbacks:
            self.callbacks[self.current_stage].call(None)

    # only switches to the next stage if the current stage is evaluation
    def only_switch_if_eval(self):
        if self.current_stage == ProgramStage.EVALUATION:
            self.next()
