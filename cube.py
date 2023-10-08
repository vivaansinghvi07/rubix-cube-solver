from __future__ import annotations
import re
import sys
import json
import random

import numpy as np
from pynterface import Background

from enums import Color, Face
from utils import get_move

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
    
    @staticmethod
    def from_commandline() -> Cube:
        side_length = int(sys.argv[1])
        if side_length == 3:
            cube = Cube3x3()
        else:
            cube = Cube(side_length)
        cube.parse(sys.argv[2])
        return cube

    @staticmethod
    def from_random_scramble() -> Cube:
        with open("./example_scrambles.json", "r") as f:
            scrambles = json.load(f)["scrambles"]
        selected = scrambles[random.randint(0, len(scrambles)-1)]
        if selected["size"] == 3:
            cube = Cube3x3()
        else:
            cube = Cube(selected["size"])
        cube.parse(selected["moves"], False)
        return cube

    def __init__(self, side_length: int = 3, scramble: list[np.ndarray] | None = None):
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

    def get_cube(self):
        """ Returns the mutable array of the cube """
        return self._cube

    def parse(self, moves: str, no_spaces: bool = False, output_movelist: list[str] | None = None):
        """
        Parses a list of moves given as a string with each move seperated by a space.
        The no_spaces argument can be passed to parse without considering spaces,
        but requires the cube to be 5x5x5 or less.
        """
        if no_spaces:
            assert self.N <= 5
            move_list = re.split(r"(?=[A-Z])", moves)
        else:
            move_list = moves.split()
        for m in filter(lambda x: bool(x.strip()), move_list):
            dist = width = layer = 1
            letter = re.search(r'[rfdublRFDUBLxyz]', m).group()
            if len(m) != 1:
                if m[-1] == '2':
                    dist = 2
                elif m[-1] == "'":
                    dist = -1
                if (nums:=re.match(r'[1-9][0-9]*', m)):
                    layer = int(nums.group())
                elif 'w' in m:
                    layer = 2
                if 'w' in m: 
                    width = layer
            if letter.islower():
                layer = width = 2
            if letter in 'xyz':
                letter = {
                    'x': 'R', 'y' : 'U', 'z': 'F' 
                }[letter]
                match m[-1]:
                    case "'": dist = -1
                    case "2": dist = 2
                    case _: dist = 1
                width = layer = self.N
            self.turn(letter.upper(), dist, layer, width, output_movelist)
        
    def turn(self, move: str, dist: int, layer: int = 1, width: int = 1, movelist: list[str] | None = None) -> None:
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
            movelist.extend(get_move(move, dist, layer, width))
        
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

    def get_3x3(self) -> Cube:
        """
        Gets the 3x3 form of the cube.
        Throws an error if: 
            the cube is smaller than a 3x3 
            the cube cannot be simplified
        """
        assert self.N > 2, "2x2 cannot be converted to 3x3"

        def get_scalar(x: np.ndarray) -> Color:
            assert x.shape == (1,), "Cube could not be converted to a 3x3"
            return x[0]

        output = Cube()
        mod_cube = output.get_cube()
        for i in range(6):
            current_side = self._cube[i]
            for corner_x, corner_y in [(0, -1), (0, 0), (-1, 0), (-1, -1)]:
                mod_cube[i][corner_y, corner_x] = current_side[corner_y, corner_x]
            for edge_y, edge_x in [(0, 1), (1, 0), (1, -1), (-1, 1)]:
                mod_cube[i][edge_y, edge_x] = get_scalar(np.unique(current_side[1:-1, edge_x] 
                                                                   if edge_y == 1 else 
                                                                   current_side[edge_y, 1:-1]))
            mod_cube[i][1, 1] = get_scalar(np.unique(current_side[1:-1, 1:-1]))
        return output

class Cube3x3(Cube):
    """
    Class for 3x3 cubes with 3x3-exclusive methods.
    Made so that non-3x3's don't call methods that
    are made for 3x3's
    """

    def __init__(self) -> None:
        super().__init__(side_length=3)

    def get_center_at(self, a: Face) -> dict[str, dict[Face, Color] | dict[Color, Face]]:
        return { 
            "c2f": (d:={self._cube[a.value][1, 1]: a}),
            "f2c": {v:k for k, v in d.items()}
        }

    def get_edge_between(self, a: Face, b: Face) -> dict[str, dict[Face, Color] | dict[Color, Face]]:
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


    def get_corner_between(self, a: Face, b: Face, c: Face) -> dict[str, dict[Face, Color] | dict[Color, Face]]:
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

if __name__ == "__main__":
    if len(sys.argv) > 1:
        a = Cube.from_commandline()
        print(a)
    else:
        a = Cube.from_random_scramble()
        print(a)

