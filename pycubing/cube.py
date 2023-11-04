from __future__ import annotations
import re
import json
import random
import argparse
from math import sqrt
from pathlib import Path
from copy import deepcopy
from typing import Optional, Union

import numpy as np
from pynterface import Background

from pycubing.enums import Color, Face
from pycubing.utils import get_move, get_letter_dist_layer_width

class Cube():

    """
    Stores a cube as an array of shape (6, n, n),
    where 'n' is the side length of the cube.
    The four sides are represented in the order:
    green, orange, blue, and red, clockwise.
    Followed by white and yellow.
     
       0  1  2 
    0 [ ][ ][ ]
    1 [ ][ ][ ]
    2 [ ][ ][ ]
    
    Applies for each face on the side when placed on the bottom.
    Additionally applies for white, when viewed with green in front.
    For yellow, it is reversed, so that the y-indeces match white's

    0 3 6
    1 4 7
    2 5 8
    
    The documentation of the turns and other things will assume a 3x3 
    cube, with the above numbering scheme.
    """

    FACE_PAIRS = {
        'y': (Face.TOP, Face.BOTTOM),
        'z': (Face.FRONT, Face.BACK),
        'x': (Face.LEFT, Face.RIGHT)
    }

    COLOR_PAIRS = {
        'x': (Color.RED, Color.ORANGE),
        'z': (Color.BLUE, Color.GREEN),
        'y': (Color.WHITE, Color.YELLOW)
    }

    COLOR_TO_STRING = {
        Color.YELLOW: 'y',
        Color.GREEN: 'g',
        Color.RED: 'r',
        Color.BLUE: 'b',
        Color.WHITE: 'w',
        Color.ORANGE: 'o'
    }  

    STRING_TO_COLOR = {
        v: k for k, v in COLOR_TO_STRING.items()
    }

    @staticmethod
    def parse_args() -> Cube:
        parser = argparse.ArgumentParser()
        parser.add_argument("-n", "--side-length", help="the side length of the cube", type=int)
        parser.add_argument("-r", "--random-scramble", help="initialize the cube with a random scramble", action="store_true")
        parser.add_argument("-c", "--custom-scramble", help="initialize the cube with your own scramble", type=str)
        parser.add_argument("-p", "--print-scramble", help="print the scramble of the cube", action="store_true")
        args = parser.parse_args()
        
        if not args.side_length: 
            args.side_length = random.randint(2, 7)
        if args.side_length == 3:
            cube = Cube3x3()
        else:
            cube = Cube(side_length=args.side_length)

        if args.custom_scramble:
            cube.parse(args.custom_scramble)
        elif args.random_scramble:
            cube.scramble(args.print_scramble)

        return cube

    @staticmethod
    def from_simple_string(cube_string: str) -> Cube:
        """
        Returns the cube represented in the following format:

        "abcdefghijklmnopqrstuvwx"

            q r
            s t
        e f a b m n i j
        k l c d o p k l
            w x
            u v
        """

        assert not {*cube_string} - {*Cube.STRING_TO_COLOR.keys()}, "Invalid characters in string."
        N = sqrt(len(cube_string) / 6)
        assert N == (N := int(N)), "String of invalid length (must be N**2*6 where N is an int)"

        c = 0
        cube_matrix = [np.full((N, N), Color.WHITE) for _ in range(6)]
        for face in list(Face):
            for i in range(N):
                for j in range(N):
                    cube_matrix[face.value][i][j] = Cube.STRING_TO_COLOR[cube_string[c]]
                    c += 1

        if N == 3:
            return Cube3x3(scramble=cube_matrix)
        return Cube(side_length=N, scramble=cube_matrix)

    def __init__(self, side_length: int = 3, scramble: Optional[list[np.ndarray]] = None):
        if scramble is None:
            self._cube = [
                np.array([[c] * side_length for _ in range(side_length)])
                for c in list(Color)
            ]
        else: 
            self._cube = scramble
        self.N = side_length

    def __str__(self):

        def get_ansii(color: Color) -> str:
            color_name = str(color).split('.')[-1]
            match color_name:
                case "ORANGE":
                    return Background.RGB((255, 165, 0))
                case other: 
                    return eval(f"Background.{other}_BRIGHT")

        output = "\n "
        top_face = self._cube[Face.TOP.value]
        for i in range(self.N):
            output += '  ' * self.N
            for j in range(self.N):
                output += get_ansii(top_face[i, j]) + '  '
            output += f"{Background.RESET_BACKGROUND}\n "
            
        for i in range(self.N):
            for face in [Face.LEFT, Face.FRONT, Face.RIGHT, Face.BACK]:
                for j in range(self.N): 
                    output += get_ansii(self._cube[face.value][i][j]) + '  '
            output += f"{Background.RESET_BACKGROUND}\n "
        
        bottom_face = self._cube[Face.BOTTOM.value]
        for i in range(self.N - 1, -1, -1):
            output += '  ' * self.N
            for j in range(self.N):
                output += get_ansii(bottom_face[i, j]) + '  '
            output += f"{Background.RESET_BACKGROUND}\n "
        
        return output

    def to_simple_string(self) -> str:
        """
        Returns the cube represented as a string in the following format:

            q r
            s t
        e f a b m n i j
        g h c d o p k l
            w x
            u v

        "abcdefghijklmnopqrstuvwx"
        """

        output = ""
        for face in list(Face):
            for i in range(self.N):
                for j in range(self.N):
                    output += Cube.COLOR_TO_STRING[self._cube[face.value][i][j]]

        return output

    def scramble(self, print_scramble: bool = False):
        if 2 <= self.N <= 7:
            with open(f"{Path(__file__).parent}/scrambles.json", "r") as f:
                scrambles = json.load(f)
            scramble = random.choice(scrambles[str(self.N)])
            if print_scramble:
                print(scramble.split())
            self.parse(scramble)
        elif self.N > 7:
            moves = []
            for _ in range(self.N**2*2):
                dist = random.randint(1, 3)
                layer = random.randint(1, self.N)
                width = random.randint(1, layer)
                move = random.choice(['R', 'L', 'U', 'B', 'D', 'F'])
                moves.extend(get_move(move, dist, layer, width, self.N))
            self.parse(" ".join(moves))
            if print_scramble:
                print(moves)

    def get_matrix(self):
        """ Returns the mutable array of the cube """
        return self._cube

    def parse(self, moves: str, output_movelist: Optional[list[str]] = None):
        """
        Parses a list of moves given as a string with each move seperated by a space.
        The no_spaces argument can be passed to parse without considering spaces,
        but requires the cube to be 5x5x5 or less.
        """
        move_list = moves.split()
        for m in filter(lambda x: bool(x.strip()), move_list):
            letter, dist, layer, width = get_letter_dist_layer_width(m, self.N)
            self.turn(letter.upper(), dist, layer, width, output_movelist)
        
    def turn(self, move: str, dist: int, layer: int = 1, width: int = 1, movelist: Optional[list[str]] = None) -> None:
        """ Turns the cube depending on the given measure. """
        move_map = {
            'R': self.__turn_right,
            'L': self.__turn_left,
            'U': self.__turn_up,
            'D': self.__turn_down,
            'F': self.__turn_front,
            'B': self.__turn_back
        }
        move_map[move](dist, layer, width)
        if movelist is not None:
            movelist.extend(get_move(move, dist, layer, width, self.N))
        
    def __turn_right(self, dist: int, layer: int = 1, width: int = 1) -> None:
        """ 
        Turns the right side of the cube.
        Arguments:
            dist: number of clockwise turns
            layer: layer number from right side for the left-most layer 
            width: number of layers to turn, going right from the layer

         g  ->  w  ->  b  ->  y
        3 6    3 6    8 5    8 5 
        4 7 -> 4 7 -> 7 4 -> 7 4
        5 8    5 8    6 3    6 3
        """
        assert layer - width >= 0, "Invalid turn: Too wide given the layer"
        assert layer <= self.N, "Invalid turn: Turning more than entire cube" 
        dist %= 4
        if layer - width == 0:
            self.__rotate(Face.RIGHT, dist)
        if layer == self.N:
            self.__rotate(Face.LEFT, -dist)
        for _ in range(dist):
            front_top_back_down = [
                np.flip(self._cube[f.value][:, layer-width:layer].copy(), axis=1) 
                if f == Face.BACK else 
                self._cube[f.value][:, self.N-layer:self.N-layer+width].copy()
                for f in [Face.FRONT, Face.TOP, Face.BACK, Face.BOTTOM]
            ]
            for i, face in enumerate([Face.TOP, Face.BACK, Face.BOTTOM, Face.FRONT]):
                if i % 2:
                    front_top_back_down[i] = np.flip(front_top_back_down[i], axis=0)
                if face == Face.BACK:
                    self._cube[face.value][:, layer-width:layer] = np.flip(front_top_back_down[i], axis=1)
                else:
                    self._cube[face.value][:, self.N-layer:self.N-layer+width] = front_top_back_down[i]
    
    def __turn_left(self, dist: int, layer: int = 1, width: int = 1) -> None:
        """ 
        Turns the left side of the cube.
        Arguments:
            dist: number of clockwise turns
            layer: layer number from left side for the right-most layer 
            width: number of layers to turn, going left from the layer

         g  ->  y  ->  b  ->  w
        0 3    8 5    8 5    0 3 
        1 4 -> 7 4 -> 7 4 -> 1 4
        2 5    6 3    6 3    2 5
        """
        assert layer - width >= 0, "Invalid turn: Too wide given the layer"
        assert layer <= self.N, "Invalid turn: Turning more than entire cube" 
        dist %= 4
        if layer - width == 0:
            self.__rotate(Face.LEFT, dist)
        if layer == self.N:
            self.__rotate(Face.RIGHT, -dist)
        for _ in range(dist):
            front_top_back_down = [
                np.flip(self._cube[f.value][:, self.N-layer:self.N-layer+width].copy(), axis=1) 
                if f == Face.BACK else 
                self._cube[f.value][:, layer-width:layer].copy()
                for f in [Face.FRONT, Face.TOP, Face.BACK, Face.BOTTOM]
            ]
            for i, face in enumerate([Face.BOTTOM, Face.FRONT, Face.TOP, Face.BACK]):
                if i % 2 == 0:
                    front_top_back_down[i] = np.flip(front_top_back_down[i], axis=0)
                if face == Face.BACK:
                    self._cube[face.value][:, self.N-layer:self.N-layer+width] = np.flip(front_top_back_down[i], axis=1)
                else:
                    self._cube[face.value][:, layer-width:layer] = front_top_back_down[i]

    def __turn_up(self, dist: int, layer: int = 1, width: int = 1) -> None:
        """ 
        Turns the top side of the cube.
        Arguments:
            dist: number of clockwise turns
            layer: layer number from top side for the bottom-most layer 
            width: number of layers to turn, going up from the layer

          g   ->   r   ->   b   ->   o
        0 1 2    0 1 2    0 1 2    0 1 2
        3 4 5 -> 3 4 5 -> 3 4 5 -> 3 4 5 
        """
        assert layer - width >= 0, "Invalid turn: Too wide given the layer"
        assert layer <= self.N, "Invalid turn: Turning more than entire cube" 
        dist %= 4
        if layer - width == 0: 
            self.__rotate(Face.TOP, dist)
        if layer == self.N:
            self.__rotate(Face.BOTTOM, dist)
        for _ in range(dist):
            front_right_back_left = [
                self._cube[f.value][layer-width:layer, :].copy()
                for f in [Face.FRONT, Face.LEFT, Face.BACK, Face.RIGHT]
            ]
            for i, face in enumerate([Face.LEFT, Face.BACK, Face.RIGHT, Face.FRONT]):
                self._cube[face.value][layer-width:layer, :] = front_right_back_left[i]

    def __turn_down(self, dist: int, layer: int = 1, width: int = 1) -> None:
        """ 
        Turns the bottom side of the cube.
        Arguments:
            dist: number of clockwise turns
            layer: layer number from bottom side for the top-most layer 
            width: number of layers to turn, going down from the layer

          g   ->   r   ->   b   ->   o
        3 4 5    3 4 5    3 4 5    3 4 5
        6 7 8 -> 6 7 8 -> 6 7 8 -> 6 7 8 
        """
        assert layer - width >= 0, "Invalid turn: Too wide given the layer"
        assert layer <= self.N, "Invalid turn: Turning more than entire cube" 
        dist %= 4
        if layer - width == 0:
            self.__rotate(Face.BOTTOM, -dist)
        if layer == self.N:
            self.__rotate(Face.TOP, -dist)
        for _ in range(dist):
            front_right_back_left = [
                self._cube[f.value][self.N-layer:self.N-layer+width, :].copy()
                for f in [Face.FRONT, Face.LEFT, Face.BACK, Face.RIGHT]
            ]
            for i, face in enumerate([Face.RIGHT, Face.FRONT, Face.LEFT, Face.BACK]):
                self._cube[face.value][self.N-layer:self.N-layer+width, :] = front_right_back_left[i]

    def __turn_front(self, dist: int, layer: int = 1, width: int = 1):
        """ 
        Turns the front side of the cube 
        Arguments:
            dist: number of clockwise turns
            layer: layer number from bottom side for the top-most layer 
            width: number of layers to turn, going down from the layer
        
          w  ->  r  ->  y  ->  o
         2 1    0 3    2 1    5 8
         5 4 -> 1 4 -> 5 4 -> 4 7
         8 7    2 5    8 7    3 6
        """
        assert layer - width >= 0, "Invalid turn: Too wide given the layer"
        assert layer <= self.N, "Invalid turn: Turning more than entire cube" 
        dist %= 4
        if layer - width == 0:
            self.__rotate(Face.FRONT, dist)
        if layer == self.N:
            self.__rotate(Face.BACK, -dist)
        for _ in range(dist):
            top_right_bottom_left = [
                np.transpose(
                    np.flip(self._cube[f.value][:, layer-width:layer].copy(), axis=1)
                        if f == Face.RIGHT else 
                        self._cube[f.value][:, self.N-layer:self.N-layer+width].copy()
                        if f == Face.LEFT else 
                        self._cube[f.value][self.N-layer:self.N-layer+width, :].copy(),
                    (1, 0)
                )
                for f in [Face.TOP, Face.RIGHT, Face.BOTTOM, Face.LEFT]
            ]
            for i, face in enumerate([Face.RIGHT, Face.BOTTOM, Face.LEFT, Face.TOP]):
                if face == Face.RIGHT:
                    self._cube[face.value][:, layer-width:layer] = np.flip(top_right_bottom_left[i], axis=1)
                elif face == Face.LEFT:
                    self._cube[face.value][:, self.N-layer:self.N-layer+width] = top_right_bottom_left[i]
                else:
                    self._cube[face.value][self.N-layer:self.N-layer+width, :] = np.flip(top_right_bottom_left[i], axis=1)

    def __turn_back(self, dist: int, layer: int = 1, width: int = 1):
        """ 
        Turns the back side of the cube 
        Arguments:
            dist: number of clockwise turns
            layer: layer number from top side for the bottom-most layer 
            width: number of layers to turn, going up from the layer
        
          w  ->  r  ->  y  ->  o
         0 1    3 6    0 1    2 5
         3 4 -> 4 7 -> 3 4 -> 1 4
         6 7    5 8    6 7    0 3
        """
        assert layer - width >= 0, "Invalid turn: Too wide given the layer"
        assert layer <= self.N, "Invalid turn: Turning more than entire cube" 
        dist %= 4
        if layer - width == 0:
            self.__rotate(Face.BACK, dist)
        if layer == self.N:
            self.__rotate(Face.FRONT, -dist)
        for _ in range(dist):
            top_right_bottom_left = [
                np.transpose(
                    self._cube[f.value][:, layer-width:layer].copy()
                        if f == Face.LEFT else 
                        np.flip(self._cube[f.value][:, self.N-layer:self.N-layer+width].copy(), axis=1)
                        if f == Face.RIGHT else 
                        np.flip(self._cube[f.value][layer-width:layer, :].copy(), axis=1),
                    (1, 0)
                )
                for f in [Face.TOP, Face.RIGHT, Face.BOTTOM, Face.LEFT]
            ]
            for i, face in enumerate([Face.LEFT, Face.TOP, Face.RIGHT, Face.BOTTOM]):
                if face == Face.LEFT:
                    self._cube[face.value][:, layer-width:layer] = top_right_bottom_left[i]
                elif face == Face.RIGHT:
                    self._cube[face.value][:, self.N-layer:self.N-layer+width] = np.flip(top_right_bottom_left[i], axis=1)
                else:
                    self._cube[face.value][layer-width:layer, :] = top_right_bottom_left[i]

    def __rotate(self, face: Face, turns: int = 1):
        """
        Arguments:
            face: the color to rotate
            turns: the number of turns to execute
        """
        self._cube[face.value] = np.rot90(
                self._cube[face.value], -(turns % 4)
            )

    def get_3x3(self) -> Cube3x3:
        """
        Gets the 3x3 form of the cube.
        Throws an error if:  
            the cube cannot be simplified
        """

        output = Cube3x3()
        mod_cube = output.get_matrix()

        # fill edges and centers with filler
        if self.N == 2:
            ref_cube_matrix = Cube3x3().get_matrix()
            for face in list(Face):
                for corner in [(0, 0), (0, -1), (-1, 0), (-1, -1)]:
                    mod_cube[face.value][*corner] = self._cube[face.value][*corner]
                for edge in [(0, 1), (1, 0), (1, -1), (-1, 1)]:
                    mod_cube[face.value][*edge] = Color.WHITE
                mod_cube[face.value][1, 1] = ref_cube_matrix[face.value][1, 1]
            return output

        def get_scalar(x: np.ndarray) -> Color:
            assert x.shape == (1,), "Cube could not be converted to a 3x3"
            return x[0]

        for i in range(6):
            current_side = self._cube[i]
            for corner in [(0, -1), (0, 0), (-1, 0), (-1, -1)]:
                mod_cube[i][*corner] = current_side[*corner]
            for edge_y, edge_x in [(0, 1), (1, 0), (1, -1), (-1, 1)]:
                mod_cube[i][edge_y, edge_x] = get_scalar(np.unique(current_side[1:-1, edge_x] 
                                                                   if edge_y == 1 else 
                                                                   current_side[edge_y, 1:-1]))
            mod_cube[i][1, 1] = get_scalar(np.unique(current_side[1:-1, 1:-1]))
        return output

    def get_rotation_to(self, other: Cube) -> list[str]:
        """
        Determines the ['x', 'y', 'z'] movements to turn the self
        into the given cube (i.e. cube rotations rather than turns)
        Assumes that the rotation is possible in the first place.
        """

        rotations = []
        target_corner_faces = [Face.TOP, Face.LEFT, Face.FRONT]

        # determine top left corner for the original
        top_left_corner = other.get_3x3().get_corner_between(*target_corner_faces)
        target_colors = set(top_left_corner["c2f"])

        # convert cube to a 3x3
        self_copy = self.get_3x3()
        for z in [Face.FRONT, Face.BACK]:
            for y in [Face.TOP, Face.BOTTOM]:
                for x in [Face.LEFT, Face.RIGHT]:
                    if target_colors == set((c := self_copy.get_corner_between(x, y, z))["c2f"]):
                        corner = c

        # rotate the corner to bring to proper place 
        if Face.BACK in corner["f2c"]:
            self_copy.parse('y2', output_movelist=rotations)
        if (Face.LEFT in corner["f2c"]) == (Face.BACK in corner["f2c"]):
            self_copy.parse('y', output_movelist=rotations)           # corner is now in the left two spots
        if Face.BOTTOM in corner["f2c"]:
            self_copy.parse('x', output_movelist=rotations)           # corner is now in the top left corner
        assert all(color in self_copy.get_corner_between(*target_corner_faces)["c2f"] for color in target_colors)

        # determine correct way of orienting items
        match self_copy.get_corner_between(*target_corner_faces)["c2f"][top_left_corner["f2c"][Face.FRONT]]:
            case Face.FRONT: pass
            case Face.TOP: self_copy.parse("y x'", output_movelist=rotations)
            case Face.LEFT: self_copy.parse("x y'", output_movelist=rotations)
            case _: raise Exception("Something went wrong.")

        assert self_copy.get_corner_between(*target_corner_faces) == top_left_corner
        return rotations

