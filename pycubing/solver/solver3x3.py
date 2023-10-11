import numpy as np

from pycubing.enums import Color, Face
from pycubing.cube import Cube, Cube3x3
from pycubing.error import ImpossibleScrambleException
from pycubing.utils import sexy_move_times, SolvePipeline

__doc__ = """
Functions for solving a 3x3. Each function works in order,
building off the results of the previous one. It will not 
work if you call functions in a different order, or if you
exclude certain functions for a specific solving case.
"""

SIDE_FACES = [Face.FRONT, Face.LEFT, Face.BACK, Face.RIGHT]
SIDE_FACE_PAIRS = [*zip(SIDE_FACES[:4], SIDE_FACES[1:4] + SIDE_FACES[0:1])]

def orient_centers(cube: Cube3x3) -> list[str]:
    """ 
    Orients the centers with white on the bottom on green on the front.
    Strategy:
        - Rotate the middle layer until white is on the bottom.
        - If unsuccessful, rotate the middle layer behind the front.
    """
    moves = []
    cube_matrix = cube.get_matrix()
    for i in range(8):
        direction = 'R'
        if i >= 4:
            direction = 'F'
        if cube_matrix[Face.BOTTOM.value][1, 1] == Color.WHITE:
            break
        cube.turn(direction, 1, 2, 1, moves)
    return moves

def solve_white_cross(cube: Cube3x3) -> list[str]:
    """
    Solves the cross for a cube, assuming centers are oriented.
    Strategy:
        - First, get all the white edges oriented correctly on the top face.
        - Then, insert each edge into the correct place using 180 turns.
    """

    def all_edges_white(cube: Cube3x3, face: Face) -> bool:
        face_array = cube.get_matrix()[face.value]
        return all([
            face_array[*indeces] == Color.WHITE for indeces
            in [(0, 1), (1, 0), (1, 2), (2, 1)]
        ])

    moves = []
    while not all_edges_white(cube, Face.TOP):

        # edge we are dealing with: top-front
        top_front_edge = cube.get_edge_between(Face.FRONT, Face.TOP)
        
        # rotate the top until dealing with an improper edge
        while top_front_edge["f2c"][Face.TOP] == Color.WHITE:
            cube.turn("U", 1, 1, 1, moves)
            top_front_edge = cube.get_edge_between(Face.FRONT, Face.TOP)

        # check if edge is there but oriented wrong, if so, flip it   
        if top_front_edge["f2c"][Face.FRONT] == Color.WHITE:
            cube.parse("F U' R", output_movelist=moves)

        # check if any white edge is in the second layer, if so, move and add it
        elif any((l:=[Color.WHITE in cube.get_edge_between(i, j)["c2f"] for i, j in SIDE_FACE_PAIRS])):
            loc = l.index(True)
            cube.turn("U", -loc, 2, 1, moves)
            if cube.get_edge_between(Face.FRONT, Face.LEFT)["f2c"][Face.FRONT] == Color.WHITE:
                cube.parse("2U' F'", output_movelist=moves)
            else:
                cube.turn('F', 1, 1, 1, moves)

        # check if any white edge is on the bottom, add depending on orientation
        elif any((l:=[Color.WHITE in cube.get_edge_between(Face.BOTTOM, i)["c2f"] for i in SIDE_FACES])):
            loc = l.index(True)
            cube.turn("D", loc, 1, 1, moves)
            if cube.get_edge_between(Face.FRONT, Face.BOTTOM)["f2c"][Face.BOTTOM] == Color.WHITE:
                cube.turn("F", 2, 1, 1, moves)
            else:
                cube.parse("F' U' R", output_movelist=moves)

    while not all_edges_white(cube, Face.BOTTOM):

        # get edge we are working with and turn the top until we get to a white edge
        top_front_edge = cube.get_edge_between(Face.FRONT, Face.TOP)
        while top_front_edge["f2c"][Face.TOP] != Color.WHITE:
            cube.turn("U", 1, 1, 1, moves)
            top_front_edge = cube.get_edge_between(Face.FRONT, Face.TOP)

        # turn the bottom two layers until the center is the same color as the edge, then insert edge
        front_edge_color = top_front_edge["f2c"][Face.FRONT]
        while front_edge_color not in cube.get_center_at(Face.FRONT)["c2f"]:
            cube.turn("D", 1, 2, 2, moves)
        cube.turn("F", 2, 1, 1, moves)

    return moves

