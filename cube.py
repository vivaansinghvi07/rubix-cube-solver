from enum import Enum
import re
from sys import argv
from time import perf_counter
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
    """

    def __init__(self, side_length: int = 3, scramble: list[np.ndarray] = None):
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

    @property
    def cube(self):
        return self.__cube.copy()

    def parse(self, moves: str):
        move_list = re.split(r"(?=[A-Z])", moves)
        for m in filter(lambda x: bool(x), move_list):
            if len(m) == 1:
                dist = 1
            elif m[1] == '2':
                dist = 2
            elif m[1] == "'":
                dist = -1
            self.turn(m[0], dist, 1)
        
    def turn(self, move: str, dist: int, layers: int = 1):
        """ Turns the cube depending on the given measure. """
        assert move in ['R', 'L', 'F', 'U', 'D', 'B']
        move_map = {
            'R': self.turn_right,
            'L': self.turn_left,
            'U': self.turn_up,
            'D': self.turn_down
        }
        move_map[move](dist, layers)
        
    def turn_right(self, dist: int, layer: int = 1, width: int = 1):
        """ 
        Turns the right side of the cube.
        Arguments:
            dist: number of clockwise turns
            layer: layer number from right side for the left-most layer 
            width: number of layers to turn, going right from the layer

         g  ->  w  ->  b  ->  y
        0 3    0 3    5 2    2 5 
        1 4 -> 1 4 -> 4 1 -> 1 4
        2 5    2 5    3 0    0 3
        """
        dist %= 4
        if layer - width:
            self.__rotate(Face.RED, dist)
        for _ in range(dist):
            front_top_back_down = [
                self.__cube[c.value][:, self.N-layer:self.N-layer+width].copy()
                if c != Face.BLUE else 
                np.flip(self.__cube[c.value][:, layer-width:layer].copy(), axis=1) 
                for c in [Face.GREEN, Face.WHITE, Face.BLUE, Face.YELLOW]
            ]
            for i, face in enumerate([Face.WHITE, Face.BLUE, Face.YELLOW, Face.GREEN]):
                if i % 2:
                    front_top_back_down[i] = np.flip(front_top_back_down[i], axis=0)
                if face == Face.BLUE:
                    self.__cube[face.value][:, layer-width:layer] = np.flip(front_top_back_down[i], axis=1)
                else:
                    self.__cube[face.value][:, self.N-layer:self.N-layer+width] = front_top_back_down[i]
    
    def turn_left(self, dist: int, layer: int = 1, width: int = 1):
        """ 
        Turns the left side of the cube.
        Arguments:
            dist: number of clockwise turns
            layer: layer number from left side for the right-most layer 
            width: number of layers to turn, going left from the layer

         g  ->  y  ->  b  ->  w
        0 3    2 5    5 2    0 3 
        1 4 -> 1 4 -> 4 1 -> 1 4
        2 5    0 3    3 0    2 5
        """
        dist %= 4
        if layer - width == 0:
            self.__rotate(Face.ORANGE, dist)
        for _ in range(dist):
            front_top_back_down = [
                self.__cube[c.value][:, layer-width:layer].copy()
                if c != Face.BLUE else 
                np.flip(self.__cube[c.value][:, self.N-layer:self.N-layer+width].copy(), axis=1) 
                for c in [Face.GREEN, Face.WHITE, Face.BLUE, Face.YELLOW]
            ]
            for i, face in enumerate([Face.YELLOW, Face.GREEN, Face.WHITE, Face.BLUE]):
                if i % 2 == 0:
                    front_top_back_down[i] = np.flip(front_top_back_down[i], axis=0)
                if face == Face.BLUE:
                    self.__cube[face.value][:, self.N-layer:self.N-layer+width] = np.flip(front_top_back_down[i], axis=1)
                else:
                    self.__cube[face.value][:, layer-width:layer] = front_top_back_down[i]

    def turn_up(self, dist: int, layers: int = 1):
        """ Turns the top side of the cube """
        assert layers <= self.N
        dist %= 4
        self.__rotate(Face.WHITE, dist)
        for _ in range(dist):
            front_right_back_left = [
                self.__cube[c.value][0:layers, :].copy()
                for c in [Face.GREEN, Face.ORANGE, Face.BLUE, Face.RED]
            ]
            for i, face in enumerate([Face.ORANGE, Face.BLUE, Face.RED, Face.GREEN]):
                self.__cube[face.value][0:layers, :] = front_right_back_left[i]

    def turn_down(self, dist: int, layers: int = 1):
        """ Turns the down side of the cube """
        assert layers <= self.N
        dist %= 4
        self.__rotate(Face.YELLOW, -dist)
        for _ in range(dist):
            front_right_back_left = [
                self.__cube[c.value][self.N-layers:self.N, :].copy()
                for c in [Face.GREEN, Face.ORANGE, Face.BLUE, Face.RED]
            ]
            for i, face in enumerate([Face.RED, Face.GREEN, Face.ORANGE, Face.BLUE]):
                self.__cube[face.value][self.N-layers:self.N, :] = front_right_back_left[i]

    def turn_front(self, dist: int, layers: int = 1):
        """ Turns the front side of the cube """
        assert layers <= self.N
        dist %= 4
        self.__rotate(Face.GREEN)
        for _ in range(dist):
            pass     

    def __rotate(self, face: Face, turns: int = 1):
        """
        Arguments:
            face: the color to rotate
        """

        turns %= 4
        self.__cube[face.value] = np.rot90(
                self.__cube[face.value], -turns
            )


if __name__ == "__main__":
    a = Cube(side_length=5)
    start = perf_counter()
    a.turn_right(1, 2, 1)
    print(a)
    a.turn_right(1, 2, 2)
    print(a)
