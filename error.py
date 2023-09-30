class ImpossibleScrambleException(Exception):
    """ Exception raised when encountering parity or an impossible solve """
    def __init__(self, message: str) -> None:
        self.message = message

class InvalidTurnException(Exception):
    """ Exception raised when the turn cannot be made """
    def __init__(self, message: str) -> None:
        self.message = message