def solve_first_layer_corners(cube: Cube3x3) -> list[str]:
    """
    Solves the corners for the first layer of the cube.
    Assumes the cross is already properly built.
    Strategy:
        - Work with the corner on the front, bottom, right of the cube.
        - If solved, move on.
        - If in right place and oriented wrong, orient it.
        - If in bottom layer elsewhere, extract it from the bottom to top.
        - If in top, insert into correct spot.
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
                cube.get_center_at(a)["f2c"][a] in corner["c2f"] and 
                cube.get_center_at(b)["f2c"][b] in corner["c2f"] and 
                Color.WHITE in corner["c2f"]
            ),
            "oriented": (
                corner["f2c"][Face.BOTTOM] == Color.WHITE and 
                corner["f2c"][a] == cube.get_center_at(a)["f2c"][a] and 
                corner["f2c"][b] == cube.get_center_at(b)["f2c"][b]
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

        # rotate bottom two layers until working with unsolved corner
        while all(is_corner_solved(cube, Face.FRONT, Face.RIGHT).values()):
            cube.turn("D", 1, 2, 2, moves)

        right_color = cube.get_center_at(Face.RIGHT)["f2c"][Face.RIGHT]
        front_color = cube.get_center_at(Face.FRONT)["f2c"][Face.FRONT] 
        
        # see if the corner is in the right place and oriented wrong
        if is_corner_solved(cube, Face.FRONT, Face.RIGHT)["permuted"]:
            match cube.get_corner_between(Face.FRONT, Face.RIGHT, Face.BOTTOM)["c2f"][Color.WHITE]:
                case Face.RIGHT: sexy_moves = 2
                case Face.FRONT: sexy_moves = 4
                case _: raise ImpossibleScrambleException("Cube could not be solved.")
            cube.parse(sexy_move_times(sexy_moves), output_movelist=moves)
            continue

        # see if the target corner is elsewhere in the bottom layer of the cube, if so, remove to top layer
        if any((l:=[
            is_corner_matched(cube, [Face.BOTTOM, a, b], [right_color, front_color, Color.WHITE])
            for a, b in SIDE_FACE_PAIRS
        ])):
            loc = l.index(True) + 1
            cube.turn('D', loc, 1, 1, moves)
            cube.parse(sexy_move_times(1), output_movelist=moves)
            cube.turn('D', -loc, 1, 1, moves)

        # see if the target corner is in the top layer, if so, insert it
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

def solve_second_layer_edges(cube: Cube3x3) -> list[str]:
    """
    Completes F2L by solving the edges of the cube.
    Assumes the first layer is already solved.
    """
    def is_f2l_solved(cube: Cube3x3) -> bool:
        """
        Determines if the first two layers are solved.
        """
        return all([
            is_edge_solved(cube, *pair)
            for pair in SIDE_FACE_PAIRS
        ])

    def is_edge_solved(cube: Cube3x3, a: Face, b: Face) -> bool:
        """
        Determines if a single f2l edge is solved.
        """
        edge_f2c = cube.get_edge_between(a, b)["f2c"]
        return (
            edge_f2c[a] == cube.get_center_at(a)["f2c"][a] and 
            edge_f2c[b] == cube.get_center_at(b)["f2c"][b]
        ) 

    def is_edge_matched(cube: Cube3x3, faces: list[Face]) -> bool:
        """
        Determines if a given edge is composed of colors 
        that are in the front and right centers.
        """
        edge = cube.get_edge_between(*faces)
        return all([
            color in edge["c2f"] for color in [
                cube.get_center_at(Face.RIGHT)["f2c"][Face.RIGHT],
                cube.get_center_at(Face.FRONT)["f2c"][Face.FRONT]
            ]
        ])

    moves = []
    EDGE_INSERT = sexy_move_times(1) + " y " + sexy_move_times(1, left_hand=True) + "y' "
    while not is_f2l_solved(cube):
        
        # rotate bottom two until unsolved edge is front-right
        while is_edge_solved(cube, Face.FRONT, Face.RIGHT):
            cube.turn('D', 1, 2, 2, moves)

        # detect if the edge is in the right place but oriented wrong
        if is_edge_matched(cube, [Face.FRONT, Face.RIGHT]):
            cube.parse(EDGE_INSERT + "U2 " + EDGE_INSERT, output_movelist=moves)

        # detect if the edge is elsewhere in the second layer, if so, spit it out 
        if any((l:=[
            is_edge_matched(cube, [*pair])
            for pair in SIDE_FACE_PAIRS
        ])):
            loc = l.index(True) + 1 
            cube.turn("D", loc, 2, 2, moves)
            cube.parse(EDGE_INSERT, output_movelist=moves)
            cube.turn("D", -loc, 2, 2, moves)

        # detect if the edge is in the top layer 
        if any((l:=[
            is_edge_matched(cube, [face, Face.TOP])
            for face in SIDE_FACES
        ])):
            loc = l.index(True) 
            cube.turn("U", -loc, 1, 1, moves)
            if (
                cube.get_edge_between(Face.TOP, Face.FRONT)["f2c"][Face.TOP] 
                == cube.get_center_at(Face.FRONT)["f2c"][Face.FRONT]
            ):
                left_edge_insert = "y " + sexy_move_times(1, left_hand=True) + "y' " + sexy_move_times(1)
                cube.parse("U2 " + left_edge_insert, output_movelist=moves)
            else:
                cube.parse("U " + EDGE_INSERT, output_movelist=moves)

    return moves

def solve_oll_edges(cube: Cube3x3) -> list[str]:
    """
    Orients the last layer edges, throws an exception if a parity is detected.
    """

    # calculate number of edges properly aligned
    moves = []
    match sum([
        cube.get_edge_between(face, Face.TOP)["f2c"][Face.TOP] == Color.YELLOW
        for face in SIDE_FACES
    ]):
        case 1 | 3:
           raise ImpossibleScrambleException("Parity detected. Fix one of the edges to continue.")
        case 4:
            return []
        case 2:            
            # detect for line case or L case, orient them correctly for solving 
            s = sum([
                face.value for face in SIDE_FACES
                if cube.get_edge_between(face, Face.TOP)["f2c"][Face.TOP] == Color.YELLOW
            ])
            layers = 1 + (s % 2 != 0)
            match s:
                case 1: 
                    cube.turn("U", -1, 1, 1, moves)
                case 2 | 5:
                    cube.turn("U", 1, 1, 1, moves)
                case 3:
                    if not cube.get_edge_between(Face.TOP, Face.FRONT)["f2c"][Face.TOP] == Color.YELLOW:
                        cube.turn("U", 2, 1, 1, moves)
            cube.turn('F', 1, layers, layers, moves)
            cube.parse(sexy_move_times(1), output_movelist=moves)
            cube.turn('F', -1, layers, layers, moves)
        case 0:
            cube.turn('F', 1, 1, 1, moves)
            cube.parse(sexy_move_times(1), output_movelist=moves)
            cube.turn('F', 1, 2, 1, moves)
            cube.parse(sexy_move_times(1), output_movelist=moves)
            cube.turn('F', -1, 2, 2, moves)

    return moves

def solve_oll_corners(cube: Cube3x3) -> list[str]:
    """
    Orients the last layer corners.
    """

    def is_oll_solved(cube: Cube3x3, face: Face) -> bool:
        """
        Determines if the last layer corners are oriented correctly.
        """
        return len({
            cube.get_corner_between(*pair, face)["f2c"][face]
            for pair in SIDE_FACE_PAIRS
        }) == 1

    moves = []
    cube.parse('x2', output_movelist=moves)
    while not is_oll_solved(cube, Face.BOTTOM):
        match cube.get_corner_between(Face.RIGHT, Face.FRONT, Face.BOTTOM)["c2f"][Color.YELLOW]:
            case Face.BOTTOM: sexy_moves = 0
            case Face.FRONT: sexy_moves = 4
            case Face.RIGHT: sexy_moves = 2 
            case _: raise ImpossibleScrambleException("Cube could not be solved.")
        cube.parse(sexy_move_times(sexy_moves), output_movelist=moves)
        cube.turn("D", 1, 1, 1, moves)    
    cube.parse('x2', output_movelist=moves)
    return moves

def solve_pll_corners(cube: Cube3x3) -> list[str]:
    """
    Permutes the last layer corners.
    """
    T_PERM = " R U R' U' R' F R2 U' R' U' R U R' F' "

    def arr_diff(arr: np.ndarray[Face]) -> int:
        """
        Returns the difference of an array with shape (2,)
        """
        return abs(arr[1].value - arr[0].value)

    moves = []
    cube_matrix = cube.get_matrix()
    edge_diff_1 = arr_diff(cube_matrix[Face.FRONT.value][0, (0, 2)])
    edge_diff_2 = arr_diff(cube_matrix[Face.BACK.value][0, (0, 2)])

    # check for diagonal corner swap or none
    if edge_diff_1 == edge_diff_2 == 0:
        return []
    elif edge_diff_1 == edge_diff_2 == 2: 
        cube.parse(T_PERM + "y2" + T_PERM, output_movelist=moves)
        return moves  
    
    # different rotations of one-corner swap
    if edge_diff_1 % 4 == 2:
        cube.turn("U", -1, 1, 1, moves)
    elif edge_diff_2 % 4 == 2: 
        cube.turn("U", 1, 1, 1, moves)
    elif arr_diff(cube_matrix[Face.LEFT.value][0, (0, 2)]) == 2:
        cube.turn("U", 2, 1, 1, moves)
    cube.parse(T_PERM, output_movelist=moves)
    return moves

def solve_pll_edges(cube: Cube3x3) -> list[str]:
    """
    Permutes the last layer edges, solving the cube.
    """

    moves = []
    cube_matrix = cube.get_matrix()
    edge_swap = (sexy_move_times(1) + sexy_move_times(1, left_hand=True)
              + sexy_move_times(-1) + sexy_move_times(-1, left_hand=True))
    
    for _ in range(2):
        match sum((l:=[
            cube_matrix[face.value][0, 1] != cube_matrix[face.value][0, 0]
            for face in SIDE_FACES
        ])):
            case 0: pass
            case 2: raise ImpossibleScrambleException("Edge parity detected. Fix it and try again.")
            case 4: cube.parse(edge_swap, output_movelist=moves)
            case 3: 
                loc = l.index(False)
                cube.turn("U", -loc, 1, 1, moves)
                if (
                    cube_matrix[Face.LEFT.value][0, 1].value 
                  - cube_matrix[Face.LEFT.value][0, 0].value 
                ) % 4 == 2:
                    cube.parse(edge_swap, output_movelist=moves)
                else:
                    cube.parse(edge_swap * 2, output_movelist=moves)

    while np.unique(cube_matrix[Face.FRONT.value]).shape != (1,):
        cube.turn("U", 1, 1, 1, moves)

    return moves

PIPELINE_3x3 = SolvePipeline(
    orient_centers,
    solve_white_cross,
    solve_first_layer_corners,
    solve_second_layer_edges,
    solve_oll_edges,
    solve_oll_corners,
    solve_pll_corners,
    solve_pll_edges,
)

if __name__ == "__main__":
    PIPELINE_3x3.set_debug(True)
    cube = Cube.parse_args()
    assert isinstance(cube, Cube3x3)
    print(cube)
    moves = PIPELINE_3x3(cube)
    print(moves)
