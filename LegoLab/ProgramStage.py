from enum import Enum


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


# TODO (future releases) convert to singleton, also add possible callbacks to call when stage transitioning
class CurrentProgramStage:

    def __init__(self):
        self.current_stage: ProgramStage = ProgramStage.WHITE_BALANCE

    def next(self):
        self.current_stage = self.current_stage.next_stage()

