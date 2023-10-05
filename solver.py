import time
import numpy as np
from cube import Cube, Cube3x3
from enums import Color, Face
from error import ImpossibleScrambleException
from utils import clean_moves, sexy_move_times

SIDE_FACES = [Face.FRONT, Face.LEFT, Face.BACK, Face.RIGHT]
SIDE_FACE_PAIRS = [*zip(SIDE_FACES[:4], SIDE_FACES[1:4] + SIDE_FACES[0:1])]

def orient_centers(cube: Cube3x3) -> list[str]:
    """ 
    Orients the centers with white on the bottom on green on the front 
    """
    assert cube.N == 3, "Can only orient centers on a 3x3"
    moves = []
    cube_matrix = cube.get_cube()
    for i in range(8):
        direction = 'R'
        if i >= 4:
            direction = 'F'
        if cube_matrix[Face.BOTTOM.value][1, 1] == Color.WHITE:
            break
        cube.turn(direction, 1, 2, 1, moves)
    return clean_moves(moves)

def solve_white_cross(cube: Cube3x3) -> list[str]:
    """
    Solves the cross for a cube, assuming centers are oriented.
    First, get all the white edges oriented correctly on the top face.
    Then, insert each edge into the correct place using 180 turns.
    """

    def all_edges_white(cube: Cube3x3, face: Face) -> bool:
        face_array = cube.get_cube()[face.value]
        return all([
            face_array[*indeces] == Color.WHITE for indeces
            in [(0, 1), (1, 0), (1, 2), (2, 1)]
        ])

    moves = []
    safety_counter = 0
    while not all_edges_white(cube, Face.TOP):
        safety_counter += 1
        if safety_counter > 100:
            raise ImpossibleScrambleException("Cube could not be solved.")

        top_front_edge = cube.get_edge_between(Face.FRONT, Face.TOP)
        while top_front_edge["f2c"][Face.TOP] == Color.WHITE:
            cube.turn("U", 1, 1, 1, moves)
            top_front_edge = cube.get_edge_between(Face.FRONT, Face.TOP)
        if top_front_edge["f2c"][Face.FRONT] == Color.WHITE:
            cube.parse("F U' R", output_movelist=moves)
        elif any((l:=[Color.WHITE in cube.get_edge_between(i, j)["c2f"] for i, j in SIDE_FACE_PAIRS])):
            loc = l.index(True)
            cube.turn("U", -loc, 2, 1, moves)
            if cube.get_edge_between(Face.FRONT, Face.LEFT)["f2c"][Face.FRONT] == Color.WHITE:
                cube.parse("2U' F'", output_movelist=moves)
            else:
                cube.turn('F', 1, 1, 1, moves)
        elif any((l:=[Color.WHITE in cube.get_edge_between(Face.BOTTOM, i)["c2f"] for i in SIDE_FACES])):
            loc = l.index(True)
            cube.turn("D", loc, 1, 1, moves)
            if cube.get_edge_between(Face.FRONT, Face.BOTTOM)["f2c"][Face.BOTTOM] == Color.WHITE:
                cube.turn("F", 2, 1, 1, moves)
            else:
                cube.parse("F' U' R", output_movelist=moves)

    while not all_edges_white(cube, Face.BOTTOM):
        safety_counter += 1 
        if safety_counter > 200:
            raise ImpossibleScrambleException("Cube could not be solved")
        top_front_edge = cube.get_edge_between(Face.FRONT, Face.TOP)
        while top_front_edge["f2c"][Face.TOP] != Color.WHITE:
            cube.turn("U", 1, 1, 1, moves)
            top_front_edge = cube.get_edge_between(Face.FRONT, Face.TOP)
        front_edge_color = top_front_edge["f2c"][Face.FRONT]
        while front_edge_color not in cube.get_center_at(Face.FRONT)["c2f"]:
            cube.turn("D", 1, 2, 2, moves)
        cube.turn("F", 2, 1, 1, moves)

    return clean_moves(moves)

