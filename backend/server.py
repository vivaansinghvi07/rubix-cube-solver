import json
import base64
import asyncio

import cv2
import websockets
import numpy as np

from cv import ImageToCube, cap_img

def base64_to_image(b64_str: str) -> cv2.Mat:
    np_buf = np.frombuffer(base64.b64decode(b64_str), np.uint8)
    img = cv2.imdecode(np_buf, cv2.IMREAD_COLOR)
    return cap_img(img)

async def handler(websocket: websockets.WebSocketServerProtocol):
    translator = None
    async for message in websocket:
        data = json.loads(message)
        match data["type"]:
            case "init":
                translator = ImageToCube(int(data["size"]))
                print("translator created")
            case "frame": 
                if translator is not None:
                    img = base64_to_image(data["data"])
                    translator.translate(img)
                    print("image read")
            case "finish":
                if translator is not None:
                    cube = translator.create_cube()
                    print(cube)
                    await websocket.send(json.dumps({
                        "type": "cv_finish", "cube": cube.to_simple_string()
                    }))

async def main():
    async with websockets.serve(handler, "", 8080):
        await asyncio.Future()

if __name__ == "__main__":
    asyncio.run(main())
