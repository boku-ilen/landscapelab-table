from TableUI.UIElements.ProgressBar import ProgressBar


class Score:

    def __init__(self, progress_bar: ProgressBar, target: float, initial_value: float = 0.0):

        self.progress_bar = progress_bar

        self.value: float = initial_value
        self.target: float = target
        self.percentage: float = 0.0
        self.calculate_percentage()

    # TODO: are there other score calculations?
    def calculate_percentage(self):
        self.percentage = (self.value / self.target)

    def add_value(self, value: float):
        self.value += value
        self.calculate_percentage()

    def remove_value(self, value: float):
        self.value -= value
        self.calculate_percentage()

    def set_value(self, value: float):
        self.value = value
        self.calculate_percentage()