def solve_first_layer_corners(cube: Cube3x3) -> list[str]:
    """
    Solves the corners for the first layer of the cube.
    Assumes the cross is already properly built.
    """
    def all_white_corners_solved(cube: Cube3x3) -> bool:
        """
        Determines if all the corners of the white face are solved.
        """
        for right, left in SIDE_FACE_PAIRS: 
            if not all(is_corner_solved(cube, left, right).values()):
                return False
        return True

    def is_corner_solved(cube: Cube3x3, a: Face, b: Face) -> dict[str, bool]:
        """
        Determines if a single corner is in a solved position.
        Returns a dictionary saying if:
            It's permuted correctly - in the right place
            It's oriented correctly - white is on bottom
        """
        corner = cube.get_corner_between(a, b, Face.BOTTOM)
        return {
            "permuted": (
                cube.get_edge_between(a, Face.BOTTOM)["f2c"][a] in corner["c2f"] and 
                cube.get_edge_between(b, Face.BOTTOM)["f2c"][b] in corner["c2f"] and 
                Color.WHITE in corner["c2f"]
            ),
            "oriented": (
                corner["f2c"][Face.BOTTOM] == Color.WHITE and 
                corner["f2c"][a] == cube.get_edge_between(a, Face.BOTTOM)["f2c"][a] and 
                corner["f2c"][b] == cube.get_edge_between(b, Face.BOTTOM)["f2c"][b]
            )
        }

    def is_corner_matched(cube: Cube3x3, faces: list[Face], colors: list[Color]) -> bool:
        """
        Determines if a given corner is composed of given colors
        """
        corner = cube.get_corner_between(*faces)
        return all([
            color in corner["c2f"] for color in colors
        ])

    moves = []
    while not all_white_corners_solved(cube):
        while all(is_corner_solved(cube, Face.FRONT, Face.RIGHT).values()):
            cube.turn("D", 1, 2, 2, moves)
        right_color = cube.get_edge_between(Face.RIGHT, Face.BOTTOM)["f2c"][Face.RIGHT]
        front_color = cube.get_edge_between(Face.FRONT, Face.BOTTOM)["f2c"][Face.FRONT] 
        if is_corner_solved(cube, Face.FRONT, Face.RIGHT)["permuted"]:
            match cube.get_corner_between(Face.FRONT, Face.RIGHT, Face.BOTTOM)["c2f"][Color.WHITE]:
                case Face.RIGHT: sexy_moves = 2
                case Face.FRONT: sexy_moves = 4
                case _: raise ImpossibleScrambleException("Cube could not be solved.")
            continue
        if any((l:=[
            is_corner_matched(cube, [Face.BOTTOM, a, b], [right_color, front_color, Color.WHITE])
            for a, b in SIDE_FACE_PAIRS
        ])):
            loc = l.index(True) + 1
            cube.turn('D', loc, 1, 1, moves)
            cube.parse(sexy_move_times(1), output_movelist=moves)
            cube.turn('D', -loc, 1, 1, moves)
        if any((l:=[
            is_corner_matched(cube, [Face.TOP, a, b], [right_color, front_color, Color.WHITE])
            for a, b in SIDE_FACE_PAIRS
        ])):
            loc = l.index(True) + 1
            cube.turn('U', -loc, 1, 1, moves)
            match cube.get_corner_between(Face.FRONT, Face.RIGHT, Face.TOP)["c2f"][Color.WHITE]:
                case Face.TOP: sexy_moves = 3
                case Face.FRONT: sexy_moves = 5
                case Face.RIGHT: sexy_moves = 1
                case _: raise ImpossibleScrambleException("Cube could not be solved.")
            cube.parse(sexy_move_times(sexy_moves), output_movelist=moves)
    
    return moves

if __name__ == "__main__":
    cube = Cube.from_commandline()
    assert isinstance(cube, Cube3x3)
    print(cube)
    print(orient_centers(cube))
    print(solve_white_cross(cube))
    print(solve_first_layer_corners(cube))
    print(cube)
