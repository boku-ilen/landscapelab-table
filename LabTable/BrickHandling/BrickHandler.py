from LabTable.Model.Brick import Brick, BrickStatus, BrickShape, BrickColor, Token


class BrickHandler:
    def queued_drawing_samples(self):
        return None

    def handle_processed_drawing(self, bitmaps, ids, bounds, resolution):
        pass

    def handle_new_brick(self, Brick):
        pass

    def handle_removed_brick(self, Brick):
        pass

    def handle_pen_down(self, pos):
        pass

    def handle_pen_up(self, pos):
        pass

    def dispose(self):
        pass
