import websocket
import time
import random

WEBSOCKET_URL = "ws://127.0.0.1:14541"
ws = websocket.WebSocket()
ws.connect(WEBSOCKET_URL)

while True:
    random_x = 0.2 + random.random() * 0.6
    random_y = 0.2 + random.random() * 0.6

    added = '{"event": "brick_added", "data": {"id": 46, "position": [' + str(random_x) + ', ' + str(random_y) + '], "shape": "BrickShape.SQUARE_BRICK", "color": "BrickColor.BLUE_BRICK"} }'
    removed = '{"event": "brick_removed", "data": {"id": 46, "position": [' + str(random_x) + ', ' + str(random_y) + '], "shape": "BrickShape.SQUARE_BRICK", "color": "BrickColor.BLUE_BRICK"} }'

    print(added)
    ws.send(added)

    time.sleep(12.0)

    print(removed)
    ws.send(removed)

    time.sleep(12.0)