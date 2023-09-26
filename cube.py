from enum import Enum
import numpy as np
from pynterface import Background

class Color(Enum):
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
    Applies for each face on the side.
    """

    def __init__(self, side_length: int = 3, scramble: list[int] = None):
        if scramble is None:
            self.__cube = [
                        np.array([[c] * side_length for _ in range(side_length)])
                        for c in list(Color)
                    ]
        else: 
            self.__cube = scramble
        self.__side_length = side_length

    def __str__(self):

        def get_ansii(color: Color):
            color_name = str(color).split('.')[-1]
            if color_name == "ORANGE":
                color_name = "PURPLE"
            return eval(f"Background.{color_name}_BRIGHT")

        output = "\n"
        top_face = self.__cube[Color.WHITE.value]
        for i in range(self.__side_length):
            output += '  ' * self.__side_length
            for j in range(self.__side_length):
                output += get_ansii(top_face[i, j]) + '  '
            output += f"{Background.RESET_BACKGROUND}\n"
            
        for i in range(self.__side_length):
            for color in [Color.ORANGE, Color.GREEN, Color.RED, Color.BLUE]:
                for j in range(self.__side_length): 
                    output += get_ansii(self.__cube[color.value][i][j]) + '  '
            output += f"{Background.RESET_BACKGROUND}\n"
        
        bottom_face = self.__cube[Color.YELLOW.value]
        for i in range(self.__side_length):
            output += '  ' * self.__side_length
            for j in range(self.__side_length):
                output += get_ansii(bottom_face[i, j]) + '  '
            output += f"{Background.RESET_BACKGROUND}\n"
        
        return output

    @property
    def cube(self):
        return self.__cube.copy()

    def turn(move: str, dist: int, layers: int = 1):
        """ Turns the cube depending on the given measure. """
        assert move.upper() in ['R', 'L', 'F', 'U', 'D', 'B']

    def turn_right(self, dist: int, layers: int):
        """ Turns the right side of the cube """
        assert layers >= self.__side_length
        dist %= 4
        for _ in range(dist):
            self.__cube

    def __rotate(self, face: Color, turns: int = 1):
        """
        Arguments:
            face: the color to rotate
        """

        turns %= 4
        self.__cube[face.value] = np.rot90(
                self.__cube[face.value], -turns
            )


if __name__ == "__main__":
    a = Cube(side_length=4)
    print(a)
