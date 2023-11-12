from pycubing.cube import Cube
from pycubing.solver import solve 

if __name__ == "__main__":
    cube = Cube.parse_args()
    solve(cube, mutate_original=True)