class Cube3x3(Cube):
    """
    Class for 3x3 cubes with 3x3-exclusive methods.
    Made so that non-3x3's don't call methods that
    are made for 3x3's
    """

    def __init__(self, scramble: Optional[list[np.ndarray]] = None) -> None:
        super().__init__(side_length=3, scramble=scramble)

    def get_center_at(self, a: Face) -> dict[str, Union[dict[Face, Color], dict[Color, Face]]]:
        return { 
            "c2f": (d:={self._cube[a.value][1, 1]: a}),
            "f2c": {v:k for k, v in d.items()}
        }

    def get_edge_between(self, a: Face, b: Face) -> dict[str, Union[dict[Face, Color], dict[Color, Face]]]:
        """
        Gets the edge between two faces.
        """
        assert not any([
            all([i in pair for i in [a, b]])
            for pair in Cube.FACE_PAIRS.values()
        ]), "Illegal edge combination"
        
        if all([i not in [Face.TOP, Face.BOTTOM] for i in [a, b]]):
            colors_to_faces = {
                self._cube[a.value][1, 0 if (b.value - a.value) % 4 == 1 else 2]: a,
                self._cube[b.value][1, 2 if (b.value - a.value) % 4 == 1 else 0]: b
            }
        else:
            top_face = a if a in [Face.TOP, Face.BOTTOM] else b
            side_face = b if top_face == a else a
            top_face_indeces = [(2, 1), (1, 0), (0, 1), (1, 2)][side_face.value]
            side_face_indeces = (0, 1) if top_face == Face.TOP else (2, 1)
            colors_to_faces = {
                self._cube[top_face.value][*top_face_indeces]: top_face,
                self._cube[side_face.value][*side_face_indeces]: side_face
            }
            
        return { 
            "c2f": colors_to_faces,
            "f2c": {v:k for k, v in colors_to_faces.items()}
        }


    def get_corner_between(self, a: Face, b: Face, c: Face) -> dict[str, Union[dict[Face, Color], dict[Color, Face]]]:
        """
        Gets the corner between two faces.
        """

        [x_face, y_face, z_face] = [None] * 3
        for k, v in Cube.FACE_PAIRS.items():
            face = filter(lambda x: x in v, [a, b, c]).__next__()
            if k == 'x':
                x_face = face
            elif k == 'y':
                y_face = face
            else:
                z_face = face
        assert all([x_face, y_face, z_face]), "Illegal corner combination"
        possible_y_corners = [
            {(2, 0), (2, 2)},
            {(0, 0), (2, 0)},
            {(0, 0), (0, 2)},
            {(0, 2), (2, 2)}
        ]
        y_face_indeces = (possible_y_corners[z_face.value] & possible_y_corners[x_face.value]).pop()
        
        xz_face_y_value = 0 if y_face == Face.TOP else 2
        x_face_indeces = (xz_face_y_value, 0 if (z_face.value - x_face.value) % 4 == 1 else 2)
        z_face_indeces = (xz_face_y_value, 2 if (z_face.value - x_face.value) % 4 == 1 else 0)
        colors_to_faces = {
            self._cube[y_face.value][*y_face_indeces]: y_face,
            self._cube[x_face.value][*x_face_indeces]: x_face,
            self._cube[z_face.value][*z_face_indeces]: z_face
        }

        return {
            "c2f": colors_to_faces,
            "f2c": {v: k for k, v in colors_to_faces.items()}
        }

def demo():
    cube = Cube.parse_args()
    print(cube)

if __name__ == "__main__":
    demo()
