class Score:

    def __init__(self, score_id: int, target: float, initial_value: float = 0.0, name: str = ""):

        self.progress_bar = None

        self.score_id: int = score_id
        self.name: str = name
        self.value: float = initial_value
        self.target: float = target
        self.percentage: float = 0.0
        self.calculate_percentage()

    # TODO: are there other score calculations?
    def calculate_percentage(self):
        self.percentage = (self.value / self.target)

    def set_value(self, value: float):
        self.value = value
        self.calculate_percentage()
