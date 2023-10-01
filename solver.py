from cube import Cube 
from enums import Color, Face
from error import ImpossibleScrambleException

def orient_centers(cube: Cube) -> list[tuple[int, int, int]]:
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
    while cube_matrix[Face.FRONT.value][1, 1] != Color.GREEN:
        cube.turn('U', 1, 2, 1, moves)
    return moves

def solve_cross(cube: Cube) -> list[tuple[int, int, int]]:
    """
    Solves the cross for a cube, assuming centers are oriented.
    """

if __name__ == "__main__":
    cube = Cube.from_commandline()
    print(orient_centers(cube))

