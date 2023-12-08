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
from pycubing.error import ParityException
from pycubing.solver.solver2x2 import orient_top_until_solve
from pycubing.solver.solverNxN import pll_parity, solve_centers, solve_edges
from pycubing.solver import PIPELINE_3x3, PIPELINE_2x2, PIPELINE_NxN, PIPELINE_NxN_3x3_STAGE
from pycubing.utils import SolvePipeline, convert_3x3_moves_to_2x2, convert_3x3_moves_to_NxN, get_letter_dist_layer_width, get_move, clean_moves

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
    solve_edges: "Make all the edges uniform, like in a 3x3.",
    pll_parity: "Apply an edge PLL parity algorithm for big cubes."
}

MOVE_OPPOSITES = (temp := {
    'R': 'L',
    'F': 'B',
    'U': 'D'
}) | {v: k for k, v in temp.items()}

def get_ttk_wide_move(letter: str, dist: int, layer: int) -> str:
    """ 
    Gets a wide move in the following form:
        - For a simple 2-layer wide, it is 'r',
        - For a 3-layer wide going backwards, it is "3r'"
        - And so on
    """
    letter_str = letter.lower() if layer > 1 else letter
    layer_str = '' if layer <= 2 else str(layer)
    dist_str = ['', '2', "'"][dist % 4 - 1]
    return f"{layer_str}{letter_str}{dist_str}"

def convert_moves_to_ttk(moves: list[str], N: int) -> list[str]:
    """
    Convert a list of moves to a form which the TwistySim library can understand.
    """
    new_moves = []
    for m in moves:
        letter, dist, layer, width = get_letter_dist_layer_width(m, N)
        if layer == 1 or layer == width == N:  # single layer turn
            new_moves.append(m)
            continue
        if layer == N // 2 + 1 and N % 2 == 1 and width == 1:  # middle layer turn
            index = ['R', 'L', 'F', 'B', 'U', 'D'].index(letter)
            middle_layer_letter = ['M', 'S', 'E'][index // 2]
            dist_multiplier = -1 if index % 2 == 0 else 1
            dist_str = ['', '2', "'"][dist * dist_multiplier % 4 - 1]
            new_moves.append(f"{middle_layer_letter}{dist_str}")
        elif layer > N // 2:  # layer exceeds the middle 
            if layer == width:  # goes all the way back
                new_moves.append(get_ttk_wide_move(MOVE_OPPOSITES[letter], dist, N - layer))
                new_moves.extend(get_move(MOVE_OPPOSITES[letter], -dist, N, N, N))  # will be a rotation move
            elif width == 1:  # single layer turn
                if N == layer: 
                    new_moves.extend(get_move(MOVE_OPPOSITES[letter], -dist, 1, 1))
                else:
                    new_moves.append(get_ttk_wide_move(MOVE_OPPOSITES[letter], -dist, N - layer + 1))
                    new_moves.append(get_ttk_wide_move(MOVE_OPPOSITES[letter], dist, N - layer))
        else:
            new_moves.append(get_ttk_wide_move(letter, dist, layer))
            if width == 1:
                new_moves.append(get_ttk_wide_move(letter, -dist, layer - 1))
    return new_moves

def add_to_response(moves: list[str], func: Callable, simple_string: str, response: list[dict]) -> None:
    """ Adds a string of moves, a description, and a simple_string of the cube to the websocket message. """
    response.append({
        "moves": " ".join(moves), 
        "desc": FUNCTION_TO_EXPLANATIONS[func],
        "simple_string": simple_string
    })

def add_pipeline_to_response(cube: Cube, response: list[dict], pipeline: SolvePipeline):
    """ Performs add_to_response for each function in a pipeline. """
    move_cube, move_function = cube, lambda x: x
    different_cube = pipeline is PIPELINE_2x2 or pipeline is PIPELINE_NxN_3x3_STAGE
    if different_cube:
        move_cube = cube.get_3x3()
        move_function = lambda x: convert_3x3_moves_to_NxN(x, cube.N)
        if cube.N == 2: 
            move_function = convert_3x3_moves_to_2x2 
    for func in getattr(pipeline, FUNCTION_LIST_ATTR):
        before_simple_string = cube.to_simple_string()
        moves = convert_moves_to_ttk(clean_moves(move_function(func(move_cube))), cube.N)
        if different_cube:
            cube.parse(" ".join(moves))
        add_to_response(moves, func, before_simple_string, response)
                    
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
                    try:
                        translator.translate(img)
                    except: 
                        pass
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
                        before_simple_string = cube.to_simple_string()
                        new_moves = orient_top_until_solve(cube)
                        add_to_response(new_moves, orient_top_until_solve, before_simple_string, response)
                    case 3:
                        add_pipeline_to_response(cube, response, PIPELINE_3x3)
                    case N:
                        add_pipeline_to_response(cube, response, PIPELINE_NxN)
                        add_pipeline_to_response(cube, response, PIPELINE_NxN_3x3_STAGE)
                        cube_3x3 = cube.get_3x3()
                        before_simple_string = cube.to_simple_string()
                        try:
                            add_to_response(convert_3x3_moves_to_NxN(
                                solve_pll_edges(cube_3x3), N
                            ), solve_pll_edges, before_simple_string, response)
                        except ParityException:
                            add_to_response(pll_parity(cube), pll_parity, before_simple_string, response)
                            before_simple_string = cube.to_simple_string()
                            add_to_response(convert_3x3_moves_to_NxN(
                                solve_pll_edges(cube_3x3), N
                            ), solve_pll_edges, before_simple_string, response)
                await websocket.send(json.dumps({
                    "type": "solve", "moves": response
                }))

async def main():
    async with websockets.serve(handler, "", 8090):
        await asyncio.Future()

if __name__ == "__main__":
    asyncio.run(main())
