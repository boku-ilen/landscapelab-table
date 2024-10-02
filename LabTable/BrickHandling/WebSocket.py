from .BrickHandler import BrickHandler
import websocket
import json

WEBSOCKET_URL = "ws://127.0.0.1:14541"

class WebSocketBrickHandler(BrickHandler):

    ws = None

    def __init__(self):
        self.ws = websocket.WebSocket()
        self.ws.connect(WEBSOCKET_URL)

    def handle_new_brick(self, brick):
        self.ws.send(json.dumps({
            "event": "brick_added",
            "data": {
                "id": brick.object_id,
                "position": brick.get_relative_position(),
                "shape": str(brick.token.shape),
                "color": str(brick.token.color)
            }
        }))

    def handle_removed_brick(self, brick):
        self.ws.send(json.dumps({
            "event": "brick_removed",
            "data": {
                "id": brick.object_id,
                "position": brick.get_relative_position(),
                "shape": str(brick.token.shape),
                "color": str(brick.token.color)
            }
        }))
