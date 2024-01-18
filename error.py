class Slide_Error(Exception):
    def __init__(self, message):
        super().__init__(message)

class Epr_Error(Exception):
    def __init__(self, message):
        super().__init__(message)