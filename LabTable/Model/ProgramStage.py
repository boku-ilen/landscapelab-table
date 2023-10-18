import logging

from enum import Enum
from typing import Dict

logger = logging.getLogger(__name__)


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

    def prev_stage(self):
        value = self.value - 1
        if value < 1:
            value = 1
        return ProgramStage(value)


# CurrentProgramStageClass
# keeps track of the current program stage
# TODO (future releases) convert to singleton
class CurrentProgramStage:

    def __init__(self):
        self.current_stage: ProgramStage = ProgramStage.WHITE_BALANCE
        logger.info("initialized first program stage: {}".format(self.current_stage))

    def next(self):
        self.current_stage = self.current_stage.next_stage()
        logger.info("entering program stage: {}".format(self.current_stage))

    def prev(self):
        self.current_stage = self.current_stage.prev_stage()
        logger.info("entering program stage: {}".format(self.current_stage))
