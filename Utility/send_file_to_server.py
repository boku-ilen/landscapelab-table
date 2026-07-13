import websocket
import time

WEBSOCKET_URL = "ws://127.0.0.1:14541"
ws = websocket.WebSocket()
ws.connect(WEBSOCKET_URL)

with open('1742839581.938.log', 'r') as file:
    # Read each line in the file
    for line in file:
        data = line.split(": ", 1)[1]
        print(data)
        ws.send(data)

        if "BrickColor.BLUE_BRICK" in data and "brick_added" in data:
            time.sleep(35.0)
        else:
            time.sleep(1.5)