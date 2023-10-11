"""
Uses a two-way BFS to generate solutions for a 2x2 cube.
A different way than solving any other cube, because I 
feel like trying to implement it.

The god's number for a 2x2 is 14, so I need to build 
two BFS trees, one before solve, one after, that sum
to 14 in complexity.

Note: There is no way this will work, it takes way too 
long. It's better to use an adapted version of a 3x3 solver.
So this is not in the real module and is just an extra.
"""

import pickle
import argparse
from copy import copy

from cube import Cube
from utils import reverse_moves

POSSIBLE_MOVES = [
    "R", "R'", "L", "L'", "U", "U'",
    "F", "F'", "B", "B'", "D", "D'"
]

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("-g", "--generate-tree-depth", help="generate a new tree with given depth", type=int, required=False)
    parser.add_argument("-s", "--scramble", help="a 2x2 scramble to solve", type=str, required=False)
    return parser.parse_args()

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
            new_cube.turn(move[0], 1 if len(move) == 1 else -1, 1, 1, new_moves)
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
            new_cube.turn(move[0], 1 if len(move) == 1 else -1, 1, 1, new_moves)
            new_cube_string = new_cube.to_simple_string()

            if sol := tree.get(new_cube_string):
                return reverse_moves(sol) + new_moves
            q.append((new_cube_string, new_moves))

if __name__ == "__main__":
    args = parse_args()
    if args.generate_tree_depth is not None:
        generate_base_tree(args.generate_tree_depth)
    cube = Cube(2)
    cube.parse(args.scramble)
    print(solve_tree(cube))
