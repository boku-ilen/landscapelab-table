import logging

from LabTable.TableUI.UICallback import UICallback

from enum import Enum
from typing import Dict

logger = logging.getLogger(__name__)


# FIXME: Program Stages will be triggered and retrieved in the future by the GameEngine within the LandscapeLab Client
class ProgramStage(Enum):

    WHITE_BALANCE = 1
    FIND_CORNERS = 2
    INTERNAL_MODE = 3  # brick detection without rules (disconnected, debug, ..)
    EXTERNAL_MODE = 4  # we are playing a game

    def next_stage(self):
        value = self.value + 1
        if value > 4:
            value = 4
        return ProgramStage(value)


# CurrentProgramStageClass
# keeps track of the current program stage
# TODO (future releases) convert to singleton
class CurrentProgramStage:

    def __init__(self, callbacks: Dict[Enum, UICallback]):
        self.current_stage: ProgramStage = ProgramStage.WHITE_BALANCE
        self.callbacks = callbacks
        logger.info("initialized first program stage: {}".format(self.current_stage))

    def next(self):
        self.current_stage = self.current_stage.next_stage()
        logger.info("entering program stage: {}".format(self.current_stage))

        # call callback function if there is one
        if self.current_stage in self.callbacks:
            self.callbacks[self.current_stage].call(None)
