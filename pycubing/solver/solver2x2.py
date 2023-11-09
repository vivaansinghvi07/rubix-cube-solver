import numpy as np

from pycubing.enums import Face
from pycubing.cube import Cube, Cube3x3
from pycubing.utils import SolvePipeline, clean_moves
from pycubing.solver.solver3x3 import orient_centers, solve_first_layer_corners, solve_oll_corners, solve_pll_corners

def cube2x2_from_3x3(cube: Cube3x3) -> Cube:
    output_cube = Cube(2)
    output_matrix = output_cube.get_matrix()
    cube_matrix = cube.get_matrix()
    for face in list(Face):
        for corner in [(0, 0), (0, -1), (-1, 0), (-1, -1)]:
            output_matrix[face.value][*corner] = cube_matrix[face.value][*corner]
    return output_cube

def orient_top_until_solve(cube: Cube) -> list[str]:
    moves = []
    while not np.unique(cube.get_matrix()[Face.FRONT.value]).shape == (1,):
        cube.turn('U', 1, 1, 1, moves)
    return clean_moves(moves)

PIPELINE_2x2 = SolvePipeline(
    orient_centers,
    solve_first_layer_corners,
    solve_oll_corners, 
    solve_pll_corners
)

if __name__ == "__main__":
    PIPELINE_2x2.set_debug(True)
    cube = Cube.parse_args()
    assert cube.N == 2
    print(cube)
    cube3x3 = cube.get_3x3()
    moves = PIPELINE_2x2(cube3x3)
    cube = cube2x2_from_3x3(cube3x3)
    moves += orient_top_until_solve(cube)
    print(moves)
    print(cube)