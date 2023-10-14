import sys
from time import perf_counter
from pycubing.cube import Cube
from pycubing.enums import Face

def solve_centers(cube: Cube) -> list[str]:
    """
    Uses commutators to solve every center in a big cube. 
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


if __name__ == "__main__":
    cube = Cube.parse_args()
    print(cube)
    start = perf_counter()
    moves = solve_centers(cube)
    end = perf_counter()
    if '-p' in sys.argv:
        print(moves)
    print(cube)
    print(f"Time: {end - start :.2f}")
    
