from enum import Enum


class ProgramStage(Enum):
    WHITE_BALANCE = 1
    FIND_CORNERS = 2
    LEGO_DETECTION = 3

    def next(self):
        value = self.value + 1
        if value > 3:
            value = 3
        return ProgramStage(value)
