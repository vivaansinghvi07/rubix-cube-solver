from __future__ import annotations
from enum import Enum 

class Face(Enum):
    """ 
    Enums for faces, representing the different sides of the cube.
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
    Enums for colors.
    """
    GREEN = 0
    ORANGE = 1
    BLUE = 2
    RED = 3
    WHITE = 4
    YELLOW = 5

    def __lt__(self, other: Color):
        return self.value < other.value
