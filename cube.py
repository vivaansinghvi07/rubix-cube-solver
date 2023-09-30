from __future__ import annotations
from enum import Enum
import re
from sys import argv
import numpy as np
from pynterface import Background

class Face(Enum):
    """ 
    Enums for colors.
    These also apply for positions, so if the cube is 
    rotated, GREEN will still represent the front.
    """
    GREEN = 0
    ORANGE = 1
    BLUE = 2
    RED = 3
    WHITE = 4
    YELLOW = 5

    def __lt__(self, other: Face):
        return self.value < other.value

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

    def __init__(self, side_length: int = 3, scramble: list[np.ndarray] | None = None):
        if scramble is None:
            self.__cube = [
                np.array([[c] * side_length for _ in range(side_length)])
                for c in list(Face)
            ]
        else: 
            self.__cube = scramble
        self.N = side_length

    def __str__(self):

        def get_ansii(color: Face) -> str:
            color_name = str(color).split('.')[-1]
            match color_name:
                case "ORANGE":
                    return Background.RGB((255, 165, 0))
                case other: 
                    return eval(f"Background.{other}_BRIGHT")

        output = "\n "
        top_face = self.__cube[Face.WHITE.value]
        for i in range(self.N):
            output += '  ' * self.N
            for j in range(self.N):
                output += get_ansii(top_face[i, j]) + '  '
            output += f"{Background.RESET_BACKGROUND}\n "
            
        for i in range(self.N):
            for color in [Face.ORANGE, Face.GREEN, Face.RED, Face.BLUE]:
                for j in range(self.N): 
                    output += get_ansii(self.__cube[color.value][i][j]) + '  '
            output += f"{Background.RESET_BACKGROUND}\n "
        
        bottom_face = self.__cube[Face.YELLOW.value]
        for i in range(self.N - 1, -1, -1):
            output += '  ' * self.N
            for j in range(self.N):
                output += get_ansii(bottom_face[i, j]) + '  '
            output += f"{Background.RESET_BACKGROUND}\n "
        
        return output

    def get_cube(self):
        """ Returns the mutable array of the cube """
        return self.__cube

    def parse(self, moves: str, no_spaces: bool = True):
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
            letter = re.search(r'[A-Za-z]', m).group()
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
                layer = 2
            self.turn(letter.upper(), dist, layer, width)
        
    def turn(self, move: str, dist: int, layer: int = 1, width: int = 1) -> None:
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
            self.__rotate(Face.RED, dist)
        if layer == self.N:
            self.__rotate(Face.ORANGE, -dist)
        for _ in range(dist):
            front_top_back_down = [
                np.flip(self.__cube[c.value][:, layer-width:layer].copy(), axis=1) 
                if c == Face.BLUE else 
                self.__cube[c.value][:, self.N-layer:self.N-layer+width].copy()
                for c in [Face.GREEN, Face.WHITE, Face.BLUE, Face.YELLOW]
            ]
            for i, face in enumerate([Face.WHITE, Face.BLUE, Face.YELLOW, Face.GREEN]):
                if i % 2:
                    front_top_back_down[i] = np.flip(front_top_back_down[i], axis=0)
                if face == Face.BLUE:
                    self.__cube[face.value][:, layer-width:layer] = np.flip(front_top_back_down[i], axis=1)
                else:
                    self.__cube[face.value][:, self.N-layer:self.N-layer+width] = front_top_back_down[i]
    
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
            self.__rotate(Face.ORANGE, dist)
        if layer == self.N:
            self.__rotate(Face.RED, -dist)
        for _ in range(dist):
            front_top_back_down = [
                np.flip(self.__cube[c.value][:, self.N-layer:self.N-layer+width].copy(), axis=1) 
                if c == Face.BLUE else 
                self.__cube[c.value][:, layer-width:layer].copy()
                for c in [Face.GREEN, Face.WHITE, Face.BLUE, Face.YELLOW]
            ]
            for i, face in enumerate([Face.YELLOW, Face.GREEN, Face.WHITE, Face.BLUE]):
                if i % 2 == 0:
                    front_top_back_down[i] = np.flip(front_top_back_down[i], axis=0)
                if face == Face.BLUE:
                    self.__cube[face.value][:, self.N-layer:self.N-layer+width] = np.flip(front_top_back_down[i], axis=1)
                else:
                    self.__cube[face.value][:, layer-width:layer] = front_top_back_down[i]

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
            self.__rotate(Face.WHITE, dist)
        if layer == 0:
            self.__rotate(Face.YELLOW, dist)
        for _ in range(dist):
            front_right_back_left = [
                self.__cube[c.value][layer-width:layer, :].copy()
                for c in [Face.GREEN, Face.ORANGE, Face.BLUE, Face.RED]
            ]
            for i, face in enumerate([Face.ORANGE, Face.BLUE, Face.RED, Face.GREEN]):
                self.__cube[face.value][layer-width:layer, :] = front_right_back_left[i]

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
            self.__rotate(Face.YELLOW, -dist)
        if layer == 0:
            self.__rotate(Face.WHITE, -dist)
        for _ in range(dist):
            front_right_back_left = [
                self.__cube[c.value][self.N-layer:self.N-layer+width, :].copy()
                for c in [Face.GREEN, Face.ORANGE, Face.BLUE, Face.RED]
            ]
            for i, face in enumerate([Face.RED, Face.GREEN, Face.ORANGE, Face.BLUE]):
                self.__cube[face.value][self.N-layer:self.N-layer+width, :] = front_right_back_left[i]

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
            self.__rotate(Face.GREEN, dist)
        if layer == 0:
            self.__rotate(Face.BLUE, -dist)
        for _ in range(dist):
            top_right_bottom_left = [
                np.transpose(
                    self.__cube[c.value][:, layer-width:layer].copy()
                        if c == Face.RED else 
                        self.__cube[c.value][:, self.N-layer:self.N-layer+width].copy()
                        if c == Face.ORANGE else 
                        self.__cube[c.value][self.N-layer:self.N-layer+width, :].copy(),
                    (1, 0)
                )
                for c in [Face.WHITE, Face.RED, Face.YELLOW, Face.ORANGE]
            ]
            for i, face in enumerate([Face.RED, Face.YELLOW, Face.ORANGE, Face.WHITE]):
                if face == Face.RED:
                    self.__cube[face.value][:, layer-width:layer] = top_right_bottom_left[i]
                elif face == Face.ORANGE:
                    self.__cube[face.value][:, self.N-layer:self.N-layer+width] = top_right_bottom_left[i]
                else:
                    self.__cube[face.value][self.N-layer:self.N-layer+width, :] = np.flip(top_right_bottom_left[i], axis=1)

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
            self.__rotate(Face.BLUE, dist)
        if layer == 0:
            self.__rotate(Face.GREEN, -dist)
        for _ in range(dist):
            top_right_bottom_left = [
                np.transpose(
                    self.__cube[c.value][:, layer-width:layer].copy()
                        if c == Face.ORANGE else 
                        self.__cube[c.value][:, self.N-layer:self.N-layer+width].copy()
                        if c == Face.RED else 
                        np.flip(self.__cube[c.value][layer-width:layer, :].copy(), axis=1),
                    (1, 0)
                )
                for c in [Face.WHITE, Face.RED, Face.YELLOW, Face.ORANGE]
            ]
            for i, face in enumerate([Face.ORANGE, Face.WHITE, Face.RED, Face.YELLOW]):
                if face == Face.ORANGE:
                    self.__cube[face.value][:, layer-width:layer] = top_right_bottom_left[i]
                elif face == Face.RED:
                    self.__cube[face.value][:, self.N-layer:self.N-layer+width] = top_right_bottom_left[i]
                else:
                    self.__cube[face.value][layer-width:layer, :] = top_right_bottom_left[i]

    def __rotate(self, face: Face, turns: int = 1):
        """
        Arguments:
            face: the color to rotate
            turns: the number of turns to execute
        """
        self.__cube[face.value] = np.rot90(
                self.__cube[face.value], -(turns % 4)
            )

    def get_3x3(self) -> Cube:
        """
        Gets the 3x3 form of the cube.
        Throws an error if: 
            the cube is smaller than a 3x3 
            the cube cannot be simplified
        """
        assert self.N > 2, "2x2 cannot be converted to 3x3"

        def get_scalar(x: np.ndarray) -> Face:
            assert x.shape == (1,), "Cube could not be converted to a 3x3"
            return x[0]

        output = Cube()
        mod_cube = output.get_cube()
        for i in range(6):
            current_side = self.__cube[i]
            for corner_x, corner_y in [(0, -1), (0, 0), (-1, 0), (-1, -1)]:
                mod_cube[i][corner_y, corner_x] = current_side[corner_y, corner_x]
            for edge_y, edge_x in [(0, 1), (1, 0), (1, -1), (-1, 1)]:
                mod_cube[i][edge_y, edge_x] = get_scalar(np.unique(current_side[1:-1, edge_x] 
                                                                   if edge_y == 1 else 
                                                                   current_side[edge_y, 1:-1]))
            mod_cube[i][1, 1] = get_scalar(np.unique(current_side[1:-1, 1:-1]))
        return output

if __name__ == "__main__":
    a = Cube(side_length=int(argv[1]))
    a.parse(argv[2], False)
    print(a)
