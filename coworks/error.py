class CwsError(Exception):
    def __init__(self, message):
        self.msg = message
