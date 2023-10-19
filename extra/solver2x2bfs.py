"""
Uses a two-way BFS to generate solutions for a 2x2 cube.
A different way than solving any other cube, because I 
feel like trying to implement it.

The god's number for a 2x2 is 14, so I need to build 
two BFS trees, one before solve, one after, that sum
to 14 in complexity.
"""

import pickle
import argparse
import numpy as np
from copy import copy

from pycubing.cube import Cube
from pycubing.enums import Face
from pycubing.utils import reverse_moves, clean_moves

POSSIBLE_MOVES = [
    "R", "R'", "D'", "D", "B", "B'"
]

def standardize_simple_string(simple_string: str) -> str:
    """
    Rearranges "simple strings" of a cube into a more consistent format.
    This is done in order to detect cases where the cube is the same but rotated.
    Ignoring illegal cases, this is guaranteed to cause no collisions.
    """
    cube = Cube.from_simple_string(simple_string)
    ref_cube = Cube(2)
    cube.parse(" ".join(cube.get_rotation_to(ref_cube)))
    return cube.to_simple_string()
    
def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("-g", "--generate-tree-depth", help="generate a new tree with given depth", type=int, required=False)
    return parser.parse_known_args()[0]

def generate_base_tree(depth: int) -> None:
    paths = {Cube(2).to_simple_string(): []}
    q = [([*paths][0], [])] 
    while q:
        current_scramble, moves = q.pop()
        if len(moves) == depth:
            continue
        for move in POSSIBLE_MOVES:
            new_cube = Cube.from_simple_string(current_scramble)
            new_moves = copy(moves)
            new_cube.parse(move, output_movelist=new_moves)
            new_cube_string = new_cube.to_simple_string()
            paths[new_cube_string] = new_moves
            q.append((new_cube_string, new_moves))

    with open('2x2_path_tree.pkl', 'wb') as f:
        pickle.dump(paths, f)

def solve_tree(cube: Cube) -> list[str]:
    
    with open('2x2_path_tree.pkl', 'rb') as f:
        tree = pickle.load(f)
    
    q = [(cube.to_simple_string(), [])]
    while True:
        current_scramble, moves = q.pop()
        for move in POSSIBLE_MOVES:
            new_cube = Cube.from_simple_string(current_scramble)
            new_moves = copy(moves)
            new_cube.parse(move, output_movelist=new_moves)
            new_cube_string = new_cube.to_simple_string()

            if sol := tree.get(standardize_simple_string(new_cube_string)):
                return new_moves + new_cube.get_rotation_to(Cube(2)) + reverse_moves(sol)
            q.append((new_cube_string, new_moves))

if __name__ == "__main__":
    args = parse_args()
    if args.generate_tree_depth is not None:
        generate_base_tree(args.generate_tree_depth)
    else:
        cube = Cube.parse_args()
        cube_matrix = cube.get_matrix()
        assert cube.N == 2, "Method only works with 2x2 cubes"
        print(cube)
        if not all([np.unique(cube_matrix[face.value]).shape == (1,) for face in list(Face)]):
            print(clean_moves(solve_tree(cube)))
