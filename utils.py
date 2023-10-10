from __future__ import annotations

import re
from typing import Callable, TYPE_CHECKING

if TYPE_CHECKING:
    from cube import Cube

from error import InvalidTurnException

class SolvePipeline:
    def __init__(self, *funcs: Callable[[Cube], list[str]], debug: bool = False):
        self.__funcs = funcs
        self.__debug = debug
    def __call__(self, cube: Cube):
        moves = []
        for func in self.__funcs:
            moves += func(cube)
            if self.__debug:
                print(f"{func.__name__}: ")
                print(cube)
        return clean_moves(moves)

def get_move(side: str, dist: int, layer: int = 1, width: int = 1) -> list[str]:

    dist %= 4
    if dist == 0:
        return []

    layer_str = '' if layer == 1 else str(layer)
    dist_str = '2' if dist == 2 else "'" if dist == 3 else ''
    output_str = f"{{}}{side}{{}}{{}}"
    
    if width == 1:
        return [output_str.format(layer_str, '', dist_str)]
    elif layer == width:
        return [output_str.format(layer_str, 'w', dist_str)]
    elif width < layer:
        opposite_dist_str = '2' if dist == 2 else "'" if dist == 1 else ''
        return [
            output_str.format(layer_str, 'w', dist_str),
            output_str.format(
                str(layer-width) if layer-width != 1 else '',
                'w' if layer-width != 1 else '', opposite_dist_str
            )
        ]
    else:
        raise InvalidTurnException("Cannot turn wider than the given layer")

def get_root_move(move: str) -> str:
    """
    Gets the "root move" from a given move
    It shouldn't ever be None if it works
    """
    return re.match(r"([1-9][0-9]*)?[rubfldRUBFLD]w?", move).group()

def get_dist(move: str) -> int:
    """
    Returns the clockwise distance of a move
    """
    return 3 if move[-1] == "'" else 2 if move[-1] == '2' else 1

def get_final_move(move: str, dist: int) -> str:
    """
    Gets the final representation of the move given root and distance
    """
    addon = ['', '', '2', "'"][dist % 4]
    return f"{move}{addon}"

def clean_moves(moves: list[str]) -> list[str]:
    """
    Replaces groups of moves (2, 3, 4) with the appropriate move.
    >>> clean_moves(['R', 'R', 'R'])
    ["R'"]
    >>> clean_moves(['Rw', 'Rw'])
    ['Rw2']
    >>> clean_moves(['3F', '3F', '3F', '3F'])
    []
    """

    new_moves = []
    prev_root = None
    prev_move_dist = 0
    for move in moves:
        root = get_root_move(move)
        if root == prev_root:
            prev_move_dist += get_dist(move)
        else:
            if prev_root is not None and prev_move_dist % 4 != 0:
                new_moves.append(get_final_move(prev_root, prev_move_dist))
            prev_move_dist = get_dist(move)
            prev_root = root
    if prev_root is None:
        return []
    return [*new_moves, get_final_move(prev_root, prev_move_dist)]

def sexy_move_times(n: int, left_hand: bool = False) -> str:
    """
    Returns a string of moves repeating the "sexy move" n times.
    If left, returns left-handed movement.
    """
    n %= 6
    use_backwards = n > 3

    move_left = "L' U' L U "
    move_left_backwards = "U' L' U L "
    move_right = "R U R' U' "
    move_right_backwards = "U R U' R' "
 
    if not use_backwards:
        if left_hand: moves = move_left
        else: moves = move_right
    else:
        if left_hand: moves = move_left_backwards
        else: moves = move_right_backwards
    
    return f" {(moves * min(n, 6 - n)).strip()} "

def reverse_moves(moves: list[str]) -> list[str]:
    """
    Reverses a list of moves and outputs the moves to get 
    back to the original position.

    >>> reverse_moves(['R', 'U'])
    ["U'", "R'"]
    """

    return [
        get_final_move(get_root_move(move), -get_dist(move))
        for move in reversed(moves)
    ]

if __name__ == "__main__":
    print(get_move('L', -1, 5, 3))
