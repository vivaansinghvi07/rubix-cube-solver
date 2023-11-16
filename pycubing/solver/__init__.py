from copy import deepcopy

from pycubing.cube import Cube
from pycubing.solver.solver3x3 import PIPELINE_3x3
from pycubing.solver.solver2x2 import PIPELINE_2x2
from pycubing.solver.solverNxN import PIPELINE_NxN
from pycubing.utils import convert_3x3_moves_to_2x2, convert_3x3_moves_to_NxN

def solve(cube: Cube, mutate_original: bool = False) -> list[str]:
    if not mutate_original:
        cube = deepcopy(cube)
    match cube.N:
        case 1:
            return []
        case 2:
            cube_3x3 = cube.get_3x3()
            moves = convert_3x3_moves_to_2x2(PIPELINE_2x2(cube_3x3))
            if mutate_original:
                cube.parse(" ".join(moves))
            return moves
        case 3:
            return PIPELINE_3x3(cube)
        case _:
            moves_to_3x3 = PIPELINE_NxN(cube)
            cube_3x3 = cube.get_3x3()
            moves_to_solve = convert_3x3_moves_to_NxN(PIPELINE_3x3(cube_3x3), cube.N)
            if mutate_original:
                cube.parse(" ".join(moves_to_solve))
            return moves_to_3x3 + moves_to_solve
