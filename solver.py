import time
import numpy as np
from cube import Cube, Cube3x3
from enums import Color, Face
from error import ImpossibleScrambleException
from utils import clean_moves

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

def solve_cross(cube: Cube3x3) -> list[str]:
    """
    Solves the cross for a cube, assuming centers are oriented.
    First, get all the white edges oriented correctly on the top face.
    Then, insert each edge into the correct place using 180 turns.
    """

    cube_matrix = cube.get_cube()
    side_faces = [Face.FRONT, Face.LEFT, Face.BACK, Face.RIGHT]
    side_face_pairs = [*zip(side_faces[:4], side_faces[1:4] + side_faces[0:1])]
    def all_edges_white(cube_matrix: list[np.ndarray], face: Face) -> bool:
        face_array = cube_matrix[face.value]
        return all([
            face_array[*indeces] == Color.WHITE for indeces
            in [(0, 1), (1, 0), (1, 2), (2, 1)]
        ])

    moves = []
    safety_counter = 0
    while not all_edges_white(cube_matrix, Face.TOP):
        safety_counter += 1
        if safety_counter > 100:
            raise ImpossibleScrambleException("Cube could not be solved.")

        top_front_edge = cube.get_edge_between(Face.FRONT, Face.TOP)
        while top_front_edge["f2c"][Face.TOP] == Color.WHITE:
            cube.turn("U", 1, 1, 1, moves)
            top_front_edge = cube.get_edge_between(Face.FRONT, Face.TOP)
        if top_front_edge["f2c"][Face.FRONT] == Color.WHITE:
            cube.parse("F U' R", output_movelist=moves)
        elif any((l:=[Color.WHITE in cube.get_edge_between(i, j)["c2f"] for i, j in side_face_pairs])):
            loc = l.index(True)
            cube.turn("U", -loc, 2, 1, moves)
            if cube.get_edge_between(Face.FRONT, Face.LEFT)["f2c"][Face.FRONT] == Color.WHITE:
                cube.parse("2U' F'", output_movelist=moves)
            else:
                cube.turn('F', 1, 1, 1, moves)
        elif any((l:=[Color.WHITE in cube.get_edge_between(Face.BOTTOM, i)["c2f"] for i in side_faces])):
            loc = l.index(True)
            cube.turn("D", loc, 1, 1, moves)
            if cube.get_edge_between(Face.FRONT, Face.BOTTOM)["f2c"][Face.BOTTOM] == Color.WHITE:
                cube.turn("F", 2, 1, 1, moves)
            else:
                cube.parse("F' U' R", output_movelist=moves)

    while not all_edges_white(cube_matrix, Face.BOTTOM):
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

if __name__ == "__main__":
    cube = Cube.from_commandline()
    assert isinstance(cube, Cube3x3)
    print(orient_centers(cube))
    print(solve_cross(cube))
    print(cube)
