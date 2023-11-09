import sys
from typing import Literal
from time import perf_counter

import numpy as np

from pycubing.enums import Color, Face
from pycubing.cube import Cube, Cube3x3
from pycubing.utils import SolvePipeline

FLIPPER_ALG = "R U R' F R' F' R"

def solve_centers(cube: Cube) -> list[str]:
    """
    Uses commutators to solve every center in a big cube. 
    Huge perf bottleneck - O(n^2) time complexity.
    """
    reference_centers = Cube(side_length=1)
    ref_matrix = reference_centers.get_matrix()
    cube_matrix = cube.get_matrix()
    if cube.N % 2 == 1:
        for face in list(Face):
            ref_matrix[face.value][0, 0] = cube_matrix[face.value][cube.N // 2, cube.N // 2]

    # these moves allow for every center to be given a chance in the front
    moves = []
    solved_colors = set()
    for main_center_move in ['', 'y', 'y', 'y', 'x', 'x2']:
        cube.parse(main_center_move, output_movelist=moves)
        reference_centers.parse(main_center_move)
        target_color = ref_matrix[Face.FRONT.value][0, 0]
        for center_selector in range(5):

            # turn centers around to cycle in top
            if center_selector < 4:
                cube.turn('B', 1, cube.N - 1, cube.N - 1, moves)
                reference_centers.turn('B', 1, 1, 1)

            # assign chosen center and check if it's already solved
            chosen_center = Face.BACK if center_selector == 4 else Face.TOP
            if ref_matrix[chosen_center.value][0, 0] in solved_colors:
                continue

            for i in range(1, cube.N - 1):
                for j in range(1, cube.N - 1):
                    if cube_matrix[chosen_center.value][i, j] == target_color:
                
                        # assign starting values depending on face
                        x, y = j, i
                        adjust_layer = 'B' if chosen_center == Face.BACK else 'U'
                        adjust_dist = -1
                        slice_dist = 2 if chosen_center == Face.BACK else 1
                        if chosen_center == Face.BACK:
                            y, x = cube.N - 1 - y, cube.N - 1 - x

                        # turn until free spot
                        while cube_matrix[Face.FRONT.value][y, x] == target_color:
                            cube.turn('F', 1, 1, 1, moves)

                        # adjust for a special case
                        layer1, layer2 = x + 1, y + 1
                        if layer1 == layer2:
                            layer2 = cube.N + 1 - layer2
                            adjust_dist *= -1

                        # perform commutator
                        cube.turn('L', -slice_dist, layer1, 1, moves)
                        cube.turn(adjust_layer, adjust_dist, 1, 1, moves)
                        cube.turn('L', -slice_dist, layer2, 1, moves)
                        cube.turn(adjust_layer, -adjust_dist, 1, 1, moves)
                        cube.turn('L', slice_dist, layer1, 1, moves)
                        cube.turn(adjust_layer, adjust_dist, 1, 1, moves)
                        cube.turn('L', slice_dist, layer2, 1, moves)
                        cube.turn(adjust_layer, -adjust_dist, 1, 1, moves)

        solved_colors.add(target_color)
                        
    return moves

def solve_edges(cube: Cube) -> list[str]:
    """
    Solves the edges of any big cube.
    For the first 8, it solves it as any human would, collecting pieces for the edge, 
      and storing it on the top or bottom.
    Then, for the next 3, it solves it by inserting pieces into the edge through flippers.
    Finally, it does the parity algorithm if needed.
    I think this is O(n) unless I just suck at programming
    """

    def parse_both(cube: Cube, ref: Cube3x3, prompt: str, moves: list[str]) -> None:
        """ Turns both the cube and the reference """
        cube.parse(prompt, output_movelist=moves)
        ref.parse(prompt)

    def turn_flat_middle(cube: Cube, ref: Cube3x3, dist: int, moves: list[str]) -> None:
        cube.turn('U', dist, cube.N - 1, cube.N - 2, moves)
        ref.turn('U', dist, 2, 1)

    def is_main_edge_solved(cube: Cube, reference_edges: Cube3x3) -> bool:
        """ Determines if the edge between Front and Right is solved. """
        cube_matrix = cube.get_matrix()
        ref_matrix = reference_edges.get_matrix()
        return (
            np.unique(cube_matrix[Face.FRONT.value][1:-1, -1]).shape
            == np.unique(cube_matrix[Face.RIGHT.value][1:-1, 0]).shape
            == (1,) and 
            cube_matrix[Face.FRONT.value][1, -1] == ref_matrix[Face.FRONT.value][1, -1] and 
            cube_matrix[Face.RIGHT.value][1, 0] == ref_matrix[Face.RIGHT.value][1, 0]
        )

    def any_piece_in_main_edge(cube: Cube, colors: set[Color]) -> bool:
        """ Determines if they are any needed edge pieces """
        cube_matrix = cube.get_matrix()
        return any([
            {
                cube_matrix[Face.FRONT.value][i, -1], 
                cube_matrix[Face.RIGHT.value][i, 0]
            } == colors
            for i in range(1, cube.N-1)
        ])

    def any_piece_in_top_edge(cube: Cube, colors: set[Color]) -> bool:
        """ Determines if there are any needed edge pieces in the Front Top edge """
        cube_matrix = cube.get_matrix()
        return any([
            {
                cube_matrix[Face.FRONT.value][0, i],
                cube_matrix[Face.TOP.value][-1, i]
            } == colors
            for i in range(1, cube.N-1)
        ])
        
    def any_piece_in_bottom_edge(cube: Cube, colors: set[Color]) -> bool:
        """ Determines if there are any needed edge pieces in the Front Bottom edge """
        cube_matrix = cube.get_matrix()
        return any([
            {
                cube_matrix[Face.FRONT.value][-1, i],
                cube_matrix[Face.BOTTOM.value][-1, i]
            } == colors
            for i in range(1, cube.N-1)
        ])
    
    def get_oriented_pieces_in_main_edge(cube: Cube, front_color: Color, right_color: Color) -> list[int]:
        """ 
        Returns the well-oriented pieces in the main edge. 
        Ordered from top to bottom.
        """
        cube_matrix = cube.get_matrix()
        return [
            i + 1 for i in range(1, cube.N-1)
            if (cube_matrix[Face.FRONT.value][i, -1] == front_color and 
            cube_matrix[Face.RIGHT.value][i, 0] == right_color)
        ]

    def get_unoriented_pieces_in_main_edge(cube: Cube, front_color: Color, right_color: Color) -> list[int]:
        """ 
        Returns the well-oriented pieces in the main edge. 
        Ordered from top to bottom.
        """
        cube_matrix = cube.get_matrix()
        return [
            i + 1 for i in range(1, cube.N-1)
            if (cube_matrix[Face.FRONT.value][i, -1] == right_color and 
            cube_matrix[Face.RIGHT.value][i, 0] == front_color)
        ]
    
    def is_front_edge_solved(cube: Cube, ref: Cube3x3, border: Literal[Face.BOTTOM, Face.TOP]) -> bool:  
        """
        Determines if the Front Top or Bottom edge is in a solved state
        """
        cube_matrix = cube.get_matrix()
        ref_matrix = ref.get_matrix()
        front_index = 0 if border == Face.TOP else -1
        return len(set([
            (cube_matrix[Face.FRONT.value][front_index, i], cube_matrix[border.value][-1, i])
            for i in range(1, cube.N - 1)
        ])) == 1 and (
            cube_matrix[Face.FRONT.value][front_index, 1] == ref_matrix[Face.FRONT.value][front_index, 1] and
            cube_matrix[border.value][-1, 1] == ref_matrix[border.value][-1, 1]
        )

    def fix_unoriented_pieces(cube: Cube, reference_edges: Cube3x3, target_layers: list[int], moves: list[str]) -> None:
        """
        Fixes edges pieces that are oriented the wrong way
        """
        for layer in target_layers:
            cube.turn('U', 1, layer, 1, moves)
        parse_both(cube, reference_edges, FLIPPER_ALG, moves)
        for layer in target_layers:
            cube.turn('U', -1, layer, 1, moves)

    # generate edges to compare the cube to 
    reference_edges = Cube3x3()
    cube_matrix = cube.get_matrix()
    if cube.N % 2 == 1:
        ref_matrix = reference_edges.get_matrix()
        for face in list(Face):
            for edge in [(0, cube.N // 2), (cube.N // 2, 0), (cube.N // 2, -1), (-1, cube.N // 2)]:
                ref_matrix[face.value][*map(lambda x: min(x, 1), edge)] = cube_matrix[face.value][*edge]
     
    # solve for first 8 egdes
    moves = []
    fix_center_moves = [0] * (cube.N-2)
    for i in range(8):

        # set constants for dealing with thingys
        target_edge = reference_edges.get_edge_between(Face.FRONT, Face.RIGHT)
        front_color, right_color = target_edge["f2c"][Face.FRONT], target_edge["f2c"][Face.RIGHT]
        target_color_set = {front_color, right_color}
        adjust_face = Face.TOP if i < 4 else Face.BOTTOM
        sub_move = "R U' R'" if i < 4 else "R' D R" 
        search_move = "U" if i < 4 else "D"

        # take care of flipped edge pieces - should only occur once 
        if target_layers := get_unoriented_pieces_in_main_edge(cube, front_color, right_color):
            fix_unoriented_pieces(cube, reference_edges, target_layers, moves)
            right_color, front_color = front_color, right_color

        # take one edge and solve it
        while not is_main_edge_solved(cube, reference_edges):

            # keep turning to find empty slots to place things in
            oriented_layers = []
            unoriented_layers = []
            for _ in range(3):
                turn_flat_middle(cube, reference_edges, 1, moves)
                
                # insert a candidate on the top or bottom into the slot
                if not any_piece_in_main_edge(cube, target_color_set):
                    for _ in range(4):
                        parse_both(cube, reference_edges, 'U D', moves=moves)
                        if any_piece_in_top_edge(cube, target_color_set):
                            parse_both(cube, reference_edges, "R U' R'", moves=moves)
                            break
                        elif any_piece_in_bottom_edge(cube, target_color_set):
                            parse_both(cube, reference_edges, "R' D R", moves=moves)
                            break

                # determine which pieces are in the proper position
                oriented_layers.append(get_oriented_pieces_in_main_edge(cube, front_color, right_color))
                unoriented_layers.append(get_unoriented_pieces_in_main_edge(cube, front_color, right_color))

            # put the cube back to main edge
            turn_flat_middle(cube, reference_edges, 1, moves)
            
            # insert all possible edge pieces
            for slot in range(3):
                for layer in oriented_layers[slot]:
                    cube.turn('U', slot+1, layer, 1, moves)
            parse_both(cube, reference_edges, FLIPPER_ALG, moves)
            front_color, right_color = right_color, front_color
            for slot in range(3):
                for layer in unoriented_layers[slot]:
                    cube.turn('U', slot+1, layer, 1, moves)

            # get the centers back to normal 
            for slot in range(3):
                for layer in oriented_layers[slot] + unoriented_layers[slot]:
                    fix_center_moves[layer-2] -= slot + 1

        # turn top/bottom face until we can insert the solved edge
        for _ in range(4):
            parse_both(cube, reference_edges, search_move, moves)
            if not is_front_edge_solved(cube, reference_edges, adjust_face):
                parse_both(cube, reference_edges, sub_move, moves)

    # fix the centers ? 
    for layer in range(cube.N - 2):
        cube.turn('U', fix_center_moves[layer], layer + 2, 1, moves)

    # do the last four edges, somehow
    for _ in range(3):

        target_edge = reference_edges.get_edge_between(Face.FRONT, Face.RIGHT)
        front_color, right_color = target_edge["f2c"][Face.FRONT], target_edge["f2c"][Face.RIGHT]

        # take care of flipped edge pieces - should only occur once 
        if target_layers := get_unoriented_pieces_in_main_edge(cube, front_color, right_color):
            fix_unoriented_pieces(cube, reference_edges, target_layers, moves)
            right_color, front_color = front_color, right_color
    
        # perform loop twice to take care of top and bottom part of edge
        for _ in range(2):

            # check for top half of edge being solved
            while not all([
                cube_matrix[Face.FRONT.value][i, -1] == front_color and 
                cube_matrix[Face.RIGHT.value][i, 0] == right_color
                for i in range(1, cube.N // 2)
            ]):

                # find all the pieces we can insert
                unoriented_layers = [None] * 3
                for slot in range(3):
                    turn_flat_middle(cube, reference_edges, 1, moves)
                    unoriented_layers[slot] = get_unoriented_pieces_in_main_edge(cube, front_color, right_color)
                turn_flat_middle(cube, reference_edges, 1, moves)

                # fill the edges from each other piece into the main one
                for slot in range(3):
                    top_unoriented = [*filter(lambda x: x > cube.N // 2, unoriented_layers[slot])]
                    for layer in top_unoriented:
                        cube.turn('U', -slot-1, cube.N+1 - layer, 1, moves)
                    turn_flat_middle(cube, reference_edges, slot+1, moves)
                    parse_both(cube, reference_edges, FLIPPER_ALG, moves)
                    turn_flat_middle(cube, reference_edges, -slot-1, moves)
                    for layer in top_unoriented:
                        cube.turn('U', slot+1, cube.N+1 - layer, 1, moves)

            # flip the main edge to move on to the other half 
            parse_both(cube, reference_edges, FLIPPER_ALG, moves)
            right_color, front_color = front_color, right_color

        # cycle edge somewhere else
        turn_flat_middle(cube, reference_edges, 1, moves)

    # solve parity in the last edge
    target_edge = reference_edges.get_edge_between(Face.FRONT, Face.RIGHT)
    front_color, right_color = target_edge["f2c"][Face.FRONT], target_edge["f2c"][Face.RIGHT]
    parity_edges = get_unoriented_pieces_in_main_edge(cube, front_color, right_color)
    num_parity_edges = len(parity_edges) // 2
    parse_both(cube, reference_edges, "F'", moves)

    # declare some helper functions just for parity
    def turn_layers(cube: Cube, layers: list[int], side: str, dist: int, moves: list[str]) -> None:
        for layer in layers:
            cube.turn(side, dist, layer, 1, moves)

    # parity algorithm
    turn_layers(cube, parity_edges[num_parity_edges:], "L", -1, moves)
    parse_both(cube, reference_edges, "U2 x", moves)
    for dist in [-1, -1, 1]:
        turn_layers(cube, parity_edges[num_parity_edges:], "L", dist, moves)
        parse_both(cube, reference_edges, "U2", moves)
    turn_layers(cube, parity_edges[:num_parity_edges], "L", 1, moves)
    parse_both(cube, reference_edges, "U2", moves)
    for layer in range(2, cube.N):
        if layer not in parity_edges[:num_parity_edges]:
            cube.turn("L", 1, layer, 1, moves)
    parse_both(cube, reference_edges, "U2", moves)
    reference_edges.turn("L", 1, 2, 1)
    for dist in [-1, 1, 1]:
        turn_layers(cube, parity_edges[num_parity_edges:], "L", dist, moves)
        parse_both(cube, reference_edges, "U2", moves)

    return moves

PIPELINE_NxN = SolvePipeline(
    solve_centers,
    solve_edges
)

if __name__ == "__main__":
    cube = Cube.parse_args()
    print(cube)
    start = perf_counter()
    moves = solve_centers(cube)
    end = perf_counter()
    if '-p' in sys.argv or '--print-scramble' in sys.argv:
        print(moves)
    print(cube)
    print(f"Time: {end - start :.2f}")
    start = perf_counter()
    moves = solve_edges(cube)
    end = perf_counter()
    if '-p' in sys.argv or '--print-scramble' in sys.argv:
        print(moves)
    print(cube)
    print(f"Time: {end - start :.2f}")
