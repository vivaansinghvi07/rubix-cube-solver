from __future__ import annotations
from enum import Enum 

class Face(Enum):
    """ 
    Enums for faces, representing the different sides of the cube.
    These numbers must be as they are, changing it will break certain
    Cube3x3 methods, as they depend on the order
    """
    FRONT = 0
    LEFT = 1
    BACK = 2
    RIGHT = 3
    TOP = 4
    BOTTOM = 5

    def __lt__(self, other: Face):
        return self.value < other.value

class Color(Enum):
    """ 
    Enums for colors, preferrably set to the values that correspond
    to each face in a standard 3x3 (green front, orange left, white top).
    """
    GREEN = 0
    ORANGE = 1
    BLUE = 2
    RED = 3
    WHITE = 4
    YELLOW = 5

    def __lt__(self, other: Color):
        return self.value < other.value
