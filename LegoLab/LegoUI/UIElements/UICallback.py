from typing import Optional, Callable

class UICallback:

    def __init__(self):
        self.callback: Optional[Callable[]] = None

    def call(self):