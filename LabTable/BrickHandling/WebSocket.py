import asyncio
import logging
import threading

from .BrickHandler import BrickHandler
import websocket, rel
import json

WEBSOCKET_URL = "ws://127.0.0.1:14541"
logger = logging.getLogger(__name__)
class WebSocketBrickHandler(BrickHandler):

    ws = None
    queued_samples = None
    reader_task = None
    def __init__(self):
        self.ws = websocket.WebSocket()
        self.ws.connect(WEBSOCKET_URL)
        self.reader_task = threading.Thread(target=self.handle_message, name="WebsocketReceiver")
        self.reader_task.start()

    def queued_drawing_samples(self):
        return self.queued_samples

    def handle_message(self):
        while True:
            data = self.ws.recv()
            if data == "":
                continue
            logger.info(f"got {data}")
            data_obj = json.loads(data)
            if data_obj["event"] == "start_drawing":
                # should be clip space ([0,1],[0,1]) to be resolution agnostic
                self.queued_samples = data_obj["data"]["points"]

    def handle_processed_drawing(self, bitmaps, ids, bounds, resolution):
        for i in range(len(bitmaps)):
            self.ws.send(json.dumps({
                "event": "drawing_processed",
                "data": {
                    "bitmap": bitmaps[i],
                    "resolution": resolution[i],
                    "bounds": bounds[i],
                    "id": ids[i]
                }
            }))
        self.queued_samples = None

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
