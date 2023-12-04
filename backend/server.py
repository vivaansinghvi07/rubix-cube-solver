import json
import base64
import asyncio
from typing import Callable

import cv2
import websockets
import numpy as np

from pycubing import Cube
from cv import ImageToCube, cap_img
from pycubing.solver.solver3x3 import (
    orient_centers, solve_white_cross, solve_first_layer_corners,
    solve_second_layer_edges, solve_oll_edges, solve_oll_corners,
    solve_pll_corners, solve_pll_edges
)
from pycubing.solver.solver2x2 import orient_top_until_solve
from pycubing.solver.solverNxN import solve_centers, solve_edges
from pycubing.solver import PIPELINE_3x3, PIPELINE_2x2, PIPELINE_NxN
from pycubing.utils import SolvePipeline, convert_3x3_moves_to_2x2, convert_3x3_moves_to_NxN

FUNCTION_LIST_ATTR = "_SolvePipeline__funcs"
FUNCTION_TO_EXPLANATIONS = {
    orient_top_until_solve: "Turn the final layer until the whole cube is solved.",
    orient_centers: "Align the centers so that white is on the bottom.",
    solve_white_cross: "Create the white cross on the bottom.",
    solve_first_layer_corners: "Put all the corners in the right place, solving the first layer.",
    solve_second_layer_edges: "Solve the middle edges, solving the second layer.",
    solve_oll_edges: "Orient all the edges in the last layer by forming a yellow cross.",
    solve_oll_corners: "Orient all the corners in the last layer, making the top all yellow.",
    solve_pll_corners: "Put all the corners in the right place.",
    solve_pll_edges: "Put all the edges in the right place, solving the cube.",
    solve_centers: "Make all the centers uniform, like in a 3x3.",
    solve_edges: "Make all the edges uniform, like in a 3x3."
}


def add_to_response(moves: list[str], func: Callable, cube: Cube, response: list[dict]) -> None:
    response.append({
        "moves": moves, 
        "desc": FUNCTION_TO_EXPLANATIONS[func],
        "simple_string": cube.to_simple_string()
    })

def add_pipeline_to_response(cube: Cube, response: list[dict], pipeline: SolvePipeline):
    move_cube, move_function = cube, lambda x: x
    different_cube = pipeline == (PIPELINE_3x3 and cube.N > 3) or pipeline == PIPELINE_2x2
    if different_cube:
        move_cube = cube.get_3x3()
        move_function = lambda x: convert_3x3_moves_to_NxN(x, cube.N)
        if cube.N == 2: 
            move_function = convert_3x3_moves_to_2x2 
    for func in getattr(pipeline, FUNCTION_LIST_ATTR):
        moves = move_function(func(move_cube))
        if different_cube:
            cube.parse(" ".join(moves))
        add_to_response(moves, func, cube, response)
                    
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
            case "frame": 
                if translator is not None:
                    img = base64_to_image(data["data"])
                    translator.translate(img)
            case "finish":
                if translator is not None:
                    cube = translator.create_cube()
                    await websocket.send(json.dumps({
                        "type": "cv_finish", "cube": cube.to_simple_string()
                    }))
            case "solve":
                cube = Cube.from_simple_string(data["simple_string"])
                response = []
                match cube.N:
                    case 1:
                        pass
                    case 2:
                        add_pipeline_to_response(cube, response, PIPELINE_2x2)
                        new_moves = orient_top_until_solve(cube)
                        add_to_response(new_moves, orient_top_until_solve, cube, response)
                    case 3:
                        add_pipeline_to_response(cube, response, PIPELINE_3x3)
                    case _:
                        add_pipeline_to_response(cube, response, PIPELINE_NxN)
                        add_pipeline_to_response(cube, response, PIPELINE_3x3)
                await websocket.send(json.dumps({
                    "type": "solve", "moves": response
                }))

async def main():
    async with websockets.serve(handler, "", 8090):
        await asyncio.Future()

if __name__ == "__main__":
    asyncio.run(main())
